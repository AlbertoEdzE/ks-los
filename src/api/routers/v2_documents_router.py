import os
import uuid
from io import BytesIO
from datetime import datetime, timezone
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.shared.auth import API_KEYS, ENFORCE_RBAC, ROLE_ORDER, get_presented_token, get_role_for_token, require_role
from src.shared.audit import log_audit
from src.shared.db import Loan, LoanDocument, get_db
from src.shared.metrics import request_counter, request_errors_total

router = APIRouter(prefix="/api/documents", tags=["v2-documents"], dependencies=[Depends(require_role("viewer"))])


def _is_officer_request(x_api_key: str | None, authorization: str | None) -> bool:
    token = get_presented_token(x_api_key, authorization)
    if ENFORCE_RBAC and API_KEYS:
        if not token:
            return False
        role = get_role_for_token(token)
        if not role:
            return False
        return ROLE_ORDER[role] >= ROLE_ORDER["operator"]
    dev_officer = os.getenv("DEV_OFFICER_TOKEN", "loan-officer-access")
    dev_admin = os.getenv("DEV_ADMIN_TOKEN", "admin-access")
    return token in (dev_officer, dev_admin)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    keep = []
    for ch in (name or "").strip():
        if ch.isalnum() or ch in {".", "-", "_"}:
            keep.append(ch)
        else:
            keep.append("_")
    out = "".join(keep).strip("._")
    return out or "file"


def _sanitize_document(doc: LoanDocument) -> dict[str, Any]:
    return {
        "id": doc.id,
        "loanId": doc.loan_id,
        "category": doc.category,
        "documentType": doc.document_type,
        "status": doc.status,
        "reviewNote": doc.review_note,
        "fileName": doc.file_name,
        "originalName": doc.original_name,
        "mimeType": doc.mime_type,
        "fileSize": doc.file_size,
        "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "reviewedAt": doc.reviewed_at.isoformat() if doc.reviewed_at else None,
        "meta": doc.meta,
    }


def _extract_text(raw: bytes, mime_type: str | None) -> tuple[str | None, str | None]:
    """Extract text from PDF or image files using OCR when needed."""
    mt = (mime_type or "").lower()
    import logging
    logger = logging.getLogger(__name__)

    try:
        # PDF handling
        if mt == "application/pdf" or raw[:4] == b"%PDF":
            try:
                from pypdf import PdfReader  # type: ignore[import-not-found]
            except Exception as e:
                logger.warning(f"pypdf not available: {e}")
                return None, f"pypdf_unavailable:{type(e).__name__}"

            try:
                reader = PdfReader(BytesIO(raw))
                chunks: list[str] = []
                for p in getattr(reader, "pages", [])[:25]:
                    try:
                        txt = p.extract_text() or ""
                    except Exception:
                        txt = ""
                    if txt.strip():
                        chunks.append(txt)
                    if sum(len(c) for c in chunks) > 20000:
                        break
                text = "\n\n".join(chunks).strip()
                if text:
                    logger.info(f"PDF text extracted: {len(text)} chars")
                    return text, None
                else:
                    logger.warning("PDF extracted but no text found (may be scanned)")
                    return None, "pdf_no_text_extractable"
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return None, f"pdf_extract_failed:{type(e).__name__}"

        # Image handling with OCR
        if mt.startswith("image/") or raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n":
            # Try PIL first
            try:
                from PIL import Image, ImageOps  # type: ignore[import-not-found]
            except Exception as e:
                logger.warning(f"PIL not available: {e}")
                return None, f"pil_unavailable:{type(e).__name__}"

            # Try pytesseract
            try:
                import pytesseract  # type: ignore[import-not-found]
            except Exception as e:
                logger.warning(f"pytesseract not available: {e}")
                return None, f"pytesseract_unavailable:{type(e).__name__}"

            # Check if tesseract binary is available
            try:
                _ = pytesseract.get_tesseract_version()
            except Exception as e:
                logger.warning(f"Tesseract binary not found: {e}")
                return None, f"tesseract_not_installed:{type(e).__name__}"

            try:
                img = Image.open(BytesIO(raw))
                img = ImageOps.exif_transpose(img)
                if img.mode not in {"RGB", "L"}:
                    img = img.convert("RGB")
                txt = pytesseract.image_to_string(img, config="--psm 6") or ""
                out = txt.strip()
                if out:
                    logger.info(f"OCR text extracted: {len(out)} chars")
                    return out, None
                else:
                    logger.warning("OCR ran but no text found")
                    return None, "ocr_no_text_found"
            except Exception as e:
                logger.error(f"OCR processing failed: {e}")
                return None, f"ocr_processing_failed:{type(e).__name__}"

    except Exception as e:
        logger.error(f"Unexpected extraction error: {e}")
        return None, f"extract_failed:{type(e).__name__}"

    return None, None


def _extract_fields(document_type: str | None, text: str | None) -> dict[str, Any]:
    dt = (document_type or "").lower()
    if not text:
        return {}
    t = text

    fields: dict[str, Any] = {}
    money = re.findall(r"(?:USD|TTD|JMD|GYD|\$)\s*[\d,]+(?:\.\d{1,2})?", t, flags=re.IGNORECASE)
    if money:
        fields["amounts"] = money[:10]

    if any(k in dt for k in ["national_id", "passport", "id"]):
        fields["containsIdentityInfo"] = True

    if "job" in dt or "employment" in dt:
        salary = re.findall(r"(?:salary|basic|gross)\s*[:\-]?\s*(?:USD|TTD|JMD|GYD|\$)?\s*[\d,]+(?:\.\d{1,2})?", t, flags=re.IGNORECASE)
        if salary:
            fields["salaryLines"] = salary[:5]

    return fields


def _require_loan_access(
    *,
    db: Session,
    loan_id: str,
    conversation_id: Optional[str],
    x_api_key: Optional[str],
    authorization: Optional[str],
) -> Loan:
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if _is_officer_request(x_api_key, authorization):
        return loan
    if not conversation_id or not loan.conversation_id or conversation_id != loan.conversation_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return loan


class ReviewDocumentRequest(BaseModel):
    status: str
    reviewNote: Optional[str] = None


@router.post("/upload")
async def upload_document(
    loan_id: str = Form(..., alias="loanId"),
    category: str = Form(...),
    document_type: str = Form(..., alias="documentType"),
    file: UploadFile = File(...),
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/documents/upload").inc()

    loan = _require_loan_access(
        db=db,
        loan_id=loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )

    allowed = {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type and file.content_type not in allowed:
        request_errors_total.labels(endpoint="/api/documents/upload").inc()
        raise HTTPException(status_code=400, detail="File type not supported")

    raw = await file.read()
    if not raw:
        request_errors_total.labels(endpoint="/api/documents/upload").inc()
        raise HTTPException(status_code=400, detail="No file uploaded")
    if len(raw) > 10 * 1024 * 1024:
        request_errors_total.labels(endpoint="/api/documents/upload").inc()
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 10 MB.")

    uploads_root = os.getenv("KS_LOS_UPLOAD_DIR", "data/uploads")
    doc_uuid = str(uuid.uuid4())
    safe = _safe_filename(file.filename or "document")
    loan_dir = os.path.join(uploads_root, "documents", loan.id)
    os.makedirs(loan_dir, exist_ok=True)
    stored_name = f"{doc_uuid}-{safe}"
    stored_path = os.path.join(loan_dir, stored_name)
    with open(stored_path, "wb") as f:
        f.write(raw)

    extracted_text, extraction_error = _extract_text(raw, file.content_type)
    extracted_fields = _extract_fields(document_type, extracted_text)
    extraction_meta: dict[str, Any] = {"status": "none"}
    if extracted_text:
        extraction_meta = {
            "status": "ok",
            "textPreview": extracted_text[:2000],
            "fields": extracted_fields,
        }
    elif extraction_error:
        extraction_meta = {"status": "error", "error": extraction_error}

    uploaded_by = "officer" if _is_officer_request(x_api_key, authorization) else "borrower"
    doc = LoanDocument(
        id=doc_uuid,
        loan_id=loan.id,
        uploaded_by=uploaded_by,
        category=(category or "").strip(),
        document_type=(document_type or "").strip(),
        status="uploaded",
        review_note=None,
        file_name=stored_name,
        original_name=file.filename,
        mime_type=file.content_type,
        file_size=len(raw),
        file_path=stored_path,
        meta={"uploadedAt": _now_iso(), "extraction": extraction_meta},
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit(
        event="v2_document_uploaded",
        endpoint="/api/documents/upload",
        status="success",
        meta={"loanId": loan.id, "documentId": doc.id, "category": category, "documentType": document_type},
    )

    try:
        status_now = (loan.stp_processing_status or "").strip().lower()
        if status_now in {"", "awaiting_documents"} and not _is_officer_request(x_api_key, authorization):
            docs = (
                db.execute(select(LoanDocument).where(LoanDocument.loan_id == loan.id).order_by(LoanDocument.uploaded_at.desc(), LoanDocument.id.desc()))
                .scalars()
                .all()
            )
            has_identity = any((d.category or "").strip().lower() == "identity" for d in docs) or any(
                any(tok in ((d.document_type or "").strip().lower()) for tok in ["id", "passport", "national"]) for d in docs
            )
            has_income = any(((d.category or "").strip().lower()).startswith("income") for d in docs) or any(
                any(tok in ((d.document_type or "").strip().lower()) for tok in ["pay", "salary", "job", "bank_statement", "bank-stat", "statement"]) for d in docs
            )
            if has_identity and has_income and len(docs) >= 2:
                from src.api.routers.v2_loan_acceptance_router import _run_stp

                loan.stp_processing_status = "processing"
                loan.stp_processing_log = [{"ts": _now_iso(), "phase": "STP started", "passed": 0, "total": 0}]
                db.add(loan)
                db.commit()
                db.refresh(loan)
                _run_stp(db, loan)
                if (
                    loan.conversation_id
                    and (loan.stp_processing_status or "").lower() == "awaiting_acceptance"
                    and isinstance(loan.stp_payload, dict)
                ):
                    from src.shared.db import Message

                    approval = loan.stp_payload.get("approval") if isinstance(loan.stp_payload.get("approval"), dict) else {}
                    affordability = loan.stp_payload.get("affordability") if isinstance(loan.stp_payload.get("affordability"), dict) else {}
                    stp_steps = loan.stp_payload.get("stpSteps") if isinstance(loan.stp_payload.get("stpSteps"), list) else []
                    
                    # Build metadata for UI cards
                    loan_app_meta = {
                        "success": True,
                        "loanId": loan.id,
                        "stpApproved": True,
                        "stpCompleted": True,
                        "awaitingAcceptance": True,
                        "approval": {
                            "rate": approval.get("rate"),
                            "tenure": approval.get("tenure"),
                            "emi": approval.get("emi"),
                            "conditions": approval.get("conditions", []),
                        },
                        "affordability": affordability,
                        "stpSteps": stp_steps,
                        "bureauReport": loan.stp_payload.get("bureau"),
                    }
                    
                    msg = Message(
                        conversation_id=loan.conversation_id,
                        role="assistant",
                        content=(
                            "Great news! Automated checks are complete and your indicative offer is ready.\n\n"
                            f"• **Interest Rate**: {approval.get('rate') or 'N/A'}\n"
                            f"• **Tenure**: {approval.get('tenure') or 'N/A'}\n"
                            f"• **Monthly EMI**: {approval.get('emi') or 'N/A'}\n\n"
                            "Please review the terms below and provide your electronic signature to proceed with disbursement."
                        ),
                        metadata_json={
                            "type": "stp_offer",
                            "loanId": loan.id,
                            "loanApplication": loan_app_meta,
                            "awaitingAcceptance": True,
                        },
                    )
                    db.add(msg)
                    db.commit()
    except Exception:
        pass

    return _sanitize_document(doc)


@router.get("/loan/{loan_id}")
def list_documents_by_loan(
    loan_id: str,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/documents/loan/{loanId}").inc()

    _require_loan_access(
        db=db,
        loan_id=loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )
    docs = (
        db.execute(select(LoanDocument).where(LoanDocument.loan_id == loan_id).order_by(LoanDocument.uploaded_at.desc(), LoanDocument.id.desc()))
        .scalars()
        .all()
    )
    return [_sanitize_document(d) for d in docs]


@router.get("/{doc_id}/download")
def download_document(
    doc_id: str,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/documents/{id}/download").inc()

    doc = db.get(LoanDocument, doc_id)
    if not doc:
        request_errors_total.labels(endpoint="/api/documents/{id}/download").inc()
        raise HTTPException(status_code=404, detail="Document not found")

    _require_loan_access(
        db=db,
        loan_id=doc.loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )

    if not doc.file_path or not os.path.exists(doc.file_path):
        request_errors_total.labels(endpoint="/api/documents/{id}/download").inc()
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=doc.file_path,
        media_type=doc.mime_type or "application/octet-stream",
        filename=doc.original_name or doc.file_name,
        headers={"Content-Disposition": f'inline; filename="{doc.original_name or doc.file_name}"'},
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    x_conversation_id: str | None = Header(default=None, alias="X-Conversation-ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/documents/{id}").inc()

    doc = db.get(LoanDocument, doc_id)
    if not doc:
        request_errors_total.labels(endpoint="/api/documents/{id}").inc()
        raise HTTPException(status_code=404, detail="Document not found")

    _require_loan_access(
        db=db,
        loan_id=doc.loan_id,
        conversation_id=x_conversation_id,
        x_api_key=x_api_key,
        authorization=authorization,
    )

    if (doc.status or "").lower() == "approved":
        request_errors_total.labels(endpoint="/api/documents/{id}").inc()
        raise HTTPException(status_code=400, detail="Cannot delete an approved document")

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()

    log_audit(
        event="v2_document_deleted",
        endpoint="/api/documents/{id}",
        status="success",
        meta={"documentId": doc_id, "loanId": doc.loan_id},
    )

    return {"success": True}


@router.patch("/{doc_id}/review")
def review_document(
    doc_id: str,
    payload: ReviewDocumentRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    request_counter.labels(endpoint="/api/documents/{id}/review").inc()
    if not _is_officer_request(x_api_key, authorization):
        request_errors_total.labels(endpoint="/api/documents/{id}/review").inc()
        raise HTTPException(status_code=403, detail="Not authorized")

    doc = db.get(LoanDocument, doc_id)
    if not doc:
        request_errors_total.labels(endpoint="/api/documents/{id}/review").inc()
        raise HTTPException(status_code=404, detail="Document not found")

    status = (payload.status or "").strip().lower()
    allowed = {"uploaded", "approved", "rejected", "needs_reupload"}
    if status not in allowed:
        request_errors_total.labels(endpoint="/api/documents/{id}/review").inc()
        raise HTTPException(status_code=400, detail="Invalid document status")

    doc.status = status
    doc.review_note = payload.reviewNote
    doc.reviewed_at = datetime.now(timezone.utc)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit(
        event="v2_document_reviewed",
        endpoint="/api/documents/{id}/review",
        status="success",
        meta={"documentId": doc.id, "loanId": doc.loan_id, "status": doc.status},
    )
    return _sanitize_document(doc)
