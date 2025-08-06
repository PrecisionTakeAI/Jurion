"""
Multi-Agent Security Extensions
===============================

Extends existing security infrastructure for secure agent-to-agent communication
with end-to-end encryption, authentication, and authorization for multi-agent systems.

Features:
- Agent authentication and authorization
- Secure message passing between agents
- End-to-end encryption for sensitive data
- Agent activity audit logging
- Rate limiting for agent interactions
"""

import os
import json
import hashlib
import hmac
import secrets
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from shared.core.security.encryption_service import get_encryption_service
from shared.core.security.input_validator import InputValidator, SecurityLevel
from shared.core.security.distributed_rate_limiter import DistributedRateLimiter


class AgentRole(Enum):
    """Roles for different agent types"""
    ORCHESTRATOR = "orchestrator"
    DOCUMENT_ANALYZER = "document_analyzer"
    LEGAL_RESEARCHER = "legal_researcher"
    COMPLIANCE_CHECKER = "compliance_checker"
    RISK_ASSESSOR = "risk_assessor"
    FINANCIAL_ANALYST = "financial_analyst"
    CASE_STRATEGIST = "case_strategist"
    CLIENT_COMMUNICATOR = "client_communicator"
    WORKFLOW_MANAGER = "workflow_manager"


class MessagePriority(Enum):
    """Priority levels for agent messages"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class AgentIdentity:
    """Agent identity and credentials"""
    agent_id: str
    agent_role: AgentRole
    public_key: bytes
    permissions: List[str]
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any]


@dataclass
class SecureMessage:
    """Secure message between agents"""
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: str
    payload: Dict[str, Any]
    priority: MessagePriority
    timestamp: datetime
    signature: str
    encrypted: bool
    requires_acknowledgment: bool


@dataclass
class MessageAcknowledgment:
    """Acknowledgment of message receipt"""
    message_id: str
    agent_id: str
    status: str  # 'received', 'processed', 'failed'
    timestamp: datetime
    error_details: Optional[str] = None


class AgentSecurityManager:
    """
    Manages security for multi-agent communication.
    
    Provides:
    - Agent registration and authentication
    - Secure message encryption and signing
    - Authorization checks for agent interactions
    - Audit logging of agent activities
    """
    
    def __init__(self, redis_client=None):
        self.encryption_service = get_encryption_service()
        self.input_validator = InputValidator()
        self.logger = logging.getLogger(__name__)
        self.redis_client = redis_client
        
        # Agent registry (in production, store in database)
        self.agent_registry: Dict[str, AgentIdentity] = {}
        self.agent_keys: Dict[str, Tuple[bytes, bytes]] = {}  # private, public keys
        
        # Rate limiter for agent interactions
        if redis_client:
            self.rate_limiter = DistributedRateLimiter(redis_client)
        else:
            self.rate_limiter = None
        
        # Security configuration
        self.message_ttl_seconds = 300  # 5 minutes
        self.max_message_size = 1024 * 1024  # 1MB
        self.require_encryption_for = ['financial_data', 'pii', 'legal_advice']
        
    def register_agent(
        self,
        agent_id: str,
        agent_role: AgentRole,
        permissions: List[str],
        validity_days: int = 30
    ) -> Dict[str, Any]:
        """
        Register a new agent with security credentials.
        
        Args:
            agent_id: Unique agent identifier
            agent_role: Role of the agent
            permissions: List of permissions granted
            validity_days: Credential validity period
            
        Returns:
            Dict with registration details and credentials
        """
        try:
            # Validate agent ID
            validation_result = self.input_validator.validate_text_input(
                agent_id,
                "agent_id",
                SecurityLevel.HIGH,
                max_length=100
            )
            if not validation_result.is_valid:
                raise ValueError(f"Invalid agent_id: {validation_result.errors}")
            
            # Generate RSA key pair for agent
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicKeyFormat.SubjectPublicKeyInfo
            )
            
            # Create agent identity
            now = datetime.utcnow()
            agent_identity = AgentIdentity(
                agent_id=agent_id,
                agent_role=agent_role,
                public_key=public_pem,
                permissions=permissions,
                created_at=now,
                expires_at=now + timedelta(days=validity_days),
                metadata={
                    'registration_source': 'agent_security_manager',
                    'key_algorithm': 'RSA-2048'
                }
            )
            
            # Store in registry
            self.agent_registry[agent_id] = agent_identity
            self.agent_keys[agent_id] = (private_pem, public_pem)
            
            # Store in Redis if available
            if self.redis_client:
                self._store_agent_in_redis(agent_identity)
            
            self.logger.info(f"Agent registered: {agent_id} with role {agent_role.value}")
            
            return {
                'agent_id': agent_id,
                'role': agent_role.value,
                'public_key': public_pem.decode('utf-8'),
                'permissions': permissions,
                'expires_at': agent_identity.expires_at.isoformat(),
                'status': 'registered'
            }
            
        except Exception as e:
            self.logger.error(f"Error registering agent: {e}")
            raise
    
    def authenticate_agent(self, agent_id: str, signature: str, challenge: str) -> bool:
        """
        Authenticate an agent using digital signature.
        
        Args:
            agent_id: Agent identifier
            signature: Base64-encoded signature of challenge
            challenge: Challenge string that was signed
            
        Returns:
            True if authentication successful
        """
        try:
            # Get agent identity
            agent_identity = self.agent_registry.get(agent_id)
            if not agent_identity:
                # Try loading from Redis
                agent_identity = self._load_agent_from_redis(agent_id)
                if not agent_identity:
                    return False
            
            # Check if credentials expired
            if datetime.utcnow() > agent_identity.expires_at:
                self.logger.warning(f"Agent {agent_id} credentials expired")
                return False
            
            # Verify signature
            public_key = serialization.load_pem_public_key(
                agent_identity.public_key,
                backend=default_backend()
            )
            
            try:
                public_key.verify(
                    base64.b64decode(signature.encode()),
                    challenge.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True
            except Exception:
                return False
                
        except Exception as e:
            self.logger.error(f"Error authenticating agent: {e}")
            return False
    
    def authorize_interaction(
        self,
        sender_id: str,
        recipient_id: str,
        action: str
    ) -> bool:
        """
        Check if sender agent is authorized to interact with recipient.
        
        Args:
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID
            action: Type of interaction
            
        Returns:
            True if authorized
        """
        try:
            sender = self.agent_registry.get(sender_id)
            recipient = self.agent_registry.get(recipient_id)
            
            if not sender or not recipient:
                return False
            
            # Check sender permissions
            required_permission = f"communicate:{recipient.agent_role.value}"
            if required_permission not in sender.permissions and 'communicate:all' not in sender.permissions:
                self.logger.warning(
                    f"Agent {sender_id} not authorized to communicate with {recipient_id}"
                )
                return False
            
            # Check action-specific permissions
            action_permission = f"action:{action}"
            if action_permission not in sender.permissions and 'action:all' not in sender.permissions:
                self.logger.warning(
                    f"Agent {sender_id} not authorized for action {action}"
                )
                return False
            
            # Apply rate limiting if available
            if self.rate_limiter:
                rate_limit_key = f"agent_interaction:{sender_id}:{recipient_id}"
                allowed = self.rate_limiter.check_rate_limit(
                    rate_limit_key,
                    max_requests=100,
                    window_seconds=60
                )
                if not allowed:
                    self.logger.warning(f"Rate limit exceeded for {sender_id} -> {recipient_id}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking authorization: {e}")
            return False
    
    def create_secure_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        encrypt: bool = None
    ) -> SecureMessage:
        """
        Create a secure message between agents.
        
        Args:
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID
            message_type: Type of message
            payload: Message payload
            priority: Message priority
            encrypt: Force encryption (auto-determined if None)
            
        Returns:
            SecureMessage object
        """
        try:
            # Validate message size
            payload_str = json.dumps(payload)
            if len(payload_str) > self.max_message_size:
                raise ValueError(f"Message too large: {len(payload_str)} bytes")
            
            # Determine if encryption required
            if encrypt is None:
                encrypt = self._requires_encryption(message_type, payload)
            
            # Create message ID
            message_id = self._generate_message_id(sender_id, recipient_id)
            
            # Prepare message
            message_data = {
                'message_id': message_id,
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'message_type': message_type,
                'payload': payload,
                'priority': priority.value,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Encrypt if required
            if encrypt:
                encrypted_payload = self.encryption_service.encrypt_string(
                    json.dumps(payload),
                    f"agent_message:{sender_id}:{recipient_id}"
                )
                message_data['payload'] = {'encrypted': encrypted_payload}
                message_data['encrypted'] = True
            else:
                message_data['encrypted'] = False
            
            # Sign message
            signature = self._sign_message(sender_id, json.dumps(message_data))
            
            # Create secure message
            secure_message = SecureMessage(
                message_id=message_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                message_type=message_type,
                payload=message_data['payload'],
                priority=priority,
                timestamp=datetime.fromisoformat(message_data['timestamp']),
                signature=signature,
                encrypted=encrypt,
                requires_acknowledgment=priority.value <= MessagePriority.HIGH.value
            )
            
            # Log message creation
            self._audit_log_message('created', secure_message)
            
            return secure_message
            
        except Exception as e:
            self.logger.error(f"Error creating secure message: {e}")
            raise
    
    def verify_message(
        self,
        message: SecureMessage,
        recipient_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify and decrypt a secure message.
        
        Args:
            message: SecureMessage to verify
            recipient_id: Expected recipient ID
            
        Returns:
            Tuple of (is_valid, decrypted_payload)
        """
        try:
            # Verify recipient
            if message.recipient_id != recipient_id:
                self.logger.warning(f"Message recipient mismatch: expected {recipient_id}, got {message.recipient_id}")
                return False, None
            
            # Check message age
            message_age = datetime.utcnow() - message.timestamp
            if message_age.total_seconds() > self.message_ttl_seconds:
                self.logger.warning(f"Message {message.message_id} expired")
                return False, None
            
            # Verify signature
            message_data = {
                'message_id': message.message_id,
                'sender_id': message.sender_id,
                'recipient_id': message.recipient_id,
                'message_type': message.message_type,
                'payload': message.payload,
                'priority': message.priority.value,
                'timestamp': message.timestamp.isoformat()
            }
            
            if not self._verify_signature(message.sender_id, json.dumps(message_data), message.signature):
                self.logger.warning(f"Invalid signature for message {message.message_id}")
                return False, None
            
            # Decrypt if necessary
            payload = message.payload
            if message.encrypted:
                encrypted_data = payload.get('encrypted')
                if not encrypted_data:
                    return False, None
                
                decrypted_json = self.encryption_service.decrypt_string(
                    encrypted_data,
                    f"agent_message:{message.sender_id}:{message.recipient_id}"
                )
                payload = json.loads(decrypted_json)
            
            # Log successful verification
            self._audit_log_message('verified', message)
            
            return True, payload
            
        except Exception as e:
            self.logger.error(f"Error verifying message: {e}")
            return False, None
    
    def acknowledge_message(
        self,
        message_id: str,
        agent_id: str,
        status: str,
        error_details: Optional[str] = None
    ) -> MessageAcknowledgment:
        """
        Create acknowledgment for a received message.
        
        Args:
            message_id: ID of message to acknowledge
            agent_id: Agent acknowledging the message
            status: Status of processing
            error_details: Optional error details
            
        Returns:
            MessageAcknowledgment object
        """
        acknowledgment = MessageAcknowledgment(
            message_id=message_id,
            agent_id=agent_id,
            status=status,
            timestamp=datetime.utcnow(),
            error_details=error_details
        )
        
        # Log acknowledgment
        self.logger.info(f"Message {message_id} acknowledged by {agent_id} with status {status}")
        
        return acknowledgment
    
    def get_agent_permissions(self, agent_id: str) -> List[str]:
        """Get permissions for an agent"""
        agent = self.agent_registry.get(agent_id)
        return agent.permissions if agent else []
    
    def revoke_agent(self, agent_id: str, reason: str = None):
        """Revoke agent credentials"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
        if agent_id in self.agent_keys:
            del self.agent_keys[agent_id]
        
        # Remove from Redis if available
        if self.redis_client:
            self.redis_client.delete(f"agent:{agent_id}")
        
        self.logger.info(f"Agent {agent_id} revoked. Reason: {reason}")
    
    def _generate_message_id(self, sender_id: str, recipient_id: str) -> str:
        """Generate unique message ID"""
        timestamp = datetime.utcnow().isoformat()
        data = f"{sender_id}:{recipient_id}:{timestamp}:{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _sign_message(self, agent_id: str, message_data: str) -> str:
        """Sign message with agent's private key"""
        if agent_id not in self.agent_keys:
            raise ValueError(f"No keys found for agent {agent_id}")
        
        private_pem, _ = self.agent_keys[agent_id]
        private_key = serialization.load_pem_private_key(
            private_pem,
            password=None,
            backend=default_backend()
        )
        
        signature = private_key.sign(
            message_data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _verify_signature(self, agent_id: str, message_data: str, signature: str) -> bool:
        """Verify message signature"""
        agent = self.agent_registry.get(agent_id)
        if not agent:
            return False
        
        public_key = serialization.load_pem_public_key(
            agent.public_key,
            backend=default_backend()
        )
        
        try:
            public_key.verify(
                base64.b64decode(signature.encode()),
                message_data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def _requires_encryption(self, message_type: str, payload: Dict[str, Any]) -> bool:
        """Determine if message requires encryption"""
        # Check message type
        for sensitive_type in self.require_encryption_for:
            if sensitive_type in message_type.lower():
                return True
        
        # Check payload content
        payload_str = json.dumps(payload).lower()
        sensitive_keywords = ['ssn', 'tfn', 'credit_card', 'bank_account', 'password']
        
        for keyword in sensitive_keywords:
            if keyword in payload_str:
                return True
        
        return False
    
    def _store_agent_in_redis(self, agent: AgentIdentity):
        """Store agent identity in Redis"""
        key = f"agent:{agent.agent_id}"
        data = {
            'agent_id': agent.agent_id,
            'role': agent.agent_role.value,
            'public_key': agent.public_key.decode('utf-8'),
            'permissions': agent.permissions,
            'created_at': agent.created_at.isoformat(),
            'expires_at': agent.expires_at.isoformat(),
            'metadata': agent.metadata
        }
        
        ttl = int((agent.expires_at - datetime.utcnow()).total_seconds())
        self.redis_client.setex(key, ttl, json.dumps(data))
    
    def _load_agent_from_redis(self, agent_id: str) -> Optional[AgentIdentity]:
        """Load agent identity from Redis"""
        key = f"agent:{agent_id}"
        data = self.redis_client.get(key)
        
        if not data:
            return None
        
        agent_data = json.loads(data)
        return AgentIdentity(
            agent_id=agent_data['agent_id'],
            agent_role=AgentRole(agent_data['role']),
            public_key=agent_data['public_key'].encode('utf-8'),
            permissions=agent_data['permissions'],
            created_at=datetime.fromisoformat(agent_data['created_at']),
            expires_at=datetime.fromisoformat(agent_data['expires_at']),
            metadata=agent_data['metadata']
        )
    
    def _audit_log_message(self, action: str, message: SecureMessage):
        """Log message action for audit"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'message_id': message.message_id,
            'sender_id': message.sender_id,
            'recipient_id': message.recipient_id,
            'message_type': message.message_type,
            'encrypted': message.encrypted,
            'priority': message.priority.value
        }
        
        # In production, store in database
        self.logger.info(f"Agent message audit: {json.dumps(audit_entry)}")


# Global instance
_agent_security_manager = None


def get_agent_security_manager(redis_client=None) -> AgentSecurityManager:
    """Get global agent security manager instance"""
    global _agent_security_manager
    if _agent_security_manager is None:
        _agent_security_manager = AgentSecurityManager(redis_client)
    return _agent_security_manager


# Helper functions for agent communication
async def secure_agent_communication(
    sender_id: str,
    recipient_id: str,
    message_type: str,
    payload: Dict[str, Any],
    priority: MessagePriority = MessagePriority.NORMAL
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Helper function for secure agent-to-agent communication.
    
    Returns:
        Tuple of (success, response_payload)
    """
    manager = get_agent_security_manager()
    
    # Check authorization
    if not manager.authorize_interaction(sender_id, recipient_id, message_type):
        return False, {'error': 'Not authorized'}
    
    # Create secure message
    message = manager.create_secure_message(
        sender_id,
        recipient_id,
        message_type,
        payload,
        priority
    )
    
    # In production, this would send via message queue
    # For now, simulate direct delivery
    success, decrypted_payload = manager.verify_message(message, recipient_id)
    
    if success and message.requires_acknowledgment:
        ack = manager.acknowledge_message(
            message.message_id,
            recipient_id,
            'processed'
        )
    
    return success, decrypted_payload