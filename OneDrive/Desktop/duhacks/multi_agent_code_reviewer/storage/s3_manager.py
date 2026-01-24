"""
S3 Storage Manager
Unified interface for all S3 operations (read, write, config)
Consolidates aws_config, s3_reader, and s3_uploader into one module
"""

from storage.aws_config import aws_config
from storage.s3_reader import S3Reader
from storage.s3_uploader import S3Uploader
from utils.logger import Logger


class S3Manager:
    """
    Unified S3 Storage Manager
    Combines all S3 operations in one place
    """
    
    def __init__(self):
        """Initialize S3 Manager with all components"""
        self.logger = Logger("S3Manager")
        self.config = aws_config
        self.reader = S3Reader()
        self.uploader = S3Uploader()
        
        self.logger.info(f"✅ S3Manager initialized")
        self.logger.info(f"   Bucket: {self.config.s3_bucket_name}")
        self.logger.info(f"   Region: {self.config.aws_region}")
        self.logger.info(f"   Mode: {'REAL' if not self.reader.use_mock else 'MOCK'}")
    
    # ==================== READ OPERATIONS ====================
    
    def read_code(self, s3_path: str) -> dict:
        """
        Read code files from S3
        
        Args:
            s3_path: S3 path (e.g., s3://bucket/prefix/)
        
        Returns:
            Dictionary of {filename: content}
        """
        return self.reader.read_code_snapshot(s3_path)
    
    def path_exists(self, s3_path: str) -> bool:
        """
        Check if S3 path exists
        
        Args:
            s3_path: S3 path to check
        
        Returns:
            True if path exists, False otherwise
        """
        return self.reader.path_exists(s3_path)
    
    def get_object_count(self, s3_path: str) -> int:
        """
        Get count of objects at S3 path
        
        Args:
            s3_path: S3 path
        
        Returns:
            Number of objects
        """
        return self.reader.get_object_count(s3_path)
    
    # ==================== WRITE OPERATIONS ====================
    
    def upload_directory(self, local_dir: str, s3_prefix: str) -> str:
        """
        Upload entire directory to S3
        
        Args:
            local_dir: Local directory path
            s3_prefix: S3 prefix to upload to
        
        Returns:
            S3 path where uploaded
        """
        return self.uploader.upload_directory(local_dir, s3_prefix)
    
    def upload_file(self, local_path: str, s3_key: str) -> str:
        """
        Upload single file to S3
        
        Args:
            local_path: Local file path
            s3_key: S3 key/path
        
        Returns:
            S3 URI
        """
        return self.uploader.upload_file(local_path, s3_key)
    
    def upload_string(self, content: str, s3_key: str, content_type: str = 'text/plain') -> str:
        """
        Upload string content to S3
        
        Args:
            content: String content
            s3_key: S3 key/path
            content_type: MIME type
        
        Returns:
            S3 URI
        """
        return self.uploader.upload_string(content, s3_key, content_type)
    
    # ==================== UTILITIES ====================
    
    def get_bucket_name(self) -> str:
        """Get bucket name"""
        return self.config.s3_bucket_name
    
    def get_region(self) -> str:
        """Get AWS region"""
        return self.config.aws_region
    
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode"""
        return self.reader.use_mock
    
    def get_status(self) -> dict:
        """
        Get S3 Manager status
        
        Returns:
            Dictionary with status info
        """
        return {
            "bucket": self.config.s3_bucket_name,
            "region": self.config.aws_region,
            "mode": "MOCK" if self.reader.use_mock else "REAL",
            "reader_ready": self.reader.s3_client is not None,
            "uploader_ready": self.uploader.s3_client is not None
        }


# Global instance for easy import
s3_manager = S3Manager()
