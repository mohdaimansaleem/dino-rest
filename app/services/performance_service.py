"""
Performance Optimization Service
Provides caching, query optimization, and performance monitoring
"""
from typing import Dict, Any, List, Optional, Callable
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import asyncio
import time
import json
from collections import defaultdict

from app.core.logging_config import get_logger
from app.core.dependency_injection import get_repository_manager

logger = get_logger(__name__)


class PerformanceService:
    """Service for performance optimization and monitoring"""
    
    def __init__(self):
        self._query_cache = {}
        self._cache_ttl = {}
        self._performance_metrics = defaultdict(list)
        self._slow_query_threshold = 1.0  # 1 second
        self._cache_duration = timedelta(minutes=5)
    
    def cache_query_result(self, cache_key: str, result: Any, ttl_minutes: int = 5) -> None:
        """Cache query result with TTL"""
        self._query_cache[cache_key] = result
        self._cache_ttl[cache_key] = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        logger.debug(f"Cached query result: {cache_key}")
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid"""
        if cache_key not in self._query_cache:
            return None
        
        if datetime.utcnow() > self._cache_ttl.get(cache_key, datetime.min):
            # Cache expired
            self._query_cache.pop(cache_key, None)
            self._cache_ttl.pop(cache_key, None)
            return None
        
        logger.debug(f"Cache hit: {cache_key}")
        return self._query_cache[cache_key]
    
    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries matching pattern"""
        if pattern:
            keys_to_remove = [key for key in self._query_cache.keys() if pattern in key]
            for key in keys_to_remove:
                self._query_cache.pop(key, None)
                self._cache_ttl.pop(key, None)
        else:
            self._query_cache.clear()
            self._cache_ttl.clear()
        
        logger.info(f"Cache cleared: {pattern or 'all'}")
    
    def monitor_query_performance(self, operation: str):
        """Decorator to monitor query performance"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Record performance metrics
                    self._performance_metrics[operation].append({
                        'execution_time': execution_time,
                        'timestamp': datetime.utcnow(),
                        'success': True
                    })
                    
                    # Log slow queries
                    if execution_time > self._slow_query_threshold:
                        logger.warning(f"Slow query detected: {operation} took {execution_time:.2f}s")
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._performance_metrics[operation].append({
                        'execution_time': execution_time,
                        'timestamp': datetime.utcnow(),
                        'success': False,
                        'error': str(e)
                    })
                    raise
            
            return wrapper
        return decorator
    
    async def get_popular_menu_items(self, venue_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular menu items with caching"""
        cache_key = f"popular_items:{venue_id}:{limit}"
        
        # Check cache first
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Query from database
        repo_manager = get_repository_manager()
        order_repo = repo_manager.get_repository('order')
        
        # Get recent orders (last 30 days)
        start_date = datetime.utcnow() - timedelta(days=30)
        orders = await order_repo.query([
            ('venue_id', '==', venue_id),
            ('created_at', '>=', start_date),
            ('status', 'in', ['served', 'delivered'])
        ])
        
        # Count item popularity
        item_counts = defaultdict(int)
        item_names = {}
        
        for order in orders:
            for item in order.get('items', []):
                item_id = item.get('menu_item_id')
                if item_id:
                    item_counts[item_id] += item.get('quantity', 1)
                    item_names[item_id] = item.get('menu_item_name', 'Unknown')
        
        # Sort by popularity
        popular_items = [
            {
                'menu_item_id': item_id,
                'menu_item_name': item_names[item_id],
                'order_count': count
            }
            for item_id, count in sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        ]
        
        # Cache result
        self.cache_query_result(cache_key, popular_items, ttl_minutes=30)
        
        return popular_items
    
    async def get_venue_analytics_cached(self, venue_id: str, days: int = 7) -> Dict[str, Any]:
        """Get venue analytics with caching"""
        cache_key = f"venue_analytics:{venue_id}:{days}"
        
        # Check cache first
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Query from database
        repo_manager = get_repository_manager()
        order_repo = repo_manager.get_repository('order')
        
        start_date = datetime.utcnow() - timedelta(days=days)
        orders = await order_repo.query([
            ('venue_id', '==', venue_id),
            ('created_at', '>=', start_date)
        ])
        
        # Calculate analytics
        total_orders = len(orders)
        total_revenue = sum(
            order.get('total_amount', 0) 
            for order in orders 
            if order.get('payment_status') == 'paid'
        )
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Status breakdown
        status_counts = defaultdict(int)
        for order in orders:
            status_counts[order.get('status', 'unknown')] += 1
        
        analytics = {
            'venue_id': venue_id,
            'period_days': days,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order_value': average_order_value,
            'status_breakdown': dict(status_counts),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Cache result for 1 hour
        self.cache_query_result(cache_key, analytics, ttl_minutes=60)
        
        return analytics
    
    async def batch_get_menu_items(self, venue_id: str, category_ids: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Efficiently get menu items by categories"""
        cache_key = f"menu_items:{venue_id}:{':'.join(category_ids or [])}"
        
        # Check cache first
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        repo_manager = get_repository_manager()
        menu_item_repo = repo_manager.get_repository('menu_item')
        
        # Build query filters
        filters = [('venue_id', '==', venue_id), ('is_available', '==', True)]
        if category_ids:
            filters.append(('category_id', 'in', category_ids))
        
        # Get items
        items = await menu_item_repo.query(filters)
        
        # Group by category
        items_by_category = defaultdict(list)
        for item in items:
            category_id = item.get('category_id')
            items_by_category[category_id].append(item)
        
        result = dict(items_by_category)
        
        # Cache result
        self.cache_query_result(cache_key, result, ttl_minutes=15)
        
        return result
    
    async def get_active_orders_optimized(self, venue_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get active orders with optimized grouping"""
        cache_key = f"active_orders:{venue_id}"
        
        # Check cache first (short TTL for real-time data)
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        repo_manager = get_repository_manager()
        order_repo = repo_manager.get_repository('order')
        
        # Get active orders
        active_statuses = ['pending', 'confirmed', 'preparing', 'ready']
        orders = await order_repo.query([
            ('venue_id', '==', venue_id),
            ('status', 'in', active_statuses)
        ])
        
        # Group by status
        orders_by_status = defaultdict(list)
        for order in orders:
            status = order.get('status', 'unknown')
            orders_by_status[status].append(order)
        
        result = dict(orders_by_status)
        
        # Cache for 1 minute (real-time data)
        self.cache_query_result(cache_key, result, ttl_minutes=1)
        
        return result
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        metrics_summary = {}
        
        for operation, metrics in self._performance_metrics.items():
            if not metrics:
                continue
            
            execution_times = [m['execution_time'] for m in metrics]
            success_count = sum(1 for m in metrics if m['success'])
            
            metrics_summary[operation] = {
                'total_calls': len(metrics),
                'success_rate': success_count / len(metrics),
                'avg_execution_time': sum(execution_times) / len(execution_times),
                'max_execution_time': max(execution_times),
                'min_execution_time': min(execution_times),
                'slow_queries': sum(1 for t in execution_times if t > self._slow_query_threshold)
            }
        
        return {
            'operations': metrics_summary,
            'cache_stats': {
                'total_entries': len(self._query_cache),
                'valid_entries': sum(
                    1 for key in self._query_cache.keys() 
                    if datetime.utcnow() <= self._cache_ttl.get(key, datetime.min)
                )
            },
            'slow_query_threshold': self._slow_query_threshold
        }
    
    def clear_old_metrics(self, hours: int = 24) -> None:
        """Clear old performance metrics"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        for operation in self._performance_metrics:
            self._performance_metrics[operation] = [
                metric for metric in self._performance_metrics[operation]
                if metric['timestamp'] > cutoff_time
            ]
        
        logger.info(f"Cleared performance metrics older than {hours} hours")


# Singleton instance
performance_service = PerformanceService()


# Convenience functions
def get_performance_service() -> PerformanceService:
    """Get performance service instance"""
    return performance_service


def cached_query(cache_key: str, ttl_minutes: int = 5):
    """Decorator for caching query results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key with args
            full_cache_key = f"{cache_key}:{':'.join(str(arg) for arg in args)}"
            
            # Check cache
            cached_result = performance_service.get_cached_result(full_cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            performance_service.cache_query_result(full_cache_key, result, ttl_minutes)
            
            return result
        
        return wrapper
    return decorator


def monitor_performance(operation: str):
    """Decorator for monitoring performance"""
    return performance_service.monitor_query_performance(operation)