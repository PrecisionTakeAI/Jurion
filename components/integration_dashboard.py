"""
Integration Monitoring Dashboard
Real-time dashboard for monitoring integration health, performance, and alerts
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from integrations.monitoring.integration_monitor import get_integration_monitor
from integrations.api.integration_manager import get_integration_manager


def render_integration_dashboard():
    """Render the integration monitoring dashboard."""
    st.title("🔗 Integration Monitoring Dashboard")
    
    # Check user permissions
    if 'user_role' not in st.session_state or st.session_state.user_role not in ['principal', 'admin', 'senior_lawyer']:
        st.error("Insufficient permissions to access integration monitoring")
        return
    
    # Initialize components (mocked for demo)
    monitor = None  # get_integration_monitor(st.session_state.db_session)
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏥 Health Status", "📊 Performance", "🚨 Alerts", "📈 Analytics", "⚙️ Configuration"
    ])
    
    with tab1:
        render_health_status_tab(monitor)
    
    with tab2:
        render_performance_tab(monitor)
    
    with tab3:
        render_alerts_tab(monitor)
    
    with tab4:
        render_analytics_tab(monitor)
    
    with tab5:
        render_configuration_tab(monitor)


def render_health_status_tab(monitor):
    """Render health status monitoring tab."""
    st.header("🏥 Integration Health Status")
    
    # Auto-refresh controls
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        auto_refresh = st.checkbox("Auto-refresh", value=True, key="health_auto_refresh")
    
    with col2:
        refresh_interval = st.select_slider(
            "Refresh interval (seconds)",
            options=[30, 60, 120, 300],
            value=60,
            key="health_refresh_interval"
        )
    
    with col3:
        if st.button("🔄 Refresh Now", key="health_refresh_now"):
            st.rerun()
    
    # Get health data (mocked for demo)
    health_data = get_mock_health_data()
    
    if health_data:
        # Health summary cards
        st.subheader("📊 Health Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            healthy_count = health_data["summary"]["healthy"]
            st.metric(
                "🟢 Healthy",
                healthy_count,
                delta=None,
                help="Integrations operating normally"
            )
        
        with col2:
            warning_count = health_data["summary"]["warning"]
            st.metric(
                "🟡 Warning",
                warning_count,
                delta=None,
                help="Integrations with performance issues"
            )
        
        with col3:
            error_count = health_data["summary"]["error"]
            st.metric(
                "🔴 Error",
                error_count,
                delta=None,
                help="Integrations with connection errors"
            )
        
        with col4:
            critical_count = health_data["summary"]["critical"]
            st.metric(
                "🚨 Critical",
                critical_count,
                delta=None,
                help="Integrations in critical state"
            )
        
        # Detailed service status
        st.subheader("🔍 Service Details")
        
        for service in health_data["services"]:
            with st.expander(f"{get_status_emoji(service['status'])} {service['service_name']}", 
                           expanded=service['status'] != 'healthy'):
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Status", service['status'].title())
                    st.metric("Response Time", f"{service['response_time_ms']:.0f}ms")
                
                with col2:
                    last_check = datetime.fromisoformat(service['last_check'])
                    time_ago = datetime.utcnow() - last_check
                    st.metric("Last Check", f"{format_time_ago(time_ago)}")
                    
                    if service.get('is_stale'):
                        st.warning("⚠️ Data is stale - check monitoring system")
                
                with col3:
                    st.metric("Integration ID", service['integration_id'])
                    
                    if service.get('error_message'):
                        st.error(f"Error: {service['error_message']}")
                
                # Response time trend (mocked)
                render_response_time_chart(service['integration_id'])
        
        # Overall health trend
        st.subheader("📈 Health Trend")
        render_health_trend_chart()
    
    else:
        st.info("No integration health data available. Ensure monitoring system is running.")
    
    # Auto-refresh logic
    if auto_refresh:
        st.empty()  # Placeholder for auto-refresh
        # In a real implementation, this would use st.rerun() with a timer


def render_performance_tab(monitor):
    """Render performance monitoring tab."""
    st.header("📊 Integration Performance")
    
    # Performance data (mocked)
    performance_data = get_mock_performance_data()
    
    if performance_data:
        # Performance metrics
        st.subheader("🎯 Performance Metrics")
        
        for integration in performance_data["integrations"]:
            st.markdown(f"### {integration['service_name']}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                success_rate = integration['success_rate']
                delta_color = "normal" if success_rate >= 95 else "inverse"
                st.metric(
                    "Success Rate",
                    f"{success_rate:.1f}%",
                    delta=f"{success_rate - 95:.1f}%",
                    delta_color=delta_color
                )
            
            with col2:
                avg_duration = integration['avg_sync_duration']
                st.metric(
                    "Avg Sync Duration",
                    f"{avg_duration:.1f}s",
                    delta=None
                )
            
            with col3:
                failed_syncs = integration['failed_syncs']
                delta_color = "normal" if failed_syncs == 0 else "inverse"
                st.metric(
                    "Failed Syncs",
                    failed_syncs,
                    delta=None,
                    delta_color=delta_color
                )
            
            with col4:
                last_sync = integration.get('last_sync')
                if last_sync:
                    last_sync_time = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                    time_since = datetime.utcnow() - last_sync_time.replace(tzinfo=None)
                    st.metric("Last Sync", format_time_ago(time_since))
                else:
                    st.metric("Last Sync", "Never")
            
            # Data volume metrics
            data_volume = integration.get('data_volume', {})
            if data_volume:
                st.markdown("**Data Volume (Last 24h)**")
                vol_col1, vol_col2, vol_col3 = st.columns(3)
                
                with vol_col1:
                    st.metric("Cases Synced", data_volume.get('cases_synced', 0))
                
                with vol_col2:
                    st.metric("Contacts Synced", data_volume.get('contacts_synced', 0))
                
                with vol_col3:
                    st.metric("Documents Synced", data_volume.get('documents_synced', 0))
        
        # Performance trends
        st.subheader("📈 Performance Trends")
        render_performance_trends_chart()
        
        # Sync success rate over time
        st.subheader("✅ Sync Success Rate")
        render_sync_success_chart()
        
        # Performance thresholds
        st.subheader("⚙️ Performance Thresholds")
        
        thresholds = performance_data.get('thresholds', {})
        threshold_df = pd.DataFrame([
            {"Metric": "Response Time Warning", "Threshold": f"{thresholds.get('response_time_warning', 2000)}ms"},
            {"Metric": "Response Time Critical", "Threshold": f"{thresholds.get('response_time_critical', 5000)}ms"},
            {"Metric": "Error Rate Warning", "Threshold": f"{thresholds.get('error_rate_warning', 5.0)}%"},
            {"Metric": "Error Rate Critical", "Threshold": f"{thresholds.get('error_rate_critical', 10.0)}%"},
            {"Metric": "Sync Failures Warning", "Threshold": f"{thresholds.get('sync_failure_warning', 3)} consecutive"},
            {"Metric": "Sync Failures Critical", "Threshold": f"{thresholds.get('sync_failure_critical', 5)} consecutive"}
        ])
        
        st.dataframe(threshold_df, use_container_width=True)


def render_alerts_tab(monitor):
    """Render alerts monitoring tab."""
    st.header("🚨 Integration Alerts")
    
    # Alert summary
    st.subheader("📊 Alert Summary")
    
    alert_data = get_mock_alert_data()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔴 Critical", alert_data["summary"]["critical"])
    
    with col2:
        st.metric("🟠 Error", alert_data["summary"]["error"])
    
    with col3:
        st.metric("🟡 Warning", alert_data["summary"]["warning"])
    
    with col4:
        st.metric("ℹ️ Info", alert_data["summary"]["info"])
    
    # Active alerts
    st.subheader("⚡ Active Alerts")
    
    if alert_data["active_alerts"]:
        for alert in alert_data["active_alerts"]:
            severity_color = {
                "critical": "🔴",
                "error": "🟠", 
                "warning": "🟡",
                "info": "ℹ️"
            }
            
            with st.container():
                st.markdown(f"""
                <div style="padding: 10px; border-left: 4px solid {'red' if alert['severity'] == 'critical' else 'orange' if alert['severity'] == 'error' else 'yellow' if alert['severity'] == 'warning' else 'blue'}; margin: 5px 0;">
                    <strong>{severity_color.get(alert['severity'], '⚠️')} {alert['service_name']}</strong><br>
                    <em>{alert['message']}</em><br>
                    <small>🕐 {datetime.fromisoformat(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Resolve Alert", key=f"resolve_{alert['id']}"):
                    st.success(f"Alert {alert['id']} marked as resolved")
                    st.rerun()
    else:
        st.success("🎉 No active alerts!")
    
    # Alert history
    st.subheader("📚 Alert History")
    
    with st.expander("View Alert History"):
        history_df = pd.DataFrame(alert_data["alert_history"])
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("No alert history available")
    
    # Alert frequency chart
    st.subheader("📊 Alert Frequency")
    render_alert_frequency_chart()


def render_analytics_tab(monitor):
    """Render integration analytics tab."""
    st.header("📈 Integration Analytics")
    
    # Time range selector
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            key="analytics_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            key="analytics_end_date"
        )
    
    # Integration usage analytics
    st.subheader("🔗 Integration Usage")
    
    usage_data = get_mock_usage_analytics(start_date, end_date)
    
    # Usage by integration
    fig_usage = px.bar(
        x=list(usage_data["by_integration"].keys()),
        y=list(usage_data["by_integration"].values()),
        title="API Calls by Integration",
        labels={"x": "Integration", "y": "API Calls"}
    )
    st.plotly_chart(fig_usage, use_container_width=True)
    
    # Sync operations over time
    st.subheader("🔄 Sync Operations")
    
    sync_df = pd.DataFrame(usage_data["sync_operations"])
    fig_sync = px.line(
        sync_df,
        x="date",
        y="operations",
        color="integration",
        title="Sync Operations Over Time"
    )
    st.plotly_chart(fig_sync, use_container_width=True)
    
    # Data transfer metrics
    st.subheader("📊 Data Transfer")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Records synced
        fig_records = px.pie(
            values=list(usage_data["records_synced"].values()),
            names=list(usage_data["records_synced"].keys()),
            title="Records Synced by Type"
        )
        st.plotly_chart(fig_records, use_container_width=True)
    
    with col2:
        # Error distribution
        fig_errors = px.pie(
            values=list(usage_data["error_distribution"].values()),
            names=list(usage_data["error_distribution"].keys()),
            title="Error Distribution by Type"
        )
        st.plotly_chart(fig_errors, use_container_width=True)
    
    # Cost analysis
    st.subheader("💰 Cost Analysis")
    
    cost_data = usage_data["cost_analysis"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total API Costs", f"${cost_data['total_cost']:.2f}")
    
    with col2:
        st.metric("Avg Cost per Call", f"${cost_data['avg_cost_per_call']:.4f}")
    
    with col3:
        st.metric("Monthly Projected", f"${cost_data['monthly_projected']:.2f}")


def render_configuration_tab(monitor):
    """Render integration configuration tab."""
    st.header("⚙️ Integration Configuration")
    
    # Available integrations
    st.subheader("🔗 Available Integrations")
    
    available_integrations = get_mock_available_integrations()
    
    for integration in available_integrations:
        with st.expander(f"{integration['name']} - {integration['type'].title()}"):
            st.write(f"**Description:** {integration['description']}")
            st.write(f"**Supported Features:** {', '.join(integration['supported_features'])}")
            
            if integration['configured']:
                st.success("✅ Configured and Active")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"Test Connection", key=f"test_{integration['provider_id']}"):
                        st.info("Testing connection...")
                        # Simulate test
                        st.success("Connection test successful!")
                
                with col2:
                    if st.button(f"Sync Now", key=f"sync_{integration['provider_id']}"):
                        st.info("Starting sync...")
                        # Simulate sync
                        st.success("Sync completed successfully!")
            else:
                st.warning("⚠️ Not Configured")
                
                if st.button(f"Configure {integration['name']}", key=f"config_{integration['provider_id']}"):
                    st.info("Opening configuration wizard...")
    
    # Monitoring settings
    st.subheader("🔧 Monitoring Settings")
    
    with st.form("monitoring_settings"):
        st.markdown("**Health Check Settings**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            health_interval = st.number_input(
                "Health Check Interval (minutes)",
                min_value=1,
                max_value=60,
                value=5
            )
            
            performance_interval = st.number_input(
                "Performance Check Interval (minutes)",
                min_value=1,
                max_value=30,
                value=1
            )
        
        with col2:
            alert_cooldown = st.number_input(
                "Alert Cooldown (minutes)",
                min_value=5,
                max_value=120,
                value=15
            )
            
            auto_resolve_hours = st.number_input(
                "Auto-resolve Alerts (hours)",
                min_value=1,
                max_value=72,
                value=24
            )
        
        st.markdown("**Performance Thresholds**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            response_warning = st.number_input(
                "Response Time Warning (ms)",
                min_value=500,
                max_value=10000,
                value=2000
            )
            
            response_critical = st.number_input(
                "Response Time Critical (ms)",
                min_value=1000,
                max_value=20000,
                value=5000
            )
        
        with col2:
            error_warning = st.number_input(
                "Error Rate Warning (%)",
                min_value=1.0,
                max_value=20.0,
                value=5.0,
                step=0.1
            )
            
            error_critical = st.number_input(
                "Error Rate Critical (%)",
                min_value=5.0,
                max_value=50.0,
                value=10.0,
                step=0.1
            )
        
        if st.form_submit_button("Save Settings"):
            st.success("Monitoring settings updated successfully!")
    
    # Alert configuration
    st.subheader("📧 Alert Configuration")
    
    with st.form("alert_settings"):
        enable_email = st.checkbox("Enable Email Alerts", value=True)
        
        if enable_email:
            email_addresses = st.text_area(
                "Email Recipients (one per line)",
                value="admin@legalfirm.com\nit@legalfirm.com"
            )
        
        enable_slack = st.checkbox("Enable Slack Alerts", value=False)
        
        if enable_slack:
            slack_webhook = st.text_input(
                "Slack Webhook URL",
                type="password",
                help="Get this from your Slack app configuration"
            )
        
        if st.form_submit_button("Save Alert Settings"):
            st.success("Alert settings updated successfully!")


# Helper functions for rendering charts
def render_response_time_chart(integration_id: str):
    """Render response time trend chart for an integration."""
    # Mock data
    dates = pd.date_range(end=datetime.now(), periods=24, freq='H')
    response_times = [200 + i * 10 + (i % 5) * 50 for i in range(24)]
    
    fig = px.line(
        x=dates,
        y=response_times,
        title=f"Response Time Trend - {integration_id}",
        labels={"x": "Time", "y": "Response Time (ms)"}
    )
    
    # Add threshold lines
    fig.add_hline(y=2000, line_dash="dash", line_color="orange", annotation_text="Warning")
    fig.add_hline(y=5000, line_dash="dash", line_color="red", annotation_text="Critical")
    
    st.plotly_chart(fig, use_container_width=True)


def render_health_trend_chart():
    """Render overall health trend chart."""
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    
    data = {
        'Date': dates,
        'Healthy': [4, 4, 3, 4, 4, 4, 4],
        'Warning': [1, 1, 2, 1, 1, 1, 1],
        'Error': [0, 0, 0, 0, 0, 0, 0],
        'Critical': [0, 0, 0, 0, 0, 0, 0]
    }
    
    df = pd.DataFrame(data)
    
    fig = px.area(
        df,
        x='Date',
        y=['Healthy', 'Warning', 'Error', 'Critical'],
        title="Integration Health Trend (7 Days)",
        color_discrete_map={
            'Healthy': '#28a745',
            'Warning': '#ffc107',
            'Error': '#dc3545',
            'Critical': '#721c24'
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_performance_trends_chart():
    """Render performance trends chart."""
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    
    # Mock data for different integrations
    leap_success = [95 + (i % 5) for i in range(30)]
    actionstep_success = [92 + (i % 7) for i in range(30)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=leap_success,
        mode='lines+markers',
        name='LEAP Success Rate',
        line=dict(color='#1f77b4')
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=actionstep_success,
        mode='lines+markers',
        name='ActionStep Success Rate',
        line=dict(color='#ff7f0e')
    ))
    
    fig.update_layout(
        title="Integration Success Rates (30 Days)",
        xaxis_title="Date",
        yaxis_title="Success Rate (%)",
        yaxis=dict(range=[80, 100])
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_sync_success_chart():
    """Render sync success rate chart."""
    integrations = ['LEAP', 'ActionStep', 'Mixpanel']
    success_rates = [97.5, 94.2, 99.1]
    
    fig = px.bar(
        x=integrations,
        y=success_rates,
        title="Sync Success Rates by Integration",
        labels={"x": "Integration", "y": "Success Rate (%)"},
        color=success_rates,
        color_continuous_scale="RdYlGn"
    )
    
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)


def render_alert_frequency_chart():
    """Render alert frequency chart."""
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    
    data = {
        'Date': dates,
        'Critical': [0, 1, 0, 0, 0, 0, 0],
        'Error': [1, 2, 1, 0, 1, 0, 1],
        'Warning': [2, 3, 2, 1, 2, 1, 2],
        'Info': [1, 1, 0, 1, 1, 0, 1]
    }
    
    df = pd.DataFrame(data)
    
    fig = px.bar(
        df,
        x='Date',
        y=['Critical', 'Error', 'Warning', 'Info'],
        title="Alert Frequency (7 Days)",
        color_discrete_map={
            'Critical': '#dc3545',
            'Error': '#fd7e14',
            'Warning': '#ffc107',
            'Info': '#17a2b8'
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)


# Mock data functions
def get_status_emoji(status: str) -> str:
    """Get emoji for health status."""
    status_emojis = {
        "healthy": "🟢",
        "warning": "🟡",
        "error": "🔴",
        "critical": "🚨",
        "unknown": "⚪"
    }
    return status_emojis.get(status, "⚪")


def format_time_ago(time_delta: timedelta) -> str:
    """Format timedelta as human-readable time ago."""
    seconds = int(time_delta.total_seconds())
    
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    else:
        return f"{seconds // 86400}d ago"


def get_mock_health_data() -> Dict[str, Any]:
    """Get mock health data for demonstration."""
    return {
        "summary": {
            "healthy": 3,
            "warning": 1,
            "error": 0,
            "critical": 0,
            "unknown": 0
        },
        "services": [
            {
                "integration_id": "firm_123_leap",
                "service_name": "LEAP Legal Software",
                "status": "healthy",
                "response_time_ms": 245.5,
                "last_check": datetime.utcnow().isoformat(),
                "is_stale": False,
                "error_message": None
            },
            {
                "integration_id": "firm_123_actionstep",
                "service_name": "ActionStep",
                "status": "warning",
                "response_time_ms": 2100.0,
                "last_check": datetime.utcnow().isoformat(),
                "is_stale": False,
                "error_message": "Slow response time"
            },
            {
                "integration_id": "firm_123_mixpanel",
                "service_name": "Mixpanel Analytics",
                "status": "healthy",
                "response_time_ms": 150.2,
                "last_check": datetime.utcnow().isoformat(),
                "is_stale": False,
                "error_message": None
            }
        ],
        "last_updated": datetime.utcnow().isoformat()
    }


def get_mock_performance_data() -> Dict[str, Any]:
    """Get mock performance data for demonstration."""
    return {
        "integrations": [
            {
                "integration_id": "firm_123_leap",
                "service_name": "LEAP Legal Software",
                "success_rate": 97.5,
                "avg_sync_duration": 45.2,
                "failed_syncs": 1,
                "last_sync": "2025-01-28T14:30:00Z",
                "data_volume": {
                    "cases_synced": 25,
                    "contacts_synced": 18,
                    "documents_synced": 42
                }
            },
            {
                "integration_id": "firm_123_actionstep",
                "service_name": "ActionStep",
                "success_rate": 94.2,
                "avg_sync_duration": 62.8,
                "failed_syncs": 2,
                "last_sync": "2025-01-28T13:45:00Z",
                "data_volume": {
                    "cases_synced": 18,
                    "contacts_synced": 12,
                    "documents_synced": 28
                }
            },
            {
                "integration_id": "firm_123_mixpanel",
                "service_name": "Mixpanel Analytics",
                "success_rate": 99.1,
                "avg_sync_duration": 12.5,
                "failed_syncs": 0,
                "last_sync": "2025-01-28T14:55:00Z",
                "data_volume": {
                    "events_tracked": 1250,
                    "users_identified": 45,
                    "properties_updated": 89
                }
            }
        ],
        "thresholds": {
            "response_time_warning": 2000,
            "response_time_critical": 5000,
            "error_rate_warning": 5.0,
            "error_rate_critical": 10.0,
            "sync_failure_warning": 3,
            "sync_failure_critical": 5
        },
        "last_updated": datetime.utcnow().isoformat()
    }


def get_mock_alert_data() -> Dict[str, Any]:
    """Get mock alert data for demonstration."""
    return {
        "summary": {
            "critical": 0,
            "error": 0,
            "warning": 1,
            "info": 0
        },
        "active_alerts": [
            {
                "id": "performance_firm_123_actionstep_response_time",
                "service_name": "ActionStep",
                "severity": "warning",
                "message": "High response time: 2100ms (threshold: 2000ms)",
                "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                "resolved": False
            }
        ],
        "alert_history": [
            {
                "Service": "LEAP",
                "Severity": "Warning",
                "Message": "Rate limit exceeded",
                "Timestamp": "2025-01-27 14:22:00",
                "Resolved": "Yes",
                "Duration": "5 minutes"
            },
            {
                "Service": "Mixpanel",
                "Severity": "Error",
                "Message": "Authentication failed",
                "Timestamp": "2025-01-26 09:15:00",
                "Resolved": "Yes",
                "Duration": "2 hours"
            }
        ]
    }


def get_mock_usage_analytics(start_date, end_date) -> Dict[str, Any]:
    """Get mock usage analytics data."""
    return {
        "by_integration": {
            "LEAP": 1250,
            "ActionStep": 890,
            "Mixpanel": 2100
        },
        "sync_operations": [
            {"date": "2025-01-20", "integration": "LEAP", "operations": 24},
            {"date": "2025-01-21", "integration": "LEAP", "operations": 28},
            {"date": "2025-01-22", "integration": "LEAP", "operations": 22},
            {"date": "2025-01-20", "integration": "ActionStep", "operations": 18},
            {"date": "2025-01-21", "integration": "ActionStep", "operations": 20},
            {"date": "2025-01-22", "integration": "ActionStep", "operations": 16}
        ],
        "records_synced": {
            "Cases": 125,
            "Contacts": 89,
            "Documents": 234,
            "Events": 1250
        },
        "error_distribution": {
            "Rate Limit": 5,
            "Authentication": 2,
            "Network": 3,
            "Validation": 1
        },
        "cost_analysis": {
            "total_cost": 125.50,
            "avg_cost_per_call": 0.0285,
            "monthly_projected": 385.20
        }
    }


def get_mock_available_integrations() -> List[Dict[str, Any]]:
    """Get mock available integrations data."""
    return [
        {
            "provider_id": "leap",
            "name": "LEAP Legal Software",
            "type": "practice_management",
            "description": "Practice management integration with LEAP",
            "supported_features": ["cases", "contacts", "documents", "time_tracking"],
            "configured": True
        },
        {
            "provider_id": "actionstep",
            "name": "ActionStep",
            "type": "practice_management", 
            "description": "Practice management integration with ActionStep",
            "supported_features": ["cases", "contacts", "documents", "workflows"],
            "configured": True
        },
        {
            "provider_id": "mixpanel",
            "name": "Mixpanel Analytics",
            "type": "analytics",
            "description": "Advanced analytics and user behavior tracking",
            "supported_features": ["event_tracking", "user_identification", "funnel_analysis"],
            "configured": True
        },
        {
            "provider_id": "xero",
            "name": "Xero Accounting",
            "type": "accounting",
            "description": "Financial management and accounting integration",
            "supported_features": ["invoicing", "expenses", "reporting"],
            "configured": False
        }
    ]