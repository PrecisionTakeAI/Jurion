"""
Real-time Analytics Dashboard Component
Advanced analytics and reporting for LegalAI Hub with Mixpanel integration
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from integrations.analytics.mixpanel_integration import get_analytics


def render_analytics_dashboard():
    """Render the main analytics dashboard."""
    st.title("📊 Analytics Dashboard")
    
    # Get user context
    if 'user_id' not in st.session_state:
        st.error("Please login to access analytics")
        return
    
    user_role = st.session_state.get('user_role', 'lawyer')
    firm_id = st.session_state.get('firm_id')
    
    # Check permissions
    if user_role not in ['principal', 'senior_lawyer', 'admin']:
        st.error("Insufficient permissions to access analytics dashboard")
        return
    
    # Analytics tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview", "👥 User Analytics", "⚖️ Case Analytics", 
        "🤖 AI Usage", "💰 Financial"
    ])
    
    with tab1:
        render_overview_analytics(firm_id, user_role)
    
    with tab2:
        render_user_analytics(firm_id)
    
    with tab3:
        render_case_analytics(firm_id)
    
    with tab4:
        render_ai_usage_analytics(firm_id)
    
    with tab5:
        render_financial_analytics(firm_id)


def render_overview_analytics(firm_id: str, user_role: str):
    """Render overview analytics dashboard."""
    st.header("📈 Overview Analytics")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            key="overview_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date", 
            value=datetime.now(),
            key="overview_end_date"
        )
    
    with col3:
        refresh_data = st.button("🔄 Refresh", key="overview_refresh")
    
    # Key Performance Indicators
    st.subheader("🎯 Key Performance Indicators")
    
    # Get KPI data
    kpi_data = get_kpi_data(firm_id, start_date, end_date)
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card(
            "Daily Active Users",
            kpi_data.get("daily_active_users", 0),
            kpi_data.get("dau_change", 0),
            "👥"
        )
    
    with col2:
        render_kpi_card(
            "Cases Created",
            kpi_data.get("cases_created", 0),
            kpi_data.get("cases_change", 0),
            "⚖️"
        )
    
    with col3:
        render_kpi_card(
            "AI Queries",
            kpi_data.get("ai_queries", 0),
            kpi_data.get("ai_queries_change", 0),
            "🤖"
        )
    
    with col4:
        render_kpi_card(
            "Documents Processed",
            kpi_data.get("documents_processed", 0),
            kpi_data.get("documents_change", 0),
            "📄"
        )
    
    # Usage trends
    st.subheader("📊 Usage Trends")
    
    # Generate trend data
    trend_data = get_usage_trend_data(firm_id, start_date, end_date)
    
    if trend_data:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Daily Active Users", "Cases Created", "AI Queries", "Document Uploads"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Daily Active Users
        fig.add_trace(
            go.Scatter(
                x=trend_data["dates"],
                y=trend_data["daily_active_users"],
                mode='lines+markers',
                name='DAU',
                line=dict(color='#1f77b4', width=3)
            ),
            row=1, col=1
        )
        
        # Cases Created
        fig.add_trace(
            go.Bar(
                x=trend_data["dates"],
                y=trend_data["cases_created"],
                name='Cases',
                marker_color='#2ca02c'
            ),
            row=1, col=2
        )
        
        # AI Queries
        fig.add_trace(
            go.Scatter(
                x=trend_data["dates"],
                y=trend_data["ai_queries"],
                mode='lines+markers',
                name='AI Queries',
                line=dict(color='#ff7f0e', width=3)
            ),
            row=2, col=1
        )
        
        # Document Uploads
        fig.add_trace(
            go.Bar(
                x=trend_data["dates"],
                y=trend_data["document_uploads"],
                name='Documents',
                marker_color='#d62728'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            title_text="Usage Trends Over Time"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Feature adoption metrics
    st.subheader("📱 Feature Adoption")
    
    feature_data = get_feature_adoption_data(firm_id, start_date, end_date)
    
    if feature_data:
        col1, col2 = st.columns(2)
        
        with col1:
            # Feature usage pie chart
            fig_pie = px.pie(
                values=list(feature_data.values()),
                names=list(feature_data.keys()),
                title="Feature Usage Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Feature adoption rates
            adoption_df = pd.DataFrame([
                {"Feature": k, "Adoption Rate": f"{v}%", "Usage Count": v}
                for k, v in feature_data.items()
            ])
            st.dataframe(adoption_df, use_container_width=True)


def render_user_analytics(firm_id: str):
    """Render user analytics dashboard."""
    st.header("👥 User Analytics")
    
    # User engagement metrics
    st.subheader("📊 User Engagement")
    
    user_data = get_user_engagement_data(firm_id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Active users chart
        if user_data.get("active_users_by_day"):
            fig = px.line(
                x=user_data["active_users_by_day"]["dates"],
                y=user_data["active_users_by_day"]["counts"],
                title="Daily Active Users",
                labels={"x": "Date", "y": "Active Users"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # User roles distribution
        if user_data.get("user_roles"):
            fig = px.pie(
                values=list(user_data["user_roles"].values()),
                names=list(user_data["user_roles"].keys()),
                title="User Roles Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # User engagement scores
    st.subheader("🎯 User Engagement Scores")
    
    engagement_data = get_user_engagement_scores(firm_id)
    
    if engagement_data:
        df = pd.DataFrame(engagement_data)
        
        fig = px.histogram(
            df, 
            x="engagement_score",
            nbins=10,
            title="User Engagement Score Distribution",
            labels={"engagement_score": "Engagement Score", "count": "Number of Users"}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top engaged users
        st.subheader("🏆 Most Engaged Users")
        top_users = df.nlargest(10, "engagement_score")[["user_name", "role", "engagement_score"]]
        st.dataframe(top_users, use_container_width=True)
    
    # User retention analysis
    st.subheader("📈 User Retention")
    
    retention_data = get_user_retention_data(firm_id)
    
    if retention_data:
        fig = px.line(
            x=retention_data["cohort_weeks"],
            y=retention_data["retention_rates"],
            title="User Retention Rate by Cohort Week",
            labels={"x": "Weeks Since First Login", "y": "Retention Rate (%)"}
        )
        st.plotly_chart(fig, use_container_width=True)


def render_case_analytics(firm_id: str):
    """Render case analytics dashboard."""
    st.header("⚖️ Case Analytics")
    
    # Case overview metrics
    st.subheader("📊 Case Overview")
    
    case_data = get_case_analytics_data(firm_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Cases",
            case_data.get("total_cases", 0),
            delta=case_data.get("cases_delta", 0)
        )
    
    with col2:
        st.metric(
            "Active Cases",
            case_data.get("active_cases", 0),
            delta=case_data.get("active_delta", 0)
        )
    
    with col3:
        st.metric(
            "Closed Cases",
            case_data.get("closed_cases", 0),
            delta=case_data.get("closed_delta", 0)
        )
    
    with col4:
        avg_duration = case_data.get("avg_case_duration", 0)
        st.metric(
            "Avg Duration (days)",
            f"{avg_duration:.1f}",
            delta=case_data.get("duration_delta", 0)
        )
    
    # Case types analysis
    col1, col2 = st.columns(2)
    
    with col1:
        if case_data.get("case_types"):
            fig = px.bar(
                x=list(case_data["case_types"].keys()),
                y=list(case_data["case_types"].values()),
                title="Cases by Type",
                labels={"x": "Case Type", "y": "Number of Cases"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if case_data.get("case_status"):
            fig = px.pie(
                values=list(case_data["case_status"].values()),
                names=list(case_data["case_status"].keys()),
                title="Cases by Status"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Case performance metrics
    st.subheader("📈 Case Performance")
    
    performance_data = get_case_performance_data(firm_id)
    
    if performance_data:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Case Resolution Time", "Case Success Rate"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Resolution time trend
        fig.add_trace(
            go.Scatter(
                x=performance_data["months"],
                y=performance_data["avg_resolution_days"],
                mode='lines+markers',
                name='Avg Resolution Time',
                line=dict(color='#1f77b4', width=3)
            ),
            row=1, col=1
        )
        
        # Success rate trend
        fig.add_trace(
            go.Scatter(
                x=performance_data["months"],
                y=performance_data["success_rates"],
                mode='lines+markers',
                name='Success Rate',
                line=dict(color='#2ca02c', width=3)
            ),
            row=1, col=2
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_ai_usage_analytics(firm_id: str):
    """Render AI usage analytics dashboard."""
    st.header("🤖 AI Usage Analytics")
    
    # AI query metrics
    st.subheader("📊 AI Query Metrics")
    
    ai_data = get_ai_usage_data(firm_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Queries",
            ai_data.get("total_queries", 0),
            delta=ai_data.get("queries_delta", 0)
        )
    
    with col2:
        st.metric(
            "Avg Response Time",
            f"{ai_data.get('avg_response_time', 0):.2f}s",
            delta=f"{ai_data.get('response_time_delta', 0):.2f}s"
        )
    
    with col3:
        st.metric(
            "Avg Confidence",
            f"{ai_data.get('avg_confidence', 0):.1f}%",
            delta=f"{ai_data.get('confidence_delta', 0):.1f}%"
        )
    
    with col4:
        st.metric(
            "Cost per Query",
            f"${ai_data.get('cost_per_query', 0):.3f}",
            delta=f"${ai_data.get('cost_delta', 0):.3f}"
        )
    
    # Query types and usage patterns
    col1, col2 = st.columns(2)
    
    with col1:
        if ai_data.get("query_types"):
            fig = px.bar(
                x=list(ai_data["query_types"].keys()),
                y=list(ai_data["query_types"].values()),
                title="AI Queries by Type",
                labels={"x": "Query Type", "y": "Number of Queries"}
            )
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if ai_data.get("confidence_distribution"):
            fig = px.histogram(
                x=ai_data["confidence_distribution"],
                nbins=10,
                title="AI Confidence Score Distribution",
                labels={"x": "Confidence Score", "y": "Frequency"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # AI cost analysis
    st.subheader("💰 AI Cost Analysis")
    
    cost_data = get_ai_cost_data(firm_id)
    
    if cost_data:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Daily AI Costs", "Cost by Model"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Daily costs
        fig.add_trace(
            go.Scatter(
                x=cost_data["dates"],
                y=cost_data["daily_costs"],
                mode='lines+markers',
                name='Daily Cost',
                line=dict(color='#ff7f0e', width=3)
            ),
            row=1, col=1
        )
        
        # Cost by model
        fig.add_trace(
            go.Bar(
                x=list(cost_data["model_costs"].keys()),
                y=list(cost_data["model_costs"].values()),
                name='Model Costs',
                marker_color='#2ca02c'
            ),
            row=1, col=2
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_financial_analytics(firm_id: str):
    """Render financial analytics dashboard."""
    st.header("💰 Financial Analytics")
    
    # Revenue metrics
    st.subheader("📊 Revenue Metrics")
    
    financial_data = get_financial_data(firm_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Monthly Revenue",
            f"${financial_data.get('monthly_revenue', 0):,.2f}",
            delta=f"${financial_data.get('revenue_delta', 0):,.2f}"
        )
    
    with col2:
        st.metric(
            "Billable Hours",
            f"{financial_data.get('billable_hours', 0):,.1f}",
            delta=f"{financial_data.get('hours_delta', 0):,.1f}"
        )
    
    with col3:
        st.metric(
            "Avg Hourly Rate",
            f"${financial_data.get('avg_hourly_rate', 0):,.2f}",
            delta=f"${financial_data.get('rate_delta', 0):,.2f}"
        )
    
    with col4:
        st.metric(
            "Collection Rate",
            f"{financial_data.get('collection_rate', 0):.1f}%",
            delta=f"{financial_data.get('collection_delta', 0):.1f}%"
        )
    
    # Revenue trends
    if financial_data.get("revenue_trend"):
        fig = px.line(
            x=financial_data["revenue_trend"]["months"],
            y=financial_data["revenue_trend"]["revenue"],
            title="Monthly Revenue Trend",
            labels={"x": "Month", "y": "Revenue ($)"}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Profitability analysis
    st.subheader("📈 Profitability Analysis")
    
    profitability_data = get_profitability_data(firm_id)
    
    if profitability_data:
        col1, col2 = st.columns(2)
        
        with col1:
            # Profit margin by case type
            fig = px.bar(
                x=list(profitability_data["case_type_margins"].keys()),
                y=list(profitability_data["case_type_margins"].values()),
                title="Profit Margin by Case Type",
                labels={"x": "Case Type", "y": "Profit Margin (%)"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Lawyer productivity
            fig = px.scatter(
                x=profitability_data["lawyer_hours"],
                y=profitability_data["lawyer_revenue"],
                title="Lawyer Productivity (Hours vs Revenue)",
                labels={"x": "Billable Hours", "y": "Revenue Generated ($)"}
            )
            st.plotly_chart(fig, use_container_width=True)


def render_kpi_card(title: str, value: Any, delta: float, icon: str):
    """Render a KPI card."""
    delta_color = "normal"
    if delta > 0:
        delta_color = "normal"
        delta_text = f"+{delta}"
    elif delta < 0:
        delta_color = "inverse"
        delta_text = str(delta)
    else:
        delta_text = "0"
    
    st.metric(
        label=f"{icon} {title}",
        value=value,
        delta=delta_text
    )


# Data fetching functions (placeholders - would integrate with actual analytics)
def get_kpi_data(firm_id: str, start_date, end_date) -> Dict[str, Any]:
    """Get KPI data for the firm."""
    # This would integrate with Mixpanel and local database
    return {
        "daily_active_users": 25,
        "dau_change": 3,
        "cases_created": 45,
        "cases_change": 5,
        "ai_queries": 235,
        "ai_queries_change": 12,
        "documents_processed": 156,
        "documents_change": -2
    }


def get_usage_trend_data(firm_id: str, start_date, end_date) -> Dict[str, List]:
    """Get usage trend data."""
    # Generate sample data
    dates = pd.date_range(start_date, end_date, freq='D')
    return {
        "dates": dates,
        "daily_active_users": [15 + i % 10 for i in range(len(dates))],
        "cases_created": [2 + i % 5 for i in range(len(dates))],
        "ai_queries": [20 + i % 15 for i in range(len(dates))],
        "document_uploads": [5 + i % 8 for i in range(len(dates))]
    }


def get_feature_adoption_data(firm_id: str, start_date, end_date) -> Dict[str, int]:
    """Get feature adoption data."""
    return {
        "Case Management": 85,
        "Document Processing": 72,
        "AI Assistant": 68,
        "Document Generation": 45,
        "Analytics": 32,
        "Integrations": 28
    }


def get_user_engagement_data(firm_id: str) -> Dict[str, Any]:
    """Get user engagement data."""
    return {
        "active_users_by_day": {
            "dates": pd.date_range("2025-01-01", "2025-01-28", freq='D'),
            "counts": [12, 15, 18, 22, 25, 23, 20, 16, 19, 24, 26, 28, 
                      25, 22, 18, 21, 24, 27, 29, 26, 23, 25, 28, 30,
                      27, 24, 26, 29]
        },
        "user_roles": {
            "Lawyers": 12,
            "Paralegals": 6,
            "Principals": 2,
            "Clients": 8
        }
    }


def get_user_engagement_scores(firm_id: str) -> List[Dict[str, Any]]:
    """Get user engagement scores."""
    return [
        {"user_name": "John Smith", "role": "Lawyer", "engagement_score": 85.2},
        {"user_name": "Jane Doe", "role": "Principal", "engagement_score": 92.1},
        {"user_name": "Bob Johnson", "role": "Paralegal", "engagement_score": 76.8},
        # ... more sample data
    ]


def get_user_retention_data(firm_id: str) -> Dict[str, List]:
    """Get user retention data."""
    return {
        "cohort_weeks": list(range(1, 13)),
        "retention_rates": [100, 85, 72, 68, 65, 62, 58, 55, 52, 50, 48, 45]
    }


def get_case_analytics_data(firm_id: str) -> Dict[str, Any]:
    """Get case analytics data."""
    return {
        "total_cases": 156,
        "cases_delta": 12,
        "active_cases": 89,
        "active_delta": 5,
        "closed_cases": 67,
        "closed_delta": 7,
        "avg_case_duration": 45.6,
        "duration_delta": -2.3,
        "case_types": {
            "Divorce": 45,
            "Property Settlement": 38,
            "Child Custody": 32,
            "Parenting Orders": 25,
            "Other": 16
        },
        "case_status": {
            "Active": 89,
            "On Hold": 12,
            "Closed": 67
        }
    }


def get_case_performance_data(firm_id: str) -> Dict[str, List]:
    """Get case performance data."""
    return {
        "months": ["Oct", "Nov", "Dec", "Jan"],
        "avg_resolution_days": [52, 48, 45, 43],
        "success_rates": [85, 87, 89, 91]
    }


def get_ai_usage_data(firm_id: str) -> Dict[str, Any]:
    """Get AI usage data."""
    return {
        "total_queries": 1245,
        "queries_delta": 156,
        "avg_response_time": 0.85,
        "response_time_delta": -0.12,
        "avg_confidence": 82.5,
        "confidence_delta": 2.1,
        "cost_per_query": 0.025,
        "cost_delta": -0.003,
        "query_types": {
            "Legal Research": 345,
            "Document Analysis": 298,
            "Case Strategy": 245,
            "Template Generation": 189,
            "General Questions": 168
        },
        "confidence_distribution": [75, 78, 82, 85, 88, 91, 84, 79, 86, 92]
    }


def get_ai_cost_data(firm_id: str) -> Dict[str, Any]:
    """Get AI cost analysis data."""
    dates = pd.date_range("2025-01-01", "2025-01-28", freq='D')
    return {
        "dates": dates,
        "daily_costs": [15.50 + i * 0.5 for i in range(len(dates))],
        "model_costs": {
            "GPT-4": 285.50,
            "GPT-3.5": 145.25,
            "Claude": 198.75,
            "Local LLM": 0.00
        }
    }


def get_financial_data(firm_id: str) -> Dict[str, Any]:
    """Get financial analytics data."""
    return {
        "monthly_revenue": 125000.00,
        "revenue_delta": 8500.00,
        "billable_hours": 420.5,
        "hours_delta": 25.3,
        "avg_hourly_rate": 350.00,
        "rate_delta": 15.00,
        "collection_rate": 92.5,
        "collection_delta": 1.2,
        "revenue_trend": {
            "months": ["Oct", "Nov", "Dec", "Jan"],
            "revenue": [108000, 115000, 122000, 125000]
        }
    }


def get_profitability_data(firm_id: str) -> Dict[str, Any]:
    """Get profitability analysis data."""
    return {
        "case_type_margins": {
            "Divorce": 65.2,
            "Property Settlement": 58.7,
            "Child Custody": 62.1,
            "Other": 55.8
        },
        "lawyer_hours": [180, 220, 195, 240, 165],
        "lawyer_revenue": [63000, 77000, 68250, 84000, 57750]
    }