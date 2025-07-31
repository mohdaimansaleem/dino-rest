"""
QR Code Encryption Service
Handles encryption and decryption of QR codes for table access
"""
import base64
import json
import os
from cryptography.fernet import Fernet
from typing import Dict, Optional
from fastapi import HTTPException, status

from app.core.logging_config import LoggerMixin


class QREncryptionService(LoggerMixin):
    """Service for QR code encryption and decryption"""
    
    def __init__(self, encryption_key: str = None):
        # Use a fixed key for QR codes (since they need to be permanent)
        try:
            # Get encryption key from parameter, environment, or generate default
            key_string = encryption_key
            if not key_string:
                key_string = os.environ.get('QR_ENCRYPTION_KEY')
            
            if key_string:
                # Ensure the key is exactly 32 bytes
                if len(key_string) < 32:
                    # Pad with zeros if too short
                    key_string = key_string.ljust(32, '0')
                elif len(key_string) > 32:
                    # Truncate if too long
                    key_string = key_string[:32]
                
                # Convert to bytes and create proper Fernet key
                key_bytes = key_string.encode('utf-8')[:32]  # Ensure exactly 32 bytes
                self.encryption_key = base64.urlsafe_b64encode(key_bytes)
            else:
                # Use a default key for development/testing
                default_key_string = "dino-default-qr-encryption-key!!"
                key_bytes = default_key_string.encode('utf-8')[:32]
                self.encryption_key = base64.urlsafe_b64encode(key_bytes)
                self.logger.warning("Using default QR encryption key. Set QR_ENCRYPTION_KEY environment variable for production.")
            
            self.cipher_suite = Fernet(self.encryption_key)
            self.logger.info("QR encryption service initialized successfully")
            
        except Exception as e:
            # Last resort fallback
            self.logger.error(f"Failed to initialize QR encryption: {e}. Using generated key.")
            self.encryption_key = Fernet.generate_key()
            self.cipher_suite = Fernet(self.encryption_key)
    
    def generate_qr_token(self, cafe_id: str, table_number: int) -> str:
        """Generate encrypted QR token for table"""
        try:
            data = {
                "cafe_id": cafe_id,
                "table_number": table_number
            }
            
            # Convert to JSON and encode
            json_data = json.dumps(data).encode()
            
            # Encrypt the data
            encrypted_data = self.cipher_suite.encrypt(json_data)
            
            # Base64 encode for URL safety
            token = base64.urlsafe_b64encode(encrypted_data).decode()
            
            self.log_operation("generate_qr_token", cafe_id=cafe_id, table_number=table_number)
            return token
            
        except Exception as e:
            self.log_error(e, "generate_qr_token", cafe_id=cafe_id, table_number=table_number)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate QR token"
            )
    
    def decrypt_qr_token(self, token: str) -> Dict[str, any]:
        """Decrypt QR token to get cafe and table info"""
        try:
            # Base64 decode
            encrypted_data = base64.urlsafe_b64decode(token.encode())
            
            # Decrypt the data
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            
            # Parse JSON
            data = json.loads(decrypted_data.decode())
            
            self.log_operation("decrypt_qr_token", 
                             cafe_id=data.get("cafe_id"), 
                             table_number=data.get("table_number"))
            return data
            
        except Exception as e:
            self.log_error(e, "decrypt_qr_token", token=token[:20] + "..." if len(token) > 20 else token)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid QR token"
            )
    
    def validate_qr_token(self, token: str) -> bool:
        """Validate if QR token is properly formatted"""
        try:
            data = self.decrypt_qr_token(token)
            return "cafe_id" in data and "table_number" in data
        except:
            return False


# Service instance with robust initialization
def create_qr_encryption_service() -> QREncryptionService:
    """Create QR encryption service with error handling"""
    try:
        return QREncryptionService()
    except Exception as e:
        # If all else fails, create with a hardcoded key
        print(f"Warning: QR encryption service initialization failed: {e}")
        print("Using fallback encryption key")
        return QREncryptionService("fallback-qr-key-32-characters!!")


# Global service instance
qr_encryption_service = create_qr_encryption_service()