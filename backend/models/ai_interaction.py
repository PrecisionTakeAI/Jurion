"""
AI Interaction model for compliance logging
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, Integer, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, ENUM, INET
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid
from .enums import AIInteractionType

class AIInteraction(Base):
    """
    AI interaction logging for compliance and optimization
    """
    __tablename__ = 'ai_interactions'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id'), index=True)
    
    # Interaction details
    interaction_type = Column(ENUM(AIInteractionType), nullable=False, index=True)
    llm_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    
    # Content
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text)
    
    # Metrics
    tokens_used = Column(Integer)
    cost_usd = Column(DECIMAL(8, 4))
    processing_time_ms = Column(Integer)
    confidence_score = Column(DECIMAL(3, 2))
    
    # Session tracking
    context_id = Column(UUID(as_uuid=True))  # For conversation threading
    session_id = Column(UUID(as_uuid=True))
    
    # Audit trail
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relationships
    firm = relationship("LawFirm", back_populates="ai_interactions")
    user = relationship("User", back_populates="ai_interactions")
    case = relationship("Case", back_populates="ai_interactions")
    
    def __repr__(self):
        return f"<AIInteraction(type='{self.interaction_type.value}', provider='{self.llm_provider}')>"
    
    @validates('llm_provider')
    def validate_llm_provider(self, key, provider):
        """Validate LLM provider name"""
        allowed_providers = ['openai', 'anthropic', 'groq', 'ollama', 'local']
        if provider.lower() not in allowed_providers:
            raise ValueError(f"LLM provider must be one of: {allowed_providers}")
        return provider.lower()
    
    @validates('confidence_score')
    def validate_confidence_score(self, key, score):
        """Validate confidence score is between 0 and 1"""
        if score is not None and (score < 0 or score > 1):
            raise ValueError("Confidence score must be between 0 and 1")
        return score
    
    def get_cost_per_token(self) -> float:
        """Calculate cost per token if data available"""
        if self.cost_usd and self.tokens_used and self.tokens_used > 0:
            return float(self.cost_usd) / self.tokens_used
        return 0.0
    
    def is_high_confidence(self) -> bool:
        """Check if interaction has high confidence score"""
        return self.confidence_score and self.confidence_score >= 0.8
    
    def requires_review(self) -> bool:
        """Check if interaction requires human review"""
        return not self.is_high_confidence()
    
    def get_processing_time_seconds(self) -> float:
        """Get processing time in seconds"""
        return self.processing_time_ms / 1000.0 if self.processing_time_ms else 0.0