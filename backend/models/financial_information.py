"""
Financial Information model for property settlements
"""

from sqlalchemy import Column, DateTime, ForeignKey, func, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from .base import Base, generate_uuid
from .enums import PartyType

class FinancialInformation(Base):
    """
    Financial information for property settlement cases
    """
    __tablename__ = 'financial_information'

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True)
    party_type = Column(ENUM(PartyType), nullable=False)
    
    # Asset categories (stored as JSONB for flexibility)
    real_estate = Column(JSONB, default=list)
    bank_accounts = Column(JSONB, default=list)
    investments = Column(JSONB, default=list)
    superannuation = Column(JSONB, default=list)
    personal_property = Column(JSONB, default=list)
    business_interests = Column(JSONB, default=list)
    
    # Liabilities
    debts_liabilities = Column(JSONB, default=list)
    
    # Income and expenses
    income_details = Column(JSONB, default=dict)
    expenses = Column(JSONB, default=dict)
    
    # Calculated totals
    total_assets = Column(DECIMAL(15, 2))
    total_liabilities = Column(DECIMAL(15, 2))
    net_worth = Column(DECIMAL(15, 2))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="financial_info")
    
    def __repr__(self):
        return f"<FinancialInformation(case_id='{self.case_id}', party='{self.party_type.value}')>"
    
    def calculate_totals(self):
        """Calculate total assets, liabilities, and net worth"""
        # Calculate total assets
        total_assets = 0
        for asset_category in [self.real_estate, self.bank_accounts, self.investments, 
                              self.superannuation, self.personal_property, self.business_interests]:
            if asset_category:
                for asset in asset_category:
                    total_assets += float(asset.get('value', 0))
        
        # Calculate total liabilities
        total_liabilities = 0
        if self.debts_liabilities:
            for debt in self.debts_liabilities:
                total_liabilities += float(debt.get('amount', 0))
        
        # Update calculated fields
        self.total_assets = total_assets
        self.total_liabilities = total_liabilities
        self.net_worth = total_assets - total_liabilities