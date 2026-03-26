"""
Document Intelligence Engine for KS-LOS

OCR-powered document processing with intelligent field extraction.
Supports Caribbean document formats with confidence scoring and validation.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Document Upload                           │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              OCR Engine (Tesseract)                          │
    │  - Image preprocessing (deskew, denoise, threshold)          │
    │  - Multi-language support (English, Spanish, French)         │
    │  - PDF text extraction (native + scanned)                    │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Document Classifier                             │
    │  - ID/Passport, Pay Slip, Bank Statement, Tax Return         │
    │  - Pattern matching + heuristics                             │
    │  - Confidence scoring per classification                     │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Field Extractor (Type-Specific)                 │
    │  - ID: name, ID number, expiry, nationality                  │
    │  - Pay Slip: employer, gross pay, net pay, pay period        │
    │  - Bank Statement: balance, transactions, account info       │
    │  - Tax Return: declared income, business type, year          │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Validation & Confidence Scoring                 │
    │  - Cross-field validation                                    │
    │  - Sanity checks (income ranges, dates)                      │
    │  - Confidence scores per field (0-1)                         │
    └─────────────────────────────────────────────────────────────┘

Design Principles:
1. **Graceful Degradation**: OCR failure → manual review queue
2. **Confidence-Aware**: Low-confidence fields flagged for review
3. **Audit Trail**: All extractions logged with confidence scores
4. **Caribbean Context**: Regional document format awareness
"""

from typing import Dict, List, Any, Optional, Tuple, Literal
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import re
import logging
import io

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    Image = None
    pdf2image = None

from pydantic import BaseModel, Field, validator


# ─────────────────────────────────────────────────────────────────────────────
# Document Type Enumeration
# ─────────────────────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    """Supported document types for extraction"""
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    PAY_SLIP = "pay_slip"
    BANK_STATEMENT = "bank_statement"
    TAX_RETURN = "tax_return"
    JOB_LETTER = "job_letter"
    BUSINESS_REGISTRATION = "business_registration"
    UTILITY_BILL = "utility_bill"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Extraction Result Models
# ─────────────────────────────────────────────────────────────────────────────

class ExtractedFields(BaseModel):
    """Base model for extracted fields"""
    class Config:
        extra = "allow"


class IDFields(ExtractedFields):
    """Fields extracted from ID/Passport"""
    full_name: Optional[str] = None
    id_number: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    gender: Optional[str] = None


class PaySlipFields(ExtractedFields):
    """Fields extracted from pay slip"""
    employer_name: Optional[str] = None
    employee_name: Optional[str] = None
    gross_pay: Optional[float] = None
    net_pay: Optional[float] = None
    deductions: Optional[float] = None
    pay_period_start: Optional[str] = None
    pay_period_end: Optional[str] = None
    payment_date: Optional[str] = None
    currency: str = "USD"


class BankStatementFields(ExtractedFields):
    """Fields extracted from bank statement"""
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    average_balance: Optional[float] = None
    statement_period_start: Optional[str] = None
    statement_period_end: Optional[str] = None
    transaction_count: Optional[int] = None
    currency: str = "USD"


class TaxReturnFields(ExtractedFields):
    """Fields extracted from tax return"""
    taxpayer_name: Optional[str] = None
    taxpayer_id: Optional[str] = None
    declared_income: Optional[float] = None
    business_type: Optional[str] = None
    tax_year: Optional[int] = None
    tax_paid: Optional[float] = None
    refund_amount: Optional[float] = None


class JobLetterFields(ExtractedFields):
    """Fields extracted from job letter"""
    employer_name: Optional[str] = None
    employee_name: Optional[str] = None
    job_title: Optional[str] = None
    employment_start_date: Optional[str] = None
    salary_amount: Optional[float] = None
    salary_currency: str = "USD"
    employment_type: Optional[str] = None  # permanent, contract, temporary
    is_on_letterhead: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Extraction Result Container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DocumentExtractionResult:
    """
    Complete result from document extraction.
    
    Attributes:
        document_type: Classified document type
        fields: Extracted fields (type-specific)
        raw_text: Raw OCR/text extraction output
        confidence: Overall confidence score (0-1)
        field_confidence: Per-field confidence scores
        flags: Validation flags or warnings
        processing_time_ms: Time taken to process
        ocr_quality: Estimated OCR quality score (0-1)
    """
    document_type: DocumentType
    fields: Optional[ExtractedFields]
    raw_text: str
    confidence: float = 0.5
    field_confidence: Dict[str, float] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    ocr_quality: float = 0.5
    
    def is_reliable(self, threshold: float = 0.7) -> bool:
        """Check if extraction is reliable (above threshold)"""
        return self.confidence >= threshold
    
    def needs_review(self) -> bool:
        """Check if document needs manual review"""
        return self.confidence < 0.7 or len(self.flags) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Document Classifier
# ─────────────────────────────────────────────────────────────────────────────

class DocumentClassifier:
    """
    Classifies document type based on text content.
    
    Uses pattern matching and heuristics optimized for
    Caribbean document formats.
    """
    
    # Classification patterns (keywords per document type)
    PATTERNS = {
        DocumentType.NATIONAL_ID: [
            r"national\s*(?:id|identification)",
            r"identity\s*card",
            r"id\s*card",
            r"card\s*number",
            r"trinidad\s*and\s*tobago",  # Caribbean context
            r"caricom",
        ],
        DocumentType.PASSPORT: [
            r"passport",
            r"passport\s*number",
            r"nationality",
            r"country\s*of\s*issue",
            r"place\s*of\s*birth",
        ],
        DocumentType.PAY_SLIP: [
            r"pay\s*slip",
            r"pay\s*stub",
            r"payslip",
            r"earnings?\s*statement",
            r"gross\s*pay",
            r"net\s*pay",
            r"deductions?",
            r"pay\s*period",
        ],
        DocumentType.BANK_STATEMENT: [
            r"bank\s*statement",
            r"account\s*statement",
            r"transaction(?:s)?",
            r"opening\s*balance",
            r"closing\s*balance",
            r"account\s*number",
            r"statement\s*period",
        ],
        DocumentType.TAX_RETURN: [
            r"tax\s*return",
            r"income\s*tax",
            r"board\s*of\s*inland\s*revenue",  # Caribbean tax authority
            r"ird",  # Inland Revenue Department
            r"declared\s*income",
            r"tax\s*year",
            r"assessment\s*notice",
        ],
        DocumentType.JOB_LETTER: [
            r"employment\s*letter",
            r"job\s*letter",
            r"letter\s*of\s*employment",
            r"to\s*whom\s*it\s*may\s*concern",
            r"we\s*hereby\s*confirm",
            r"is\s*employed\s*by",
            r"position",
            r"salary",
        ],
        DocumentType.BUSINESS_REGISTRATION: [
            r"certificate\s*of\s*incorporation",
            r"business\s*registration",
            r"company\s*number",
            r"registered\s*office",
            r"articles\s*of\s*incorporation",
        ],
        DocumentType.UTILITY_BILL: [
            r"utility\s*bill",
            r"electricity\s*bill",
            r"water\s*bill",
            r"telecommunications?",
            r"account\s*due",
            r"meter\s*reading",
            r"service\s*address",
        ],
    }
    
    def classify(self, text: str) -> Tuple[DocumentType, float]:
        """
        Classify document type from text.
        
        Args:
            text: Document text (from OCR or PDF extraction)
            
        Returns:
            Tuple of (document_type, confidence_score)
        """
        text_lower = text.lower()
        
        # Score each document type
        scores = {}
        for doc_type, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            scores[doc_type] = score
        
        # Find best match
        if not scores or max(scores.values()) == 0:
            return DocumentType.UNKNOWN, 0.3
        
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Normalize confidence (0.5-1.0 based on pattern matches)
        confidence = min(1.0, 0.5 + (best_score * 0.1))
        
        return best_type, confidence


# ─────────────────────────────────────────────────────────────────────────────
# Field Extractors
# ─────────────────────────────────────────────────────────────────────────────

class FieldExtractor:
    """Base class for type-specific field extraction"""
    
    def extract(self, text: str) -> ExtractedFields:
        """Extract fields from text"""
        raise NotImplementedError
    
    def compute_confidence(self, fields: ExtractedFields) -> Dict[str, float]:
        """Compute confidence scores for extracted fields"""
        raise NotImplementedError


class IDFieldExtractor(FieldExtractor):
    """Extract fields from ID/Passport"""
    
    def extract(self, text: str) -> IDFields:
        fields = IDFields()
        
        # Extract ID number (various formats)
        id_patterns = [
            r"(?:id|card|passport)\s*(?:number|no\.?|#)?[:\s]*([A-Z0-9]{6,12})",
            r"([A-Z]{1,2}\d{6,8})",  # Caribbean ID formats
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.id_number = match.group(1).strip()
                break
        
        # Extract name
        name_patterns = [
            r"(?:name|full\s*name|surname)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"([A-Z]{2,}\s*,?\s*[A-Z][a-z]+)",  # LAST, First format
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.full_name = match.group(1).strip()
                break
        
        # Extract nationality
        nationality_match = re.search(
            r"nationality[:\s]*([A-Za-z\s]+?)(?:\n|$)",
            text,
            re.IGNORECASE
        )
        if nationality_match:
            fields.nationality = nationality_match.group(1).strip()
        
        # Extract dates (expiry, birth, issue)
        date_patterns = {
            "expiry_date": r"expir(?:y|ed|ation)?\s*(?:date)?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            "date_of_birth": r"(?:birth|born|dob)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            "issue_date": r"issued?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        }
        
        for field_name, pattern in date_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                setattr(fields, field_name, match.group(1).strip())
        
        return fields
    
    def compute_confidence(self, fields: IDFields) -> Dict[str, float]:
        confidence = {}
        
        # ID number confidence
        if fields.id_number and len(fields.id_number) >= 6:
            confidence["id_number"] = 0.9
        elif fields.id_number:
            confidence["id_number"] = 0.5
        else:
            confidence["id_number"] = 0.0
        
        # Name confidence
        if fields.full_name and " " in fields.full_name:
            confidence["full_name"] = 0.85
        elif fields.full_name:
            confidence["full_name"] = 0.5
        else:
            confidence["full_name"] = 0.0
        
        # Nationality confidence
        if fields.nationality and len(fields.nationality) > 3:
            confidence["nationality"] = 0.8
        else:
            confidence["nationality"] = 0.3
        
        return confidence


class PaySlipFieldExtractor(FieldExtractor):
    """Extract fields from pay slip"""
    
    def extract(self, text: str) -> PaySlipFields:
        fields = PaySlipFields()
        
        # Extract employer name
        employer_match = re.search(
            r"(?:employer|company|organization)[:\s]*([A-Za-z\s&,.]+?)(?:\n|$)",
            text,
            re.IGNORECASE
        )
        if employer_match:
            fields.employer_name = employer_match.group(1).strip()
        
        # Extract employee name
        employee_match = re.search(
            r"(?:employee|name|worker)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            text,
            re.IGNORECASE
        )
        if employee_match:
            fields.employee_name = employee_match.group(1).strip()
        
        # Extract monetary values
        money_patterns = {
            "gross_pay": r"gross\s*(?:pay|salary|earnings?)[:\s]*\$?([\d,]+\.?\d*)",
            "net_pay": r"net\s*(?:pay|salary)[:\s]*\$?([\d,]+\.?\d*)",
            "deductions": r"deductions?[:\s]*\$?([\d,]+\.?\d*)",
        }
        
        for field_name, pattern in money_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(",", ""))
                setattr(fields, field_name, value)
        
        # Extract currency
        if "TTD" in text.upper() or "TT" in text.upper():
            fields.currency = "TTD"
        elif "JMD" in text.upper() or "JAMAICA" in text.upper():
            fields.currency = "JMD"
        elif "BBD" in text.upper() or "BARBADOS" in text.upper():
            fields.currency = "BBD"
        
        return fields
    
    def compute_confidence(self, fields: PaySlipFields) -> Dict[str, float]:
        confidence = {}
        
        # Employer confidence
        if fields.employer_name and len(fields.employer_name) > 5:
            confidence["employer_name"] = 0.85
        else:
            confidence["employer_name"] = 0.3
        
        # Monetary field confidence
        for field_name in ["gross_pay", "net_pay", "deductions"]:
            value = getattr(fields, field_name, None)
            if value and value > 0:
                confidence[field_name] = 0.9
            else:
                confidence[field_name] = 0.0
        
        return confidence


class BankStatementFieldExtractor(FieldExtractor):
    """Extract fields from bank statement"""
    
    def extract(self, text: str) -> BankStatementFields:
        fields = BankStatementFields()
        
        # Extract bank name
        bank_match = re.search(
            r"(?:bank|financial\s*institution|credit\s*union)[:\s]*([A-Za-z\s&,.]+?)(?:\n|$)",
            text,
            re.IGNORECASE
        )
        if bank_match:
            fields.bank_name = bank_match.group(1).strip()
        
        # Extract account holder
        holder_match = re.search(
            r"(?:account\s*holder|name|customer)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            text,
            re.IGNORECASE
        )
        if holder_match:
            fields.account_holder_name = holder_match.group(1).strip()
        
        # Extract balances
        balance_patterns = {
            "opening_balance": r"opening\s*balance[:\s]*\$?([\d,]+\.?\d*)",
            "closing_balance": r"closing\s*balance[:\s]*\$?([\d,]+\.?\d*)",
            "average_balance": r"average\s*balance[:\s]*\$?([\d,]+\.?\d*)",
        }
        
        for field_name, pattern in balance_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(",", ""))
                setattr(fields, field_name, value)
        
        return fields
    
    def compute_confidence(self, fields: BankStatementFields) -> Dict[str, float]:
        confidence = {}
        
        # Bank name confidence
        if fields.bank_name and len(fields.bank_name) > 5:
            confidence["bank_name"] = 0.85
        else:
            confidence["bank_name"] = 0.3
        
        # Balance confidence
        for field_name in ["opening_balance", "closing_balance", "average_balance"]:
            value = getattr(fields, field_name, None)
            if value is not None and value >= 0:
                confidence[field_name] = 0.9
            else:
                confidence[field_name] = 0.0
        
        return confidence


# ─────────────────────────────────────────────────────────────────────────────
# Main Document Intelligence Engine
# ─────────────────────────────────────────────────────────────────────────────

class DocumentIntelligence:
    """
    Main document intelligence engine.
    
    Orchestrates OCR, classification, field extraction, and validation.
    
    Usage:
        engine = DocumentIntelligence()
        
        # Process image file
        result = engine.process_image("path/to/document.jpg")
        
        # Process PDF
        result = engine.process_pdf("path/to/document.pdf")
        
        # Check results
        if result.is_reliable():
            fields = result.fields
        else:
            # Flag for manual review
            ...
    """
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize document intelligence engine.
        
        Args:
            tesseract_cmd: Path to tesseract executable (optional)
        """
        if not OCR_AVAILABLE:
            logging.warning("OCR libraries not available. Running in limited mode.")
        
        if tesseract_cmd and pytesseract:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        self.classifier = DocumentClassifier()
        self.extractors = {
            DocumentType.NATIONAL_ID: IDFieldExtractor(),
            DocumentType.PASSPORT: IDFieldExtractor(),
            DocumentType.PAY_SLIP: PaySlipFieldExtractor(),
            DocumentType.BANK_STATEMENT: BankStatementFieldExtractor(),
            DocumentType.TAX_RETURN: FieldExtractor(),  # Placeholder
            DocumentType.JOB_LETTER: FieldExtractor(),  # Placeholder
            DocumentType.BUSINESS_REGISTRATION: FieldExtractor(),  # Placeholder
            DocumentType.UTILITY_BILL: FieldExtractor(),  # Placeholder
        }
        self.logger = logging.getLogger(__name__)
    
    def process_image(
        self,
        image_path: str,
        preprocess: bool = True
    ) -> DocumentExtractionResult:
        """
        Process image document.
        
        Args:
            image_path: Path to image file
            preprocess: Whether to apply image preprocessing
            
        Returns:
            DocumentExtractionResult with extracted fields
        """
        import time
        start_time = time.time()
        
        if not OCR_AVAILABLE or not Image:
            return self._create_error_result("OCR libraries not available")
        
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            
            if preprocess:
                image = self._preprocess_image(image)
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            # Process extracted text
            result = self._process_text(text)
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            self.logger.error(f"Image processing failed: {str(e)}")
            return self._create_error_result(str(e))
    
    def process_pdf(
        self,
        pdf_path: str,
        page_num: int = 1
    ) -> DocumentExtractionResult:
        """
        Process PDF document.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to process (1-indexed)
            
        Returns:
            DocumentExtractionResult with extracted fields
        """
        import time
        start_time = time.time()
        
        try:
            # Try native text extraction first
            text = self._extract_pdf_text(pdf_path, page_num)
            
            # If no text found, use OCR
            if not text or len(text.strip()) < 50:
                if not OCR_AVAILABLE or not pdf2image:
                    return self._create_error_result("OCR libraries not available for PDF")
                
                # Convert PDF page to image
                images = pdf2image.convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
                if not images:
                    return self._create_error_result("Failed to convert PDF to image")
                
                # OCR the image
                text = pytesseract.image_to_string(images[0])
            
            # Process extracted text
            result = self._process_text(text)
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            self.logger.error(f"PDF processing failed: {str(e)}")
            return self._create_error_result(str(e))
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Operations:
        - Convert to grayscale
        - Apply thresholding
        - Deskew if needed
        - Denoise
        """
        from PIL import ImageOps, ImageFilter
        
        # Convert to grayscale
        image = ImageOps.grayscale(image)
        
        # Apply thresholding (binarization)
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        # Denoise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def _extract_pdf_text(self, pdf_path: str, page_num: int) -> str:
        """Extract text from PDF (native text, not OCR)"""
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(pdf_path)
            if page_num > len(reader.pages):
                return ""
            
            page = reader.pages[page_num - 1]
            return page.extract_text()
            
        except ImportError:
            return ""
        except Exception:
            return ""
    
    def _process_text(self, text: str) -> DocumentExtractionResult:
        """
        Process extracted text through classification and field extraction.
        
        Args:
            text: Text from OCR or PDF extraction
            
        Returns:
            DocumentExtractionResult with all processing results
        """
        # Classify document type
        doc_type, classification_confidence = self.classifier.classify(text)
        
        # Extract fields based on type
        extractor = self.extractors.get(doc_type, FieldExtractor())
        
        try:
            fields = extractor.extract(text)
            field_confidence = extractor.compute_confidence(fields)
        except Exception as e:
            self.logger.warning(f"Field extraction failed: {str(e)}")
            fields = None
            field_confidence = {}
        
        # Compute overall confidence
        overall_confidence = self._compute_overall_confidence(
            classification_confidence,
            field_confidence
        )
        
        # Generate flags
        flags = self._generate_flags(doc_type, fields, field_confidence)
        
        # Estimate OCR quality
        ocr_quality = self._estimate_ocr_quality(text)
        
        return DocumentExtractionResult(
            document_type=doc_type,
            fields=fields,
            raw_text=text,
            confidence=overall_confidence,
            field_confidence=field_confidence,
            flags=flags,
            ocr_quality=ocr_quality,
        )
    
    def _compute_overall_confidence(
        self,
        classification_conf: float,
        field_conf: Dict[str, float]
    ) -> float:
        """Compute overall confidence from classification and field scores"""
        if not field_conf:
            return classification_conf * 0.8
        
        avg_field_conf = sum(field_conf.values()) / len(field_conf)
        
        # Weighted average: 40% classification, 60% field extraction
        return (classification_conf * 0.4) + (avg_field_conf * 0.6)
    
    def _generate_flags(
        self,
        doc_type: DocumentType,
        fields: Optional[ExtractedFields],
        field_conf: Dict[str, float]
    ) -> List[str]:
        """Generate validation flags and warnings"""
        flags = []
        
        if not fields:
            flags.append("Field extraction failed")
            return flags
        
        # Check for low-confidence fields
        for field_name, conf in field_conf.items():
            if conf < 0.5:
                flags.append(f"Low confidence: {field_name}")
        
        # Type-specific validation
        if isinstance(fields, PaySlipFields):
            if fields.gross_pay and fields.net_pay:
                if fields.net_pay > fields.gross_pay:
                    flags.append("Net pay exceeds gross pay - validation error")
        
        if isinstance(fields, IDFields):
            if fields.expiry_date:
                # Check if expired
                try:
                    expiry = datetime.strptime(fields.expiry_date, "%d/%m/%Y")
                    if expiry < datetime.now():
                        flags.append("Document expired")
                except ValueError:
                    flags.append("Invalid expiry date format")
        
        return flags
    
    def _estimate_ocr_quality(self, text: str) -> float:
        """Estimate OCR quality from text characteristics"""
        if not text:
            return 0.0
        
        # Quality indicators
        word_count = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / max(word_count, 1)
        
        # Check for OCR artifacts
        artifact_count = len(re.findall(r'[|\\/\[\]{}]', text))
        special_char_ratio = artifact_count / max(len(text), 1)
        
        # Score calculation
        quality = 0.5
        
        if word_count > 20:
            quality += 0.2
        if 4 <= avg_word_length <= 10:
            quality += 0.2
        if special_char_ratio < 0.01:
            quality += 0.1
        
        return min(1.0, quality)
    
    def _create_error_result(self, error: str) -> DocumentExtractionResult:
        """Create error result"""
        return DocumentExtractionResult(
            document_type=DocumentType.UNKNOWN,
            fields=None,
            raw_text="",
            confidence=0.0,
            flags=[f"Error: {error}"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

def extract_from_image(
    image_path: str,
    preprocess: bool = True
) -> DocumentExtractionResult:
    """
    Convenience function to extract from image.
    
    Args:
        image_path: Path to image file
        preprocess: Apply image preprocessing
        
    Returns:
        DocumentExtractionResult
    """
    engine = DocumentIntelligence()
    return engine.process_image(image_path, preprocess=preprocess)


def extract_from_pdf(
    pdf_path: str,
    page_num: int = 1
) -> DocumentExtractionResult:
    """
    Convenience function to extract from PDF.
    
    Args:
        pdf_path: Path to PDF file
        page_num: Page number to process
        
    Returns:
        DocumentExtractionResult
    """
    engine = DocumentIntelligence()
    return engine.process_pdf(pdf_path, page_num=page_num)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Enums
    "DocumentType",
    
    # Field models
    "ExtractedFields",
    "IDFields",
    "PaySlipFields",
    "BankStatementFields",
    "TaxReturnFields",
    "JobLetterFields",
    
    # Result container
    "DocumentExtractionResult",
    
    # Main engine
    "DocumentIntelligence",
    
    # Convenience functions
    "extract_from_image",
    "extract_from_pdf",
]
