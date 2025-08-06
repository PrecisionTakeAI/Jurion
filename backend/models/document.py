"""
Document model with AI processing and security features
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, Boolean, BigInteger, Integer, DECIMAL, Date
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB, ARRAY
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid
from .enums import DocumentType, ProcessingStatus
import hashlib

class Document(Base):
    """
    Document entity with AI processing and privilege protection
    """
    __tablename__ = 'documents'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    
    # Document classification
    document_type = Column(ENUM(DocumentType))
    document_category = Column(String(100))
    
    # Security and privilege
    is_privileged = Column(Boolean, default=False, index=True)
    is_confidential = Column(Boolean, default=True)
    
    # Version control
    version = Column(Integer, default=1)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'))
    
    # Upload tracking
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    # AI processing
    processed_at = Column(DateTime)
    processing_status = Column(ENUM(ProcessingStatus), default=ProcessingStatus.PENDING, index=True)
    extracted_text = Column(Text)
    ai_summary = Column(Text)
    ai_key_points = Column(JSONB)
    ai_extracted_entities = Column(JSONB)
    ai_classification_confidence = Column(DECIMAL(3, 2))
    ocr_confidence = Column(DECIMAL(3, 2))
    
    # Organization
    tags = Column(ARRAY(String))
    
    # Retention and compliance
    retention_date = Column(Date)
    
    # Additional metadata
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm", back_populates="documents")
    case = relationship("Case", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    parent_document = relationship("Document", remote_side=[id])
    child_documents = relationship("Document", back_populates="parent_document")
    
    def __repr__(self):
        return f"<Document(filename='{self.filename}', type='{self.document_type}')>"
    
    @validates('file_hash')
    def validate_file_hash(self, key, file_hash):
        """Validate file hash format (SHA-256)"""
        if file_hash and len(file_hash) != 64:
            raise ValueError("File hash must be 64 characters (SHA-256)")
        return file_hash
    
    @validates('mime_type')
    def validate_mime_type(self, key, mime_type):
        """Validate MIME type format"""
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/tiff'
        ]
        if mime_type not in allowed_types:
            raise ValueError(f"MIME type {mime_type} not allowed")
        return mime_type
    
    @staticmethod
    def calculate_file_hash(file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def is_processed(self) -> bool:
        """Check if document processing is complete"""
        return self.processing_status == ProcessingStatus.COMPLETED
    
    def requires_review(self) -> bool:
        """Check if document requires human review based on confidence"""
        if self.ai_classification_confidence and self.ai_classification_confidence < 0.8:
            return True
        if self.ocr_confidence and self.ocr_confidence < 0.9:
            return True
        return False
    
    def get_file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size / (1024 * 1024)
    
    def add_tag(self, tag: str):
        """Add a tag to the document"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """Remove a tag from the document"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def update_processing_status(self, status: ProcessingStatus, result_data: dict = None):
        """Update processing status with optional result data"""
        self.processing_status = status
        if status == ProcessingStatus.COMPLETED:
            self.processed_at = func.now()
            if result_data:
                self.extracted_text = result_data.get('text')
                self.ai_summary = result_data.get('summary')
                self.ai_key_points = result_data.get('key_points')
                self.ai_extracted_entities = result_data.get('entities')
                self.ai_classification_confidence = result_data.get('classification_confidence')
                self.ocr_confidence = result_data.get('ocr_confidence')
    
    def create_new_version(self, file_content: bytes, filename: str, uploaded_by_id: str):
        """Create a new version of this document"""
        new_version = Document(
            firm_id=self.firm_id,
            case_id=self.case_id,
            filename=filename,
            original_filename=filename,
            file_size=len(file_content),
            mime_type=self.mime_type,
            file_hash=self.calculate_file_hash(file_content),
            document_type=self.document_type,
            document_category=self.document_category,
            is_privileged=self.is_privileged,
            is_confidential=self.is_confidential,
            version=self.version + 1,
            parent_document_id=self.id,
            uploaded_by=uploaded_by_id,
            tags=self.tags.copy() if self.tags else None
        )
        return new_version