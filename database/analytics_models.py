"""
Analytics Database Models
=========================

Extended database models for storing analytics data, performance metrics,
and business intelligence for the LegalLLM Professional platform.

Features:
- Multi-agent performance tracking
- User journey analytics storage
- Predictive model results storage
- Business intelligence metrics
- Australian legal compliance reporting data
- A/B testing experiment tracking
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, DECIMAL, Float,
    ForeignKey, JSON, Index, CheckConstraint, UniqueConstraint,
    BigInteger, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
import uuid

from shared.database.models import Base


# Analytics-specific ENUM types
analytics_event_type = ENUM(
    'agent_processing_start', 'agent_processing_complete', 'agent_collaboration_consensus',
    'agent_conflict_resolution', 'case_initiation', 'document_upload',
    'document_processing_complete', 'human_review_start', 'human_review_complete',
    'output_generation', 'workflow_completion', 'batch_processing_start',
    'batch_processing_complete', 'cache_hit', 'cache_miss', 'user_login',
    'feature_usage', 'error_occurrence', 'compliance_check',
    name='analytics_event_type',
    create_type=False
)

agent_type_enum = ENUM(
    'document_analyzer', 'legal_researcher', 'compliance_checker',
    'risk_assessor', 'financial_analyzer', 'template_generator',
    name='agent_type_enum',
    create_type=False
)

consensus_status_enum = ENUM(
    'pending', 'resolved', 'conflicted', 'escalated', 'completed',
    name='consensus_status_enum',
    create_type=False
)

journey_status_enum = ENUM(
    'started', 'in_progress', 'completed', 'abandoned', 'error',
    name='journey_status_enum',
    create_type=False
)

prediction_confidence_enum = ENUM(
    'very_low', 'low', 'medium', 'high', 'very_high',
    name='prediction_confidence_enum',
    create_type=False
)

experiment_status_enum = ENUM(
    'draft', 'running', 'paused', 'completed', 'cancelled',
    name='experiment_status_enum',
    create_type=False
)


class AnalyticsEvent(Base):
    """
    Analytics events tracking system for multi-agent performance and user behavior.
    Stores all trackable events with associated metadata for analysis.
    """
    __tablename__ = 'analytics_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=True)
    
    # Event details
    event_type = Column(analytics_event_type, nullable=False)
    event_name = Column(String(255), nullable=False)
    event_value = Column(JSON)
    
    # Metadata and context
    tags = Column(ARRAY(String), default=[])
    metadata = Column(JSON, default={})
    session_id = Column(String(255))
    
    # Performance metrics
    duration_ms = Column(Float, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    user = relationship("User")
    case = relationship("Case")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_analytics_events_firm_created', 'firm_id', 'created_at'),
        Index('idx_analytics_events_user_created', 'user_id', 'created_at'),
        Index('idx_analytics_events_type_created', 'event_type', 'created_at'),
        Index('idx_analytics_events_tags', 'tags', postgresql_using='gin'),
    )


class AgentPerformanceMetric(Base):
    """
    Performance metrics for individual AI agents in the multi-agent system.
    Tracks processing times, success rates, and collaboration effectiveness.
    """
    __tablename__ = 'agent_performance_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    
    # Agent identification
    agent_name = Column(String(100), nullable=False)
    agent_type = Column(agent_type_enum, nullable=False)
    agent_version = Column(String(50))
    
    # Performance metrics
    processing_time_ms = Column(Float, nullable=False)
    success_rate = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    accuracy_rating = Column(Float, nullable=True)  # Human-rated accuracy
    
    # Processing details
    document_count = Column(Integer, default=0)
    total_processing_time_ms = Column(Float, default=0)
    successful_operations = Column(Integer, default=0)
    failed_operations = Column(Integer, default=0)
    
    # Collaboration metrics
    collaboration_score = Column(Float, nullable=True)  # Quality of collaboration
    consensus_participation_count = Column(Integer, default=0)
    conflict_resolution_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Timestamps
    measurement_period_start = Column(DateTime(timezone=True), nullable=False)
    measurement_period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_metrics_firm_agent', 'firm_id', 'agent_name'),
        Index('idx_agent_metrics_period', 'measurement_period_start', 'measurement_period_end'),
        UniqueConstraint('firm_id', 'agent_name', 'measurement_period_start', 
                        name='uq_agent_metrics_period'),
    )


class MultiAgentConsensus(Base):
    """
    Multi-agent consensus decisions and conflict resolution tracking.
    Stores details about agent collaboration and decision-making quality.
    """
    __tablename__ = 'multi_agent_consensus'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=True)
    
    # Consensus identification
    consensus_id = Column(String(255), nullable=False, unique=True)
    consensus_type = Column(String(100))  # Type of decision being made
    
    # Participating agents
    participating_agents = Column(ARRAY(String), nullable=False)
    agent_responses = Column(JSON, default={})  # Individual agent responses
    
    # Consensus metrics
    consensus_confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    agreement_percentage = Column(Float, nullable=False)  # 0.0 to 100.0
    conflict_resolution_time_ms = Column(Float, nullable=False)
    
    # Decision details
    final_decision = Column(JSON)
    decision_rationale = Column(Text)
    human_override = Column(Boolean, default=False)
    
    # Quality assessment
    final_decision_accuracy = Column(Float, nullable=True)  # Post-evaluation accuracy
    human_satisfaction_rating = Column(Float, nullable=True)  # 1.0 to 5.0
    
    # Status and metadata
    status = Column(consensus_status_enum, default='pending')
    metadata = Column(JSON, default={})
    
    # Timestamps
    consensus_start_time = Column(DateTime(timezone=True), nullable=False)
    consensus_end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    case = relationship("Case")
    
    # Indexes
    __table_args__ = (
        Index('idx_consensus_firm_created', 'firm_id', 'created_at'),
        Index('idx_consensus_case_created', 'case_id', 'created_at'),
        Index('idx_consensus_status', 'status'),
    )


class UserJourney(Base):
    """
    User journey tracking for workflow analytics and productivity measurement.
    Captures complete user workflows from initiation to completion.
    """
    __tablename__ = 'user_journeys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'), nullable=True)
    
    # Journey identification
    journey_id = Column(String(255), nullable=False, unique=True)
    journey_type = Column(String(100))  # Type of workflow
    
    # Journey metrics
    total_duration_ms = Column(Float, nullable=True)
    productive_time_ms = Column(Float, nullable=True)  # Time spent on value-adding activities
    wait_time_ms = Column(Float, nullable=True)  # Time spent waiting
    
    # Productivity scoring
    productivity_score = Column(Float, nullable=True)  # 0.0 to 1.0
    manual_task_reduction_percentage = Column(Float, nullable=True)  # 0.0 to 100.0
    automation_utilization_rate = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Journey steps and data
    workflow_steps = Column(JSON, default=[])  # Array of step objects
    step_count = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    
    # Quality metrics
    error_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    user_satisfaction_rating = Column(Float, nullable=True)  # 1.0 to 5.0
    
    # Status and metadata
    status = Column(journey_status_enum, default='started')
    exit_point = Column(String(255))  # Where user exited if abandoned
    completion_rate = Column(Float, nullable=True)  # Percentage completed
    
    metadata = Column(JSON, default={})
    
    # Timestamps
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    user = relationship("User")
    case = relationship("Case")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_journeys_firm_user', 'firm_id', 'user_id'),
        Index('idx_user_journeys_created', 'created_at'),
        Index('idx_user_journeys_status', 'status'),
    )


class PredictiveModel(Base):
    """
    Predictive analytics models and their results for case outcome forecasting.
    Stores model predictions, confidence levels, and accuracy tracking.
    """
    __tablename__ = 'predictive_models'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    case_id = Column(UUID(as_uuid=True), ForeignKey('cases.id', ondelete='CASCADE'))
    
    # Model information
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50))
    model_type = Column(String(50))  # classification, regression, etc.
    
    # Prediction details
    predicted_outcome = Column(String(255), nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence_level = Column(prediction_confidence_enum)
    success_probability = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Case outcome predictions
    estimated_duration_days = Column(Integer, nullable=True)
    estimated_cost_aud = Column(DECIMAL(12, 2), nullable=True)
    settlement_likelihood = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Risk assessment
    risk_factors = Column(ARRAY(String), default=[])
    risk_score = Column(Float, nullable=True)  # 0.0 to 1.0 (higher = more risk)
    financial_complexity_score = Column(Float, nullable=True)
    
    # Feature importance and model explainability
    feature_importance = Column(JSON, default={})
    model_explanation = Column(Text)
    input_features = Column(JSON, default={})
    
    # Accuracy tracking
    actual_outcome = Column(String(255), nullable=True)  # Filled when case completes
    actual_duration_days = Column(Integer, nullable=True)
    actual_cost_aud = Column(DECIMAL(12, 2), nullable=True)
    prediction_accuracy = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Metadata
    prediction_context = Column(JSON, default={})
    model_parameters = Column(JSON, default={})
    
    # Timestamps
    prediction_date = Column(DateTime(timezone=True), server_default=func.now())
    outcome_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    case = relationship("Case")
    
    # Indexes
    __table_args__ = (
        Index('idx_predictions_firm_case', 'firm_id', 'case_id'),
        Index('idx_predictions_model', 'model_name', 'model_version'),
        Index('idx_predictions_confidence', 'confidence_score'),
        Index('idx_predictions_created', 'created_at'),
    )


class BusinessIntelligenceMetric(Base):
    """
    Business intelligence metrics for law firm management dashboards.
    Aggregated metrics for financial, operational, and strategic analysis.
    """
    __tablename__ = 'business_intelligence_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    
    # Metric identification
    metric_name = Column(String(100), nullable=False)
    metric_category = Column(String(50))  # financial, operational, client, etc.
    metric_type = Column(String(50))  # kpi, ratio, count, percentage, etc.
    
    # Metric values
    metric_value = Column(Float, nullable=False)
    metric_value_currency = Column(DECIMAL(12, 2), nullable=True)  # For financial metrics
    metric_value_percentage = Column(Float, nullable=True)  # For percentage metrics
    metric_value_count = Column(Integer, nullable=True)  # For count metrics
    
    # Comparison and trends
    previous_period_value = Column(Float, nullable=True)
    trend_direction = Column(String(20))  # up, down, stable
    trend_percentage = Column(Float, nullable=True)
    
    # Measurement period
    measurement_period = Column(String(50))  # daily, weekly, monthly, quarterly
    period_start_date = Column(DateTime(timezone=True), nullable=False)
    period_end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Context and metadata
    metric_description = Column(Text)
    calculation_method = Column(Text)
    data_sources = Column(ARRAY(String), default=[])
    metadata = Column(JSON, default={})
    
    # Quality indicators
    data_quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    confidence_interval = Column(JSON, nullable=True)  # Statistical confidence
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    
    # Indexes
    __table_args__ = (
        Index('idx_bi_metrics_firm_category', 'firm_id', 'metric_category'),
        Index('idx_bi_metrics_name_period', 'metric_name', 'period_start_date'),
        Index('idx_bi_metrics_calculated', 'calculated_at'),
        UniqueConstraint('firm_id', 'metric_name', 'period_start_date', 
                        name='uq_bi_metrics_period'),
    )


class ComplianceReport(Base):
    """
    Australian legal compliance reporting and monitoring.
    Automated compliance checks and audit trail maintenance.
    """
    __tablename__ = 'compliance_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    
    # Report identification
    report_type = Column(String(100), nullable=False)  # privacy_act, professional_standards, etc.
    report_period = Column(String(50))
    report_name = Column(String(255), nullable=False)
    
    # Compliance status
    overall_compliance_status = Column(String(50))  # compliant, non_compliant, partial
    compliance_score = Column(Float, nullable=True)  # 0.0 to 100.0
    
    # Compliance details
    checks_performed = Column(Integer, default=0)
    checks_passed = Column(Integer, default=0)
    checks_failed = Column(Integer, default=0)
    violations_found = Column(Integer, default=0)
    
    # Report sections
    privacy_compliance = Column(JSON, default={})
    data_retention_compliance = Column(JSON, default={})
    professional_standards_compliance = Column(JSON, default={})
    audit_trail_compliance = Column(JSON, default={})
    
    # Risk assessment
    risk_level = Column(String(20))  # low, medium, high, critical
    risk_factors = Column(ARRAY(String), default=[])
    recommended_actions = Column(ARRAY(String), default=[])
    
    # Report data
    report_data = Column(JSON, default={})
    executive_summary = Column(Text)
    detailed_findings = Column(Text)
    
    # Report period
    period_start_date = Column(DateTime(timezone=True), nullable=False)
    period_end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    
    # Indexes
    __table_args__ = (
        Index('idx_compliance_reports_firm_type', 'firm_id', 'report_type'),
        Index('idx_compliance_reports_period', 'period_start_date', 'period_end_date'),
        Index('idx_compliance_reports_status', 'overall_compliance_status'),
    )


class ABTestExperiment(Base):
    """
    A/B testing experiments for workflow optimization.
    Tracks experiment configurations, participant assignments, and results.
    """
    __tablename__ = 'ab_test_experiments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=True)
    
    # Experiment identification
    experiment_name = Column(String(255), nullable=False)
    experiment_description = Column(Text)
    experiment_hypothesis = Column(Text)
    
    # Experiment configuration
    control_variant = Column(JSON, nullable=False)  # Control group configuration
    test_variants = Column(JSON, nullable=False)  # Array of test variant configurations
    traffic_allocation = Column(JSON, default={})  # Percentage allocation to each variant
    
    # Targeting and segmentation
    target_audience = Column(JSON, default={})  # Audience targeting criteria
    exclusion_criteria = Column(JSON, default={})  # Exclusion rules
    
    # Metrics and success criteria
    primary_metric = Column(String(100), nullable=False)
    secondary_metrics = Column(ARRAY(String), default=[])
    success_criteria = Column(JSON, default={})
    minimum_sample_size = Column(Integer)
    
    # Statistical configuration
    statistical_power = Column(Float, default=0.8)  # Desired statistical power
    significance_level = Column(Float, default=0.05)  # Alpha level
    minimum_detectable_effect = Column(Float)  # Minimum effect size to detect
    
    # Experiment status and results
    status = Column(experiment_status_enum, default='draft')
    participant_count = Column(Integer, default=0)
    conversion_rate_control = Column(Float, nullable=True)
    conversion_rate_test = Column(Float, nullable=True)
    statistical_significance = Column(Boolean, nullable=True)
    confidence_interval = Column(JSON, nullable=True)
    
    # Experiment results
    results_summary = Column(JSON, default={})
    variant_performance = Column(JSON, default={})
    conclusions = Column(Text)
    recommendations = Column(Text)
    
    # Experiment timeline
    planned_start_date = Column(DateTime(timezone=True))
    planned_end_date = Column(DateTime(timezone=True))
    actual_start_date = Column(DateTime(timezone=True), nullable=True)
    actual_end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    experiment_metadata = Column(JSON, default={})
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    firm = relationship("LawFirm")
    creator = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_ab_experiments_firm_status', 'firm_id', 'status'),
        Index('idx_ab_experiments_created', 'created_at'),
        Index('idx_ab_experiments_dates', 'actual_start_date', 'actual_end_date'),
    )


class ABTestParticipant(Base):
    """
    A/B test participant assignments and individual results.
    Tracks which users are assigned to which experiment variants.
    """
    __tablename__ = 'ab_test_participants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey('ab_test_experiments.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    firm_id = Column(UUID(as_uuid=True), ForeignKey('law_firms.id', ondelete='CASCADE'))
    
    # Participant assignment
    variant_assigned = Column(String(100), nullable=False)  # control, test_a, test_b, etc.
    assignment_method = Column(String(50))  # random, targeted, etc.
    
    # Participant metrics
    converted = Column(Boolean, default=False)
    conversion_value = Column(Float, nullable=True)
    engagement_score = Column(Float, nullable=True)
    session_count = Column(Integer, default=0)
    
    # Participant data
    baseline_metrics = Column(JSON, default={})  # Pre-experiment metrics
    experiment_metrics = Column(JSON, default={})  # During-experiment metrics
    participant_metadata = Column(JSON, default={})
    
    # Timestamps
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    first_exposure_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    experiment = relationship("ABTestExperiment")
    user = relationship("User")
    firm = relationship("LawFirm")
    
    # Indexes
    __table_args__ = (
        Index('idx_ab_participants_experiment_user', 'experiment_id', 'user_id'),
        Index('idx_ab_participants_variant', 'variant_assigned'),
        Index('idx_ab_participants_converted', 'converted'),
        UniqueConstraint('experiment_id', 'user_id', name='uq_ab_participant_experiment'),
    )


# Helper function for creating analytics database tables
def create_analytics_tables(engine):
    """
    Create all analytics tables in the database.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        # Create the analytics tables
        Base.metadata.create_all(engine)
        print("Analytics database tables created successfully")
        
    except Exception as e:
        print(f"Error creating analytics tables: {e}")
        raise


# SQL for creating additional indexes and constraints
ANALYTICS_ADDITIONAL_SQL = """
-- Additional performance indexes for analytics queries

-- Composite index for time-series analytics queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_events_firm_type_time 
ON analytics_events (firm_id, event_type, created_at DESC);

-- Partial indexes for active journeys
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_journeys_active 
ON user_journeys (firm_id, user_id, start_time) 
WHERE status IN ('started', 'in_progress');

-- Index for predictive model accuracy analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_accuracy_analysis 
ON predictive_models (firm_id, model_name, prediction_accuracy) 
WHERE actual_outcome IS NOT NULL;

-- Materialized view for real-time dashboard metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_metrics_realtime AS
SELECT 
    firm_id,
    COUNT(*) FILTER (WHERE event_type = 'workflow_completion') as workflows_completed_today,
    COUNT(*) FILTER (WHERE event_type = 'document_upload') as documents_uploaded_today,
    COUNT(*) FILTER (WHERE event_type = 'agent_processing_complete') as agent_tasks_completed_today,
    AVG(duration_ms) FILTER (WHERE event_type = 'workflow_completion') as avg_workflow_duration_ms,
    COUNT(DISTINCT user_id) as active_users_today
FROM analytics_events 
WHERE created_at >= CURRENT_DATE
GROUP BY firm_id;

-- Index on the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_dashboard_metrics_firm 
ON dashboard_metrics_realtime (firm_id);

-- Function to refresh dashboard metrics (call this periodically)
CREATE OR REPLACE FUNCTION refresh_dashboard_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard_metrics_realtime;
END;
$$ LANGUAGE plpgsql;

-- Row-level security policies for multi-tenant analytics

-- Analytics events policy
CREATE POLICY IF NOT EXISTS analytics_events_tenant_isolation ON analytics_events
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- Agent performance metrics policy
CREATE POLICY IF NOT EXISTS agent_metrics_tenant_isolation ON agent_performance_metrics
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- User journeys policy
CREATE POLICY IF NOT EXISTS user_journeys_tenant_isolation ON user_journeys
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- Predictive models policy
CREATE POLICY IF NOT EXISTS predictive_models_tenant_isolation ON predictive_models
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- Business intelligence metrics policy
CREATE POLICY IF NOT EXISTS bi_metrics_tenant_isolation ON business_intelligence_metrics
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- Compliance reports policy
CREATE POLICY IF NOT EXISTS compliance_reports_tenant_isolation ON compliance_reports
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- A/B test experiments policy (can be global or firm-specific)
CREATE POLICY IF NOT EXISTS ab_experiments_tenant_isolation ON ab_test_experiments
    USING (firm_id IS NULL OR firm_id = current_setting('app.current_firm_id')::uuid);

-- A/B test participants policy
CREATE POLICY IF NOT EXISTS ab_participants_tenant_isolation ON ab_test_participants
    USING (firm_id = current_setting('app.current_firm_id')::uuid);

-- Enable RLS on all analytics tables
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE multi_agent_consensus ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_journeys ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictive_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_intelligence_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_participants ENABLE ROW LEVEL SECURITY;
"""