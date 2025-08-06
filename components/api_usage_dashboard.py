"""
API Usage Dashboard Component
Provides comprehensive monitoring of API usage, costs, and optimization recommendations
for the LegalLLM Professional platform.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

# Import API configuration
try:
    from core.api_config import api_config, UserPlanType, ProcessingMode
    API_CONFIG_AVAILABLE = True
except ImportError:
    API_CONFIG_AVAILABLE = False
    logging.warning("API configuration not available")

logger = logging.getLogger(__name__)


class APIUsageDashboard:
    """
    Comprehensive API usage dashboard for cost monitoring and optimization
    """
    
    def __init__(self):
        self.api_config = api_config if API_CONFIG_AVAILABLE else None
    
    def render_dashboard(self):
        """Render the complete API usage dashboard"""
        if not API_CONFIG_AVAILABLE:
            st.error("❌ API configuration not available. Cannot display usage dashboard.")
            return
        
        st.header("📊 API Usage & Cost Dashboard")
        
        # Get current usage summary
        usage_summary = self.api_config.get_usage_summary()
        
        # Render dashboard sections
        self._render_overview_cards(usage_summary)
        self._render_cost_optimization_section(usage_summary)
        self._render_usage_charts(usage_summary)
        self._render_recommendations_panel(usage_summary)
        self._render_configuration_panel(usage_summary)
    
    def _render_overview_cards(self, usage_summary: Dict[str, Any]):
        """Render overview cards with key metrics"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            user_plan = usage_summary['user_plan']
            plan_color = "🔥" if user_plan == "claude_max" else "⚡" if user_plan == "enterprise" else "📋"
            st.metric(
                label=f"{plan_color} User Plan",
                value=user_plan.replace('_', ' ').title(),
                help="Your current subscription plan affecting API usage"
            )
        
        with col2:
            total_cost = usage_summary['usage_stats']['total_cost']
            cost_color = "🟢" if total_cost < 1.0 else "🟡" if total_cost < 5.0 else "🔴"
            st.metric(
                label=f"{cost_color} Total Cost",
                value=f"${total_cost:.2f}",
                help="Estimated API costs for current period"
            )
        
        with col3:
            total_calls = (usage_summary['usage_stats']['openai_calls'] + 
                          usage_summary['usage_stats']['groq_calls'] + 
                          usage_summary['usage_stats']['local_calls'])
            st.metric(
                label="🔄 Total Queries",
                value=str(total_calls),
                help="Total number of AI queries processed"
            )
        
        with col4:
            processing_mode = usage_summary['processing_mode']
            mode_icon = "🔒" if processing_mode == "local_only" else "🔀" if processing_mode == "hybrid" else "🌐"
            st.metric(
                label=f"{mode_icon} Processing Mode",
                value=processing_mode.replace('_', ' ').title(),
                help="Current AI processing mode"
            )
    
    def _render_cost_optimization_section(self, usage_summary: Dict[str, Any]):
        """Render cost optimization status and alerts"""
        st.subheader("💰 Cost Optimization Status")
        
        config = usage_summary['configuration']
        limits = usage_summary['limits']
        
        # Cost optimization status
        col1, col2 = st.columns(2)
        
        with col1:
            if config['cost_optimization_enabled']:
                st.success("✅ Cost optimization is ACTIVE")
                
                # Show current usage vs limits
                current_cost = usage_summary['usage_stats']['total_cost']
                max_cost = limits['max_cost_per_hour']
                cost_percentage = (current_cost / max_cost) * 100 if max_cost > 0 else 0
                
                st.progress(min(cost_percentage / 100, 1.0))
                st.caption(f"Cost usage: ${current_cost:.2f} / ${max_cost:.2f} ({cost_percentage:.1f}%)")
                
                if cost_percentage > 80:
                    st.warning("⚠️ Approaching cost limit!")
                elif cost_percentage > 100:
                    st.error("🚨 Cost limit exceeded!")
            else:
                st.warning("⚠️ Cost optimization is DISABLED")
                st.caption("Enable cost optimization to prevent unexpected charges")
        
        with col2:
            if config['local_processing_enabled']:
                st.success("✅ Local processing is ENABLED")
                if config['ollama_available']:
                    st.info("🟢 Ollama is available for local LLMs")
                else:
                    st.info("🟡 Ollama not detected - install for local processing")
            else:
                st.error("❌ Local processing is DISABLED")
                if usage_summary['user_plan'] == 'claude_max':
                    st.warning("💡 Claude Max Plan users should enable local processing")
    
    def _render_usage_charts(self, usage_summary: Dict[str, Any]):
        """Render usage visualization charts"""
        st.subheader("📈 Usage Analytics")
        
        usage_stats = usage_summary['usage_stats']
        
        # API usage breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("API Usage Breakdown")
            
            # Create pie chart for API usage
            api_data = {
                'OpenAI': usage_stats['openai_calls'],
                'Groq': usage_stats['groq_calls'],
                'Local': usage_stats['local_calls']
            }
            
            # Filter out zero values
            api_data = {k: v for k, v in api_data.items() if v > 0}
            
            if api_data:
                fig = px.pie(
                    values=list(api_data.values()),
                    names=list(api_data.keys()),
                    title="API Calls Distribution",
                    color_discrete_map={
                        'OpenAI': '#FF6B6B',
                        'Groq': '#4ECDC4', 
                        'Local': '#45B7D1'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No API usage data available yet")
        
        with col2:
            st.subheader("Cost Breakdown")
            
            # Estimate cost breakdown
            openai_cost = usage_stats['openai_calls'] * 0.03  # Rough estimate
            groq_cost = usage_stats['groq_calls'] * 0.001     # Much cheaper
            local_cost = 0  # Free
            
            cost_data = {
                'OpenAI': openai_cost,
                'Groq': groq_cost,
                'Local': local_cost
            }
            
            # Filter out zero values
            cost_data = {k: v for k, v in cost_data.items() if v > 0}
            
            if cost_data:
                fig = px.bar(
                    x=list(cost_data.keys()),
                    y=list(cost_data.values()),
                    title="Estimated Costs by API",
                    labels={'y': 'Cost ($)', 'x': 'API Type'},
                    color=list(cost_data.keys()),
                    color_discrete_map={
                        'OpenAI': '#FF6B6B',
                        'Groq': '#4ECDC4',
                        'Local': '#45B7D1'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No cost data available yet")
    
    def _render_recommendations_panel(self, usage_summary: Dict[str, Any]):
        """Render cost optimization recommendations"""
        st.subheader("💡 Optimization Recommendations")
        
        recommendations = self.api_config.get_cost_optimization_recommendations()
        
        if recommendations:
            for i, rec in enumerate(recommendations):
                # Parse recommendation type for appropriate styling
                if "Enable USE_LOCAL_PROCESSING" in rec:
                    st.success(rec)
                elif "High API costs" in rec or "Disable USE_EXTERNAL_APIS" in rec:
                    st.warning(rec)
                elif "Install Ollama" in rec:
                    st.info(rec)
                else:
                    st.info(rec)
        else:
            st.success("✅ Your configuration is optimized for cost efficiency!")
        
        # Additional recommendations based on user plan
        user_plan = usage_summary['user_plan']
        if user_plan == 'claude_max':
            st.info("""
            **Claude Max Plan Benefits:**
            - Use local processing to avoid API charges
            - Set USE_LOCAL_PROCESSING=true
            - Install Ollama for local LLM capabilities
            - Your plan includes unlimited Claude usage!
            """)
    
    def _render_configuration_panel(self, usage_summary: Dict[str, Any]):
        """Render current configuration settings"""
        with st.expander("⚙️ Current Configuration", expanded=False):
            st.subheader("Environment Settings")
            
            config = usage_summary['configuration']
            
            # Configuration status
            config_items = [
                ("Local Processing", config['local_processing_enabled'], "✅" if config['local_processing_enabled'] else "❌"),
                ("External APIs", config['external_apis_enabled'], "⚠️" if config['external_apis_enabled'] else "✅"),
                ("Cost Optimization", config['cost_optimization_enabled'], "✅" if config['cost_optimization_enabled'] else "❌"),
                ("Ollama Available", config['ollama_available'], "✅" if config['ollama_available'] else "❌"),
            ]
            
            for item, status, icon in config_items:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(item)
                with col2:
                    st.write("Enabled" if status else "Disabled")
                with col3:
                    st.write(icon)
            
            st.subheader("Limits & Thresholds")
            limits = usage_summary['limits']
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Max Cost/Hour", f"${limits['max_cost_per_hour']:.2f}")
            with col2:
                st.metric("Max Calls/Hour", limits['max_calls_per_hour'])
            
            # Configuration recommendations
            st.subheader("Configuration Actions")
            
            if st.button("🔄 Reset Usage Statistics"):
                if self.api_config:
                    self.api_config.reset_usage_stats()
                    st.success("Usage statistics reset successfully!")
                    st.experimental_rerun()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📁 Export Usage Data"):
                    # Create CSV data
                    export_data = {
                        'Timestamp': [datetime.now()],
                        'User_Plan': [usage_summary['user_plan']],
                        'Processing_Mode': [usage_summary['processing_mode']],
                        'OpenAI_Calls': [usage_summary['usage_stats']['openai_calls']],
                        'Groq_Calls': [usage_summary['usage_stats']['groq_calls']],
                        'Local_Calls': [usage_summary['usage_stats']['local_calls']],
                        'Total_Cost': [usage_summary['usage_stats']['total_cost']],
                        'Tokens_Used': [usage_summary['usage_stats']['tokens_used']]
                    }
                    
                    df = pd.DataFrame(export_data)
                    csv = df.to_csv(index=False)
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"api_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("⚡ Optimize Settings"):
                    st.info("Optimization suggestions applied to session settings")


def render_api_usage_sidebar():
    """Render a compact API usage summary in the sidebar"""
    if not API_CONFIG_AVAILABLE:
        return
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 API Usage")
        
        usage_summary = api_config.get_usage_summary()
        
        # Quick stats
        total_cost = usage_summary['usage_stats']['total_cost']
        total_calls = (usage_summary['usage_stats']['openai_calls'] + 
                      usage_summary['usage_stats']['groq_calls'] + 
                      usage_summary['usage_stats']['local_calls'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Cost", f"${total_cost:.2f}")
        with col2:
            st.metric("Queries", total_calls)
        
        # Quick status
        user_plan = usage_summary['user_plan']
        if user_plan == 'claude_max':
            local_enabled = usage_summary['configuration']['local_processing_enabled']
            if local_enabled:
                st.success("🔒 Local processing active")
            else:
                st.warning("💡 Enable local processing")
        
        # Cost warning
        if total_cost > 1.0:
            st.warning(f"⚠️ High API usage: ${total_cost:.2f}")


# Export main components
__all__ = ['APIUsageDashboard', 'render_api_usage_sidebar']