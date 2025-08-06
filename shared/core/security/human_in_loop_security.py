"""
Human-in-the-Loop Security Controls
==================================

Secure human intervention framework for multi-agent legal workflows.
Ensures Australian legal compliance by requiring human oversight for critical decisions.

Features:
- Mandatory human approval for high-risk legal advice
- Secure escalation workflows with audit trails
- Australian legal practitioner verification
- Client consent and confidentiality protection
- Privacy Act 1988 compliance for human interventions
- Professional standards enforcement
- Secure notification and approval systems
"""

import asyncio
import logging
import time
import json
import secrets
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import uuid
from abc import ABC, abstractmethod

# Import existing security components
from shared.core.security.encryption_service import EncryptionService, get_encryption_service
from shared.core.security.input_validator import InputValidator, ValidationResult, SecurityLevel
from shared.core.security.a2a_protocol_security import AgentSecurityLevel, MessageSeverity, get_a2a_security

logger = logging.getLogger(__name__)


class InterventionTrigger(Enum):
    """Triggers that require human intervention"""
    HIGH_RISK_ADVICE = "high_risk_advice"           # Legal advice with high liability
    FINANCIAL_THRESHOLD = "financial_threshold"     # Financial matters above threshold
    CLIENT_PII_ACCESS = "client_pii_access"        # Access to personal information
    CONFIDENTIAL_DISCLOSURE = "confidential_disclosure"  # Confidential client information
    LEGAL_PRECEDENT_CONFLICT = "legal_precedent_conflict"  # Conflicting legal precedents
    COMPLIANCE_VIOLATION = "compliance_violation"   # Potential compliance issues
    ETHICAL_CONCERN = "ethical_concern"            # Professional ethics concerns
    AGENT_CONSENSUS_FAILURE = "agent_consensus_failure"  # Agents can't reach consensus
    CLIENT_CONSENT_REQUIRED = "client_consent_required"  # Client consent needed
    COURT_DOCUMENT_GENERATION = "court_document_generation"  # Court documents


class InterventionUrgency(Enum):
    """Urgency levels for human intervention"""
    LOW = 1      # Can wait 24 hours
    MEDIUM = 2   # Should be addressed within 4 hours
    HIGH = 3     # Requires attention within 1 hour
    URGENT = 4   # Immediate attention required (within 15 minutes)
    CRITICAL = 5 # Stop all processing until resolved


class InterventionStatus(Enum):
    """Status of intervention requests"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PractitionerRole(Enum):
    """Australian legal practitioner roles"""
    PRINCIPAL = "principal"           # Firm principal/partner
    SENIOR_SOLICITOR = "senior_solicitor"  # Senior practitioner
    SOLICITOR = "solicitor"          # Qualified practitioner
    PARALEGAL = "paralegal"          # Supervised paralegal
    COMPLIANCE_OFFICER = "compliance_officer"  # Compliance specialist


@dataclass
class LegalPractitioner:
    """Australian legal practitioner with credentials"""
    practitioner_id: str
    name: str
    role: PractitionerRole
    practitioner_number: str  # Australian legal practitioner number
    jurisdiction: str         # NSW, VIC, QLD, etc.
    firm_id: str
    security_clearance: AgentSecurityLevel
    specializations: List[str] = field(default_factory=list)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_verification: datetime = field(default_factory=datetime.now)


@dataclass
class InterventionContext:
    """Context requiring human intervention"""
    case_id: str
    client_id: str
    matter_type: str
    financial_value: Optional[float] = None
    confidentiality_level: AgentSecurityLevel = AgentSecurityLevel.STANDARD
    client_consents: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)


@dataclass
class InterventionRequest:
    """Request for human intervention in agent workflow"""
    request_id: str
    trigger: InterventionTrigger
    urgency: InterventionUrgency
    context: InterventionContext
    requesting_agent_id: str
    agent_recommendation: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    required_approver_role: PractitionerRole
    created_at: datetime
    expires_at: datetime
    status: InterventionStatus = InterventionStatus.PENDING
    assigned_practitioner: Optional[str] = None
    approval_chain: List[str] = field(default_factory=list)
    client_notification_sent: bool = False
    
    # Encrypted sensitive data
    encrypted_details: Optional[str] = None
    encrypted_client_data: Optional[str] = None


@dataclass
class InterventionDecision:
    """Decision made by human practitioner"""
    decision_id: str
    request_id: str
    practitioner_id: str
    decision: InterventionStatus  # APPROVED or REJECTED
    reasoning: str
    conditions: List[str] = field(default_factory=list)
    client_consent_obtained: bool = False
    compliance_notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    # Digital signature for decision integrity
    digital_signature: Optional[str] = None


@dataclass
class ClientConsentRecord:
    """Record of client consent for specific actions"""
    consent_id: str
    client_id: str
    case_id: str
    consent_type: str
    consent_details: str
    granted: bool
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    witness_practitioner: Optional[str] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None


class HumanInterventionError(Exception):
    """Exception raised for human intervention errors"""
    
    def __init__(self, message: str, intervention_details: Dict[str, Any] = None):
        super().__init__(message)
        self.intervention_details = intervention_details or {}


class InterventionSecurityManager:
    """
    Security manager for human-in-the-loop interventions.
    
    Ensures secure, compliant human oversight of AI agent decisions
    with comprehensive audit trails and Australian legal compliance.
    """
    
    def __init__(self, encryption_service: Optional[EncryptionService] = None):
        self.logger = logging.getLogger(__name__)
        
        # Core security services
        self.encryption_service = encryption_service or get_encryption_service()
        self.input_validator = InputValidator()
        self.a2a_security = get_a2a_security()
        
        # Practitioner management
        self.registered_practitioners: Dict[str, LegalPractitioner] = {}
        self.active_sessions: Dict[str, datetime] = {}  # Practitioner security sessions
        
        # Intervention management
        self.pending_interventions: Dict[str, InterventionRequest] = {}
        self.intervention_history: List[InterventionRequest] = []
        self.intervention_decisions: Dict[str, InterventionDecision] = {}
        
        # Client consent management
        self.client_consents: Dict[str, List[ClientConsentRecord]] = {}
        
        # Risk thresholds (configurable per firm)
        self.financial_thresholds = {
            'high_risk': 100000.0,      # $100k requires senior approval
            'critical_risk': 500000.0,   # $500k requires principal approval
        }
        
        # Notification callbacks
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Security metrics
        self.metrics = {
            'interventions_requested': 0,
            'interventions_approved': 0,
            'interventions_rejected': 0,
            'interventions_expired': 0,
            'security_escalations': 0,
            'compliance_violations': 0
        }
        
        self.logger.info("Human-in-the-Loop Security Manager initialized")
    
    async def register_practitioner(
        self,
        practitioner_id: str,
        name: str,
        role: PractitionerRole,
        practitioner_number: str,
        jurisdiction: str,
        firm_id: str,
        security_clearance: AgentSecurityLevel,
        specializations: List[str] = None
    ) -> LegalPractitioner:
        """
        Register legal practitioner for human interventions.
        
        Args:
            practitioner_id: Unique practitioner identifier
            name: Practitioner full name
            role: Legal role/position
            practitioner_number: Australian legal practitioner number
            jurisdiction: Australian jurisdiction (NSW, VIC, etc.)
            firm_id: Law firm identifier
            security_clearance: Security clearance level
            specializations: Areas of legal specialization
            
        Returns:
            LegalPractitioner object
        """
        try:
            # Validate practitioner number format
            practitioner_validation = self.input_validator.validate_australian_legal_identifier(
                practitioner_number,
                'legal_practitioner_number'
            )
            
            if not practitioner_validation.is_valid:
                raise ValueError(f"Invalid practitioner number: {practitioner_validation.errors}")
            
            # Validate jurisdiction
            valid_jurisdictions = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']
            if jurisdiction.upper() not in valid_jurisdictions:
                raise ValueError(f"Invalid jurisdiction: {jurisdiction}")
            
            # Create practitioner record
            practitioner = LegalPractitioner(
                practitioner_id=practitioner_id,
                name=name,
                role=role,
                practitioner_number=practitioner_number,
                jurisdiction=jurisdiction.upper(),
                firm_id=firm_id,
                security_clearance=security_clearance,
                specializations=specializations or []
            )
            
            # Store practitioner
            self.registered_practitioners[practitioner_id] = practitioner
            
            # Log registration
            await self._log_security_event(
                event_type="PRACTITIONER_REGISTERED",
                severity=MessageSeverity.INFO,
                practitioner_id=practitioner_id,
                firm_id=firm_id,
                details={
                    'role': role.value,
                    'jurisdiction': jurisdiction,
                    'security_clearance': security_clearance.value,
                    'specializations': specializations
                }
            )
            
            self.logger.info(f"Registered practitioner {practitioner_id} ({role.value}) for firm {firm_id}")
            
            return practitioner
            
        except Exception as e:
            await self._log_security_event(
                event_type="PRACTITIONER_REGISTRATION_FAILED",
                severity=MessageSeverity.ERROR,
                practitioner_id=practitioner_id,
                firm_id=firm_id,
                details={'error': str(e)}
            )
            raise
    
    async def request_intervention(
        self,
        trigger: InterventionTrigger,
        context: InterventionContext,
        requesting_agent_id: str,
        agent_recommendation: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        urgency: InterventionUrgency = InterventionUrgency.MEDIUM,
        sensitive_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Request human intervention for agent decision.
        
        Args:
            trigger: What triggered the intervention requirement
            context: Context of the legal matter
            requesting_agent_id: ID of agent requesting intervention
            agent_recommendation: Agent's recommended action
            risk_assessment: Risk analysis from agents
            urgency: Urgency level for intervention
            sensitive_details: Sensitive information requiring encryption
            
        Returns:
            Intervention request ID
        """
        try:
            self.metrics['interventions_requested'] += 1
            
            # Generate request ID
            request_id = str(uuid.uuid4())
            
            # Determine required approver role based on trigger and risk
            required_role = self._determine_required_approver(trigger, context, risk_assessment)
            
            # Calculate expiration based on urgency
            expires_at = self._calculate_expiration(urgency)
            
            # Encrypt sensitive details if provided
            encrypted_details = None
            encrypted_client_data = None
            
            if sensitive_details:
                encrypted_details = self.encryption_service.encrypt_sensitive_field(
                    sensitive_details,
                    f"intervention_details:{request_id}",
                    context.case_id
                )
            
            if context.client_id:
                # Encrypt client context for privacy protection
                client_data = {
                    'client_id': context.client_id,
                    'case_id': context.case_id,
                    'matter_type': context.matter_type
                }
                encrypted_client_data = self.encryption_service.encrypt_sensitive_field(
                    client_data,
                    f"client_data:{request_id}",
                    context.case_id
                )
            
            # Create intervention request
            intervention_request = InterventionRequest(
                request_id=request_id,
                trigger=trigger,
                urgency=urgency,
                context=context,
                requesting_agent_id=requesting_agent_id,
                agent_recommendation=agent_recommendation,
                risk_assessment=risk_assessment,
                required_approver_role=required_role,
                created_at=datetime.now(),
                expires_at=expires_at,
                encrypted_details=encrypted_details,
                encrypted_client_data=encrypted_client_data
            )
            
            # Store request
            self.pending_interventions[request_id] = intervention_request
            
            # Assign to appropriate practitioner
            assigned_practitioner = await self._assign_practitioner(intervention_request)
            if assigned_practitioner:
                intervention_request.assigned_practitioner = assigned_practitioner.practitioner_id
                intervention_request.status = InterventionStatus.IN_REVIEW
            
            # Send notifications
            await self._notify_stakeholders(intervention_request)
            
            # Log intervention request
            await self._log_security_event(
                event_type="INTERVENTION_REQUESTED",
                severity=self._get_severity_for_urgency(urgency),
                practitioner_id=assigned_practitioner.practitioner_id if assigned_practitioner else None,
                firm_id=context.case_id,  # Using case_id as identifier
                details={
                    'request_id': request_id,
                    'trigger': trigger.value,
                    'urgency': urgency.value,
                    'requesting_agent': requesting_agent_id,
                    'required_role': required_role.value,
                    'financial_value': context.financial_value,
                    'expires_at': expires_at.isoformat()
                }
            )
            
            self.logger.info(f"Intervention requested: {request_id} (trigger: {trigger.value}, urgency: {urgency.value})")
            
            return request_id
            
        except Exception as e:
            await self._log_security_event(
                event_type="INTERVENTION_REQUEST_FAILED",
                severity=MessageSeverity.ERROR,
                practitioner_id=None,
                firm_id=context.case_id if context else None,
                details={
                    'trigger': trigger.value,
                    'requesting_agent': requesting_agent_id,
                    'error': str(e)
                }
            )
            raise HumanInterventionError(f"Failed to request intervention: {e}")
    
    async def process_intervention_decision(
        self,
        request_id: str,
        practitioner_id: str,
        decision: InterventionStatus,
        reasoning: str,
        conditions: List[str] = None,
        client_consent_obtained: bool = False,
        compliance_notes: str = ""
    ) -> InterventionDecision:
        """
        Process decision from legal practitioner.
        
        Args:
            request_id: Intervention request ID
            practitioner_id: Practitioner making decision
            decision: APPROVED or REJECTED
            reasoning: Reasoning for decision
            conditions: Any conditions attached to approval
            client_consent_obtained: Whether client consent was obtained
            compliance_notes: Compliance-related notes
            
        Returns:
            InterventionDecision object
        """
        try:
            # Validate request exists
            if request_id not in self.pending_interventions:
                raise ValueError(f"Intervention request not found: {request_id}")
            
            intervention_request = self.pending_interventions[request_id]
            
            # Validate practitioner authorization
            if not await self._validate_practitioner_authorization(practitioner_id, intervention_request):
                raise ValueError(f"Practitioner not authorized for this intervention: {practitioner_id}")
            
            # Check if request has expired
            if datetime.now() > intervention_request.expires_at:
                intervention_request.status = InterventionStatus.EXPIRED
                self.metrics['interventions_expired'] += 1
                raise ValueError(f"Intervention request has expired: {request_id}")
            
            # Validate decision
            if decision not in [InterventionStatus.APPROVED, InterventionStatus.REJECTED]:
                raise ValueError(f"Invalid decision status: {decision}")
            
            # Create decision record
            decision_id = str(uuid.uuid4())
            intervention_decision = InterventionDecision(
                decision_id=decision_id,
                request_id=request_id,
                practitioner_id=practitioner_id,
                decision=decision,
                reasoning=reasoning,
                conditions=conditions or [],
                client_consent_obtained=client_consent_obtained,
                compliance_notes=compliance_notes
            )
            
            # Create digital signature for decision
            decision_data = {
                'decision_id': decision_id,
                'request_id': request_id,
                'practitioner_id': practitioner_id,
                'decision': decision.value,
                'timestamp': intervention_decision.created_at.isoformat()
            }
            
            intervention_decision.digital_signature = self.encryption_service.create_hash(
                json.dumps(decision_data, sort_keys=True)
            )
            
            # Update intervention request
            intervention_request.status = decision
            intervention_request.approval_chain.append(practitioner_id)
            
            # Store decision
            self.intervention_decisions[decision_id] = intervention_decision
            
            # Update metrics
            if decision == InterventionStatus.APPROVED:
                self.metrics['interventions_approved'] += 1
            else:
                self.metrics['interventions_rejected'] += 1
            
            # Move to history and remove from pending
            self.intervention_history.append(intervention_request)
            del self.pending_interventions[request_id]
            
            # Notify relevant stakeholders
            await self._notify_decision_made(intervention_request, intervention_decision)
            
            # Log decision
            await self._log_security_event(
                event_type="INTERVENTION_DECIDED",
                severity=MessageSeverity.INFO,
                practitioner_id=practitioner_id,
                firm_id=intervention_request.context.case_id,
                details={
                    'request_id': request_id,
                    'decision_id': decision_id,
                    'decision': decision.value,
                    'trigger': intervention_request.trigger.value,
                    'client_consent_obtained': client_consent_obtained,
                    'conditions_count': len(conditions or [])
                }
            )
            
            self.logger.info(f"Intervention decision made: {decision.value} for request {request_id} by {practitioner_id}")
            
            return intervention_decision
            
        except Exception as e:
            await self._log_security_event(
                event_type="INTERVENTION_DECISION_FAILED",
                severity=MessageSeverity.ERROR,
                practitioner_id=practitioner_id,
                firm_id=None,
                details={
                    'request_id': request_id,
                    'error': str(e)
                }
            )
            raise HumanInterventionError(f"Failed to process intervention decision: {e}")
    
    async def record_client_consent(
        self,
        client_id: str,
        case_id: str,
        consent_type: str,
        consent_details: str,
        granted: bool,
        witness_practitioner: str,
        expires_at: Optional[datetime] = None
    ) -> ClientConsentRecord:
        """
        Record client consent for specific actions.
        
        Args:
            client_id: Client identifier
            case_id: Case identifier
            consent_type: Type of consent (data_processing, disclosure, etc.)
            consent_details: Detailed description of what is consented to
            granted: Whether consent is granted or denied
            witness_practitioner: Practitioner witnessing consent
            expires_at: Optional expiration date
            
        Returns:
            ClientConsentRecord
        """
        try:
            # Validate witness practitioner
            if witness_practitioner not in self.registered_practitioners:
                raise ValueError(f"Unknown witness practitioner: {witness_practitioner}")
            
            # Create consent record
            consent_id = str(uuid.uuid4())
            consent_record = ClientConsentRecord(
                consent_id=consent_id,
                client_id=client_id,
                case_id=case_id,
                consent_type=consent_type,
                consent_details=consent_details,
                granted=granted,
                granted_at=datetime.now() if granted else None,
                expires_at=expires_at,
                witness_practitioner=witness_practitioner
            )
            
            # Store consent record
            if client_id not in self.client_consents:
                self.client_consents[client_id] = []
            
            self.client_consents[client_id].append(consent_record)
            
            # Log consent recording
            await self._log_security_event(
                event_type="CLIENT_CONSENT_RECORDED",
                severity=MessageSeverity.INFO,
                practitioner_id=witness_practitioner,
                firm_id=case_id,
                details={
                    'consent_id': consent_id,
                    'client_id': client_id,
                    'consent_type': consent_type,
                    'granted': granted,
                    'expires_at': expires_at.isoformat() if expires_at else None
                }
            )
            
            self.logger.info(f"Client consent recorded: {consent_id} (granted: {granted})")
            
            return consent_record
            
        except Exception as e:
            await self._log_security_event(
                event_type="CLIENT_CONSENT_RECORDING_FAILED",
                severity=MessageSeverity.ERROR,
                practitioner_id=witness_practitioner,
                firm_id=case_id,
                details={
                    'client_id': client_id,
                    'consent_type': consent_type,
                    'error': str(e)
                }
            )
            raise
    
    def _determine_required_approver(
        self,
        trigger: InterventionTrigger,
        context: InterventionContext,
        risk_assessment: Dict[str, Any]
    ) -> PractitionerRole:
        """Determine required approver role based on trigger and context"""
        
        # High-value financial matters require principal approval
        if (context.financial_value and 
            context.financial_value >= self.financial_thresholds['critical_risk']):
            return PractitionerRole.PRINCIPAL
        
        # Critical triggers require senior approval
        critical_triggers = {
            InterventionTrigger.HIGH_RISK_ADVICE,
            InterventionTrigger.CONFIDENTIAL_DISCLOSURE,
            InterventionTrigger.COMPLIANCE_VIOLATION,
            InterventionTrigger.ETHICAL_CONCERN,
            InterventionTrigger.COURT_DOCUMENT_GENERATION
        }
        
        if trigger in critical_triggers:
            return PractitionerRole.SENIOR_SOLICITOR
        
        # High-risk assessments require senior approval
        risk_score = risk_assessment.get('overall_risk_score', 0)
        if risk_score >= 0.8:  # 80% risk threshold
            return PractitionerRole.SENIOR_SOLICITOR
        
        # Medium financial matters or standard triggers
        if (context.financial_value and 
            context.financial_value >= self.financial_thresholds['high_risk']):
            return PractitionerRole.SENIOR_SOLICITOR
        
        # Default to qualified solicitor
        return PractitionerRole.SOLICITOR
    
    def _calculate_expiration(self, urgency: InterventionUrgency) -> datetime:
        """Calculate expiration time based on urgency"""
        now = datetime.now()
        
        expiration_times = {
            InterventionUrgency.LOW: timedelta(hours=24),
            InterventionUrgency.MEDIUM: timedelta(hours=4),
            InterventionUrgency.HIGH: timedelta(hours=1),
            InterventionUrgency.URGENT: timedelta(minutes=15),
            InterventionUrgency.CRITICAL: timedelta(minutes=5)
        }
        
        return now + expiration_times[urgency]
    
    async def _assign_practitioner(self, request: InterventionRequest) -> Optional[LegalPractitioner]:
        """Assign appropriate practitioner to intervention request"""
        
        # Find practitioners with appropriate role and security clearance
        suitable_practitioners = [
            p for p in self.registered_practitioners.values()
            if (p.role.value >= request.required_approver_role.value and
                p.security_clearance.value >= request.context.confidentiality_level.value and
                p.active and 
                p.firm_id == request.context.case_id)  # Using case_id as firm identifier
        ]
        
        # Prefer practitioners with relevant specializations
        if suitable_practitioners:
            specialized_practitioners = [
                p for p in suitable_practitioners
                if any(spec in request.context.matter_type.lower() 
                      for spec in [s.lower() for s in p.specializations])
            ]
            
            if specialized_practitioners:
                return specialized_practitioners[0]
            else:
                return suitable_practitioners[0]
        
        return None
    
    async def _validate_practitioner_authorization(
        self,
        practitioner_id: str,
        request: InterventionRequest
    ) -> bool:
        """Validate practitioner is authorized to make this decision"""
        
        if practitioner_id not in self.registered_practitioners:
            return False
        
        practitioner = self.registered_practitioners[practitioner_id]
        
        # Check if practitioner is active
        if not practitioner.active:
            return False
        
        # Check role authorization
        if practitioner.role.value < request.required_approver_role.value:
            return False
        
        # Check security clearance
        if practitioner.security_clearance.value < request.context.confidentiality_level.value:
            return False
        
        # Check firm association (simplified)
        if practitioner.firm_id != request.context.case_id:
            return False
        
        return True
    
    def _get_severity_for_urgency(self, urgency: InterventionUrgency) -> MessageSeverity:
        """Map intervention urgency to message severity"""
        severity_map = {
            InterventionUrgency.LOW: MessageSeverity.INFO,
            InterventionUrgency.MEDIUM: MessageSeverity.INFO,
            InterventionUrgency.HIGH: MessageSeverity.WARNING,
            InterventionUrgency.URGENT: MessageSeverity.ERROR,
            InterventionUrgency.CRITICAL: MessageSeverity.CRITICAL
        }
        return severity_map[urgency]
    
    async def _notify_stakeholders(self, request: InterventionRequest):
        """Send notifications to relevant stakeholders"""
        # This would integrate with notification systems (email, SMS, etc.)
        
        if request.assigned_practitioner:
            # Notify assigned practitioner
            await self._send_practitioner_notification(
                request.assigned_practitioner,
                f"Intervention Required: {request.trigger.value}",
                f"Request ID: {request.request_id}\nUrgency: {request.urgency.value}\nExpires: {request.expires_at}"
            )
        
        # Notify client if required
        if (request.trigger in [InterventionTrigger.CLIENT_CONSENT_REQUIRED, 
                              InterventionTrigger.CONFIDENTIAL_DISCLOSURE] and
            not request.client_notification_sent):
            await self._send_client_notification(request)
            request.client_notification_sent = True
    
    async def _notify_decision_made(self, request: InterventionRequest, decision: InterventionDecision):
        """Notify stakeholders of intervention decision"""
        # Notify requesting agent
        if 'agent_notification' in self.notification_handlers:
            await self.notification_handlers['agent_notification'](
                request.requesting_agent_id,
                {
                    'request_id': request.request_id,
                    'decision': decision.decision.value,
                    'conditions': decision.conditions,
                    'reasoning': decision.reasoning
                }
            )
    
    async def _send_practitioner_notification(self, practitioner_id: str, subject: str, message: str):
        """Send notification to practitioner"""
        if 'practitioner_notification' in self.notification_handlers:
            await self.notification_handlers['practitioner_notification'](
                practitioner_id, subject, message
            )
    
    async def _send_client_notification(self, request: InterventionRequest):
        """Send notification to client"""
        if 'client_notification' in self.notification_handlers:
            await self.notification_handlers['client_notification'](
                request.context.client_id,
                f"Your legal matter requires attention: {request.context.matter_type}"
            )
    
    async def _log_security_event(
        self,
        event_type: str,
        severity: MessageSeverity,
        practitioner_id: Optional[str],
        firm_id: Optional[str],
        details: Dict[str, Any]
    ):
        """Log security event for audit trail"""
        # Delegate to A2A security logging
        await self.a2a_security._log_security_event(
            event_type=f"HUMAN_INTERVENTION_{event_type}",
            severity=severity,
            agent_id=practitioner_id or "system",
            firm_id=firm_id,
            details=details
        )
    
    def get_intervention_metrics(self, firm_id: Optional[str] = None) -> Dict[str, Any]:
        """Get intervention metrics for monitoring"""
        
        # Filter by firm if specified
        pending_requests = [
            r for r in self.pending_interventions.values()
            if not firm_id or r.context.case_id == firm_id
        ]
        
        history_requests = [
            r for r in self.intervention_history
            if not firm_id or r.context.case_id == firm_id
        ]
        
        # Calculate average response times
        completed_requests = [r for r in history_requests if r.status in [InterventionStatus.APPROVED, InterventionStatus.REJECTED]]
        
        if completed_requests:
            response_times = []
            for request in completed_requests:
                if request.request_id in self.intervention_decisions:
                    decision = self.intervention_decisions[request.request_id]
                    response_time = (decision.created_at - request.created_at).total_seconds() / 60  # minutes
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        else:
            avg_response_time = 0
        
        return {
            'pending_interventions': len(pending_requests),
            'completed_interventions': len(completed_requests),
            'average_response_time_minutes': avg_response_time,
            'interventions_by_trigger': self._count_by_trigger(pending_requests + history_requests),
            'interventions_by_urgency': self._count_by_urgency(pending_requests + history_requests),
            'approval_rate': self._calculate_approval_rate(history_requests),
            'expired_interventions': len([r for r in history_requests if r.status == InterventionStatus.EXPIRED]),
            **self.metrics
        }
    
    def _count_by_trigger(self, requests: List[InterventionRequest]) -> Dict[str, int]:
        """Count interventions by trigger type"""
        counts = {}
        for request in requests:
            trigger = request.trigger.value
            counts[trigger] = counts.get(trigger, 0) + 1
        return counts
    
    def _count_by_urgency(self, requests: List[InterventionRequest]) -> Dict[str, int]:
        """Count interventions by urgency level"""
        counts = {}
        for request in requests:
            urgency = request.urgency.value
            counts[urgency] = counts.get(urgency, 0) + 1
        return counts
    
    def _calculate_approval_rate(self, requests: List[InterventionRequest]) -> float:
        """Calculate approval rate for completed interventions"""
        completed = [r for r in requests if r.status in [InterventionStatus.APPROVED, InterventionStatus.REJECTED]]
        if not completed:
            return 0.0
        
        approved = len([r for r in completed if r.status == InterventionStatus.APPROVED])
        return approved / len(completed)


# Global Human Intervention Security instance
_intervention_security = None


def get_intervention_security() -> InterventionSecurityManager:
    """Get global intervention security instance"""
    global _intervention_security
    if _intervention_security is None:
        _intervention_security = InterventionSecurityManager()
    return _intervention_security


# Helper functions for multi-agent integration
async def request_human_approval(
    trigger: InterventionTrigger,
    context: InterventionContext,
    agent_id: str,
    recommendation: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    urgency: InterventionUrgency = InterventionUrgency.MEDIUM
) -> str:
    """Helper function to request human approval"""
    intervention_security = get_intervention_security()
    return await intervention_security.request_intervention(
        trigger, context, agent_id, recommendation, risk_assessment, urgency
    )


async def register_legal_practitioner(
    practitioner_id: str,
    name: str,
    role: PractitionerRole,
    practitioner_number: str,
    jurisdiction: str,
    firm_id: str,
    security_clearance: AgentSecurityLevel = AgentSecurityLevel.STANDARD
) -> LegalPractitioner:
    """Helper function to register legal practitioner"""
    intervention_security = get_intervention_security()
    return await intervention_security.register_practitioner(
        practitioner_id, name, role, practitioner_number, jurisdiction, firm_id, security_clearance
    )