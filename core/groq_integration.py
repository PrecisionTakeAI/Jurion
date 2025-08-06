"""
Groq Integration for Legal AI Platform
Enhanced AI capabilities with Kimi K2 model integration
Following the Groq Integration Guide specifications
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import hashlib

# Groq imports
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logging.warning("Groq package not installed. Install with: pip install groq")

# Environment variable loading - removed to prevent recursion
# Note: Environment variables should be loaded at application startup, not module import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
KIMI_MODEL = "moonshotai/kimi-k2-instruct"

@dataclass
class GroqValidationResult:
    """Result of Groq-powered validation"""
    approved: bool
    issues: List[str]
    required_fixes: List[str]
    recommendations: List[str]
    confidence_score: float
    analysis_details: Dict[str, Any]

@dataclass
class LegalProjectContext:
    """Comprehensive legal project context for Groq analysis"""
    structure: Dict[str, Any]
    code: Dict[str, str]
    dependencies: List[str]
    config: Dict[str, Any]
    documentation: Dict[str, str]
    tests: Dict[str, str]
    legal_business_logic: Dict[str, Any]
    legal_workflows: List[str]
    legal_data_flows: Dict[str, Any]

class LegalContextManager:
    """Manages comprehensive legal project context for Groq analysis"""
    
    def __init__(self):
        self.project_context = {}
        self.session_history = []
        self.system_state = {}
    
    def load_project(self, project_path: str) -> LegalProjectContext:
        """Load complete Legal AI project context for comprehensive understanding"""
        context = LegalProjectContext(
            structure={},
            code={},
            dependencies=[],
            config={},
            documentation={},
            tests={},
            legal_business_logic={},
            legal_workflows=[],
            legal_data_flows={}
        )
        
        try:
            # Load project structure
            context.structure = self._analyze_project_structure(project_path)
            
            # Load source code
            context.code = self._load_all_source_code(project_path)
            
            # Load dependencies
            context.dependencies = self._analyze_dependencies(project_path)
            
            # Load configuration
            context.config = self._load_configuration_files(project_path)
            
            # Load documentation
            context.documentation = self._load_documentation(project_path)
            
            # Load tests
            context.tests = self._load_test_files(project_path)
            
            # Analyze legal business logic
            context.legal_business_logic = self._extract_legal_business_logic(context.code)
            
            # Analyze legal workflows
            context.legal_workflows = self._analyze_legal_workflows(context.code)
            
            # Map legal data flows
            context.legal_data_flows = self._map_legal_data_flows(context.code)
            
            # Store context for session continuity
            self.project_context = context
            
            logger.info("Legal project context loaded successfully")
            return context
            
        except Exception as e:
            logger.error(f"Error loading legal project context: {str(e)}")
            raise
    
    def _analyze_project_structure(self, project_path: str) -> Dict[str, Any]:
        """Analyze project directory structure"""
        import os
        structure = {}
        
        for root, dirs, files in os.walk(project_path):
            rel_path = os.path.relpath(root, project_path)
            structure[rel_path] = {
                'directories': dirs,
                'files': files,
                'file_count': len(files),
                'python_files': [f for f in files if f.endswith('.py')]
            }
        
        return structure
    
    def _load_all_source_code(self, project_path: str) -> Dict[str, str]:
        """Load all source code files"""
        import os
        code = {}
        
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code[rel_path] = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read file {rel_path}: {str(e)}")
                        code[rel_path] = f"# Error reading file: {str(e)}"
        
        return code
    
    def _analyze_dependencies(self, project_path: str) -> List[str]:
        """Analyze project dependencies"""
        import os
        dependencies = []
        
        # Check requirements.txt
        req_path = os.path.join(project_path, 'requirements.txt')
        if os.path.exists(req_path):
            try:
                with open(req_path, 'r') as f:
                    dependencies.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
            except Exception as e:
                logger.warning(f"Could not read requirements.txt: {str(e)}")
        
        return dependencies
    
    def _load_configuration_files(self, project_path: str) -> Dict[str, Any]:
        """Load configuration files"""
        import os
        config = {}
        
        config_files = ['Procfile', 'railway.toml', 'railway.json', '.env', 'config.py']
        
        for config_file in config_files:
            config_path = os.path.join(project_path, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config[config_file] = f.read()
                except Exception as e:
                    logger.warning(f"Could not read {config_file}: {str(e)}")
        
        return config
    
    def _load_documentation(self, project_path: str) -> Dict[str, str]:
        """Load documentation files"""
        import os
        docs = {}
        
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith(('.md', '.txt', '.rst')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            docs[rel_path] = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read documentation {rel_path}: {str(e)}")
        
        return docs
    
    def _load_test_files(self, project_path: str) -> Dict[str, str]:
        """Load test files"""
        import os
        tests = {}
        
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if 'test' in file.lower() and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            tests[rel_path] = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read test file {rel_path}: {str(e)}")
        
        return tests
    
    def _extract_legal_business_logic(self, code: Dict[str, str]) -> Dict[str, Any]:
        """Extract legal business logic patterns from code"""
        legal_logic = {
            'jurisdiction_handling': [],
            'document_processing': [],
            'legal_analysis': [],
            'compliance_checks': []
        }
        
        for file_path, content in code.items():
            if 'jurisdiction' in content.lower():
                legal_logic['jurisdiction_handling'].append(file_path)
            if 'document' in content.lower() and 'process' in content.lower():
                legal_logic['document_processing'].append(file_path)
            if 'legal' in content.lower() and 'analy' in content.lower():
                legal_logic['legal_analysis'].append(file_path)
            if 'compliance' in content.lower() or 'regulation' in content.lower():
                legal_logic['compliance_checks'].append(file_path)
        
        return legal_logic
    
    def _analyze_legal_workflows(self, code: Dict[str, str]) -> List[str]:
        """Analyze legal workflows in the codebase"""
        workflows = []
        
        workflow_patterns = [
            'document_upload',
            'legal_analysis',
            'case_management',
            'client_consultation',
            'research_workflow'
        ]
        
        for pattern in workflow_patterns:
            for file_path, content in code.items():
                if pattern in content.lower():
                    workflows.append(f"{pattern} in {file_path}")
        
        return workflows
    
    def _map_legal_data_flows(self, code: Dict[str, str]) -> Dict[str, Any]:
        """Map legal data flows in the system"""
        data_flows = {
            'input_sources': [],
            'processing_stages': [],
            'output_destinations': [],
            'data_transformations': []
        }
        
        # Simple pattern matching for data flow analysis
        for file_path, content in code.items():
            if 'upload' in content.lower() or 'input' in content.lower():
                data_flows['input_sources'].append(file_path)
            if 'process' in content.lower() or 'analyze' in content.lower():
                data_flows['processing_stages'].append(file_path)
            if 'output' in content.lower() or 'result' in content.lower():
                data_flows['output_destinations'].append(file_path)
            if 'transform' in content.lower() or 'convert' in content.lower():
                data_flows['data_transformations'].append(file_path)
        
        return data_flows

class GroqLegalEnhancement:
    """Main Groq integration class for Legal AI enhancement"""
    
    def __init__(self):
        if not GROQ_AVAILABLE:
            raise ImportError("Groq package not available. Install with: pip install groq")
        
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = KIMI_MODEL
        self.context_manager = LegalContextManager()
        self.safety_protocols = LegalSafetyProtocols()
        
        logger.info("Groq Legal Enhancement initialized successfully")
    
    def analyze_legal_codebase(self, project_path: str) -> Dict[str, Any]:
        """Comprehensive legal codebase analysis using Kimi K2"""
        try:
            # Load project context
            codebase_context = self.context_manager.load_project(project_path)
            
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze this complete Legal AI codebase for development planning:
            
            Project Structure: {json.dumps(codebase_context.structure, indent=2)}
            Dependencies: {codebase_context.dependencies}
            Legal Business Logic: {json.dumps(codebase_context.legal_business_logic, indent=2)}
            Legal Workflows: {codebase_context.legal_workflows}
            
            Provide comprehensive analysis including:
            1. Legal AI architecture assessment and recommendations
            2. Code quality evaluation and improvement opportunities
            3. Security vulnerability identification for legal data handling
            4. Performance optimization potential for legal document processing
            5. Integration compatibility assessment with legal databases
            6. Technical debt identification and prioritization
            
            Analysis:
            """
            
            # Get Groq analysis
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=4000,
                temperature=0.1
            )
            
            analysis_result = self._process_analysis_results(response.choices[0].message.content)
            
            logger.info("Legal codebase analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in legal codebase analysis: {str(e)}")
            raise
    
    def validate_changes_before_commit(self, changes: str, branch_name: str) -> GroqValidationResult:
        """CRITICAL: Validate all changes before committing to branch"""
        try:
            # Enforce branch strategy
            if branch_name == "main":
                raise ValueError("❌ DIRECT MAIN BRANCH COMMITS PROHIBITED ❌")
            
            # Create validation prompt
            validation_prompt = f"""
            Validate these code changes before branch commit:
            
            Target Branch: {branch_name}
            Changes: {changes}
            Current System State: {self._get_current_state()}
            
            Validate:
            1. Integration compatibility with existing Legal AI code
            2. Potential breaking changes identification
            3. Security implications for legal data handling
            4. Performance impact analysis for legal document processing
            5. Testing requirements determination for legal workflows
            6. Documentation update needs for legal compliance
            
            Provide validation report with approval/rejection recommendation.
            Include confidence score (0.0-1.0) and detailed analysis.
            """
            
            # Get Groq validation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": validation_prompt}],
                max_tokens=3000,
                temperature=0.1
            )
            
            validation_result = self._process_validation_results(response.choices[0].message.content)
            
            logger.info(f"Change validation completed for branch: {branch_name}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in change validation: {str(e)}")
            raise
    
    def enhance_legal_query_processing(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance legal query processing with Groq intelligence"""
        try:
            enhancement_prompt = f"""
            Enhance this legal query processing with advanced AI capabilities:
            
            Original Query: {query}
            Context: {json.dumps(context, indent=2)}
            
            Provide enhanced response that:
            1. Demonstrates deep legal understanding
            2. Considers jurisdictional implications
            3. Identifies potential legal risks and opportunities
            4. Suggests comprehensive legal strategies
            5. Maintains professional legal standards
            
            Enhanced Response:
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": enhancement_prompt}],
                max_tokens=2000,
                temperature=0.2
            )
            
            enhanced_response = response.choices[0].message.content
            
            logger.info("Legal query processing enhanced successfully")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error in legal query enhancement: {str(e)}")
            return query  # Fallback to original query
    
    def _process_analysis_results(self, analysis_content: str) -> Dict[str, Any]:
        """Process Groq analysis results into structured format"""
        return {
            "analysis_content": analysis_content,
            "timestamp": datetime.now().isoformat(),
            "model_used": self.model,
            "analysis_type": "legal_codebase_analysis"
        }
    
    def _process_validation_results(self, validation_content: str) -> GroqValidationResult:
        """Process Groq validation results into structured format"""
        # Simple parsing - in production, this would be more sophisticated
        approved = "approved" in validation_content.lower() or "approve" in validation_content.lower()
        
        return GroqValidationResult(
            approved=approved,
            issues=[],  # Would extract from content
            required_fixes=[],  # Would extract from content
            recommendations=[],  # Would extract from content
            confidence_score=0.8,  # Would extract from content
            analysis_details={
                "content": validation_content,
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model
            }
        )
    
    def _get_current_state(self) -> Dict[str, Any]:
        """Get current system state for validation"""
        return {
            "timestamp": datetime.now().isoformat(),
            "groq_integration_active": True,
            "model": self.model,
            "context_loaded": bool(self.context_manager.project_context)
        }

class LegalSafetyProtocols:
    """Safety protocols for legal AI development"""
    
    def __init__(self):
        self.branch_protection = True
        self.validation_required = True
        
    def enforce_branch_strategy(self, target_branch: str) -> bool:
        """CRITICAL: Enforce mandatory branching strategy"""
        if target_branch == "main":
            raise SecurityError(
                "❌ DIRECT MAIN BRANCH DEPLOYMENT PROHIBITED ❌\n"
                "All changes must go through feature branches:\n"
                "1. Create feature branch\n"
                "2. Develop and test in branch\n"
                "3. Validate functionality\n"
                "4. Create pull request\n"
                "5. Review and approve\n"
                "6. Merge to main"
            )
        
        # Validate branch naming convention
        if not self._validate_branch_name(target_branch):
            raise ValueError(f"Invalid branch name: {target_branch}")
        
        return True
    
    def _validate_branch_name(self, branch_name: str) -> bool:
        """Validate branch naming convention"""
        valid_prefixes = ['feature/', 'bugfix/', 'hotfix/']
        return any(branch_name.startswith(prefix) for prefix in valid_prefixes)

class SecurityError(Exception):
    """Custom exception for security violations"""
    pass

# Export main classes
__all__ = [
    'GroqLegalEnhancement',
    'LegalContextManager', 
    'LegalSafetyProtocols',
    'GroqValidationResult',
    'LegalProjectContext'
]

