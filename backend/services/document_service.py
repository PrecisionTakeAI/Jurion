"""
Document Service for AI-powered document processing with 4-tier extraction
"""

import os
import hashlib
import mimetypes
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from sqlalchemy.orm import Session
from datetime import datetime
import json
import asyncio
import tempfile
import uuid

# Document processing libraries
try:
    import PyPDF2
    import pdfplumber
    import fitz  # PyMuPDF
    from PIL import Image
    import pytesseract
    import docx2txt
except ImportError as e:
    print(f"Warning: Some document processing libraries not available: {e}")

from ..models import Document, Case, User, AIInteraction
from ..models.enums import DocumentType, ProcessingStatus, AIInteractionType
from .ai_service import AIService

class DocumentExtractionTier:
    """Document extraction tiers"""
    TIER_1_BASIC = "basic_text"       # Simple text extraction
    TIER_2_STRUCTURED = "structured"  # Structured data extraction
    TIER_3_AI_ENHANCED = "ai_enhanced" # AI analysis and classification
    TIER_4_OCR_FALLBACK = "ocr_fallback" # OCR for scanned documents

class DocumentService:
    """Service for document processing and management"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.supported_mime_types = {
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/tiff': 'tiff'
        }
        
        # OCR configuration
        self.ocr_config = {
            'languages': ['eng'],  # English - can be extended
            'config': '--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
        }
    
    async def upload_and_process_document(self, file_data: bytes, filename: str, 
                                        case_id: str, user: User, 
                                        db: Session) -> Dict[str, Any]:
        """
        Upload and process document with 4-tier extraction
        
        Args:
            file_data: Binary file data
            filename: Original filename
            case_id: Associated case ID
            user: Uploading user
            db: Database session
            
        Returns:
            Dict with upload and processing results
        """
        
        # Validate file
        validation_result = await self._validate_file(file_data, filename)
        if not validation_result["is_valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "details": validation_result
            }
        
        try:
            # Calculate file hash
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # Check for duplicate
            existing_doc = db.query(Document).filter(
                Document.file_hash == file_hash,
                Document.firm_id == user.firm_id
            ).first()
            
            if existing_doc:
                return {
                    "success": False,
                    "error": "Document already exists",
                    "existing_document_id": str(existing_doc.id)
                }
            
            # Create document record
            document = Document(
                firm_id=user.firm_id,
                case_id=case_id,
                filename=self._sanitize_filename(filename),
                original_filename=filename,
                file_size=len(file_data),
                mime_type=validation_result["mime_type"],
                file_hash=file_hash,
                storage_path=self._generate_storage_path(file_hash, filename),
                uploaded_by=user.id,
                processing_status=ProcessingStatus.PENDING
            )
            
            db.add(document)
            db.flush()  # Get document ID
            
            # Store file (in production, use cloud storage)
            storage_result = await self._store_file(file_data, document.storage_path)
            if not storage_result["success"]:
                db.rollback()
                return {
                    "success": False,
                    "error": "Failed to store file",
                    "details": storage_result
                }
            
            # Start async processing
            processing_task = asyncio.create_task(
                self._process_document_async(document, file_data, db)
            )
            
            db.commit()
            
            return {
                "success": True,
                "document_id": str(document.id),
                "filename": document.filename,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "processing_status": document.processing_status.value,
                "message": "Document uploaded successfully. Processing started.",
                "processing_task_id": id(processing_task)
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}"
            }
    
    async def _process_document_async(self, document: Document, file_data: bytes, 
                                    db: Session):
        """Asynchronously process document with 4-tier extraction"""
        
        try:
            # Update status to processing
            document.processing_status = ProcessingStatus.PROCESSING
            document.processed_at = datetime.utcnow()
            db.commit()
            
            # Tier 1: Basic text extraction
            tier1_result = await self._tier1_basic_extraction(file_data, document.mime_type)
            
            # Tier 2: Structured data extraction
            tier2_result = await self._tier2_structured_extraction(
                tier1_result["text"], document.mime_type
            )
            
            # Tier 3: AI-enhanced analysis
            tier3_result = await self._tier3_ai_analysis(
                tier1_result["text"], tier2_result, document
            )
            
            # Tier 4: OCR fallback (if needed)
            tier4_result = {}
            if tier1_result.get("ocr_needed") or tier1_result.get("confidence", 1.0) < 0.5:
                tier4_result = await self._tier4_ocr_fallback(file_data, document.mime_type)
                
                # Use OCR text if better
                if tier4_result.get("confidence", 0) > tier1_result.get("confidence", 1.0):
                    tier1_result["text"] = tier4_result["text"]
                    tier1_result["confidence"] = tier4_result["confidence"]
            
            # Combine results and update document
            await self._update_document_with_results(
                document, tier1_result, tier2_result, tier3_result, tier4_result, db
            )
            
            # Mark as completed
            document.processing_status = ProcessingStatus.COMPLETED
            db.commit()
            
        except Exception as e:
            # Mark as failed
            document.processing_status = ProcessingStatus.FAILED
            db.commit()
            
            # Log error
            print(f"Document processing failed for {document.id}: {str(e)}")
    
    async def _tier1_basic_extraction(self, file_data: bytes, 
                                    mime_type: str) -> Dict[str, Any]:
        """Tier 1: Basic text extraction"""
        
        result = {
            "text": "",
            "confidence": 1.0,
            "method": "unknown",
            "ocr_needed": False,
            "page_count": 0
        }
        
        try:
            if mime_type == 'application/pdf':
                result = await self._extract_pdf_text(file_data)
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                result = await self._extract_docx_text(file_data)
            elif mime_type == 'text/plain':
                result = await self._extract_txt_text(file_data)
            elif mime_type.startswith('image/'):
                result = await self._extract_image_text(file_data)
                result["ocr_needed"] = True
            else:
                result["text"] = "Unsupported file type for text extraction"
                result["confidence"] = 0.0
                
        except Exception as e:
            result["text"] = f"Text extraction failed: {str(e)}"
            result["confidence"] = 0.0
            result["ocr_needed"] = True
        
        return result
    
    async def _tier2_structured_extraction(self, text: str, 
                                         mime_type: str) -> Dict[str, Any]:
        """Tier 2: Structured data extraction"""
        
        structured_data = {
            "dates": [],
            "amounts": [],
            "parties": [],
            "addresses": [],
            "phone_numbers": [],
            "email_addresses": [],
            "case_references": [],
            "court_references": []
        }
        
        if not text:
            return structured_data
        
        try:
            # Extract dates
            import re
            date_patterns = [
                r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # DD/MM/YYYY, DD-MM-YYYY
                r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4}\b',
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                structured_data["dates"].extend(matches)
            
            # Extract monetary amounts
            amount_patterns = [
                r'\$[\d,]+\.?\d*',  # $1,000.00
                r'AUD\s*[\d,]+\.?\d*',  # AUD 1000
                r'[\d,]+\.?\d*\s*dollars?'  # 1000 dollars
            ]
            
            for pattern in amount_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                structured_data["amounts"].extend(matches)
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            structured_data["email_addresses"] = re.findall(email_pattern, text)
            
            # Extract phone numbers (Australian format)
            phone_patterns = [
                r'\b0[2-478]\d{8}\b',  # Australian landline
                r'\b04\d{8}\b',  # Australian mobile
                r'\+61\s*[2-478]\d{8}\b'  # International format
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, text)
                structured_data["phone_numbers"].extend(matches)
            
            # Extract case references
            case_patterns = [
                r'\b[A-Z]{2,4}\s*\d{4}\s*\d+\b',  # NSW 2024 123
                r'\b\d{4}\s*[A-Z]{2,6}\s*\d+\b'   # 2024 NSWSC 123
            ]
            
            for pattern in case_patterns:
                matches = re.findall(pattern, text)
                structured_data["case_references"].extend(matches)
            
            # Clean and deduplicate
            for key in structured_data:
                structured_data[key] = list(set(structured_data[key]))
                
        except Exception as e:
            print(f"Structured extraction error: {str(e)}")
        
        return structured_data
    
    async def _tier3_ai_analysis(self, text: str, structured_data: Dict[str, Any], 
                               document: Document) -> Dict[str, Any]:
        """Tier 3: AI-enhanced analysis and classification"""
        
        ai_result = {
            "document_type": None,
            "confidence": 0.0,
            "summary": "",
            "key_points": [],
            "extracted_entities": {},
            "legal_analysis": {},
            "recommendations": []
        }
        
        if not text or len(text.strip()) < 50:
            return ai_result
        
        try:
            # AI document classification
            classification_prompt = self._build_classification_prompt(text, structured_data)
            
            if self.ai_service.groq_client or self.ai_service.openai_client:
                try:
                    classification_response = await self.ai_service._query_groq(
                        classification_prompt, "document_classification"
                    ) if self.ai_service.groq_client else await self.ai_service._query_openai(
                        classification_prompt, "document_classification"
                    )
                    
                    classification_result = self._parse_classification_response(
                        classification_response.get("content", "")
                    )
                    ai_result.update(classification_result)
                    
                except Exception as e:
                    print(f"AI classification failed: {str(e)}")
                    # Fallback to rule-based classification
                    ai_result.update(self._rule_based_classification(text, structured_data))
            else:
                # Rule-based classification if no AI available
                ai_result.update(self._rule_based_classification(text, structured_data))
            
            # AI summary generation
            if ai_result.get("document_type"):
                summary_prompt = self._build_summary_prompt(text, ai_result["document_type"])
                
                try:
                    if self.ai_service.groq_client or self.ai_service.openai_client:
                        summary_response = await self.ai_service._query_groq(
                            summary_prompt, "document_summary"
                        ) if self.ai_service.groq_client else await self.ai_service._query_openai(
                            summary_prompt, "document_summary"
                        )
                        
                        ai_result["summary"] = summary_response.get("content", "")[:1000]  # Limit length
                    else:
                        ai_result["summary"] = self._generate_rule_based_summary(text)
                        
                except Exception as e:
                    ai_result["summary"] = self._generate_rule_based_summary(text)
            
        except Exception as e:
            print(f"AI analysis error: {str(e)}")
            # Fallback to rule-based analysis
            ai_result.update(self._rule_based_classification(text, structured_data))
        
        return ai_result
    
    async def _tier4_ocr_fallback(self, file_data: bytes, 
                                mime_type: str) -> Dict[str, Any]:
        """Tier 4: OCR fallback for scanned documents"""
        
        ocr_result = {
            "text": "",
            "confidence": 0.0,
            "method": "ocr",
            "language": "eng"
        }
        
        try:
            if mime_type == 'application/pdf':
                ocr_result = await self._ocr_pdf(file_data)
            elif mime_type.startswith('image/'):
                ocr_result = await self._ocr_image(file_data)
            else:
                ocr_result["text"] = "OCR not supported for this file type"
                
        except Exception as e:
            ocr_result["text"] = f"OCR processing failed: {str(e)}"
            ocr_result["confidence"] = 0.0
        
        return ocr_result
    
    async def _extract_pdf_text(self, file_data: bytes) -> Dict[str, Any]:
        """Extract text from PDF using multiple methods"""
        
        result = {
            "text": "",
            "confidence": 1.0,
            "method": "pdf_extraction",
            "page_count": 0
        }
        
        # Try pdfplumber first (best for tables and structured content)
        try:
            import io
            with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                result["text"] = "\n\n".join(text_parts)
                result["page_count"] = len(pdf.pages)
                result["method"] = "pdfplumber"
                
                if result["text"].strip():
                    return result
        except Exception as e:
            print(f"pdfplumber failed: {str(e)}")
        
        # Try PyMuPDF (fitz) as fallback
        try:
            import io
            pdf_doc = fitz.open(stream=file_data, filetype="pdf")
            text_parts = []
            
            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text_parts.append(page_text)
            
            result["text"] = "\n\n".join(text_parts)
            result["page_count"] = pdf_doc.page_count
            result["method"] = "pymupdf"
            
            pdf_doc.close()
            
            if result["text"].strip():
                return result
        except Exception as e:
            print(f"PyMuPDF failed: {str(e)}")
        
        # Try PyPDF2 as final fallback
        try:
            import io
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
            text_parts = []
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            result["text"] = "\n\n".join(text_parts)
            result["page_count"] = len(pdf_reader.pages)
            result["method"] = "pypdf2"
            
        except Exception as e:
            print(f"PyPDF2 failed: {str(e)}")
            result["confidence"] = 0.0
        
        # If no text extracted, mark for OCR
        if not result["text"].strip():
            result["confidence"] = 0.0
            result["ocr_needed"] = True
        
        return result
    
    async def _extract_docx_text(self, file_data: bytes) -> Dict[str, Any]:
        """Extract text from DOCX files"""
        
        result = {
            "text": "",
            "confidence": 1.0,
            "method": "docx_extraction"
        }
        
        try:
            import io
            # Save to temporary file for docx2txt
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(file_data)
                temp_file.flush()
                
                result["text"] = docx2txt.process(temp_file.name)
                result["method"] = "docx2txt"
                
                # Clean up
                os.unlink(temp_file.name)
                
        except Exception as e:
            result["text"] = f"DOCX extraction failed: {str(e)}"
            result["confidence"] = 0.0
        
        return result
    
    async def _extract_txt_text(self, file_data: bytes) -> Dict[str, Any]:
        """Extract text from plain text files"""
        
        result = {
            "text": "",
            "confidence": 1.0,
            "method": "text_file"
        }
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    result["text"] = file_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not result["text"]:
                result["text"] = "Could not decode text file"
                result["confidence"] = 0.0
                
        except Exception as e:
            result["text"] = f"Text extraction failed: {str(e)}"
            result["confidence"] = 0.0
        
        return result
    
    async def _extract_image_text(self, file_data: bytes) -> Dict[str, Any]:
        """Extract text from images using OCR"""
        
        result = {
            "text": "",
            "confidence": 0.0,
            "method": "image_ocr",
            "ocr_needed": True
        }
        
        try:
            # Convert to PIL Image
            import io
            image = Image.open(io.BytesIO(file_data))
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(
                image, 
                lang='+'.join(self.ocr_config['languages']),
                config=self.ocr_config['config']
            )
            
            # Get confidence data
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            result["text"] = ocr_text
            result["confidence"] = avg_confidence / 100.0  # Convert to 0-1 scale
            
        except Exception as e:
            result["text"] = f"Image OCR failed: {str(e)}"
            result["confidence"] = 0.0
        
        return result
    
    async def _ocr_pdf(self, file_data: bytes) -> Dict[str, Any]:
        """Perform OCR on PDF pages"""
        
        ocr_result = {
            "text": "",
            "confidence": 0.0,
            "method": "pdf_ocr"
        }
        
        try:
            import io
            pdf_doc = fitz.open(stream=file_data, filetype="pdf")
            text_parts = []
            confidences = []
            
            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # OCR the image
                image = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(
                    image,
                    lang='+'.join(self.ocr_config['languages']),
                    config=self.ocr_config['config']
                )
                
                if page_text.strip():
                    text_parts.append(page_text)
                
                # Get confidence
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                page_confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                if page_confidences:
                    confidences.extend(page_confidences)
            
            pdf_doc.close()
            
            ocr_result["text"] = "\n\n".join(text_parts)
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                ocr_result["confidence"] = avg_confidence / 100.0
            
        except Exception as e:
            ocr_result["text"] = f"PDF OCR failed: {str(e)}"
            ocr_result["confidence"] = 0.0
        
        return ocr_result
    
    async def _ocr_image(self, file_data: bytes) -> Dict[str, Any]:
        """Perform OCR on image files"""
        
        return await self._extract_image_text(file_data)
    
    def _build_classification_prompt(self, text: str, 
                                   structured_data: Dict[str, Any]) -> str:
        """Build prompt for AI document classification"""
        
        return f"""
        Analyze this legal document and classify it according to Australian legal document types.
        
        Document text (first 2000 characters):
        {text[:2000]}
        
        Extracted structured data:
        - Dates found: {len(structured_data.get('dates', []))}
        - Amounts found: {structured_data.get('amounts', [])}
        - Case references: {structured_data.get('case_references', [])}
        - Email addresses: {len(structured_data.get('email_addresses', []))}
        
        Classify this document and respond in JSON format:
        {{
            "document_type": "agreement|affidavit|court_order|financial_statement|correspondence|evidence|pleading|contract|will|power_of_attorney|other",
            "confidence": 0.95,
            "reasoning": "Explanation of classification",
            "key_indicators": ["indicator1", "indicator2"],
            "summary": "Brief summary of document content",
            "legal_significance": "high|medium|low",
            "requires_review": true|false
        }}
        """
    
    def _build_summary_prompt(self, text: str, document_type: str) -> str:
        """Build prompt for AI document summarization"""
        
        return f"""
        Summarize this {document_type} document for legal professionals.
        
        Document text:
        {text[:3000]}
        
        Provide a concise professional summary focusing on:
        1. Key legal points and obligations
        2. Important dates and deadlines
        3. Parties involved
        4. Financial information (if any)
        5. Next steps or actions required
        
        Keep the summary under 500 words and use professional legal language.
        """
    
    def _parse_classification_response(self, response_content: str) -> Dict[str, Any]:
        """Parse AI classification response"""
        
        try:
            # Try to extract JSON from response
            if "{" in response_content and "}" in response_content:
                json_start = response_content.find("{")
                json_end = response_content.rfind("}") + 1
                json_str = response_content[json_start:json_end]
                parsed = json.loads(json_str)
                
                return {
                    "document_type": parsed.get("document_type"),
                    "confidence": parsed.get("confidence", 0.5),
                    "summary": parsed.get("summary", ""),
                    "key_points": parsed.get("key_indicators", []),
                    "legal_analysis": {
                        "significance": parsed.get("legal_significance", "medium"),
                        "requires_review": parsed.get("requires_review", True),
                        "reasoning": parsed.get("reasoning", "")
                    }
                }
        except Exception as e:
            print(f"Failed to parse classification response: {str(e)}")
        
        # Fallback
        return {
            "document_type": "other",
            "confidence": 0.3,
            "summary": "Could not classify document",
            "key_points": [],
            "legal_analysis": {"significance": "medium", "requires_review": True}
        }
    
    def _rule_based_classification(self, text: str, 
                                 structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based document classification fallback"""
        
        text_lower = text.lower()
        
        # Simple keyword-based classification
        if any(word in text_lower for word in ['affidavit', 'sworn', 'affirm', 'deponent']):
            return {
                "document_type": "affidavit",
                "confidence": 0.8,
                "summary": "Document appears to be an affidavit based on keyword analysis",
                "key_points": ["Contains affidavit keywords"],
                "legal_analysis": {"significance": "high", "requires_review": True}
            }
        
        elif any(word in text_lower for word in ['order', 'court', 'judge', 'magistrate']):
            return {
                "document_type": "court_order",
                "confidence": 0.7,
                "summary": "Document appears to be a court order based on keyword analysis",
                "key_points": ["Contains court-related keywords"],
                "legal_analysis": {"significance": "high", "requires_review": True}
            }
        
        elif any(word in text_lower for word in ['agreement', 'contract', 'terms', 'parties agree']):
            return {
                "document_type": "agreement",
                "confidence": 0.7,
                "summary": "Document appears to be an agreement or contract",
                "key_points": ["Contains agreement keywords"],
                "legal_analysis": {"significance": "medium", "requires_review": True}
            }
        
        elif len(structured_data.get('amounts', [])) > 2:
            return {
                "document_type": "financial_statement",
                "confidence": 0.6,
                "summary": "Document contains multiple financial amounts",
                "key_points": ["Multiple monetary amounts found"],
                "legal_analysis": {"significance": "medium", "requires_review": True}
            }
        
        else:
            return {
                "document_type": "other",
                "confidence": 0.3,
                "summary": "Could not determine document type from content",
                "key_points": ["No clear classification indicators"],
                "legal_analysis": {"significance": "medium", "requires_review": True}
            }
    
    def _generate_rule_based_summary(self, text: str) -> str:
        """Generate rule-based summary"""
        
        # Simple extractive summary - take first few sentences
        sentences = text.split('.')[:3]
        summary = '. '.join(sentences).strip()
        
        if len(summary) > 500:
            summary = summary[:500] + "..."
        
        return summary or "Document summary not available"
    
    async def _update_document_with_results(self, document: Document, 
                                          tier1: Dict[str, Any], 
                                          tier2: Dict[str, Any],
                                          tier3: Dict[str, Any], 
                                          tier4: Dict[str, Any],
                                          db: Session):
        """Update document record with processing results"""
        
        # Update document fields
        document.extracted_text = tier1.get("text", "")
        document.ai_summary = tier3.get("summary", "")
        document.ai_key_points = tier3.get("key_points", [])
        document.ai_extracted_entities = tier2  # Structured data
        document.ai_classification_confidence = tier3.get("confidence", 0.0)
        document.ocr_confidence = tier4.get("confidence") if tier4 else tier1.get("confidence")
        
        # Set document type if classified
        if tier3.get("document_type"):
            try:
                document.document_type = DocumentType(tier3["document_type"])
            except ValueError:
                document.document_type = DocumentType.OTHER
        
        # Update metadata
        document.metadata = {
            "extraction_methods": [tier1.get("method"), tier4.get("method") if tier4 else None],
            "processing_tiers_completed": ["tier1", "tier2", "tier3"] + (["tier4"] if tier4 else []),
            "page_count": tier1.get("page_count"),
            "requires_review": tier3.get("legal_analysis", {}).get("requires_review", True),
            "legal_significance": tier3.get("legal_analysis", {}).get("significance", "medium")
        }
        
        db.commit()
    
    async def _validate_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Validate uploaded file"""
        
        validation_result = {
            "is_valid": True,
            "error": None,
            "mime_type": None,
            "file_extension": None
        }
        
        # Check file size
        if len(file_data) > self.max_file_size:
            validation_result["is_valid"] = False
            validation_result["error"] = f"File size exceeds {self.max_file_size // (1024*1024)}MB limit"
            return validation_result
        
        # Check file type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type or mime_type not in self.supported_mime_types:
            validation_result["is_valid"] = False
            validation_result["error"] = f"Unsupported file type: {mime_type}"
            return validation_result
        
        validation_result["mime_type"] = mime_type
        validation_result["file_extension"] = self.supported_mime_types[mime_type]
        
        # Basic file content validation
        if len(file_data) < 10:
            validation_result["is_valid"] = False
            validation_result["error"] = "File appears to be empty or corrupted"
            return validation_result
        
        return validation_result
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        
        import re
        # Remove unsafe characters
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        return sanitized
    
    def _generate_storage_path(self, file_hash: str, filename: str) -> str:
        """Generate storage path for file"""
        
        # Use hash-based directory structure for distribution
        dir1 = file_hash[:2]
        dir2 = file_hash[2:4]
        
        _, ext = os.path.splitext(filename)
        stored_filename = f"{file_hash}{ext}"
        
        return f"documents/{dir1}/{dir2}/{stored_filename}"
    
    async def _store_file(self, file_data: bytes, storage_path: str) -> Dict[str, Any]:
        """Store file to filesystem (in production, use cloud storage)"""
        
        try:
            # Create directory structure
            full_path = os.path.join("data", storage_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'wb') as f:
                f.write(file_data)
            
            return {"success": True, "path": full_path}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"File storage failed: {str(e)}"
            }
    
    async def get_document_processing_status(self, document_id: str, 
                                           db: Session) -> Dict[str, Any]:
        """Get document processing status"""
        
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {"error": "Document not found"}
        
        return {
            "document_id": str(document.id),
            "filename": document.filename,
            "processing_status": document.processing_status.value,
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
            "has_text": bool(document.extracted_text),
            "has_summary": bool(document.ai_summary),
            "classification_confidence": document.ai_classification_confidence,
            "ocr_confidence": document.ocr_confidence,
            "requires_review": document.metadata.get("requires_review") if document.metadata else True
        }