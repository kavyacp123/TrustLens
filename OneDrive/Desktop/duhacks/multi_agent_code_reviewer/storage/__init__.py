"""
Storage Package
All S3 operations consolidated here
"""

# Import all S3 components
from storage.aws_config import aws_config
from storage.s3_reader import S3Reader
from storage.s3_uploader import S3Uploader
from storage.s3_manager import S3Manager, s3_manager

# Export for easy importing
__all__ = [
    'aws_config',
    'S3Reader',
    'S3Uploader',
    'S3Manager',
    's3_manager',  # Global instance
]
