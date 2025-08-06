"""
Children Information model for family law cases
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, func, Integer, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import Base, generate_uuid
from datetime import date

class ChildrenInformation(Base):
    """
    Children information for family law cases
    """
    __tablename__ = 'children_information'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Child details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    
    # Living arrangements
    current_living_arrangement = Column(String(255))
    proposed_living_arrangement = Column(String(255))
    
    # School and education
    school_name = Column(String(255))
    school_year = Column(String(20))
    special_needs = Column(Boolean, default=False)
    special_needs_details = Column(String(500))
    
    # Parenting arrangements
    current_parenting_time = Column(JSONB)  # Percentage time with each parent
    proposed_parenting_time = Column(JSONB)
    
    # Financial support
    child_support_amount = Column(String(100))  # Current amount
    proposed_child_support = Column(String(100))
    
    # Medical and welfare
    medical_conditions = Column(String(500))
    doctor_details = Column(JSONB)
    
    # Additional information
    extracurricular_activities = Column(JSONB, default=list)
    special_considerations = Column(String(1000))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="children_info")
    
    def __repr__(self):
        return f"<ChildrenInformation(name='{self.first_name} {self.last_name}', dob='{self.date_of_birth}')>"
    
    @validates('date_of_birth')
    def validate_date_of_birth(self, key, dob):
        """Validate date of birth is reasonable"""
        if dob > date.today():
            raise ValueError("Date of birth cannot be in the future")
        
        # Check if child is over 18 (might need special handling)
        age = (date.today() - dob).days / 365.25
        if age > 18:
            # Log warning but don't reject - might be adult child in family case
            pass
        
        return dob
    
    def get_age(self) -> int:
        """Calculate current age of child"""
        today = date.today()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
        return age
    
    def get_full_name(self) -> str:
        """Get child's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def is_school_age(self) -> bool:
        """Check if child is of school age (5-17)"""
        age = self.get_age()
        return 5 <= age <= 17