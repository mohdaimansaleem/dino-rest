"""
Transaction Service
Handles payment processing, transaction tracking, and financial operations
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from app.database.firestore import FirestoreRepository
from app.models.schemas import (
    Transaction, TransactionCreate, TransactionType, PaymentMethod, 
    PaymentStatus, Order, OrderStatus
)
from app.services.notification_service import get_notification_service


class PaymentGateway(str, Enum):
    """Supported payment gateways"""
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    PAYTM = "paytm"
    PHONEPE = "phonepe"
    GPAY = "gpay"
    CASH = "cash"


class TransactionRepository(FirestoreRepository):
    """Repository for transaction data operations"""
    
    def __init__(self):
        super().__init__("transactions")
    
    async def get_by_order_id(self, order_id: str) -> List[Dict[str, Any]]:
        """Get all transactions for a specific order"""
        return await self.query([("order_id", "==", order_id)], order_by="created_at")
    
    async def get_by_status(self, status: PaymentStatus) -> List[Dict[str, Any]]:
        """Get transactions by status"""
        return await self.query([("status", "==", status)], order_by="created_at")
    
    async def get_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        cafe_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get transactions within a date range"""
        filters = [
            ("created_at", ">=", start_date),
            ("created_at", "<=", end_date)
        ]
        
        if cafe_id:
            filters.append(("cafe_id", "==", cafe_id))
        
        return await self.query(filters, order_by="created_at")
    
    async def get_revenue_summary(
        self, 
        cafe_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get revenue summary for a cafe within date range"""
        transactions = await self.get_by_date_range(start_date, end_date, cafe_id)
        
        total_revenue = 0
        total_transactions = 0
        successful_transactions = 0
        failed_transactions = 0
        refunded_amount = 0
        
        payment_method_breakdown = {}
        daily_revenue = {}
        
        for transaction in transactions:
            total_transactions += 1
            
            if transaction["status"] == PaymentStatus.PAID:
                successful_transactions += 1
                total_revenue += transaction["amount"]
                
                # Payment method breakdown
                method = transaction["payment_method"]
                payment_method_breakdown[method] = payment_method_breakdown.get(method, 0) + transaction["amount"]
                
                # Daily revenue
                date_key = transaction["created_at"].date().isoformat()
                daily_revenue[date_key] = daily_revenue.get(date_key, 0) + transaction["amount"]
                
            elif transaction["status"] == PaymentStatus.FAILED:
                failed_transactions += 1
            elif transaction["status"] == PaymentStatus.REFUNDED:
                refunded_amount += transaction.get("refunded_amount", transaction["amount"])
        
        return {
            "total_revenue": total_revenue,
            "net_revenue": total_revenue - refunded_amount,
            "total_transactions": total_transactions,
            "successful_transactions": successful_transactions,
            "failed_transactions": failed_transactions,
            "success_rate": (successful_transactions / total_transactions * 100) if total_transactions > 0 else 0,
            "refunded_amount": refunded_amount,
            "payment_method_breakdown": payment_method_breakdown,
            "daily_revenue": daily_revenue
        }


class PaymentProcessor:
    """Base class for payment processing"""
    
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway
    
    async def create_payment_intent(
        self, 
        amount: float, 
        currency: str = "INR",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a payment intent with the gateway"""
        # This is a mock implementation
        # In a real system, you would integrate with actual payment gateways
        
        payment_intent = {
            "id": f"pi_{uuid.uuid4().hex[:24]}",
            "amount": amount,
            "currency": currency,
            "status": "requires_payment_method",
            "gateway": self.gateway.value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        return payment_intent
    
    async def confirm_payment(
        self, 
        payment_intent_id: str,
        payment_method: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Confirm a payment with the gateway"""
        # Mock implementation
        # In reality, this would call the actual payment gateway API
        
        import random
        success = random.choice([True, True, True, False])  # 75% success rate for demo
        
        if success:
            return {
                "id": payment_intent_id,
                "status": "succeeded",
                "amount_received": payment_method.get("amount", 0),
                "charges": {
                    "data": [{
                        "id": f"ch_{uuid.uuid4().hex[:24]}",
                        "amount": payment_method.get("amount", 0),
                        "currency": "INR",
                        "status": "succeeded",
                        "payment_method": payment_method.get("type", "card")
                    }]
                }
            }
        else:
            return {
                "id": payment_intent_id,
                "status": "failed",
                "last_payment_error": {
                    "code": "card_declined",
                    "message": "Your card was declined."
                }
            }
    
    async def create_refund(
        self, 
        charge_id: str, 
        amount: Optional[float] = None,
        reason: str = "requested_by_customer"
    ) -> Dict[str, Any]:
        """Create a refund for a charge"""
        # Mock implementation
        return {
            "id": f"re_{uuid.uuid4().hex[:24]}",
            "amount": amount,
            "charge": charge_id,
            "status": "succeeded",
            "reason": reason,
            "created_at": datetime.utcnow().isoformat()
        }


class TransactionService:
    """Service for handling transactions and payments"""
    
    def __init__(self):
        self.transaction_repo = TransactionRepository()
        self.notification_service = get_notification_service()
        
        # Initialize payment processors
        self.payment_processors = {
            PaymentGateway.RAZORPAY: PaymentProcessor(PaymentGateway.RAZORPAY),
            PaymentGateway.STRIPE: PaymentProcessor(PaymentGateway.STRIPE),
            PaymentGateway.PAYTM: PaymentProcessor(PaymentGateway.PAYTM),
            PaymentGateway.PHONEPE: PaymentProcessor(PaymentGateway.PHONEPE),
            PaymentGateway.GPAY: PaymentProcessor(PaymentGateway.GPAY),
            PaymentGateway.CASH: PaymentProcessor(PaymentGateway.CASH)
        }
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:8].upper()
        return f"TXN{timestamp}{random_part}"
    
    async def create_transaction(
        self, 
        transaction_data: TransactionCreate,
        cafe_id: str
    ) -> Transaction:
        """Create a new transaction record"""
        try:
            # Add additional fields
            transaction_dict = transaction_data.dict()
            transaction_dict["cafe_id"] = cafe_id
            transaction_dict["transaction_id"] = self._generate_transaction_id()
            transaction_dict["processed_at"] = None
            transaction_dict["refunded_amount"] = 0.0
            
            # Create transaction in database
            doc_id = await self.transaction_repo.create(transaction_dict)
            
            # Get created transaction
            created_transaction = await self.transaction_repo.get_by_id(doc_id)
            return Transaction(**created_transaction)
            
        except Exception as e:
            print(f"Error creating transaction: {e}")
            raise
    
    async def process_payment(
        self, 
        order: Order,
        payment_method: PaymentMethod,
        payment_gateway: PaymentGateway = PaymentGateway.RAZORPAY,
        payment_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process payment for an order"""
        try:
            # Create payment intent with gateway
            processor = self.payment_processors[payment_gateway]
            
            payment_intent = await processor.create_payment_intent(
                amount=order.total_amount,
                metadata={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "cafe_id": order.cafe_id,
                    "customer_id": order.customer_id
                }
            )
            
            # Create transaction record
            transaction_data = TransactionCreate(
                order_id=order.id,
                amount=order.total_amount,
                transaction_type=TransactionType.PAYMENT,
                payment_method=payment_method,
                payment_gateway=payment_gateway.value,
                gateway_transaction_id=payment_intent["id"],
                gateway_response=payment_intent,
                status=PaymentStatus.PENDING,
                description=f"Payment for order #{order.order_number}"
            )
            
            transaction = await self.create_transaction(transaction_data, order.cafe_id)
            
            # For cash payments, mark as paid immediately
            if payment_method == PaymentMethod.CASH:
                await self.confirm_payment(transaction.id, {
                    "type": "cash",
                    "amount": order.total_amount
                })
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "payment_intent": payment_intent,
                "status": transaction.status
            }
            
        except Exception as e:
            print(f"Error processing payment: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def confirm_payment(
        self, 
        transaction_id: str,
        payment_confirmation: Dict[str, Any]
    ) -> bool:
        """Confirm a payment transaction"""
        try:
            # Get transaction
            transaction_data = await self.transaction_repo.get_by_id(transaction_id)
            if not transaction_data:
                return False
            
            transaction = Transaction(**transaction_data)
            
            # Get payment processor
            gateway = PaymentGateway(transaction.payment_gateway)
            processor = self.payment_processors[gateway]
            
            # Confirm payment with gateway (except for cash)
            if gateway != PaymentGateway.CASH:
                confirmation_result = await processor.confirm_payment(
                    transaction.gateway_transaction_id,
                    payment_confirmation
                )
            else:
                confirmation_result = {
                    "status": "succeeded",
                    "amount_received": transaction.amount
                }
            
            # Update transaction status
            if confirmation_result["status"] == "succeeded":
                await self.transaction_repo.update(transaction_id, {
                    "status": PaymentStatus.PAID,
                    "processed_at": datetime.utcnow(),
                    "gateway_response": confirmation_result
                })
                
                # Send notification
                from app.database.firestore import order_repo
                order_data = await order_repo.get_by_id(transaction.order_id)
                if order_data:
                    order = Order(**order_data)
                    await self.notification_service.notify_payment_received(order)
                
                return True
            else:
                await self.transaction_repo.update(transaction_id, {
                    "status": PaymentStatus.FAILED,
                    "gateway_response": confirmation_result
                })
                return False
                
        except Exception as e:
            print(f"Error confirming payment: {e}")
            return False
    
    async def create_refund(
        self, 
        transaction_id: str,
        refund_amount: Optional[float] = None,
        reason: str = "requested_by_customer"
    ) -> Dict[str, Any]:
        """Create a refund for a transaction"""
        try:
            # Get original transaction
            transaction_data = await self.transaction_repo.get_by_id(transaction_id)
            if not transaction_data:
                return {"success": False, "error": "Transaction not found"}
            
            transaction = Transaction(**transaction_data)
            
            if transaction.status != PaymentStatus.PAID:
                return {"success": False, "error": "Transaction is not in paid status"}
            
            # Calculate refund amount
            if refund_amount is None:
                refund_amount = transaction.amount
            
            if refund_amount > transaction.amount:
                return {"success": False, "error": "Refund amount cannot exceed transaction amount"}
            
            # Process refund with gateway
            gateway = PaymentGateway(transaction.payment_gateway)
            processor = self.payment_processors[gateway]
            
            if gateway != PaymentGateway.CASH:
                refund_result = await processor.create_refund(
                    transaction.gateway_transaction_id,
                    refund_amount,
                    reason
                )
            else:
                refund_result = {
                    "id": f"refund_{uuid.uuid4().hex[:16]}",
                    "amount": refund_amount,
                    "status": "succeeded"
                }
            
            # Create refund transaction
            refund_transaction_data = TransactionCreate(
                order_id=transaction.order_id,
                amount=refund_amount,
                transaction_type=TransactionType.REFUND,
                payment_method=transaction.payment_method,
                payment_gateway=transaction.payment_gateway,
                gateway_transaction_id=refund_result["id"],
                gateway_response=refund_result,
                status=PaymentStatus.REFUNDED,
                description=f"Refund for transaction {transaction_id}: {reason}"
            )
            
            refund_transaction = await self.create_transaction(
                refund_transaction_data, 
                transaction_data["cafe_id"]
            )
            
            # Update original transaction
            new_refunded_amount = transaction.refunded_amount + refund_amount
            new_status = PaymentStatus.REFUNDED if new_refunded_amount >= transaction.amount else PaymentStatus.PARTIALLY_REFUNDED
            
            await self.transaction_repo.update(transaction_id, {
                "refunded_amount": new_refunded_amount,
                "status": new_status
            })
            
            return {
                "success": True,
                "refund_transaction_id": refund_transaction.id,
                "refund_amount": refund_amount,
                "status": new_status
            }
            
        except Exception as e:
            print(f"Error creating refund: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_order_transactions(self, order_id: str) -> List[Transaction]:
        """Get all transactions for an order"""
        transactions_data = await self.transaction_repo.get_by_order_id(order_id)
        return [Transaction(**data) for data in transactions_data]
    
    async def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get a transaction by ID"""
        transaction_data = await self.transaction_repo.get_by_id(transaction_id)
        return Transaction(**transaction_data) if transaction_data else None
    
    async def get_cafe_revenue_summary(
        self, 
        cafe_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get revenue summary for a cafe"""
        return await self.transaction_repo.get_revenue_summary(cafe_id, start_date, end_date)
    
    async def get_pending_transactions(self, cafe_id: Optional[str] = None) -> List[Transaction]:
        """Get all pending transactions"""
        filters = [("status", "==", PaymentStatus.PENDING)]
        if cafe_id:
            filters.append(("cafe_id", "==", cafe_id))
        
        transactions_data = await self.transaction_repo.query(filters, order_by="created_at")
        return [Transaction(**data) for data in transactions_data]
    
    async def reconcile_payments(self, cafe_id: str, date: datetime) -> Dict[str, Any]:
        """Reconcile payments for a specific date"""
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        transactions = await self.transaction_repo.get_by_date_range(start_date, end_date, cafe_id)
        
        reconciliation = {
            "date": date.date().isoformat(),
            "total_transactions": len(transactions),
            "successful_payments": 0,
            "failed_payments": 0,
            "refunds": 0,
            "total_amount": 0,
            "refunded_amount": 0,
            "net_amount": 0,
            "discrepancies": []
        }
        
        for transaction in transactions:
            if transaction["transaction_type"] == TransactionType.PAYMENT:
                if transaction["status"] == PaymentStatus.PAID:
                    reconciliation["successful_payments"] += 1
                    reconciliation["total_amount"] += transaction["amount"]
                elif transaction["status"] == PaymentStatus.FAILED:
                    reconciliation["failed_payments"] += 1
            elif transaction["transaction_type"] == TransactionType.REFUND:
                reconciliation["refunds"] += 1
                reconciliation["refunded_amount"] += transaction["amount"]
        
        reconciliation["net_amount"] = reconciliation["total_amount"] - reconciliation["refunded_amount"]
        
        return reconciliation
    
    async def generate_financial_report(
        self, 
        cafe_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive financial report"""
        revenue_summary = await self.get_cafe_revenue_summary(cafe_id, start_date, end_date)
        
        # Get daily reconciliation
        daily_reports = []
        current_date = start_date
        while current_date <= end_date:
            daily_report = await self.reconcile_payments(cafe_id, current_date)
            daily_reports.append(daily_report)
            current_date += timedelta(days=1)
        
        return {
            "cafe_id": cafe_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": revenue_summary,
            "daily_reports": daily_reports,
            "generated_at": datetime.utcnow().isoformat()
        }


# Global service instance
transaction_service = TransactionService()


def get_transaction_service() -> TransactionService:
    """Get transaction service instance"""
    return transaction_service