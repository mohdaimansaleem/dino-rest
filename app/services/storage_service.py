"""
Cloud Storage Service for file uploads
Production-ready implementation for Google Cloud Run
"""
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io
from datetime import timedelta

from app.core.config import get_storage_bucket, settings
from app.core.logging_config import LoggerMixin


class StorageService(LoggerMixin):
    """Storage service for handling file uploads and management"""
    
    def __init__(self):
        self.bucket = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure storage service is initialized"""
        if not self._initialized:
            try:
                self.bucket = get_storage_bucket()
                self._initialized = True
                self.log_operation("storage_service_initialized", bucket_name=settings.GCS_BUCKET_NAME)
            except Exception as e:
                self.log_error(e, "storage_service_initialization")
                raise
    
    async def upload_image(self, file: UploadFile, folder: str = "images", 
                          optimize: bool = True, max_size: tuple = (1200, 900)):
        """Upload image to storage"""
        self._ensure_initialized()
        return await upload_image_to_gcs(file, folder, optimize, max_size)
    
    async def upload_file(self, file: UploadFile, folder: str = "documents"):
        """Upload file to storage"""
        self._ensure_initialized()
        return await upload_file_to_gcs(file, folder)
    
    async def delete_file(self, file_url: str):
        """Delete file from storage"""
        self._ensure_initialized()
        return await delete_file_from_gcs(file_url)
    
    def get_signed_url(self, blob_path: str, expiration: int = 3600):
        """Get signed URL for file"""
        self._ensure_initialized()
        return get_signed_url(blob_path, expiration)
    
    async def upload_multiple_images(self, files: list, folder: str = "images", optimize: bool = True):
        """Upload multiple images"""
        self._ensure_initialized()
        results = []
        for file in files:
            try:
                url = await upload_image_to_gcs(file, folder, optimize)
                results.append({"success": True, "file_url": url, "filename": file.filename})
            except Exception as e:
                results.append({"success": False, "error": str(e), "filename": file.filename})
        
        from app.models.schemas import BulkImageUploadResponse
        return BulkImageUploadResponse(
            success=all(r["success"] for r in results),
            message=f"Uploaded {sum(1 for r in results if r['success'])} of {len(results)} images",
            results=results
        )
    
    async def upload_document(self, file: UploadFile, folder: str = "documents"):
        """Upload document file"""
        self._ensure_initialized()
        url = await upload_file_to_gcs(file, folder)
        from app.models.schemas import ImageUploadResponse
        return ImageUploadResponse(
            success=True,
            message="Document uploaded successfully",
            file_url=url
        )
    
    async def delete_multiple_files(self, file_paths: list):
        """Delete multiple files"""
        self._ensure_initialized()
        results = {}
        for file_path in file_paths:
            try:
                # Convert file path to URL format for deletion
                file_url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{file_path}"
                success = await delete_file_from_gcs(file_url)
                results[file_path] = success
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
                results[file_path] = False
        return results
    
    def get_file_info(self, file_path: str):
        """Get file information"""
        self._ensure_initialized()
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                blob.reload()
                return {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "public_url": blob.public_url
                }
            return None
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def list_files(self, prefix: str = "", max_results: int = 100):
        """List files in storage"""
        self._ensure_initialized()
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_results)
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "public_url": blob.public_url
                })
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def cleanup_old_files(self, folder: str, days_old: int):
        """Clean up old files"""
        self._ensure_initialized()
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            blobs = self.bucket.list_blobs(prefix=folder)
            deleted_count = 0
            
            for blob in blobs:
                if blob.time_created and blob.time_created < cutoff_date:
                    blob.delete()
                    deleted_count += 1
                    
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")
            return 0


# Global storage service instance
_storage_service = None


def get_storage_service() -> StorageService:
    """Get storage service instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


async def upload_image_to_gcs(
    file: UploadFile, 
    folder: str = "images",
    optimize: bool = True,
    max_size: tuple = (1200, 900)
) -> str:
    """
    Upload image to Google Cloud Storage
    
    Args:
        file: The uploaded file
        folder: Folder path in the bucket
        optimize: Whether to optimize the image
        max_size: Maximum image dimensions (width, height)
    
    Returns:
        Public URL of the uploaded file
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Check file size
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{uuid.uuid4()}.{file_extension}"
        blob_path = f"{settings.GCS_IMAGES_FOLDER}/{folder}/{filename}"
        
        # Get bucket
        bucket = get_storage_bucket()
        blob = bucket.blob(blob_path)
        
        # Optimize image if requested
        if optimize:
            try:
                # Open image with PIL
                image = Image.open(io.BytesIO(content))
                
                # Convert to RGB if necessary
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                
                # Resize if too large
                if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                    image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized image to bytes
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=85, optimize=True)
                content = output.getvalue()
                
                logger.info(f"✅ Optimized image: {file.filename}")
                
            except Exception as e:
                logger.warning(f"⚠️ Image optimization failed, using original: {e}")
        
        # Upload to Cloud Storage
        blob.upload_from_string(
            content,
            content_type=file.content_type
        )
        
        # Try to make blob publicly readable, fallback to signed URL
        try:
            blob.make_public()
            public_url = blob.public_url
            logger.info(f"File uploaded with public access: {blob_path}")
        except Exception as e:
            logger.warning(f"Could not make blob public (likely due to Public Access Prevention): {e}")
            # Generate signed URL with longer expiration for uploaded files
            from datetime import timedelta
            public_url = blob.generate_signed_url(
                expiration=timedelta(days=365),  # Long-lived URL for uploaded content
                method="GET"
            )
            logger.info(f"File uploaded with signed URL access: {blob_path}")
        
        logger.info(f"✅ Uploaded image to: {public_url}")
        
        return public_url
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


async def upload_file_to_gcs(
    file: UploadFile,
    folder: str = "documents"
) -> str:
    """
    Upload any file to Google Cloud Storage
    
    Args:
        file: The uploaded file
        folder: Folder path in the bucket
    
    Returns:
        Public URL of the uploaded file
    """
    try:
        # Check file size
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "bin"
        filename = f"{uuid.uuid4()}.{file_extension}"
        blob_path = f"{settings.GCS_DOCUMENTS_FOLDER}/{folder}/{filename}"
        
        # Get bucket
        bucket = get_storage_bucket()
        blob = bucket.blob(blob_path)
        
        # Upload to Cloud Storage
        blob.upload_from_string(
            content,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # Try to make blob publicly readable, fallback to signed URL
        try:
            blob.make_public()
            public_url = blob.public_url
            logger.info(f"File uploaded with public access: {blob_path}")
        except Exception as e:
            logger.warning(f"Could not make blob public (likely due to Public Access Prevention): {e}")
            # Generate signed URL with longer expiration for uploaded files
            from datetime import timedelta
            public_url = blob.generate_signed_url(
                expiration=timedelta(days=365),  # Long-lived URL for uploaded content
                method="GET"
            )
            logger.info(f"File uploaded with signed URL access: {blob_path}")
        
        logger.info(f"✅ Uploaded file to: {public_url}")
        
        return public_url
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


async def delete_file_from_gcs(file_url: str) -> bool:
    """
    Delete file from Google Cloud Storage
    
    Args:
        file_url: Public URL of the file to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract blob path from URL
        bucket_name = settings.GCS_BUCKET_NAME
        if bucket_name not in file_url:
            logger.warning(f"⚠️ File URL doesn't belong to our bucket: {file_url}")
            return False
        
        # Extract blob path
        blob_path = file_url.split(f"{bucket_name}/")[-1]
        
        # Get bucket and blob
        bucket = get_storage_bucket()
        blob = bucket.blob(blob_path)
        
        # Delete blob
        blob.delete()
        
        logger.info(f"✅ Deleted file: {file_url}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting file {file_url}: {e}")
        return False


def get_signed_url(blob_path: str, expiration: int = 3600) -> str:
    """
    Generate a signed URL for private file access
    
    Args:
        blob_path: Path to the blob in the bucket
        expiration: URL expiration time in seconds
    
    Returns:
        Signed URL
    """
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(blob_path)
        
        # Generate signed URL
        signed_url = blob.generate_signed_url(
            expiration=expiration,
            method="GET"
        )
        
        logger.info(f"✅ Generated signed URL for: {blob_path}")
        
        return signed_url
        
    except Exception as e:
        logger.error(f"❌ Error generating signed URL for {blob_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate signed URL: {str(e)}"
        )