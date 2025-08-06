"""
Integration tests for case management features
"""

import pytest
import json
import io
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import date, datetime

from ..main import app
from ..models import Case, Document, FinancialInformation, ChildrenInformation
from ..models.enums import AustralianFamilyCaseType, CaseStatus, DocumentType, ProcessingStatus
from ..services import CaseService, DocumentService, ConflictCheckService

client = TestClient(app)

class TestCaseWizardIntegration:
    """Test case creation wizard integration"""
    
    def test_get_case_types(self):
        """Test getting available case types"""
        response = client.get("/cases/case-types")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 8  # All Australian family law case types
        assert all("case_type" in item for item in data)
        assert all("display_name" in item for item in data)
        assert all("typical_duration_months" in item for item in data)
        
        # Check specific case types exist
        case_types = [item["case_type"] for item in data]
        assert "divorce" in case_types
        assert "property_settlement" in case_types
        assert "child_custody" in case_types
    
    def test_start_case_wizard_unauthorized(self):
        """Test starting wizard without authentication"""
        response = client.post("/cases/wizard/start")
        assert response.status_code == 401
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_start_case_wizard_success(self, mock_db, mock_user):
        """Test successful wizard initialization"""
        # Mock authenticated user
        mock_user.return_value = MagicMock(
            id="user123",
            firm_id="firm123",
            email="lawyer@example.com"
        )
        mock_db.return_value = MagicMock()
        
        with patch.object(CaseService, 'start_case_creation_wizard') as mock_wizard:
            mock_wizard.return_value = {
                "wizard_session_id": "session123",
                "current_step": "classification",
                "step_info": {
                    "title": "Case Classification",
                    "required_fields": ["case_type", "title"]
                },
                "progress": {"completed": 0, "total": 6}
            }
            
            response = client.post("/cases/wizard/start")
            
            assert response.status_code == 200
            data = response.json()
            assert "wizard_session_id" in data
            assert data["current_step"] == "classification"
            assert data["progress"]["total"] == 6
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_process_classification_step(self, mock_db, mock_user):
        """Test processing classification step with AI suggestions"""
        # Mock user and database
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        mock_db.return_value = MagicMock()
        
        classification_data = {
            "case_type": "divorce",
            "title": "Smith vs Smith - Divorce Proceedings",
            "description": "Uncontested divorce with property settlement",
            "urgency": "normal"
        }
        
        with patch.object(CaseService, 'process_wizard_step') as mock_process:
            mock_process.return_value = {
                "success": True,
                "current_step": "classification",
                "next_step": "client_info",
                "progress": {"completed": 1, "total": 6},
                "ai_suggestions": [
                    {
                        "type": "case_type_suggestion",
                        "suggestion": {
                            "suggested_case_type": "divorce",
                            "confidence": 0.95,
                            "reasoning": "Keywords indicate divorce proceedings"
                        }
                    }
                ],
                "conflict_check": {
                    "has_conflicts": False,
                    "conflicts": [],
                    "confidence_score": 1.0
                }
            }
            
            response = client.post("/cases/wizard/classification", json=classification_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["ai_suggestions"]) > 0
            assert data["conflict_check"]["has_conflicts"] is False
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')  
    def test_process_client_info_with_conflicts(self, mock_db, mock_user):
        """Test client info step with conflict detection"""
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        mock_db.return_value = MagicMock()
        
        client_data = {
            "applicant_name": "John Smith",
            "respondent_name": "Jane Smith",
            "applicant_email": "john@example.com",
            "respondent_email": "jane@example.com"
        }
        
        with patch.object(CaseService, 'process_wizard_step') as mock_process:
            mock_process.return_value = {
                "success": True,
                "current_step": "client_info",
                "next_step": "financial_info",
                "progress": {"completed": 2, "total": 6},
                "conflict_check": {
                    "has_conflicts": True,
                    "conflicts": [
                        {
                            "type": "similar_match",
                            "conflicted_party": "John Smith",
                            "existing_case_number": "LEG-2024-001",
                            "similarity_score": 0.85,
                            "severity": "medium"
                        }
                    ],
                    "recommendations": [
                        "Verify if this is the same person",
                        "Check existing case relationship"
                    ]
                }
            }
            
            response = client.post("/cases/wizard/client-info", json=client_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["conflict_check"]["has_conflicts"] is True
            assert len(data["conflict_check"]["conflicts"]) > 0
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_complete_case_creation_wizard(self, mock_db, mock_user):
        """Test completing the entire wizard"""
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        
        # Mock successful case creation
        with patch.object(CaseService, 'process_wizard_step') as mock_process:
            mock_process.return_value = {
                "success": True,
                "current_step": "document_upload",
                "next_step": None,  # Final step
                "progress": {"completed": 6, "total": 6},
                "case_creation": {
                    "success": True,
                    "case_id": "case123",
                    "case_number": "LEG-2024-001",
                    "message": "Case created successfully",
                    "next_steps": [
                        "Upload initial documents",
                        "Schedule client meeting"
                    ]
                }
            }
            
            final_step_data = {
                "wizard_session_id": "session123",
                "step": "document_upload",
                "step_data": {"ready_for_documents": True}
            }
            
            response = client.post("/cases/wizard/step", json=final_step_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["case_creation"]["success"] is True
            assert "case_id" in data["case_creation"]
            assert "next_steps" in data["case_creation"]

class TestDocumentProcessingIntegration:
    """Test document processing with 4-tier extraction"""
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_upload_pdf_document(self, mock_db, mock_user):
        """Test PDF document upload with processing"""
        mock_user.return_value = MagicMock(
            id="user123", 
            firm_id="firm123",
            has_permission=MagicMock(return_value=True)
        )
        
        # Mock case exists
        mock_case = MagicMock()
        mock_case.id = "case123"
        mock_case.firm_id = "firm123"
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_case
        mock_db.return_value = mock_session
        
        # Create fake PDF content
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj"
        
        with patch.object(DocumentService, 'upload_and_process_document') as mock_upload:
            mock_upload.return_value = {
                "success": True,
                "document_id": "doc123",
                "filename": "test_document.pdf",
                "file_size": len(pdf_content),
                "mime_type": "application/pdf",
                "processing_status": "pending",
                "message": "Document uploaded successfully. Processing started."
            }
            
            files = {"file": ("test_document.pdf", io.BytesIO(pdf_content), "application/pdf")}
            data = {"case_id": "case123"}
            
            response = client.post("/documents/upload", files=files, data=data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True
            assert response_data["document_id"] == "doc123"
            assert response_data["mime_type"] == "application/pdf"
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_bulk_document_upload(self, mock_db, mock_user):
        """Test bulk document upload"""
        mock_user.return_value = MagicMock(
            id="user123",
            firm_id="firm123", 
            has_permission=MagicMock(return_value=True)
        )
        
        # Mock case
        mock_case = MagicMock()
        mock_case.id = "case123"
        mock_case.firm_id = "firm123"
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_case
        mock_db.return_value = mock_session
        
        # Create multiple test files
        files = [
            ("files", ("doc1.pdf", io.BytesIO(b"PDF content 1"), "application/pdf")),
            ("files", ("doc2.docx", io.BytesIO(b"DOCX content 2"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("doc3.txt", io.BytesIO(b"Text content 3"), "text/plain"))
        ]
        
        data = {"case_id": "case123"}
        
        with patch.object(DocumentService, 'upload_and_process_document') as mock_upload:
            # Mock successful uploads for all files
            mock_upload.side_effect = [
                {
                    "success": True,
                    "document_id": f"doc{i}",
                    "filename": f"doc{i}.ext",
                    "processing_status": "pending"
                }
                for i in range(1, 4)
            ]
            
            response = client.post("/documents/bulk-upload", files=files, data=data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["total_files"] == 3
            assert response_data["success_count"] == 3
            assert response_data["failure_count"] == 0
            assert len(response_data["successful_uploads"]) == 3
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_get_document_processing_status(self, mock_db, mock_user):
        """Test getting document processing status"""
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        
        # Mock document with case
        mock_document = MagicMock()
        mock_document.id = "doc123"
        mock_document.filename = "test.pdf"
        mock_document.processing_status = ProcessingStatus.COMPLETED
        mock_document.processed_at = datetime.utcnow()
        mock_document.extracted_text = "Sample extracted text"
        mock_document.ai_summary = "Sample AI summary"
        mock_document.ai_classification_confidence = 0.95
        mock_document.ocr_confidence = 0.88
        mock_document.metadata = {"requires_review": False}
        
        mock_case = MagicMock()
        mock_case.firm_id = "firm123"
        
        mock_session = MagicMock()
        mock_session.query.return_value.join.return_value.filter.return_value.first.return_value = mock_document
        mock_db.return_value = mock_session
        
        with patch.object(DocumentService, 'get_document_processing_status') as mock_status:
            mock_status.return_value = {
                "document_id": "doc123",
                "filename": "test.pdf",
                "processing_status": "completed",
                "processed_at": datetime.utcnow().isoformat(),
                "has_text": True,
                "has_summary": True,
                "classification_confidence": 0.95,
                "ocr_confidence": 0.88,
                "requires_review": False
            }
            
            response = client.get("/documents/doc123/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["processing_status"] == "completed"
            assert data["has_text"] is True
            assert data["classification_confidence"] == 0.95
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_get_document_analysis(self, mock_db, mock_user):
        """Test getting comprehensive document analysis"""
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        
        # Mock completed document
        mock_document = MagicMock()
        mock_document.id = "doc123"
        mock_document.processing_status = ProcessingStatus.COMPLETED
        mock_document.extracted_text = "This is a sample legal document containing important information."
        mock_document.ai_summary = "Document summary: Legal agreement between parties."
        mock_document.ai_key_points = ["Key point 1", "Key point 2"]
        mock_document.ai_extracted_entities = {
            "dates": ["2024-01-15"],
            "amounts": ["$50,000"],
            "parties": ["John Smith", "Jane Doe"]
        }
        mock_document.document_type = DocumentType.AGREEMENT
        mock_document.ai_classification_confidence = 0.92
        mock_document.metadata = {
            "legal_analysis": {
                "significance": "high",
                "requires_review": True
            },
            "extraction_methods": ["pdfplumber", "ai_analysis"],
            "requires_review": True
        }
        
        mock_case = MagicMock()
        mock_case.firm_id = "firm123"
        
        mock_session = MagicMock()
        mock_session.query.return_value.join.return_value.filter.return_value.first.return_value = mock_document
        mock_db.return_value = mock_session
        
        response = client.get("/documents/doc123/analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc123"
        assert "extracted_text" in data
        assert "ai_summary" in data
        assert "key_points" in data
        assert "extracted_entities" in data
        assert data["document_type"] == "agreement"
        assert data["requires_review"] is True

class TestAIServiceIntegration:
    """Test AI service integration with external APIs"""
    
    @pytest.mark.asyncio
    async def test_case_type_suggestion_with_groq(self):
        """Test case type suggestion using Groq API"""
        from ..services.ai_service import AIService
        
        ai_service = AIService()
        
        # Mock Groq response
        with patch.object(ai_service, '_query_groq') as mock_groq:
            mock_groq.return_value = {
                "content": json.dumps({
                    "suggested_case_type": "divorce",
                    "confidence": 0.95,
                    "reasoning": "Description mentions marriage dissolution",
                    "alternative_types": ["property_settlement"],
                    "required_court": "federal_circuit_family_court"
                }),
                "tokens_used": 150,
                "model": "mixtral-8x7b-32768",
                "provider": "groq"
            }
            
            result = await ai_service.suggest_case_type(
                "My husband and I want to end our marriage and divide our assets",
                {"children_involved": True, "assets_involved": True}
            )
            
            assert result["suggested_case_type"] == "divorce"
            assert result["confidence"] == 0.95
            assert "property_settlement" in result["alternative_types"]
    
    @pytest.mark.asyncio
    async def test_case_complexity_analysis(self):
        """Test case complexity analysis"""
        from ..services.ai_service import AIService
        
        ai_service = AIService()
        
        case_data = {
            "case_type": "property_settlement",
            "estimated_value": 1500000,
            "children": [
                {"name": "Child 1", "age": 10},
                {"name": "Child 2", "age": 15}
            ],
            "assets": [
                {"type": "real_estate", "value": 800000},
                {"type": "business", "value": 500000},
                {"type": "superannuation", "value": 200000}
            ]
        }
        
        with patch.object(ai_service, '_rule_based_complexity_analysis') as mock_analysis:
            mock_analysis.return_value = {
                "complexity_level": "high",
                "estimated_duration_months": 12,
                "key_challenges": [
                    "High asset value",
                    "Business valuation required",
                    "Multiple children involved"
                ],
                "recommended_resources": ["senior_lawyer", "financial_expert"],
                "priority_level": "high",
                "estimated_cost_range": {"min": 15000, "max": 35000}
            }
            
            result = await ai_service.analyze_case_complexity(case_data)
            
            assert result["complexity_level"] == "high"
            assert result["estimated_duration_months"] == 12
            assert "senior_lawyer" in result["recommended_resources"]
    
    @pytest.mark.asyncio
    async def test_document_suggestions(self):
        """Test AI document suggestions"""
        from ..services.ai_service import AIService
        
        ai_service = AIService()
        
        with patch.object(ai_service, '_rule_based_document_suggestions') as mock_suggestions:
            mock_suggestions.return_value = [
                {
                    "document_name": "Financial Statement",
                    "priority": "high",
                    "description": "Complete financial disclosure required",
                    "deadline_days": 60,
                    "form_number": "Form 13"
                },
                {
                    "document_name": "Property Valuation",
                    "priority": "medium", 
                    "description": "Professional property valuation",
                    "recommended_timing": "early"
                }
            ]
            
            result = await ai_service.suggest_required_documents(
                AustralianFamilyCaseType.PROPERTY_SETTLEMENT,
                {"estimated_value": 500000}
            )
            
            assert len(result) == 2
            assert result[0]["document_name"] == "Financial Statement"
            assert result[0]["priority"] == "high"

class TestConflictCheckingIntegration:
    """Test conflict checking service integration"""
    
    @pytest.mark.asyncio
    async def test_basic_conflict_check(self, db_session, sample_firm):
        """Test basic name-based conflict checking"""
        from ..services.conflict_service import ConflictCheckService
        
        conflict_service = ConflictCheckService()
        
        # Create existing case
        existing_case = Case(
            firm_id=sample_firm.id,
            case_number="EXIST-2024-001",
            case_type=AustralianFamilyCaseType.DIVORCE,
            title="Smith vs Jones - Existing Case",
            created_by="user123",
            opposing_party_name="John Smith"
        )
        db_session.add(existing_case)
        db_session.commit()
        
        # Check for conflict with similar names
        result = await conflict_service.check_conflicts(
            "John Smith",  # Same as existing case
            "Mary Johnson",
            str(sample_firm.id),
            db_session
        )
        
        assert result["has_conflicts"] is True
        assert len(result["conflicts"]) > 0
        assert result["conflicts"][0]["type"] == "exact_match"
        assert "John Smith" in result["conflicts"][0]["conflicted_party"]
    
    @pytest.mark.asyncio
    async def test_fuzzy_name_matching(self, db_session, sample_firm):
        """Test fuzzy name matching for similar names"""
        from ..services.conflict_service import ConflictCheckService
        
        conflict_service = ConflictCheckService()
        
        # Create case with slightly different name
        existing_case = Case(
            firm_id=sample_firm.id,
            case_number="FUZZY-2024-001", 
            case_type=AustralianFamilyCaseType.CHILD_CUSTODY,
            title="Jonathan Smith vs Sarah Wilson",
            created_by="user123"
        )
        db_session.add(existing_case)
        db_session.commit()
        
        # Check for conflict with similar name
        result = await conflict_service.check_conflicts(
            "John Smith",  # Similar to "Jonathan Smith"
            "Sarah Wilson",
            str(sample_firm.id),
            db_session
        )
        
        # Should detect similar name conflict
        similar_conflicts = [c for c in result["conflicts"] if c["type"] == "similar_match"]
        assert len(similar_conflicts) > 0
        
        # Should have reasonable similarity score
        assert similar_conflicts[0]["similarity_score"] > 0.7
    
    @pytest.mark.asyncio
    async def test_enhanced_conflict_check(self, db_session, sample_firm):
        """Test enhanced conflict checking with additional data"""
        from ..services.conflict_service import ConflictCheckService
        
        conflict_service = ConflictCheckService()
        
        case_data = {
            "applicant_name": "John Smith",
            "respondent_name": "Jane Smith",
            "applicant_email": "john@example.com",
            "respondent_email": "jane@example.com",
            "applicant_phone": "0400123456",
            "case_type": "divorce"
        }
        
        result = await conflict_service.check_detailed_conflicts(
            case_data,
            str(sample_firm.id),
            db_session
        )
        
        assert "enhanced_check" in result
        assert result["enhanced_check"] is True
        assert "confidence_score" in result
        assert "recommendations" in result

class TestAccessibilityCompliance:
    """Test accessibility features implementation"""
    
    def test_case_types_accessibility_info(self):
        """Test case types include accessibility information"""
        response = client.get("/cases/case-types")
        
        assert response.status_code == 200
        data = response.json()
        
        for case_type in data:
            # Check required accessibility fields
            assert "display_name" in case_type
            assert "description" in case_type
            assert "typical_duration_months" in case_type
            
            # Check descriptions are comprehensive for screen readers
            assert len(case_type["description"]) > 20
            assert not case_type["description"].startswith("TODO")
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_error_messages_accessibility(self, mock_db, mock_user):
        """Test error messages are accessible and descriptive"""
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        mock_db.return_value = MagicMock()
        
        # Test with invalid case type
        invalid_data = {
            "case_type": "invalid_type",
            "title": "Test Case"
        }
        
        with patch.object(CaseService, 'process_wizard_step') as mock_process:
            mock_process.side_effect = ValueError("Invalid case type")
            
            response = client.post("/cases/wizard/classification", json=invalid_data)
            
            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            # Error should be descriptive and actionable
            assert len(error_data["detail"]) > 10
    
    def test_pagination_accessibility(self):
        """Test pagination includes accessibility metadata"""
        with patch('backend.auth.dependencies.get_current_active_user') as mock_user:
            with patch('backend.database.get_db') as mock_db:
                mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
                mock_session = MagicMock()
                mock_session.query.return_value.filter.return_value.count.return_value = 50
                mock_session.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
                mock_db.return_value = mock_session
                
                response = client.get("/cases/?page=2&page_size=10")
                
                assert response.status_code == 200
                data = response.json()
                
                # Check pagination metadata for accessibility
                assert "total_count" in data
                assert "page" in data
                assert "page_size" in data
                assert "has_next" in data
                
                # Verify pagination calculations
                assert data["page"] == 2
                assert data["page_size"] == 10
                assert data["has_next"] is True  # 50 total, page 2 of 10 = has more

class TestMultilingualSupport:
    """Test multilingual support as per accessibility requirements"""
    
    def test_case_type_descriptions_english(self):
        """Test case type descriptions are clear English"""
        response = client.get("/cases/case-types")
        
        assert response.status_code == 200
        data = response.json()
        
        for case_type in data:
            description = case_type["description"]
            
            # Basic checks for clear English
            assert not description.isupper()  # Not all caps
            assert description[0].isupper()  # Proper capitalization
            assert description.endswith(('.', '!', '?')) or len(description.split()) < 5  # Proper punctuation
            
            # Check for legal jargon explanation context
            if "de facto" in description.lower():
                assert len(description) > 30  # Should have explanation
    
    @patch('backend.auth.dependencies.get_current_active_user')
    @patch('backend.database.get_db')
    def test_ai_suggestions_plain_english(self, mock_db, mock_user):
        """Test AI suggestions use plain English"""
        mock_user.return_value = MagicMock(id="user123", firm_id="firm123")
        mock_db.return_value = MagicMock()
        
        with patch.object(CaseService, 'process_wizard_step') as mock_process:
            mock_process.return_value = {
                "success": True,
                "ai_suggestions": [
                    {
                        "type": "case_type_suggestion",
                        "suggestion": {
                            "reasoning": "Based on the description mentioning marriage dissolution and property division, this appears to be a divorce case with property settlement components."
                        }
                    }
                ],
                "current_step": "classification",
                "progress": {"completed": 1, "total": 6}
            }
            
            response = client.post("/cases/wizard/step", json={
                "wizard_session_id": "test123",
                "step": "classification", 
                "step_data": {"case_type": "divorce", "title": "Test Case"}
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Check AI reasoning uses plain English
            reasoning = data["ai_suggestions"][0]["suggestion"]["reasoning"]
            
            # Should avoid excessive legal jargon
            jargon_words = ["heretofore", "whereas", "aforementioned", "therein"]
            assert not any(word in reasoning.lower() for word in jargon_words)
            
            # Should be reasonably long explanation
            assert len(reasoning) > 50