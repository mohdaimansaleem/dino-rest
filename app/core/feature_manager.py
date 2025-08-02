"""
Feature Manager
Manages feature flags and toggles for the application
"""
import os
from typing import Dict, Any, Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class FeatureManager:
    """Manages application feature flags"""
    
    def __init__(self):
        self.features = {
            "database_logging": os.environ.get("ENABLE_DATABASE_LOGGING", "false").lower() == "true",
            "enhanced_logging": os.environ.get("ENABLE_ENHANCED_LOGGING", "true").lower() == "true",
            "debug_mode": os.environ.get("DEBUG", "false").lower() == "true",
            "performance_monitoring": os.environ.get("ENABLE_PERFORMANCE_MONITORING", "false").lower() == "true",
            "audit_logging": os.environ.get("ENABLE_AUDIT_LOGGING", "true").lower() == "true",
        }
        
        logger.info(f"Feature flags initialized: {self.features}")
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature_name, False)
    
    def is_database_logging_enabled(self) -> bool:
        """Check if database logging is enabled"""
        return self.is_enabled("database_logging")
    
    def is_enhanced_logging_enabled(self) -> bool:
        """Check if enhanced logging is enabled"""
        return self.is_enabled("enhanced_logging")
    
    def is_debug_mode_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self.is_enabled("debug_mode")
    
    def is_performance_monitoring_enabled(self) -> bool:
        """Check if performance monitoring is enabled"""
        return self.is_enabled("performance_monitoring")
    
    def is_audit_logging_enabled(self) -> bool:
        """Check if audit logging is enabled"""
        return self.is_enabled("audit_logging")
    
    def enable_feature(self, feature_name: str):
        """Enable a feature"""
        self.features[feature_name] = True
        logger.info(f"Feature enabled: {feature_name}")
    
    def disable_feature(self, feature_name: str):
        """Disable a feature"""
        self.features[feature_name] = False
        logger.info(f"Feature disabled: {feature_name}")
    
    def get_all_features(self) -> Dict[str, bool]:
        """Get all feature flags"""
        return self.features.copy()


# Global instance
_feature_manager = None


def get_feature_manager() -> FeatureManager:
    """Get feature manager instance"""
    global _feature_manager
    if _feature_manager is None:
        _feature_manager = FeatureManager()
    return _feature_manager