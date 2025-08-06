#!/usr/bin/env python3
"""
Multi-Agent Visualization Components for LegalLLM Professional
Advanced UI components for real-time agent monitoring and workflow visualization

Features:
- LangGraph workflow progress tracking with step-by-step updates
- Real-time agent communication visualization
- Human-in-the-loop intervention management
- Performance monitoring dashboards
- Consensus mechanism visualization
- Agent status indicators with detailed metrics
"""

import streamlit as st
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import asyncio
import threading

# Import core multi-agent components
try:
    from core.multi_agent_system import (
        AgentType, AgentResult, WorkflowState, WorkflowProgress,
        HumanIntervention, InterventionType, ConfidenceLevel
    )
    from core.multi_agent_orchestrator import LegalMultiAgentOrchestrator
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    MULTI_AGENT_AVAILABLE = False

class AgentVisualizationState(Enum):
    """Visual states for agent representation"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    COMMUNICATING = "communicating"
    WAITING_CONSENSUS = "waiting_consensus"
    COMPLETED = "completed"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class AgentStatusVisualization:
    """Enhanced agent status for visualization"""
    agent_id: str
    agent_type: AgentType
    display_name: str
    description: str
    visual_state: AgentVisualizationState
    current_task: Optional[str] = None
    progress_percentage: float = 0.0
    last_activity: Optional[datetime] = None
    communication_count: int = 0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)

@dataclass
class WorkflowVisualization:
    """Enhanced workflow visualization data"""
    workflow_id: str
    workflow_name: str
    current_phase: str
    total_phases: int
    completed_phases: int
    active_agents: List[str]
    agent_communications: List[Dict[str, Any]] = field(default_factory=list)
    decision_points: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    estimated_completion: Optional[datetime] = None
    human_interventions: List[HumanIntervention] = field(default_factory=list)

def render_agent_status_dashboard():
    """Render comprehensive agent status dashboard with real-time updates"""
    st.markdown("### 🤖 Multi-Agent System Status")
    
    # Initialize mock agent data for demonstration
    if 'agent_statuses' not in st.session_state:
        st.session_state.agent_statuses = initialize_mock_agent_data()
    
    # Auto-refresh mechanism
    if st.button("🔄 Refresh Status", help="Refresh agent status information"):
        update_agent_statuses()
        st.rerun()
    
    # Agent status grid with enhanced visualization
    render_enhanced_agent_grid()
    
    # Agent communication network
    render_agent_communication_network()
    
    # Performance comparison dashboard
    render_agent_performance_comparison()

def initialize_mock_agent_data() -> Dict[str, AgentStatusVisualization]:
    """Initialize mock agent data for demonstration"""
    agents = {
        'document_analyzer': AgentStatusVisualization(
            agent_id='document_analyzer',
            agent_type=AgentType.DOCUMENT_ANALYSIS,
            display_name='📄 Document Analyzer',
            description='Processes legal documents with OCR and parallel extraction',
            visual_state=AgentVisualizationState.PROCESSING,
            current_task='Processing batch of 25 financial documents',
            progress_percentage=67.3,
            last_activity=datetime.now() - timedelta(seconds=15),
            communication_count=8,
            performance_metrics={
                'documents_processed': 1247,
                'avg_processing_time': 2.3,
                'success_rate': 0.94,
                'uptime_percentage': 98.7
            },
            capabilities=['PDF extraction', 'OCR processing', 'Parallel processing', 'Document categorization']
        ),
        'legal_researcher': AgentStatusVisualization(
            agent_id='legal_researcher',
            agent_type=AgentType.LEGAL_RESEARCH,
            display_name='🔍 Legal Researcher',
            description='Searches precedents and analyzes Australian legal statutes',
            visual_state=AgentVisualizationState.WAITING_CONSENSUS,
            current_task='Analyzing precedents for property settlement case',
            progress_percentage=85.0,
            last_activity=datetime.now() - timedelta(seconds=3),
            communication_count=12,
            performance_metrics={
                'research_queries': 856,
                'avg_response_time': 1.8,
                'success_rate': 0.91,
                'uptime_percentage': 97.2
            },
            capabilities=['Case law research', 'Statute analysis', 'Precedent matching', 'Citation generation']
        ),
        'compliance_checker': AgentStatusVisualization(
            agent_id='compliance_checker',
            agent_type=AgentType.COMPLIANCE,
            display_name='✅ Compliance Checker',
            description='Ensures Australian legal compliance and regulatory requirements',
            visual_state=AgentVisualizationState.COMPLETED,
            current_task='Completed Form 13 compliance analysis',
            progress_percentage=100.0,
            last_activity=datetime.now() - timedelta(minutes=2),
            communication_count=5,
            performance_metrics={
                'compliance_checks': 623,
                'avg_check_time': 1.2,
                'success_rate': 0.97,
                'uptime_percentage': 99.1
            },
            capabilities=['Regulatory compliance', 'Disclosure requirements', 'Court procedures', 'Ethical compliance']
        ),
        'risk_assessor': AgentStatusVisualization(
            agent_id='risk_assessor',
            agent_type=AgentType.RISK_ANALYSIS,
            display_name='⚠️ Risk Assessor',
            description='Analyzes litigation and financial risks',
            visual_state=AgentVisualizationState.COMMUNICATING,
            current_task='Collaborating with Financial Analyzer on settlement risks',
            progress_percentage=42.8,
            last_activity=datetime.now() - timedelta(seconds=8),
            communication_count=15,
            performance_metrics={
                'risk_assessments': 445,
                'avg_assessment_time': 3.1,
                'success_rate': 0.89,
                'uptime_percentage': 96.8
            },
            capabilities=['Litigation risk', 'Financial risk', 'Strategic risk', 'Compliance risk']
        ),
        'financial_analyzer': AgentStatusVisualization(
            agent_id='financial_analyzer',
            agent_type=AgentType.FINANCIAL_ANALYSIS,
            display_name='💰 Financial Analyzer',
            description='Analyzes property settlements and financial disclosures',
            visual_state=AgentVisualizationState.PROCESSING,
            current_task='Modeling settlement scenarios for $2.8M asset pool',
            progress_percentage=73.5,
            last_activity=datetime.now() - timedelta(seconds=5),
            communication_count=9,
            performance_metrics={
                'financial_analyses': 334,
                'avg_analysis_time': 4.2,
                'success_rate': 0.93,
                'uptime_percentage': 98.3
            },
            capabilities=['Asset valuation', 'Settlement modeling', 'Tax implications', 'Maintenance calculations']
        )
    }
    
    return agents

def update_agent_statuses():
    """Update agent statuses with simulated real-time data"""
    import random
    
    for agent_id, status in st.session_state.agent_statuses.items():
        # Simulate status changes
        if random.random() < 0.3:  # 30% chance of status change
            possible_states = [
                AgentVisualizationState.PROCESSING,
                AgentVisualizationState.COMMUNICATING,
                AgentVisualizationState.WAITING_CONSENSUS,
                AgentVisualizationState.COMPLETED
            ]
            status.visual_state = random.choice(possible_states)
        
        # Update progress
        if status.visual_state == AgentVisualizationState.PROCESSING:
            status.progress_percentage = min(100.0, status.progress_percentage + random.uniform(5, 15))
        
        # Update activity timestamp
        if status.visual_state != AgentVisualizationState.IDLE:
            status.last_activity = datetime.now()
        
        # Update communication count
        if status.visual_state == AgentVisualizationState.COMMUNICATING:
            status.communication_count += random.randint(1, 3)

def render_enhanced_agent_grid():
    """Render enhanced agent status grid with detailed information"""
    st.markdown('<div class="agent-status-grid" role="region" aria-label="Agent status overview">', unsafe_allow_html=True)
    
    # Create responsive columns based on number of agents
    agents = st.session_state.agent_statuses
    cols = st.columns(min(len(agents), 3))  # Max 3 columns for readability
    
    for i, (agent_id, status) in enumerate(agents.items()):
        col_index = i % len(cols)
        
        with cols[col_index]:
            render_agent_status_card(status)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_agent_status_card(status: AgentStatusVisualization):
    """Render individual agent status card with enhanced visualization"""
    
    # Determine card styling based on agent state
    state_styles = {
        AgentVisualizationState.IDLE: {"class": "idle", "color": "#64748b"},
        AgentVisualizationState.PROCESSING: {"class": "processing", "color": "#d97706"},
        AgentVisualizationState.COMMUNICATING: {"class": "communicating", "color": "#0ea5e9"},
        AgentVisualizationState.WAITING_CONSENSUS: {"class": "waiting", "color": "#8b5cf6"},
        AgentVisualizationState.COMPLETED: {"class": "completed", "color": "#059669"},
        AgentVisualizationState.ERROR: {"class": "error", "color": "#dc2626"},
        AgentVisualizationState.OFFLINE: {"class": "offline", "color": "#6b7280"}
    }
    
    style = state_styles.get(status.visual_state, state_styles[AgentVisualizationState.IDLE])
    
    # Calculate time since last activity
    time_since_activity = "Unknown"
    if status.last_activity:
        delta = datetime.now() - status.last_activity
        if delta.total_seconds() < 60:
            time_since_activity = f"{int(delta.total_seconds())}s ago"
        else:
            time_since_activity = f"{int(delta.total_seconds() // 60)}m ago"
    
    # Create agent card HTML
    st.markdown(f"""
    <div class="agent-card {style['class']}" role="article" aria-labelledby="agent-{status.agent_id}">
        <div class="agent-status-indicator {style['class']}" 
             style="background-color: {style['color']}"
             aria-label="Agent status: {status.visual_state.value}"></div>
        
        <h4 id="agent-{status.agent_id}">{status.display_name}</h4>
        <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem;">
            {status.description}
        </p>
        
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-size: 0.875rem; font-weight: 600;">Current Task</span>
                <span style="font-size: 0.75rem; color: {style['color']};">
                    {status.visual_state.value.replace('_', ' ').title()}
                </span>
            </div>
            <p style="font-size: 0.875rem; color: var(--text-primary); margin-bottom: 0.5rem;">
                {status.current_task or 'No active task'}
            </p>
            
            {f'''<div class="progress-bar" style="height: 6px; margin-bottom: 0.5rem;">
                <div class="progress-bar-fill" style="width: {status.progress_percentage}%; background-color: {style['color']};"></div>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-secondary);">
                Progress: {status.progress_percentage:.1f}%
            </div>''' if status.progress_percentage > 0 else ''}
        </div>
        
        <div style="font-size: 0.875rem; line-height: 1.4;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span>Tasks Completed:</span>
                <strong>{status.performance_metrics.get('documents_processed', status.performance_metrics.get('research_queries', status.performance_metrics.get('compliance_checks', status.performance_metrics.get('risk_assessments', status.performance_metrics.get('financial_analyses', 0)))))}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span>Avg Response:</span>
                <strong>{status.performance_metrics.get('avg_processing_time', status.performance_metrics.get('avg_response_time', status.performance_metrics.get('avg_check_time', status.performance_metrics.get('avg_assessment_time', status.performance_metrics.get('avg_analysis_time', 0))))):.1f}s</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span>Success Rate:</span>
                <strong>{status.performance_metrics.get('success_rate', 0) * 100:.1f}%</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span>Communications:</span>
                <strong>{status.communication_count}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Last Activity:</span>
                <strong style="color: {style['color']};">{time_since_activity}</strong>
            </div>
        </div>
        
        <div style="margin-top: 1rem;">
            <details style="font-size: 0.875rem;">
                <summary style="cursor: pointer; font-weight: 600; margin-bottom: 0.5rem;">
                    Capabilities ({len(status.capabilities)})
                </summary>
                <ul style="margin: 0; padding-left: 1rem; list-style-type: disc;">
                    {''.join(f'<li>{cap}</li>' for cap in status.capabilities)}
                </ul>
            </details>
        </div>
        
        {f'<div style="margin-top: 1rem; padding: 0.5rem; background: #fee2e2; border-radius: 4px; color: #dc2626; font-size: 0.875rem;"><strong>Error:</strong> {status.error_message}</div>' if status.error_message else ''}
    </div>
    """, unsafe_allow_html=True)

def render_agent_communication_network():
    """Render agent communication network visualization"""
    st.markdown("### 🔗 Agent Communication Network")
    
    # Create communication visualization
    with st.container():
        st.markdown("""
        <div class="communication-network" style="background: white; border-radius: 12px; padding: 1.5rem; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <h4 style="margin-bottom: 1rem;">Real-Time Agent Interactions</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
        """, unsafe_allow_html=True)
        
        # Show recent communications
        communications = generate_mock_communications()
        
        for comm in communications[:6]:  # Show last 6 communications
            timestamp = comm['timestamp'].strftime('%H:%M:%S')
            
            st.markdown(f"""
            <div class="communication-item" style="background: #f8fafc; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; border-left: 4px solid {comm['color']};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="color: {comm['color']};">{comm['from']} → {comm['to']}</strong>
                    <span style="font-size: 0.75rem; color: #64748b;">{timestamp}</span>
                </div>
                <p style="font-size: 0.875rem; margin: 0; color: #1e293b;">{comm['message']}</p>
                <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #64748b;">
                    Type: {comm['type']} • Priority: {comm['priority']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)

def generate_mock_communications() -> List[Dict[str, Any]]:
    """Generate mock agent communications for demonstration"""
    import random
    
    agents = list(st.session_state.agent_statuses.keys())
    communication_types = [
        'data_request', 'consensus_vote', 'result_sharing', 'status_update', 
        'error_notification', 'task_completion', 'resource_request'
    ]
    
    colors = {
        'document_analyzer': '#d97706',
        'legal_researcher': '#0ea5e9',
        'compliance_checker': '#059669',
        'risk_assessor': '#dc2626',
        'financial_analyzer': '#8b5cf6'
    }
    
    messages = {
        'data_request': 'Requesting financial document analysis results',
        'consensus_vote': 'Voting on settlement recommendation consensus',
        'result_sharing': 'Sharing completed analysis with orchestrator',
        'status_update': 'Reporting processing status update',
        'error_notification': 'Reporting processing error for document batch',
        'task_completion': 'Completed assigned analysis task',
        'resource_request': 'Requesting additional processing resources'
    }
    
    communications = []
    
    for i in range(20):
        from_agent = random.choice(agents)
        to_agent = random.choice([a for a in agents if a != from_agent])
        comm_type = random.choice(communication_types)
        
        communications.append({
            'from': st.session_state.agent_statuses[from_agent].display_name,
            'to': st.session_state.agent_statuses[to_agent].display_name,
            'type': comm_type.replace('_', ' ').title(),
            'message': messages[comm_type],
            'timestamp': datetime.now() - timedelta(seconds=random.randint(10, 300)),
            'priority': random.choice(['Low', 'Medium', 'High']),
            'color': colors[from_agent]
        })
    
    return sorted(communications, key=lambda x: x['timestamp'], reverse=True)

def render_agent_performance_comparison():
    """Render agent performance comparison dashboard"""
    st.markdown("### 📊 Agent Performance Comparison")
    
    # Performance metrics comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Response Time Comparison")
        
        # Create performance data
        import pandas as pd
        
        performance_data = []
        for agent_id, status in st.session_state.agent_statuses.items():
            metrics = status.performance_metrics
            performance_data.append({
                'Agent': status.display_name,
                'Avg Response Time (s)': metrics.get('avg_processing_time', 
                    metrics.get('avg_response_time',
                        metrics.get('avg_check_time',
                            metrics.get('avg_assessment_time',
                                metrics.get('avg_analysis_time', 0))))),
                'Success Rate (%)': metrics.get('success_rate', 0) * 100,
                'Uptime (%)': metrics.get('uptime_percentage', 0),
                'Tasks Completed': metrics.get('documents_processed',
                    metrics.get('research_queries',
                        metrics.get('compliance_checks',
                            metrics.get('risk_assessments',
                                metrics.get('financial_analyses', 0)))))
            })
        
        df = pd.DataFrame(performance_data)
        
        # Response time chart
        st.bar_chart(df.set_index('Agent')['Avg Response Time (s)'])
    
    with col2:
        st.markdown("#### Success Rate Comparison")
        
        # Success rate chart
        st.bar_chart(df.set_index('Agent')['Success Rate (%)'])
    
    # Detailed performance table
    st.markdown("#### Detailed Performance Metrics")
    st.dataframe(df, use_container_width=True)

def render_workflow_progress_tracker():
    """Render advanced workflow progress tracking interface"""
    st.markdown("### 🔄 Workflow Progress Tracking")
    
    # Initialize mock workflow if not exists
    if 'active_workflow' not in st.session_state:
        st.session_state.active_workflow = create_mock_workflow()
    
    workflow = st.session_state.active_workflow
    
    # Workflow overview card
    st.markdown(f"""
    <div class="workflow-progress" role="region" aria-labelledby="workflow-progress">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h4 id="workflow-progress">🔄 {workflow.workflow_name}</h4>
            <div style="display: flex; gap: 1rem; align-items: center;">
                <span style="font-size: 0.875rem; color: var(--text-secondary);">
                    Phase {workflow.completed_phases + 1} of {workflow.total_phases}
                </span>
                <div style="background: #0ea5e9; color: white; padding: 0.25rem 0.75rem; border-radius: 16px; font-size: 0.75rem; font-weight: 600;">
                    {workflow.current_phase}
                </div>
            </div>
        </div>
        
        <div class="progress-bar" style="height: 12px; margin: 1rem 0;">
            <div class="progress-bar-fill" style="width: {(workflow.completed_phases / workflow.total_phases) * 100}%; background: linear-gradient(90deg, #0ea5e9, #059669);"></div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0;">
            <div>
                <strong>Active Agents:</strong> {len(workflow.active_agents)}
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    {', '.join(workflow.active_agents)}
                </div>
            </div>
            <div>
                <strong>Communications:</strong> {len(workflow.agent_communications)}
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    Last: {workflow.agent_communications[-1]['timestamp'].strftime('%H:%M:%S') if workflow.agent_communications else 'None'}
                </div>
            </div>
            <div>
                <strong>Decision Points:</strong> {len(workflow.decision_points)}
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    Pending: {sum(1 for dp in workflow.decision_points if not dp.get('resolved', False))}
                </div>
            </div>
            <div>
                <strong>ETA:</strong> 
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    {workflow.estimated_completion.strftime('%H:%M:%S') if workflow.estimated_completion else 'Calculating...'}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Phase breakdown
    render_workflow_phases(workflow)
    
    # Decision points and interventions
    if workflow.decision_points:
        render_workflow_decision_points(workflow.decision_points)
    
    # Human interventions
    if workflow.human_interventions:
        render_human_interventions_panel(workflow.human_interventions)

def create_mock_workflow() -> WorkflowVisualization:
    """Create mock workflow for demonstration"""
    workflow_id = str(uuid.uuid4())[:8]
    
    return WorkflowVisualization(
        workflow_id=workflow_id,
        workflow_name=f"Family Law Case Analysis - {workflow_id}",
        current_phase="Financial Analysis & Settlement Modeling",
        total_phases=6,
        completed_phases=3,
        active_agents=["Financial Analyzer", "Risk Assessor", "Compliance Checker"],
        agent_communications=[
            {
                'timestamp': datetime.now() - timedelta(seconds=30),
                'from': 'Document Analyzer',
                'to': 'Financial Analyzer',
                'message': 'Completed extraction of 15 financial documents',
                'type': 'data_transfer'
            },
            {
                'timestamp': datetime.now() - timedelta(seconds=45),
                'from': 'Legal Researcher',
                'to': 'Orchestrator',
                'message': 'Found 8 relevant precedents for property settlement',
                'type': 'research_results'
            }
        ],
        decision_points=[
            {
                'id': 'settlement_approach',
                'title': 'Settlement Approach Decision',
                'description': 'Choose between 50/50 split vs. needs-based adjustment',
                'options': ['Equal Split (50/50)', 'Needs-Based (55/45)', 'Contribution-Based (60/40)'],
                'resolved': False,
                'timestamp': datetime.now()
            }
        ],
        estimated_completion=datetime.now() + timedelta(minutes=12)
    )

def render_workflow_phases(workflow: WorkflowVisualization):
    """Render workflow phases with progress indicators"""
    st.markdown("#### 📋 Workflow Phases")
    
    phases = [
        {"name": "Document Upload & Validation", "status": "completed", "duration": "2m 15s"},
        {"name": "Parallel Document Analysis", "status": "completed", "duration": "4m 30s"},
        {"name": "Legal Research & Precedent Analysis", "status": "completed", "duration": "3m 45s"},
        {"name": "Financial Analysis & Settlement Modeling", "status": "active", "duration": "5m 20s (est)"},
        {"name": "Risk Assessment & Compliance Check", "status": "pending", "duration": "3m 10s (est)"},
        {"name": "Consensus Building & Final Report", "status": "pending", "duration": "2m 30s (est)"}
    ]
    
    for i, phase in enumerate(phases):
        status_colors = {
            "completed": "#059669",
            "active": "#d97706", 
            "pending": "#64748b"
        }
        
        status_icons = {
            "completed": "✅",
           "active": "🔄",
            "pending": "⏳"
        }
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; padding: 0.75rem; margin: 0.5rem 0; background: {'#f0fdf4' if phase['status'] == 'completed' else '#fffbeb' if phase['status'] == 'active' else '#f8fafc'}; border-radius: 8px; border-left: 4px solid {status_colors[phase['status']]};">
            <div style="font-size: 1.25rem; margin-right: 1rem;">
                {status_icons[phase['status']]}
            </div>
            <div style="flex-grow: 1;">
                <div style="font-weight: 600; color: {status_colors[phase['status']]};">
                    Phase {i + 1}: {phase['name']}
                </div>
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    Duration: {phase['duration']}
                </div>
            </div>
            <div style="font-size: 0.875rem; font-weight: 600; color: {status_colors[phase['status']]}; text-transform: uppercase;">
                {phase['status']}
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_workflow_decision_points(decision_points: List[Dict[str, Any]]):
    """Render workflow decision points requiring human input"""
    st.markdown("#### 🤔 Decision Points")
    
    for decision in decision_points:
        if not decision.get('resolved', False):
            st.markdown(f"""
            <div class="intervention-alert" style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 1rem; margin: 1rem 0; border-left: 4px solid #d97706;">
                <h5 style="margin-bottom: 0.5rem; color: #92400e;">
                    🤔 {decision['title']}
                </h5>
                <p style="margin-bottom: 1rem; color: #92400e;">
                    {decision['description']}
                </p>
                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                    {' '.join(f'<button onclick="selectDecision(\'{decision["id"]}\', \'{option}\')" style="background: #d97706; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">{option}</button>' for option in decision['options'])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Streamlit buttons for actual interaction
            st.write("**Select an option:**")
            cols = st.columns(len(decision['options']))
            for i, option in enumerate(decision['options']):
                with cols[i]:
                    if st.button(option, key=f"decision_{decision['id']}_{i}"):
                        st.success(f"✅ Selected: {option}")
                        decision['resolved'] = True
                        decision['selected_option'] = option
                        st.rerun()

def render_human_interventions_panel(interventions: List[HumanIntervention]):
    """Render human intervention requests panel"""
    st.markdown("#### 🚨 Human Interventions Required")
    
    for intervention in interventions:
        if not intervention.resolved_at:
            urgency_class = "urgent" if intervention.timeout_minutes < 30 else ""
            
            st.markdown(f"""
            <div class="intervention-alert {'urgent' if urgency_class else ''}" style="background: {'#fee2e2' if urgency_class else '#fef3c7'}; border: 1px solid {'#dc2626' if urgency_class else '#f59e0b'}; border-radius: 8px; padding: 1rem; margin: 1rem 0; border-left: 4px solid {'#dc2626' if urgency_class else '#d97706'};">
                <h5 style="margin-bottom: 0.5rem; color: {'#dc2626' if urgency_class else '#92400e'};">
                    {'🚨' if urgency_class else '⚠️'} {intervention.title}
                </h5>
                <p style="margin-bottom: 1rem; color: {'#dc2626' if urgency_class else '#92400e'};">
                    {intervention.description}
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; font-size: 0.875rem; color: {'#dc2626' if urgency_class else '#92400e'};">
                    <span><strong>Required Role:</strong> {intervention.required_role.value.replace('_', ' ').title()}</span>
                    <span><strong>Timeout:</strong> {intervention.timeout_minutes} minutes</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve", key=f"approve_{intervention.intervention_id}"):
                    intervention.resolved_at = datetime.now()
                    intervention.resolution = {"action": "approved", "user": "Demo User"}
                    st.success("✅ Intervention approved!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Reject", key=f"reject_{intervention.intervention_id}"):
                    intervention.resolved_at = datetime.now()
                    intervention.resolution = {"action": "rejected", "user": "Demo User"}
                    st.error("❌ Intervention rejected!")
                    st.rerun()
            
            with col3:
                if st.button("❓ Request Info", key=f"info_{intervention.intervention_id}"):
                    st.info("ℹ️ Additional information requested from agents")

def render_consensus_mechanism_visualization():
    """Render consensus mechanism visualization"""
    st.markdown("### 🤝 Agent Consensus Mechanism")
    
    # Mock consensus data
    consensus_topics = [
        {
            'topic': 'Settlement Recommendation',
            'agents_participating': 4,
            'consensus_reached': True,
            'confidence_score': 0.87,
            'majority_opinion': '50/50 property split',
            'dissenting_agents': ['Risk Assessor'],
            'dissenting_opinion': 'Recommends 55/45 split due to child care responsibilities'
        },
        {
            'topic': 'Litigation Risk Level',
            'agents_participating': 3,
            'consensus_reached': True,
            'confidence_score': 0.92,
            'majority_opinion': 'Medium risk',
            'dissenting_agents': [],
            'dissenting_opinion': None
        },
        {
            'topic': 'Compliance Status',
            'agents_participating': 2,
            'consensus_reached': False,
            'confidence_score': 0.45,
            'majority_opinion': 'Additional disclosure required',
            'dissenting_agents': ['Financial Analyzer'],
            'dissenting_opinion': 'Current disclosure sufficient for initial assessment'
        }
    ]
    
    for topic in consensus_topics:
        consensus_color = "#059669" if topic['consensus_reached'] else "#dc2626"
        consensus_icon = "✅" if topic['consensus_reached'] else "❌"
        
        st.markdown(f"""
        <div style="background: white; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h5 style="margin: 0; color: {consensus_color};">
                    {consensus_icon} {topic['topic']}
                </h5>
                <div style="background: {consensus_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 16px; font-size: 0.75rem; font-weight: 600;">
                    Confidence: {topic['confidence_score'] * 100:.1f}%
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                <div>
                    <strong>Participating Agents:</strong> {topic['agents_participating']}
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">
                        All specialized agents contributed
                    </div>
                </div>
                <div>
                    <strong>Majority Opinion:</strong>
                    <div style="font-size: 0.875rem; color: {consensus_color}; font-weight: 600;">
                        {topic['majority_opinion']}
                    </div>
                </div>
            </div>
            
            {f'''<div style="background: #fef2f2; border-radius: 8px; padding: 1rem; border-left: 4px solid #dc2626;">
                <strong style="color: #dc2626;">Dissenting Opinion:</strong>
                <div style="font-size: 0.875rem; color: #dc2626; margin-top: 0.5rem;">
                    <strong>{", ".join(topic["dissenting_agents"])}:</strong> {topic["dissenting_opinion"]}
                </div>
            </div>''' if topic['dissenting_agents'] else ''}
        </div>
        """, unsafe_allow_html=True)

# Export main functions for use in unified interface
__all__ = [
    'render_agent_status_dashboard',
    'render_workflow_progress_tracker', 
    'render_consensus_mechanism_visualization',
    'AgentStatusVisualization',
    'WorkflowVisualization',
    'AgentVisualizationState'
]