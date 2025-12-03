"""
AWS S3 Storage Module for PAPL Digital First
Handles all S3 operations for document storage and retrieval
"""

import boto3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class S3Storage:
    """
    Manages document storage in AWS S3 for PAPL Digital First ecosystem
    
    Bucket Structure:
        /source-documents/
            /papl/
            /catalogues/
            /operational-guides/
            /would-we-fund-it/
            /code-guides/
        /processed-data/
            /papl-json/
            /papl-yaml/
            /papl-markdown/
            /catalogues-json/
            /guides-json/
        /comparisons/
            /papl-comparisons/
            /catalogue-comparisons/
        /embeddings/
            /metadata/
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize S3 storage client
        
        Args:
            bucket_name: S3 bucket name (defaults to env var S3_BUCKET_NAME)
            region: AWS region (defaults to env var AWS_DEFAULT_REGION)
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', 'papl-digital-first')
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'ap-southeast-2')
        
        # Initialize S3 client with proper credential handling
        # Check if using named profile or explicit credentials
        profile_name = os.getenv('AWS_PROFILE')
        
        # Only use profile if it's actually set and not empty
        if profile_name and profile_name.strip():
            # Use named profile (for local development)
            try:
                logger.info(f"Attempting to use AWS profile: {profile_name}")
                session = boto3.Session(profile_name=profile_name)
                self.s3_client = session.client('s3', region_name=self.region)
                logger.info(f"Successfully initialized with profile: {profile_name}")
            except Exception as e:
                # Profile failed, fall back to explicit credentials
                logger.warning(f"Profile '{profile_name}' failed: {e}")
                logger.info("Falling back to explicit AWS credentials from environment")
                self.s3_client = boto3.client('s3', region_name=self.region)
        else:
            # Use explicit credentials from environment variables (for Docker)
            logger.info("Using explicit AWS credentials from environment variables")
            self.s3_client = boto3.client('s3', region_name=self.region)
        
        logger.info(f"S3Storage initialized: bucket={self.bucket_name}, region={self.region}")
    
    def ensure_bucket_exists(self) -> bool:
        """
        Ensure S3 bucket exists, create if it doesn't
        
        Returns:
            True if bucket exists or was created successfully
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
            return True
        except:
            try:
                if self.region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                logger.info(f"Created bucket {self.bucket_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")
                return False
    
    # ===== SOURCE DOCUMENTS =====
    
    def upload_source_document(
        self,
        file_data: bytes,
        document_type: str,
        filename: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload source document to S3
        
        Args:
            file_data: Raw file bytes
            document_type: Type of document ('papl', 'catalogue', 'guide', etc.)
            filename: Original filename
            metadata: Additional metadata to store
        
        Returns:
            S3 key (path) of uploaded document
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"source-documents/{document_type}/{timestamp}_{filename}"
        
        # Prepare metadata
        s3_metadata = metadata or {}
        s3_metadata.update({
            'original-filename': filename,
            'document-type': document_type,
            'upload-timestamp': timestamp
        })
        
        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=file_data,
            Metadata=s3_metadata
        )
        
        logger.info(f"Uploaded source document: {s3_key}")
        return s3_key
    
    def download_source_document(self, s3_key: str) -> bytes:
        """
        Download source document from S3
        
        Args:
            s3_key: S3 key of document
        
        Returns:
            File bytes
        """
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        return response['Body'].read()
    
    # ===== PROCESSED DATA =====
    
    def upload_processed_data(
        self,
        data: Any,
        source_s3_key: str,
        format: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload processed data (JSON, YAML, Markdown) to S3
        
        Args:
            data: Processed data (dict for JSON, string for YAML/MD)
            source_s3_key: S3 key of source document
            format: Output format ('json', 'yaml', 'markdown')
            metadata: Additional metadata
        
        Returns:
            S3 key of processed data
        """
        # Extract document info from source key
        parts = source_s3_key.split('/')
        doc_type = parts[1] if len(parts) > 1 else 'unknown'
        source_filename = parts[-1] if parts else 'unknown'
        
        # Generate processed data key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = source_filename.rsplit('.', 1)[0]
        s3_key = f"processed-data/{doc_type}-{format}/{timestamp}_{base_name}.{format}"
        
        # Serialize data based on format
        if format == 'json':
            body = json.dumps(data, indent=2)
            content_type = 'application/json'
        elif format == 'yaml':
            body = data if isinstance(data, str) else str(data)
            content_type = 'text/yaml'
        elif format == 'markdown':
            body = data if isinstance(data, str) else str(data)
            content_type = 'text/markdown'
        else:
            body = str(data)
            content_type = 'text/plain'
        
        # Prepare metadata
        s3_metadata = metadata or {}
        s3_metadata.update({
            'source-s3-key': source_s3_key,
            'format': format,
            'processed-timestamp': timestamp
        })
        
        # Upload
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=body.encode('utf-8'),
            ContentType=content_type,
            Metadata=s3_metadata
        )
        
        logger.info(f"Uploaded processed data: {s3_key}")
        return s3_key
    
    def download_processed_data(self, s3_key: str, format: str = 'json') -> Any:
        """
        Download processed data from S3
        
        Args:
            s3_key: S3 key of processed data
            format: Expected format ('json', 'yaml', 'markdown')
        
        Returns:
            Parsed data (dict for JSON, string for others)
        """
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        body = response['Body'].read().decode('utf-8')
        
        if format == 'json':
            return json.loads(body)
        else:
            return body
    
    # ===== COMPARISONS =====
    
    def upload_comparison(
        self,
        comparison_data: Dict[str, Any],
        comparison_type: str,
        old_doc_key: str,
        new_doc_key: str
    ) -> str:
        """
        Upload comparison results to S3
        
        Args:
            comparison_data: Comparison results (dict)
            comparison_type: Type of comparison ('papl', 'catalogue')
            old_doc_key: S3 key of old document
            new_doc_key: S3 key of new document
        
        Returns:
            S3 key of comparison
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        comparison_id = f"{comparison_type}_comparison_{timestamp}"
        s3_key = f"comparisons/{comparison_type}-comparisons/{comparison_id}.json"
        
        # Add metadata to comparison
        comparison_with_metadata = {
            'comparison_id': comparison_id,
            'timestamp': timestamp,
            'comparison_type': comparison_type,
            'old_document': old_doc_key,
            'new_document': new_doc_key,
            'results': comparison_data
        }
        
        # Upload
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(comparison_with_metadata, indent=2).encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'comparison-type': comparison_type,
                'timestamp': timestamp
            }
        )
        
        logger.info(f"Uploaded comparison: {s3_key}")
        return s3_key
    
    def list_comparisons(
        self,
        comparison_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List recent comparisons
        
        Args:
            comparison_type: Filter by type ('papl', 'catalogue'), None for all
            limit: Maximum number of results
        
        Returns:
            List of comparison metadata
        """
        prefix = f"comparisons/{comparison_type}-comparisons/" if comparison_type else "comparisons/"
        
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix,
            MaxKeys=limit
        )
        
        comparisons = []
        if 'Contents' in response:
            for obj in response['Contents']:
                comparisons.append({
                    's3_key': obj['Key'],
                    'last_modified': obj['LastModified'],
                    'size': obj['Size']
                })
        
        return sorted(comparisons, key=lambda x: x['last_modified'], reverse=True)
    
    # ===== EMBEDDINGS METADATA =====
    
    def upload_embedding_metadata(
        self,
        document_s3_key: str,
        embedding_info: Dict[str, Any]
    ) -> str:
        """
        Upload embedding metadata (actual embeddings go to OpenSearch)
        
        Args:
            document_s3_key: S3 key of source document
            embedding_info: Info about embeddings (chunk count, model, etc.)
        
        Returns:
            S3 key of metadata
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        doc_id = document_s3_key.replace('/', '_')
        s3_key = f"embeddings/metadata/{timestamp}_{doc_id}_embedding_info.json"
        
        metadata = {
            'document_s3_key': document_s3_key,
            'timestamp': timestamp,
            'embedding_info': embedding_info
        }
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(metadata, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
        
        logger.info(f"Uploaded embedding metadata: {s3_key}")
        return s3_key
    
    # ===== UTILITY FUNCTIONS =====
    
    def list_documents_by_type(
        self,
        document_type: str,
        source: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all documents of a given type
        
        Args:
            document_type: Type to list ('papl', 'catalogue', etc.)
            source: If True, list source documents; if False, list processed
        
        Returns:
            List of document metadata
        """
        if source:
            prefix = f"source-documents/{document_type}/"
        else:
            prefix = f"processed-data/{document_type}-"
        
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
        )
        
        documents = []
        if 'Contents' in response:
            for obj in response['Contents']:
                documents.append({
                    's3_key': obj['Key'],
                    'last_modified': obj['LastModified'],
                    'size': obj['Size']
                })
        
        return sorted(documents, key=lambda x: x['last_modified'], reverse=True)
    
    def get_object_metadata(self, s3_key: str) -> Dict[str, Any]:
        """
        Get metadata for an S3 object
        
        Args:
            s3_key: S3 key
        
        Returns:
            Metadata dict
        """
        response = self.s3_client.head_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        
        return {
            'content_type': response.get('ContentType'),
            'content_length': response.get('ContentLength'),
            'last_modified': response.get('LastModified'),
            'metadata': response.get('Metadata', {})
        }
    
    def delete_object(self, s3_key: str) -> bool:
        """
        Delete an object from S3
        
        Args:
            s3_key: S3 key to delete
        
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {s3_key}: {e}")
            return False
        
    def upload_feedback(self, feedback: dict, prefix: str = "feedback"):
        """
        Save user feedback JSON into S3 with timestamp-based key.
        Uses same S3 client structure as upload_source_document().
        """
        timestamp = feedback.get("timestamp", datetime.now().isoformat())
        safe_timestamp = timestamp.replace(":", "-")  # avoid illegal S3 key characters

        key = f"{prefix}/feedback_{safe_timestamp}.json"

        body = json.dumps(feedback, indent=2)

        # Use the correct S3 client for your class
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "feedback-timestamp": timestamp
            }
        )

        logger.info(f"Uploaded feedback: {key}")
        return key

    


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize storage
    storage = S3Storage()
    
    # Ensure bucket exists
    storage.ensure_bucket_exists()
    
    # Example: Upload a document
    # with open('PAPL_2024Q1.docx', 'rb') as f:
    #     s3_key = storage.upload_source_document(
    #         file_data=f.read(),
    #         document_type='papl',
    #         filename='PAPL_2024Q1.docx',
    #         metadata={'version': '2024Q1', 'quarter': 'Q1'}
    #     )
    #     print(f"Uploaded to: {s3_key}")