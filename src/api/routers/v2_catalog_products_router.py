import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.routers.v2_auth import require_officer_role
from src.shared.audit import log_audit
from src.shared.db import LoanProductCatalog, get_db
from src.shared.metrics import request_counter, request_errors_total, v2_catalog_product_writes_total


router = APIRouter(
    prefix="/api/catalog-products",
    tags=["v2_catalog_products"],
    dependencies=[Depends(require_officer_role)],
)


DEFAULT_PRODUCTS = [
    {
        "name": "Home Purchase Loan",
        "code": "HL-PUR-001",
        "category": "home_loan",
        "description": "Standard home loan for purchasing residential properties.",
        "min_amount": "₹5,00,000",
        "max_amount": "₹10,00,00,000",
        "min_tenure_months": 12,
        "max_tenure_months": 360,
        "base_interest_rate": "8.40%",
        "max_interest_rate": "11.50%",
        "processing_fee_percent": "0.50%",
        "prepayment_penalty": "Nil for floating rate",
        "min_credit_score": 700,
        "max_ltv": "80%",
        "min_income": "₹25,000",
        "collateral_required": True,
        "insurance_required": True,
        "required_documents": ["PAN Card", "Aadhaar Card", "Salary Slips (3 months)", "Bank Statements (6 months)"],
        "eligibility_criteria": ["Age 21–65 years", "CIBIL score 700+"],
        "features": ["Floating & fixed rate options", "Balance transfer facility"],
        "target_segment": "Salaried & Self-employed",
        "risk_grade": "AA",
        "status": "active",
        "icon": "home",
        "color": "#3b82f6",
    },
    {
        "name": "New Car Loan",
        "code": "AL-NEW-001",
        "category": "auto_loan",
        "description": "Financing for brand new passenger vehicles from authorized dealerships.",
        "min_amount": "₹1,00,000",
        "max_amount": "₹1,50,00,000",
        "min_tenure_months": 12,
        "max_tenure_months": 84,
        "base_interest_rate": "7.65%",
        "max_interest_rate": "12.50%",
        "processing_fee_percent": "0.50%",
        "prepayment_penalty": "2% on fixed rate, Nil on floating",
        "min_credit_score": 700,
        "max_ltv": "90%",
        "min_income": "₹20,000",
        "collateral_required": True,
        "insurance_required": True,
        "required_documents": ["PAN Card", "Aadhaar Card", "Proforma invoice from dealer"],
        "eligibility_criteria": ["Age 21–65 years", "CIBIL 700+"],
        "features": ["Up to 90% financing", "Same-day approval possible"],
        "target_segment": "Salaried & Self-employed professionals",
        "risk_grade": "AA",
        "status": "active",
        "icon": "car",
        "color": "#0ea5e9",
    },
    {
        "name": "Personal Loan — Salaried",
        "code": "PL-SAL-001",
        "category": "personal_loan",
        "description": "Unsecured personal loan for salaried professionals.",
        "min_amount": "₹50,000",
        "max_amount": "₹40,00,000",
        "min_tenure_months": 12,
        "max_tenure_months": 60,
        "base_interest_rate": "10.49%",
        "max_interest_rate": "21.00%",
        "processing_fee_percent": "2.00%",
        "prepayment_penalty": "4% of outstanding in first year",
        "min_credit_score": 700,
        "max_ltv": None,
        "min_income": "₹25,000",
        "collateral_required": False,
        "insurance_required": False,
        "required_documents": ["PAN Card", "Aadhaar Card", "Salary slips (3 months)", "Bank statements (6 months)"],
        "eligibility_criteria": ["Age 23–58 years", "CIBIL 700+"],
        "features": ["100% digital process", "Disbursal within 4 hours"],
        "target_segment": "Salaried professionals",
        "risk_grade": "A",
        "status": "active",
        "icon": "wallet",
        "color": "#6366f1",
    },
]


def _ensure_seeded(db: Session):
    existing = db.execute(select(LoanProductCatalog.id).limit(1)).first()
    if existing is not None:
        return
    for p in DEFAULT_PRODUCTS:
        db.add(LoanProductCatalog(**p))
    db.commit()


def _serialize_product(p: LoanProductCatalog) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "code": p.code,
        "category": p.category,
        "description": p.description,
        "minAmount": p.min_amount,
        "maxAmount": p.max_amount,
        "minTenureMonths": p.min_tenure_months,
        "maxTenureMonths": p.max_tenure_months,
        "baseInterestRate": p.base_interest_rate,
        "maxInterestRate": p.max_interest_rate,
        "processingFeePercent": p.processing_fee_percent,
        "prepaymentPenalty": p.prepayment_penalty,
        "minCreditScore": p.min_credit_score,
        "maxLtv": p.max_ltv,
        "minIncome": p.min_income,
        "collateralRequired": p.collateral_required,
        "requiredDocuments": p.required_documents,
        "eligibilityCriteria": p.eligibility_criteria,
        "features": p.features,
        "targetSegment": p.target_segment,
        "riskGrade": p.risk_grade,
        "insuranceRequired": p.insurance_required,
        "status": p.status,
        "icon": p.icon,
        "color": p.color,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
    }


class CreateCatalogProductRequest(BaseModel):
    name: str
    code: str
    category: str
    description: Optional[str] = None
    minAmount: Optional[str] = None
    maxAmount: Optional[str] = None
    minTenureMonths: Optional[int] = None
    maxTenureMonths: Optional[int] = None
    baseInterestRate: Optional[str] = None
    maxInterestRate: Optional[str] = None
    processingFeePercent: Optional[str] = None
    prepaymentPenalty: Optional[str] = None
    minCreditScore: Optional[int] = None
    maxLtv: Optional[str] = None
    minIncome: Optional[str] = None
    collateralRequired: Optional[bool] = None
    requiredDocuments: Optional[list] = None
    eligibilityCriteria: Optional[list] = None
    features: Optional[list] = None
    targetSegment: Optional[str] = None
    riskGrade: Optional[str] = None
    insuranceRequired: Optional[bool] = None
    status: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class PatchCatalogProductRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    minAmount: Optional[str] = None
    maxAmount: Optional[str] = None
    minTenureMonths: Optional[int] = None
    maxTenureMonths: Optional[int] = None
    baseInterestRate: Optional[str] = None
    maxInterestRate: Optional[str] = None
    processingFeePercent: Optional[str] = None
    prepaymentPenalty: Optional[str] = None
    minCreditScore: Optional[int] = None
    maxLtv: Optional[str] = None
    minIncome: Optional[str] = None
    collateralRequired: Optional[bool] = None
    requiredDocuments: Optional[list] = None
    eligibilityCriteria: Optional[list] = None
    features: Optional[list] = None
    targetSegment: Optional[str] = None
    riskGrade: Optional[str] = None
    insuranceRequired: Optional[bool] = None
    status: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.get("")
def list_catalog_products(db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/catalog-products").inc()
    _ensure_seeded(db)
    rows = db.execute(select(LoanProductCatalog).order_by(LoanProductCatalog.created_at.desc())).scalars().all()
    return [_serialize_product(p) for p in rows]


@router.post("")
def create_catalog_product(req: CreateCatalogProductRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/catalog-products").inc()
    _ensure_seeded(db)
    product = LoanProductCatalog(
        id=str(uuid.uuid4()),
        name=req.name,
        code=req.code,
        category=req.category,
        description=req.description,
        min_amount=req.minAmount,
        max_amount=req.maxAmount,
        min_tenure_months=req.minTenureMonths,
        max_tenure_months=req.maxTenureMonths,
        base_interest_rate=req.baseInterestRate,
        max_interest_rate=req.maxInterestRate,
        processing_fee_percent=req.processingFeePercent,
        prepayment_penalty=req.prepaymentPenalty,
        min_credit_score=req.minCreditScore,
        max_ltv=req.maxLtv,
        min_income=req.minIncome,
        collateral_required=req.collateralRequired if req.collateralRequired is not None else False,
        required_documents=req.requiredDocuments,
        eligibility_criteria=req.eligibilityCriteria,
        features=req.features,
        target_segment=req.targetSegment,
        risk_grade=req.riskGrade,
        insurance_required=req.insuranceRequired if req.insuranceRequired is not None else False,
        status=req.status or "draft",
        icon=req.icon,
        color=req.color,
    )
    try:
        db.add(product)
        db.commit()
        db.refresh(product)
        log_audit(
            event="v2_catalog_product_create",
            endpoint="/api/catalog-products",
            status="success",
            meta={"productId": product.id, "code": product.code, "statusValue": product.status},
        )
        v2_catalog_product_writes_total.labels(op="create", status="success").inc()
        return _serialize_product(product)
    except Exception as e:
        db.rollback()
        request_errors_total.labels(endpoint="/api/catalog-products").inc()
        log_audit(
            event="v2_catalog_product_create",
            endpoint="/api/catalog-products",
            status="error",
            meta={"error": str(e)},
        )
        v2_catalog_product_writes_total.labels(op="create", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{product_id}")
def patch_catalog_product(product_id: str, req: PatchCatalogProductRequest, db: Session = Depends(get_db)):
    request_counter.labels(endpoint="/api/catalog-products/{product_id}").inc()
    product = db.get(LoanProductCatalog, product_id)
    if not product:
        request_errors_total.labels(endpoint="/api/catalog-products/{product_id}").inc()
        log_audit(
            event="v2_catalog_product_patch",
            endpoint="/api/catalog-products/{product_id}",
            status="not_found",
            meta={"productId": product_id},
        )
        v2_catalog_product_writes_total.labels(op="patch", status="not_found").inc()
        raise HTTPException(status_code=404, detail="Product not found")

    if req.name is not None:
        product.name = req.name
    if req.code is not None:
        product.code = req.code
    if req.category is not None:
        product.category = req.category
    if req.description is not None:
        product.description = req.description
    if req.minAmount is not None:
        product.min_amount = req.minAmount
    if req.maxAmount is not None:
        product.max_amount = req.maxAmount
    if req.minTenureMonths is not None:
        product.min_tenure_months = req.minTenureMonths
    if req.maxTenureMonths is not None:
        product.max_tenure_months = req.maxTenureMonths
    if req.baseInterestRate is not None:
        product.base_interest_rate = req.baseInterestRate
    if req.maxInterestRate is not None:
        product.max_interest_rate = req.maxInterestRate
    if req.processingFeePercent is not None:
        product.processing_fee_percent = req.processingFeePercent
    if req.prepaymentPenalty is not None:
        product.prepayment_penalty = req.prepaymentPenalty
    if req.minCreditScore is not None:
        product.min_credit_score = req.minCreditScore
    if req.maxLtv is not None:
        product.max_ltv = req.maxLtv
    if req.minIncome is not None:
        product.min_income = req.minIncome
    if req.collateralRequired is not None:
        product.collateral_required = req.collateralRequired
    if req.requiredDocuments is not None:
        product.required_documents = req.requiredDocuments
    if req.eligibilityCriteria is not None:
        product.eligibility_criteria = req.eligibilityCriteria
    if req.features is not None:
        product.features = req.features
    if req.targetSegment is not None:
        product.target_segment = req.targetSegment
    if req.riskGrade is not None:
        product.risk_grade = req.riskGrade
    if req.insuranceRequired is not None:
        product.insurance_required = req.insuranceRequired
    if req.status is not None:
        product.status = req.status
    if req.icon is not None:
        product.icon = req.icon
    if req.color is not None:
        product.color = req.color

    try:
        db.add(product)
        db.commit()
        db.refresh(product)
        log_audit(
            event="v2_catalog_product_patch",
            endpoint="/api/catalog-products/{product_id}",
            status="success",
            meta={"productId": product_id, "code": product.code, "statusValue": product.status},
        )
        v2_catalog_product_writes_total.labels(op="patch", status="success").inc()
        return _serialize_product(product)
    except Exception as e:
        db.rollback()
        request_errors_total.labels(endpoint="/api/catalog-products/{product_id}").inc()
        log_audit(
            event="v2_catalog_product_patch",
            endpoint="/api/catalog-products/{product_id}",
            status="error",
            meta={"productId": product_id, "error": str(e)},
        )
        v2_catalog_product_writes_total.labels(op="patch", status="error").inc()
        raise HTTPException(status_code=400, detail=str(e))
