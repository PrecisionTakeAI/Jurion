"""
API Configuration and Cost Optimization Module
Manages API usage preferences, local processing detection, and cost controls
for Claude Max Plan users and external API optimization.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class UserPlanType(Enum):
    """User subscription plan types"""
    CLAUDE_MAX = "claude_max"
    CLAUDE_PRO = "claude_pro" 
    CLAUDE_FREE = "claude_free"
    EXTERNAL_USER = "external_user"
    ENTERPRISE = "enterprise"

class ProcessingMode(Enum):
    """AI processing mode preferences"""
    LOCAL_ONLY = "local_only"           # Only local/Claude processing
    HYBRID = "hybrid"                   # Local preferred, external fallback
    EXTERNAL_ALLOWED = "external_allowed"  # External APIs allowed
    COST_OPTIMIZED = "cost_optimized"   # Minimize API costs

@dataclass
class APIUsageStats:
    """Track API usage and costs"""
    openai_calls: int = 0
    groq_calls: int = 0
    local_calls: int = 0
    estimated_cost: float = 0.0
    tokens_used: int = 0
    period_start: datetime = None
    last_reset: datetime = None

class APIConfiguration:
    """
    Central API configuration and cost optimization manager
    Handles Claude Max Plan detection and processing preferences
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.usage_stats = APIUsageStats()
        self._detect_environment()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load API configuration from environment variables"""
        return {
            # Primary API Control Flags
            'USE_LOCAL_PROCESSING': self._get_bool_env('USE_LOCAL_PROCESSING', True),
            'USE_EXTERNAL_APIS': self._get_bool_env('USE_EXTERNAL_APIS', False),
            'PREFER_LOCAL_LLMS': self._get_bool_env('PREFER_LOCAL_LLMS', True),
            'ENABLE_COST_OPTIMIZATION': self._get_bool_env('ENABLE_COST_OPTIMIZATION', True),
            
            # Claude Plan Detection
            'CLAUDE_MAX_PLAN': self._get_bool_env('CLAUDE_MAX_PLAN', False),
            'CLAUDE_CODE_SESSION': self._detect_claude_code_session(),
            'ANTHROPIC_API_AVAILABLE': self._get_bool_env('ANTHROPIC_API_AVAILABLE', True),
            
            # Processing Mode Selection
            'PROCESSING_MODE': os.getenv('PROCESSING_MODE', 'hybrid'),
            'MAX_API_COST_PER_HOUR': float(os.getenv('MAX_API_COST_PER_HOUR', '5.0')),
            'MAX_API_CALLS_PER_HOUR': int(os.getenv('MAX_API_CALLS_PER_HOUR', '100')),
            
            # API Keys (for cost tracking)
            'OPENAI_API_KEY_AVAILABLE': bool(os.getenv('OPENAI_API_KEY')),
            'GROQ_API_KEY_AVAILABLE': bool(os.getenv('GROQ_API_KEY')),
            'ANTHROPIC_API_KEY_AVAILABLE': bool(os.getenv('ANTHROPIC_API_KEY')),
            
            # Local LLM Configuration
            'OLLAMA_AVAILABLE': self._check_ollama_availability(),
            'LOCAL_LLM_MODELS': os.getenv('LOCAL_LLM_MODELS', 'llama3,mistral').split(','),
            
            # Database and Enterprise Features
            'USE_DATABASE': self._get_bool_env('USE_DATABASE', False),
            'ENTERPRISE_MODE': self._get_bool_env('ENTERPRISE_MODE', False),
        }
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable with proper parsing"""
        value = os.getenv(key, '').lower()
        if value in ['true', '1', 'yes', 'on']:
            return True
        elif value in ['false', '0', 'no', 'off']:
            return False
        return default
    
    def _detect_claude_code_session(self) -> bool:
        """Detect if running in Claude Code session"""
        # Check for Claude Code specific environment variables or patterns
        claude_indicators = [
            'CLAUDE_CODE',
            'ANTHROPIC_CLAUDE',
            'CLAUDE_IDE',
            '_CLAUDE_SESSION'
        ]
        
        for indicator in claude_indicators:
            if os.getenv(indicator):
                return True
        
        # Check for typical Claude Code execution patterns
        if os.getenv('USER') and 'claude' in os.getenv('USER', '').lower():
            return True
            
        return False
    
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is available for local processing"""
        try:
            import requests
            ollama_host = os.getenv('OLLAMA_HOST', 'localhost:11434')
            response = requests.get(f'http://{ollama_host}/api/version', timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _detect_environment(self):
        """Detect the current deployment environment and user plan"""
        # Environment detection
        if os.getenv('RAILWAY_ENVIRONMENT'):
            self.environment = 'railway'
        elif os.getenv('DOCKER_CONTAINER'):
            self.environment = 'docker'
        elif self.config['CLAUDE_CODE_SESSION']:
            self.environment = 'claude_code'
        else:
            self.environment = 'local'
            
        # User plan detection
        self.user_plan = self._detect_user_plan()
        
        logger.info(f"Environment: {self.environment}, User Plan: {self.user_plan.value}")
    
    def _detect_user_plan(self) -> UserPlanType:
        """Detect user's Claude subscription plan"""
        if self.config['CLAUDE_MAX_PLAN'] or self.config['CLAUDE_CODE_SESSION']:
            return UserPlanType.CLAUDE_MAX
        elif os.getenv('CLAUDE_PRO'):
            return UserPlanType.CLAUDE_PRO
        elif self.config['ENTERPRISE_MODE']:
            return UserPlanType.ENTERPRISE
        else:
            return UserPlanType.EXTERNAL_USER
    
    def get_processing_mode(self) -> ProcessingMode:
        """Determine the appropriate processing mode based on user plan and config"""
        # Claude Max Plan users should get local processing by default
        if self.user_plan == UserPlanType.CLAUDE_MAX:
            if self.config['USE_LOCAL_PROCESSING']:
                return ProcessingMode.LOCAL_ONLY
            else:
                return ProcessingMode.HYBRID
        
        # Enterprise users get hybrid mode
        elif self.user_plan == UserPlanType.ENTERPRISE:
            return ProcessingMode.HYBRID
        
        # External users can use external APIs
        else:
            if self.config['USE_EXTERNAL_APIS']:
                return ProcessingMode.EXTERNAL_ALLOWED
            else:
                return ProcessingMode.COST_OPTIMIZED
    
    def should_use_external_api(self, api_type: str) -> bool:
        """Determine if external API should be used based on current configuration"""
        processing_mode = self.get_processing_mode()
        
        # Local only mode - never use external APIs
        if processing_mode == ProcessingMode.LOCAL_ONLY:
            logger.info(f"🔒 Blocking {api_type} API call - LOCAL_ONLY mode for Claude Max Plan user")
            return False
        
        # Check API usage limits
        if not self._check_api_limits():
            logger.warning(f"⚠️ API usage limits exceeded - blocking {api_type} call")
            return False
        
        # Check cost optimization settings
        if self.config['ENABLE_COST_OPTIMIZATION']:
            if self.usage_stats.estimated_cost > self.config['MAX_API_COST_PER_HOUR']:
                logger.warning(f"💰 Cost limit exceeded (${self.usage_stats.estimated_cost:.2f}) - blocking {api_type}")
                return False
        
        # Hybrid mode - prefer local but allow external as fallback
        if processing_mode == ProcessingMode.HYBRID:
            if api_type == 'local' or not self.config['OLLAMA_AVAILABLE']:
                return api_type != 'local'  # Allow external if local unavailable
            return False  # Prefer local when available
        
        # External allowed mode
        if processing_mode == ProcessingMode.EXTERNAL_ALLOWED:
            return self.config['USE_EXTERNAL_APIS']
        
        # Cost optimized mode - minimize external usage
        if processing_mode == ProcessingMode.COST_OPTIMIZED:
            return False
        
        return False
    
    def _check_api_limits(self) -> bool:
        """Check if API usage is within configured limits"""
        total_calls = self.usage_stats.openai_calls + self.usage_stats.groq_calls
        
        if total_calls >= self.config['MAX_API_CALLS_PER_HOUR']:
            return False
        
        if self.usage_stats.estimated_cost >= self.config['MAX_API_COST_PER_HOUR']:
            return False
        
        return True
    
    def log_api_usage(self, api_type: str, tokens_used: int = 0, estimated_cost: float = 0.0):
        """Log API usage for monitoring and cost tracking"""
        if api_type == 'openai':
            self.usage_stats.openai_calls += 1
        elif api_type == 'groq':
            self.usage_stats.groq_calls += 1
        elif api_type == 'local':
            self.usage_stats.local_calls += 1
        
        self.usage_stats.tokens_used += tokens_used
        self.usage_stats.estimated_cost += estimated_cost
        
        # Log for transparency
        logger.info(f"📊 API Usage - {api_type}: calls={getattr(self.usage_stats, f'{api_type}_calls', 0)}, "
                   f"cost=${estimated_cost:.4f}, total_cost=${self.usage_stats.estimated_cost:.2f}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get comprehensive API usage summary"""
        return {
            'user_plan': self.user_plan.value,
            'processing_mode': self.get_processing_mode().value,
            'environment': self.environment,
            'usage_stats': {
                'openai_calls': self.usage_stats.openai_calls,
                'groq_calls': self.usage_stats.groq_calls,
                'local_calls': self.usage_stats.local_calls,
                'total_cost': self.usage_stats.estimated_cost,
                'tokens_used': self.usage_stats.tokens_used
            },
            'configuration': {
                'local_processing_enabled': self.config['USE_LOCAL_PROCESSING'],
                'external_apis_enabled': self.config['USE_EXTERNAL_APIS'],
                'cost_optimization_enabled': self.config['ENABLE_COST_OPTIMIZATION'],
                'ollama_available': self.config['OLLAMA_AVAILABLE']
            },
            'limits': {
                'max_cost_per_hour': self.config['MAX_API_COST_PER_HOUR'],
                'max_calls_per_hour': self.config['MAX_API_CALLS_PER_HOUR'],
                'within_limits': self._check_api_limits()
            }
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics (typically called hourly)"""
        self.usage_stats = APIUsageStats()
        self.usage_stats.period_start = datetime.now()
        logger.info("🔄 API usage statistics reset")
    
    def get_cost_optimization_recommendations(self) -> List[str]:
        """Get personalized cost optimization recommendations"""
        recommendations = []
        
        if self.user_plan == UserPlanType.CLAUDE_MAX:
            if not self.config['USE_LOCAL_PROCESSING']:
                recommendations.append("✅ Enable USE_LOCAL_PROCESSING=true to use your Claude Max Plan benefits")
            if self.config['USE_EXTERNAL_APIS']:
                recommendations.append("💰 Disable USE_EXTERNAL_APIS=false to avoid unnecessary charges")
        
        if self.usage_stats.estimated_cost > 1.0:
            recommendations.append(f"⚠️ High API costs detected (${self.usage_stats.estimated_cost:.2f}) - consider local processing")
        
        if not self.config['OLLAMA_AVAILABLE'] and self.config['PREFER_LOCAL_LLMS']:
            recommendations.append("🔧 Install Ollama for local LLM capabilities: https://ollama.ai")
        
        if self.config['USE_DATABASE'] and not self.config['ENABLE_COST_OPTIMIZATION']:
            recommendations.append("💡 Enable ENABLE_COST_OPTIMIZATION=true for automatic cost controls")
        
        return recommendations

# Global configuration instance
api_config = APIConfiguration()

# Export main classes and functions
__all__ = [
    'APIConfiguration', 'UserPlanType', 'ProcessingMode', 'APIUsageStats',
    'api_config'
]