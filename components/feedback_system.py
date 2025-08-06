"""
User Feedback System and Survey Component
Comprehensive feedback collection, NPS tracking, and user satisfaction surveys
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum


class SurveyType(Enum):
    """Types of surveys available."""
    NPS = "nps"
    FEATURE_FEEDBACK = "feature_feedback"
    ONBOARDING = "onboarding"
    QUARTERLY_SATISFACTION = "quarterly_satisfaction"
    POST_CASE_COMPLETION = "post_case_completion"
    AI_EXPERIENCE = "ai_experience"


class FeedbackType(Enum):
    """Types of feedback."""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    GENERAL_FEEDBACK = "general_feedback"
    SUPPORT_REQUEST = "support_request"


@dataclass
class FeedbackSubmission:
    """Feedback submission data structure."""
    id: str
    user_id: str
    firm_id: str
    feedback_type: str
    title: str
    description: str
    rating: Optional[int]
    category: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    attachments: List[str]
    tags: List[str]
    
    
@dataclass
class SurveyResponse:
    """Survey response data structure."""
    id: str
    survey_id: str
    user_id: str
    firm_id: str
    survey_type: str
    responses: Dict[str, Any]
    nps_score: Optional[int]
    completion_time: int  # seconds
    created_at: datetime


class FeedbackManager:
    """Manages feedback collection and surveys."""
    
    def __init__(self):
        """Initialize feedback manager."""
        self.logger = logging.getLogger(__name__)
        
    def render_feedback_widget(self, context: str = "general"):
        """Render floating feedback widget."""
        
        # Feedback widget in sidebar
        with st.sidebar:
            st.markdown("---")
            st.subheader("💬 Quick Feedback")
            
            with st.expander("Send Feedback", expanded=False):
                feedback_type = st.selectbox(
                    "Feedback Type",
                    options=["Bug Report", "Feature Request", "General Feedback", "Support Request"],
                    key=f"feedback_type_{context}"
                )
                
                rating = st.slider(
                    "How would you rate this feature?",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"feedback_rating_{context}"
                )
                
                feedback_text = st.text_area(
                    "Tell us more:",
                    placeholder="Share your thoughts, report issues, or suggest improvements...",
                    key=f"feedback_text_{context}"
                )
                
                if st.button("Send Feedback", key=f"send_feedback_{context}"):
                    if feedback_text:
                        success = self.submit_feedback(
                            feedback_type=feedback_type.lower().replace(" ", "_"),
                            title=f"{feedback_type} - {context}",
                            description=feedback_text,
                            rating=rating,
                            context=context
                        )
                        
                        if success:
                            st.success("Thank you for your feedback!")
                            st.balloons()
                        else:
                            st.error("Failed to submit feedback. Please try again.")
                    else:
                        st.warning("Please provide feedback text.")
    
    def render_nps_survey(self, trigger_condition: str = "quarterly"):
        """Render Net Promoter Score survey."""
        
        # Check if user should see NPS survey
        if not self._should_show_nps_survey(trigger_condition):
            return
        
        st.markdown("---")
        st.info("📊 Help us improve! Your feedback is valuable.")
        
        with st.container():
            st.subheader("Net Promoter Score Survey")
            st.write("How likely are you to recommend LegalAI Hub to a colleague?")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                nps_score = st.slider(
                    "Rating (0 = Not at all likely, 10 = Extremely likely)",
                    min_value=0,
                    max_value=10,
                    value=7,
                    key="nps_score"
                )
                
                # Get NPS category
                if nps_score >= 9:
                    category = "Promoter"
                    color = "green"
                elif nps_score >= 7:
                    category = "Passive"
                    color = "orange"
                else:
                    category = "Detractor"
                    color = "red"
                
                st.markdown(f"**Category:** :{color}[{category}]")
            
            with col2:
                st.metric("Your Score", nps_score, delta=None)
            
            # Follow-up question based on score
            if nps_score >= 9:
                follow_up_prompt = "What do you like most about LegalAI Hub?"
            elif nps_score >= 7:
                follow_up_prompt = "What could we do to improve your experience?"
            else:
                follow_up_prompt = "What's the primary reason for your score?"
            
            nps_comment = st.text_area(
                follow_up_prompt,
                placeholder="Your feedback helps us improve...",
                key="nps_comment"
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("Submit NPS Survey", type="primary"):
                    success = self.submit_nps_survey(nps_score, nps_comment)
                    
                    if success:
                        st.success("Thank you for your feedback!")
                        st.session_state.nps_survey_completed = True
                        st.rerun()
                    else:
                        st.error("Failed to submit survey. Please try again.")
    
    def render_feature_feedback_survey(self, feature_name: str):
        """Render feature-specific feedback survey."""
        
        st.subheader(f"📝 {feature_name} Feedback")
        
        # Feature satisfaction
        satisfaction = st.radio(
            "How satisfied are you with this feature?",
            options=["Very Dissatisfied", "Dissatisfied", "Neutral", "Satisfied", "Very Satisfied"],
            index=3,
            key=f"satisfaction_{feature_name}"
        )
        
        # Ease of use
        ease_of_use = st.slider(
            "How easy is this feature to use?",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = Very Difficult, 5 = Very Easy",
            key=f"ease_{feature_name}"
        )
        
        # Feature importance
        importance = st.slider(
            "How important is this feature to your workflow?",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = Not Important, 5 = Critical",
            key=f"importance_{feature_name}"
        )
        
        # Specific feedback
        specific_feedback = st.text_area(
            "Specific feedback or suggestions:",
            placeholder="What works well? What could be improved?",
            key=f"specific_{feature_name}"
        )
        
        # Feature requests
        feature_requests = st.text_area(
            "Related features you'd like to see:",
            placeholder="What additional functionality would be helpful?",
            key=f"requests_{feature_name}"
        )
        
        if st.button(f"Submit {feature_name} Feedback", key=f"submit_{feature_name}"):
            feedback_data = {
                "feature_name": feature_name,
                "satisfaction": satisfaction,
                "ease_of_use": ease_of_use,
                "importance": importance,
                "specific_feedback": specific_feedback,
                "feature_requests": feature_requests
            }
            
            success = self.submit_feature_feedback(feature_name, feedback_data)
            
            if success:
                st.success("Thank you for your detailed feedback!")
            else:
                st.error("Failed to submit feedback. Please try again.")
    
    def render_post_case_survey(self, case_id: str):
        """Render post-case completion survey."""
        
        st.subheader("📋 Case Completion Survey")
        st.write("Help us understand how LegalAI Hub supported your case.")
        
        # Overall case management experience
        overall_experience = st.radio(
            "Overall, how would you rate your case management experience?",
            options=["Poor", "Fair", "Good", "Very Good", "Excellent"],
            index=2,
            key=f"overall_{case_id}"
        )
        
        # Specific ratings
        col1, col2 = st.columns(2)
        
        with col1:
            case_organization = st.slider(
                "Case Organization",
                min_value=1,
                max_value=5,
                value=3,
                key=f"organization_{case_id}"
            )
            
            document_management = st.slider(
                "Document Management",
                min_value=1,
                max_value=5,
                value=3,
                key=f"documents_{case_id}"
            )
        
        with col2:
            ai_assistance = st.slider(
                "AI Assistant Helpfulness",
                min_value=1,
                max_value=5,
                value=3,
                key=f"ai_{case_id}"
            )
            
            time_saved = st.slider(
                "Time Saved vs. Traditional Methods",
                min_value=1,
                max_value=5,
                value=3,
                help="1 = No time saved, 5 = Significant time saved",
                key=f"time_{case_id}"
            )
        
        # Most helpful features
        helpful_features = st.multiselect(
            "Which features were most helpful for this case?",
            options=[
                "Case Timeline", "Document Upload", "AI Legal Research",
                "Document Generation", "Client Communication", "Task Management",
                "Calendar Integration", "Billing Tracking", "Team Collaboration"
            ],
            key=f"helpful_{case_id}"
        )
        
        # Areas for improvement
        improvements = st.text_area(
            "What could we improve for future cases?",
            placeholder="Specific suggestions for better case management...",
            key=f"improvements_{case_id}"
        )
        
        # Success metrics
        st.subheader("Case Outcome")
        
        case_outcome = st.radio(
            "How would you rate the case outcome?",
            options=["Poor", "Fair", "Good", "Very Good", "Excellent"],
            index=2,
            key=f"outcome_{case_id}"
        )
        
        client_satisfaction = st.slider(
            "Client Satisfaction (if applicable)",
            min_value=1,
            max_value=5,
            value=3,
            key=f"client_sat_{case_id}"
        )
        
        if st.button(f"Submit Case Survey", key=f"submit_case_{case_id}"):
            survey_data = {
                "case_id": case_id,
                "overall_experience": overall_experience,
                "case_organization": case_organization,
                "document_management": document_management,
                "ai_assistance": ai_assistance,
                "time_saved": time_saved,
                "helpful_features": helpful_features,
                "improvements": improvements,
                "case_outcome": case_outcome,
                "client_satisfaction": client_satisfaction
            }
            
            success = self.submit_case_survey(case_id, survey_data)
            
            if success:
                st.success("Thank you for completing the case survey!")
            else:
                st.error("Failed to submit survey. Please try again.")
    
    def render_ai_experience_survey(self):
        """Render AI experience feedback survey."""
        
        st.subheader("🤖 AI Assistant Experience")
        
        # AI usage frequency
        usage_frequency = st.radio(
            "How often do you use the AI Assistant?",
            options=["Never", "Rarely", "Sometimes", "Often", "Very Often"],
            index=2,
            key="ai_frequency"
        )
        
        if usage_frequency != "Never":
            # AI helpfulness ratings
            col1, col2 = st.columns(2)
            
            with col1:
                accuracy = st.slider(
                    "AI Response Accuracy",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="ai_accuracy"
                )
                
                speed = st.slider(
                    "Response Speed",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="ai_speed"
                )
            
            with col2:
                relevance = st.slider(
                    "Response Relevance",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="ai_relevance"
                )
                
                understanding = st.slider(
                    "Understanding of Legal Context",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="ai_understanding"
                )
            
            # Most useful AI features
            useful_ai_features = st.multiselect(
                "Which AI features do you find most useful?",
                options=[
                    "Legal Research", "Document Analysis", "Document Generation",
                    "Case Strategy Suggestions", "Legal Citations", "Contract Review",
                    "Question Answering", "Precedent Search"
                ],
                key="useful_ai_features"
            )
            
            # AI improvement suggestions
            ai_improvements = st.text_area(
                "How can we improve the AI Assistant?",
                placeholder="Suggestions for better AI responses, new features, etc.",
                key="ai_improvements"
            )
            
            # Trust and confidence
            trust_level = st.slider(
                "How much do you trust AI-generated responses?",
                min_value=1,
                max_value=5,
                value=3,
                help="1 = Don't trust at all, 5 = Trust completely",
                key="ai_trust"
            )
        
        if st.button("Submit AI Experience Survey"):
            ai_survey_data = {
                "usage_frequency": usage_frequency,
                "accuracy": accuracy if usage_frequency != "Never" else None,
                "speed": speed if usage_frequency != "Never" else None,
                "relevance": relevance if usage_frequency != "Never" else None,
                "understanding": understanding if usage_frequency != "Never" else None,
                "useful_features": useful_ai_features if usage_frequency != "Never" else [],
                "improvements": ai_improvements if usage_frequency != "Never" else "",
                "trust_level": trust_level if usage_frequency != "Never" else None
            }
            
            success = self.submit_ai_survey(ai_survey_data)
            
            if success:
                st.success("Thank you for your AI experience feedback!")
            else:
                st.error("Failed to submit survey. Please try again.")
    
    def render_feedback_analytics(self):
        """Render feedback analytics dashboard for admins."""
        
        if 'user_role' not in st.session_state or st.session_state.user_role not in ['principal', 'admin']:
            st.error("Insufficient permissions to view feedback analytics")
            return
        
        st.header("📊 Feedback Analytics")
        
        # Feedback summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Feedback", "156", delta="12")
        
        with col2:
            st.metric("Avg NPS Score", "72", delta="5")
        
        with col3:
            st.metric("Response Rate", "68%", delta="3%")
        
        with col4:
            st.metric("Satisfaction Score", "4.2/5", delta="0.1")
        
        # Feedback trends
        feedback_data = self.get_feedback_trends()
        if feedback_data:
            st.subheader("📈 Feedback Trends")
            
            # Create sample chart
            import plotly.express as px
            df = pd.DataFrame({
                'Date': pd.date_range('2025-01-01', periods=30, freq='D'),
                'Feedback Count': [5 + i % 8 for i in range(30)],
                'NPS Score': [70 + (i % 15) for i in range(30)]
            })
            
            fig = px.line(df, x='Date', y=['Feedback Count', 'NPS Score'], 
                         title="Feedback Volume and NPS Trends")
            st.plotly_chart(fig, use_container_width=True)
        
        # Feature feedback breakdown
        st.subheader("🔧 Feature Feedback")
        
        feature_feedback = self.get_feature_feedback_summary()
        if feature_feedback:
            df = pd.DataFrame(feature_feedback)
            st.dataframe(df, use_container_width=True)
        
        # Recent feedback
        st.subheader("💬 Recent Feedback")
        
        recent_feedback = self.get_recent_feedback()
        if recent_feedback:
            for feedback in recent_feedback[:5]:
                with st.expander(f"{feedback['type']} - {feedback['title']}"):
                    st.write(f"**Rating:** {feedback['rating']}/5")
                    st.write(f"**User:** {feedback['user']}")
                    st.write(f"**Date:** {feedback['date']}")
                    st.write(f"**Feedback:** {feedback['description']}")
    
    def submit_feedback(self, feedback_type: str, title: str, description: str,
                       rating: int, context: str = "general") -> bool:
        """Submit user feedback."""
        try:
            user_id = st.session_state.get('user_id')
            firm_id = st.session_state.get('firm_id')
            
            if not user_id or not firm_id:
                return False
            
            feedback = FeedbackSubmission(
                id=f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
                user_id=user_id,
                firm_id=firm_id,
                feedback_type=feedback_type,
                title=title,
                description=description,
                rating=rating,
                category=context,
                priority="medium",
                status="open",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                attachments=[],
                tags=[context, feedback_type]
            )
            
            # Save to database or external system
            success = self._save_feedback(feedback)
            
            # Track in analytics
            if success:
                self._track_feedback_submission(feedback)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error submitting feedback: {e}")
            return False
    
    def submit_nps_survey(self, nps_score: int, comment: str) -> bool:
        """Submit NPS survey response."""
        try:
            user_id = st.session_state.get('user_id')
            firm_id = st.session_state.get('firm_id')
            
            if not user_id or not firm_id:
                return False
            
            survey_response = SurveyResponse(
                id=f"nps_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
                survey_id="nps_quarterly_2025",
                user_id=user_id,
                firm_id=firm_id,
                survey_type="nps",
                responses={"nps_score": nps_score, "comment": comment},
                nps_score=nps_score,
                completion_time=60,  # Estimated
                created_at=datetime.utcnow()
            )
            
            success = self._save_survey_response(survey_response)
            
            if success:
                self._track_nps_submission(survey_response)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error submitting NPS survey: {e}")
            return False
    
    def submit_feature_feedback(self, feature_name: str, feedback_data: Dict[str, Any]) -> bool:
        """Submit feature-specific feedback."""
        try:
            user_id = st.session_state.get('user_id')
            firm_id = st.session_state.get('firm_id')
            
            if not user_id or not firm_id:
                return False
            
            survey_response = SurveyResponse(
                id=f"feature_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
                survey_id=f"feature_feedback_{feature_name}",
                user_id=user_id,
                firm_id=firm_id,
                survey_type="feature_feedback",
                responses=feedback_data,
                nps_score=None,
                completion_time=180,  # Estimated
                created_at=datetime.utcnow()
            )
            
            success = self._save_survey_response(survey_response)
            
            if success:
                self._track_feature_feedback(feature_name, feedback_data)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error submitting feature feedback: {e}")
            return False
    
    def submit_case_survey(self, case_id: str, survey_data: Dict[str, Any]) -> bool:
        """Submit post-case completion survey."""
        try:
            user_id = st.session_state.get('user_id')
            firm_id = st.session_state.get('firm_id')
            
            if not user_id or not firm_id:
                return False
            
            survey_response = SurveyResponse(
                id=f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
                survey_id=f"post_case_{case_id}",
                user_id=user_id,
                firm_id=firm_id,
                survey_type="post_case_completion",
                responses=survey_data,
                nps_score=None,
                completion_time=300,  # Estimated
                created_at=datetime.utcnow()
            )
            
            success = self._save_survey_response(survey_response)
            
            if success:
                self._track_case_survey(case_id, survey_data)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error submitting case survey: {e}")
            return False
    
    def submit_ai_survey(self, survey_data: Dict[str, Any]) -> bool:
        """Submit AI experience survey."""
        try:
            user_id = st.session_state.get('user_id')
            firm_id = st.session_state.get('firm_id')
            
            if not user_id or not firm_id:
                return False
            
            survey_response = SurveyResponse(
                id=f"ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
                survey_id="ai_experience_2025",
                user_id=user_id,
                firm_id=firm_id,
                survey_type="ai_experience",
                responses=survey_data,
                nps_score=None,
                completion_time=240,  # Estimated
                created_at=datetime.utcnow()
            )
            
            success = self._save_survey_response(survey_response)
            
            if success:
                self._track_ai_survey(survey_data)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error submitting AI survey: {e}")
            return False
    
    def _should_show_nps_survey(self, trigger_condition: str) -> bool:
        """Check if NPS survey should be shown to user."""
        # Check if user has already completed NPS survey recently
        if st.session_state.get('nps_survey_completed'):
            return False
        
        # Check trigger conditions
        if trigger_condition == "quarterly":
            # Show quarterly to random sample of users
            import random
            return random.random() < 0.1  # 10% chance
        
        return False
    
    def _save_feedback(self, feedback: FeedbackSubmission) -> bool:
        """Save feedback to database."""
        # This would integrate with actual database
        self.logger.info(f"Saving feedback: {feedback.id}")
        return True
    
    def _save_survey_response(self, survey_response: SurveyResponse) -> bool:
        """Save survey response to database."""
        # This would integrate with actual database
        self.logger.info(f"Saving survey response: {survey_response.id}")
        return True
    
    def _track_feedback_submission(self, feedback: FeedbackSubmission):
        """Track feedback submission in analytics."""
        from integrations.analytics.mixpanel_integration import get_analytics
        
        analytics = get_analytics()
        if analytics:
            analytics.mixpanel.track_event({
                "event_name": "Feedback Submitted",
                "user_id": feedback.user_id,
                "properties": {
                    "firm_id": feedback.firm_id,
                    "feedback_type": feedback.feedback_type,
                    "rating": feedback.rating,
                    "category": feedback.category
                }
            })
    
    def _track_nps_submission(self, survey_response: SurveyResponse):
        """Track NPS survey submission in analytics."""
        from integrations.analytics.mixpanel_integration import get_analytics
        
        analytics = get_analytics()
        if analytics:
            analytics.mixpanel.track_event({
                "event_name": "NPS Survey Completed",
                "user_id": survey_response.user_id,
                "properties": {
                    "firm_id": survey_response.firm_id,
                    "nps_score": survey_response.nps_score,
                    "survey_type": survey_response.survey_type
                }
            })
    
    def _track_feature_feedback(self, feature_name: str, feedback_data: Dict[str, Any]):
        """Track feature feedback in analytics."""
        from integrations.analytics.mixpanel_integration import get_analytics
        
        analytics = get_analytics()
        if analytics:
            analytics.mixpanel.track_feature_usage(
                user_id=st.session_state.get('user_id'),
                firm_id=st.session_state.get('firm_id'),
                feature_name=feature_name,
                action="feedback_submitted",
                context=feedback_data
            )
    
    def _track_case_survey(self, case_id: str, survey_data: Dict[str, Any]):
        """Track case survey in analytics."""
        from integrations.analytics.mixpanel_integration import get_analytics
        
        analytics = get_analytics()
        if analytics:
            analytics.mixpanel.track_event({
                "event_name": "Case Survey Completed",
                "user_id": st.session_state.get('user_id'),
                "properties": {
                    "firm_id": st.session_state.get('firm_id'),
                    "case_id": case_id,
                    "overall_experience": survey_data.get("overall_experience"),
                    "time_saved": survey_data.get("time_saved")
                }
            })
    
    def _track_ai_survey(self, survey_data: Dict[str, Any]):
        """Track AI survey in analytics."""
        from integrations.analytics.mixpanel_integration import get_analytics
        
        analytics = get_analytics()
        if analytics:
            analytics.mixpanel.track_event({
                "event_name": "AI Survey Completed",
                "user_id": st.session_state.get('user_id'),
                "properties": {
                    "firm_id": st.session_state.get('firm_id'),
                    "usage_frequency": survey_data.get("usage_frequency"),
                    "trust_level": survey_data.get("trust_level"),
                    "accuracy_rating": survey_data.get("accuracy")
                }
            })
    
    def get_feedback_trends(self) -> Dict[str, Any]:
        """Get feedback trends data."""
        # This would query actual database
        return {}
    
    def get_feature_feedback_summary(self) -> List[Dict[str, Any]]:
        """Get feature feedback summary."""
        # This would aggregate actual feedback data
        return [
            {"Feature": "Case Management", "Avg Rating": 4.2, "Response Count": 45},
            {"Feature": "AI Assistant", "Avg Rating": 3.8, "Response Count": 38},
            {"Feature": "Document Processing", "Avg Rating": 4.0, "Response Count": 52},
            {"Feature": "Analytics Dashboard", "Avg Rating": 3.9, "Response Count": 23}
        ]
    
    def get_recent_feedback(self) -> List[Dict[str, Any]]:
        """Get recent feedback submissions."""
        # This would query actual database
        return [
            {
                "type": "Feature Request",
                "title": "Calendar Integration",
                "rating": 4,
                "user": "John Smith",
                "date": "Jan 28, 2025",
                "description": "Would love to see calendar integration for court dates."
            },
            {
                "type": "Bug Report",
                "title": "Document Upload Issue",
                "rating": 2,
                "user": "Jane Doe",
                "date": "Jan 27, 2025",
                "description": "Having trouble uploading large PDF files."
            }
        ]


# Global feedback manager instance
feedback_manager = FeedbackManager()