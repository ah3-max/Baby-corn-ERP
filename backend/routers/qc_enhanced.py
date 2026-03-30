"""
WP2：QC 品質管理強化 API

QC 檢驗：
  GET    /qc/inspections              - 檢驗列表
  POST   /qc/inspections              - 新增檢驗（含評分卡）
  GET    /qc/inspections/:id          - 檢驗詳情
  PUT    /qc/inspections/:id          - 更新檢驗
  DELETE /qc/inspections/:id          - 刪除檢驗

QC 照片：
  POST   /qc/inspections/:id/photos   - 上傳照片
  GET    /qc/inspections/:id/photos   - 照片列表
  DELETE /qc/photos/:id               - 刪除照片

抽樣規則：
  GET    /qc/sampling-rules           - 列表
  POST   /qc/sampling-rules           - 新增
  PUT    /qc/sampling-rules/:id       - 更新

通路品質標準：
  GET    /qc/channel-standards        - 列表
  POST   /qc/channel-standards        - 新增
  PUT    /qc/channel-standards/:id    - 更新
  GET    /qc/channel-standards/:id/check-batch/:bid - 檢查批次是否符合

QC 分析：
  GET    /qc/analytics/trend          - QC 趨勢
  GET    /qc/analytics/supplier-quality - 供應商品質排名
  GET    /qc/analytics/defect-frequency - 缺陷頻率
"""
import os
import shutil
from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_

from database import get_db
from models.user import User
from models.batch import Batch
from models.qc_enhanced import (
    QCInspection, QCPhoto, QCScoreCard, QCSamplingRule,
    ChannelQCStandard, INSPECTION_STAGES, INSPECTION_RESULTS,
)
from schemas.qc_enhanced import (
    QCInspectionCreate, QCInspectionUpdate, QCInspectionOut,
    QCPhotoOut, QCScoreCardCreate,
    QCSamplingRuleCreate, QCSamplingRuleUpdate, QCSamplingRuleOut,
    ChannelQCStandardCreate, ChannelQCStandardUpdate, ChannelQCStandardOut,
)
from utils.dependencies import check_permission

router = APIRouter(prefix="/qc", tags=["QC 品質管理"])


# ─── 工具函式 ────────────────────────────────────────────

def _generate_inspection_no(db: Session) -> str:
    """產生檢驗編號：QC-YYYYMMDD-XXX"""
    from sqlalchemy import text
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('qc_inspection_no'))"))
    date_str = date.today().strftime("%Y%m%d")
    prefix = f"QC-{date_str}-"
    count = db.query(func.count(QCInspection.id)).filter(
        QCInspection.inspection_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _load_inspection(db: Session, inspection_id: UUID) -> QCInspection:
    insp = (
        db.query(QCInspection)
        .options(
            joinedload(QCInspection.photos),
            joinedload(QCInspection.score_cards),
        )
        .filter(QCInspection.id == inspection_id)
        .first()
    )
    if not insp:
        raise HTTPException(status_code=404, detail="檢驗記錄不存在")
    return insp


# ─── QC 檢驗 CRUD ───────────────────────────────────────

@router.get("/inspections", response_model=List[QCInspectionOut])
def list_inspections(
    batch_id:   Optional[UUID] = Query(None),
    stage:      Optional[str]  = Query(None),
    result:     Optional[str]  = Query(None),
    skip:       int = 0,
    limit:      int = 100,
    db:         Session = Depends(get_db),
    _:          User = Depends(check_permission("qc", "view")),
):
    q = db.query(QCInspection).options(
        joinedload(QCInspection.photos),
        joinedload(QCInspection.score_cards),
    )
    if batch_id:
        q = q.filter(QCInspection.batch_id == batch_id)
    if stage:
        q = q.filter(QCInspection.inspection_stage == stage)
    if result:
        q = q.filter(QCInspection.overall_result == result)
    return q.order_by(QCInspection.inspection_datetime.desc()).offset(skip).limit(limit).all()


@router.post("/inspections", response_model=QCInspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload:      QCInspectionCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("qc", "create")),
):
    """新增 QC 檢驗（含內嵌評分卡）"""
    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    if payload.inspection_stage not in INSPECTION_STAGES:
        raise HTTPException(status_code=400, detail=f"無效的檢驗階段：{payload.inspection_stage}")
    if payload.overall_result not in INSPECTION_RESULTS:
        raise HTTPException(status_code=400, detail=f"無效的檢驗結果：{payload.overall_result}")

    inspection_no = _generate_inspection_no(db)
    insp = QCInspection(
        inspection_no=inspection_no,
        batch_id=payload.batch_id,
        inspection_stage=payload.inspection_stage,
        sampling_rule_id=payload.sampling_rule_id,
        total_boxes_in_batch=payload.total_boxes_in_batch,
        sampled_boxes=payload.sampled_boxes,
        sampled_units=payload.sampled_units,
        inspector_user_id=current_user.id,
        inspector_name=payload.inspector_name,
        inspection_datetime=payload.inspection_datetime or datetime.utcnow(),
        environment_temp_c=payload.environment_temp_c,
        environment_humidity_pct=payload.environment_humidity_pct,
        overall_result=payload.overall_result,
        overall_grade=payload.overall_grade,
        overall_score=payload.overall_score,
        defect_summary=payload.defect_summary or {},
        grade_distribution=payload.grade_distribution or {},
        recommendation=payload.recommendation,
        next_batch_notes=payload.next_batch_notes,
        pesticide_test_result=payload.pesticide_test_result,
        created_by=current_user.id,
    )
    db.add(insp)
    db.flush()

    # 建立內嵌評分卡
    if payload.score_cards:
        for sc in payload.score_cards:
            db.add(QCScoreCard(
                inspection_id=insp.id,
                score_item=sc.score_item,
                score_value=sc.score_value,
                score_text=sc.score_text,
                is_pass=sc.is_pass,
                weight=sc.weight,
                note=sc.note,
            ))

    # ─── QC 自動推播通知 ───
    from services.qc_notification import notify_qc_result
    notify_qc_result(db, insp, batch, current_user)

    # QC 通過時自動推進批次狀態
    if payload.overall_result in ("pass", "conditional_pass") and batch.status == "qc_pending":
        batch.status = "qc_done"

    db.commit()
    return _load_inspection(db, insp.id)


@router.get("/inspections/{inspection_id}", response_model=QCInspectionOut)
def get_inspection(
    inspection_id: UUID,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("qc", "view")),
):
    return _load_inspection(db, inspection_id)


@router.put("/inspections/{inspection_id}", response_model=QCInspectionOut)
def update_inspection(
    inspection_id: UUID,
    payload:       QCInspectionUpdate,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("qc", "edit")),
):
    insp = db.query(QCInspection).filter(QCInspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="檢驗記錄不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(insp, field, value)
    db.commit()
    return _load_inspection(db, inspection_id)


@router.delete("/inspections/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inspection(
    inspection_id: UUID,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("qc", "delete")),
):
    insp = db.query(QCInspection).filter(QCInspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="檢驗記錄不存在")
    db.delete(insp)
    db.commit()


# ─── QC 照片 ────────────────────────────────────────────

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/qc")


@router.post("/inspections/{inspection_id}/photos", response_model=QCPhotoOut)
async def upload_photo(
    inspection_id: UUID,
    file:          UploadFile = File(...),
    photo_type:    str = Form("overview"),
    box_no:        Optional[str] = Form(None),
    unit_no:       Optional[str] = Form(None),
    caption:       Optional[str] = Form(None),
    db:            Session = Depends(get_db),
    current_user:  User = Depends(check_permission("qc", "create")),
):
    """上傳 QC 照片"""
    insp = db.query(QCInspection).filter(QCInspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="檢驗記錄不存在")

    # 儲存檔案
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_url = f"/uploads/qc/{filename}"
    photo = QCPhoto(
        inspection_id=inspection_id,
        photo_type=photo_type,
        file_url=file_url,
        box_no=box_no,
        unit_no=unit_no,
        caption=caption,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/inspections/{inspection_id}/photos", response_model=List[QCPhotoOut])
def list_photos(
    inspection_id: UUID,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("qc", "view")),
):
    return db.query(QCPhoto).filter(QCPhoto.inspection_id == inspection_id).order_by(QCPhoto.created_at).all()


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "delete")),
):
    photo = db.query(QCPhoto).filter(QCPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    db.delete(photo)
    db.commit()


# ─── 抽樣規則 ───────────────────────────────────────────

@router.get("/sampling-rules", response_model=List[QCSamplingRuleOut])
def list_sampling_rules(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("qc", "view")),
):
    return db.query(QCSamplingRule).order_by(QCSamplingRule.rule_code).all()


@router.post("/sampling-rules", response_model=QCSamplingRuleOut, status_code=status.HTTP_201_CREATED)
def create_sampling_rule(
    payload: QCSamplingRuleCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("qc", "create")),
):
    rule = QCSamplingRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/sampling-rules/{rule_id}", response_model=QCSamplingRuleOut)
def update_sampling_rule(
    rule_id: UUID,
    payload: QCSamplingRuleUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("qc", "edit")),
):
    rule = db.query(QCSamplingRule).filter(QCSamplingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="抽樣規則不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


# ─── 通路品質標準 ────────────────────────────────────────

@router.get("/channel-standards", response_model=List[ChannelQCStandardOut])
def list_channel_standards(
    channel_type: Optional[str] = Query(None),
    db:           Session = Depends(get_db),
    _:            User = Depends(check_permission("qc", "view")),
):
    q = db.query(ChannelQCStandard)
    if channel_type:
        q = q.filter(ChannelQCStandard.channel_type == channel_type)
    return q.order_by(ChannelQCStandard.standard_code).all()


@router.post("/channel-standards", response_model=ChannelQCStandardOut, status_code=status.HTTP_201_CREATED)
def create_channel_standard(
    payload: ChannelQCStandardCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("qc", "create")),
):
    std = ChannelQCStandard(**payload.model_dump())
    db.add(std)
    db.commit()
    db.refresh(std)
    return std


@router.put("/channel-standards/{standard_id}", response_model=ChannelQCStandardOut)
def update_channel_standard(
    standard_id: UUID,
    payload:     ChannelQCStandardUpdate,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("qc", "edit")),
):
    std = db.query(ChannelQCStandard).filter(ChannelQCStandard.id == standard_id).first()
    if not std:
        raise HTTPException(status_code=404, detail="通路標準不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(std, field, value)
    db.commit()
    db.refresh(std)
    return std


@router.get("/channel-standards/{standard_id}/check-batch/{batch_id}")
def check_batch_against_standard(
    standard_id: UUID,
    batch_id:    UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("qc", "view")),
):
    """檢查批次最新 QC 檢驗結果是否符合通路標準"""
    std = db.query(ChannelQCStandard).filter(ChannelQCStandard.id == standard_id).first()
    if not std:
        raise HTTPException(status_code=404, detail="通路標準不存在")

    latest_insp = (
        db.query(QCInspection)
        .filter(QCInspection.batch_id == batch_id)
        .order_by(QCInspection.inspection_datetime.desc())
        .first()
    )
    if not latest_insp:
        return {"meets_standard": False, "reason": "此批次尚無 QC 檢驗記錄"}

    reqs = std.grade_requirements or {}
    issues = []

    # 檢查最低等級
    grade_order = {"A": 1, "B": 2, "C": 3, "D": 4, "reject": 5}
    min_grade = reqs.get("min_grade")
    if min_grade and latest_insp.overall_grade:
        if grade_order.get(latest_insp.overall_grade, 5) > grade_order.get(min_grade, 5):
            issues.append(f"等級 {latest_insp.overall_grade} 低於要求的 {min_grade}")

    # 檢查最低分數
    min_score = reqs.get("min_score")
    if min_score and latest_insp.overall_score:
        if float(latest_insp.overall_score) < float(min_score):
            issues.append(f"分數 {latest_insp.overall_score} 低於要求的 {min_score}")

    # 檢查最大缺陷率
    max_defect = reqs.get("max_defect_pct")
    if max_defect and latest_insp.defect_summary:
        total_defects = sum(latest_insp.defect_summary.values()) if isinstance(latest_insp.defect_summary, dict) else 0
        total_sampled = latest_insp.sampled_units or 1
        defect_pct = (total_defects / total_sampled) * 100
        if defect_pct > float(max_defect):
            issues.append(f"缺陷率 {defect_pct:.1f}% 超過要求的 {max_defect}%")

    return {
        "meets_standard": len(issues) == 0,
        "inspection_no": latest_insp.inspection_no,
        "overall_grade": latest_insp.overall_grade,
        "overall_score": float(latest_insp.overall_score) if latest_insp.overall_score else None,
        "issues": issues,
    }


# ─── QC 分析 ────────────────────────────────────────────

@router.get("/analytics/trend")
def qc_trend(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("qc", "view")),
):
    """QC 趨勢分析（分數、等級分佈、缺陷頻率）"""
    q = db.query(QCInspection)
    if date_from:
        q = q.filter(QCInspection.inspection_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(QCInspection.inspection_datetime <= datetime.combine(date_to, datetime.max.time()))
    inspections = q.order_by(QCInspection.inspection_datetime).all()

    # 計算趨勢
    avg_score = sum(float(i.overall_score) for i in inspections if i.overall_score) / max(len(inspections), 1)
    grade_counts = {}
    result_counts = {"pass": 0, "fail": 0, "conditional_pass": 0}
    defect_totals = {}

    for insp in inspections:
        if insp.overall_grade:
            grade_counts[insp.overall_grade] = grade_counts.get(insp.overall_grade, 0) + 1
        result_counts[insp.overall_result] = result_counts.get(insp.overall_result, 0) + 1
        if insp.defect_summary and isinstance(insp.defect_summary, dict):
            for defect, count in insp.defect_summary.items():
                defect_totals[defect] = defect_totals.get(defect, 0) + count

    return {
        "total_inspections": len(inspections),
        "avg_score": round(avg_score, 1),
        "grade_distribution": grade_counts,
        "result_distribution": result_counts,
        "defect_frequency": dict(sorted(defect_totals.items(), key=lambda x: -x[1])),
        "pass_rate_pct": round(result_counts["pass"] / max(len(inspections), 1) * 100, 1),
    }


@router.get("/analytics/supplier-quality")
def supplier_quality(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("qc", "view")),
):
    """供應商品質排名（基於批次 QC 結果追溯到供應商）"""
    from models.purchase import PurchaseOrder
    from models.supplier import Supplier

    results = (
        db.query(
            Supplier.id,
            Supplier.name,
            func.count(QCInspection.id).label("inspection_count"),
            func.avg(QCInspection.overall_score).label("avg_score"),
            func.sum(func.cast(QCInspection.overall_result == "pass", Integer)).label("pass_count"),
        )
        .join(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .join(Batch, Batch.purchase_order_id == PurchaseOrder.id)
        .join(QCInspection, QCInspection.batch_id == Batch.id)
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.avg(QCInspection.overall_score).desc().nullslast())
        .all()
    )

    return [
        {
            "supplier_id": str(r.id),
            "supplier_name": r.name,
            "inspection_count": r.inspection_count,
            "avg_score": round(float(r.avg_score), 1) if r.avg_score else None,
            "pass_rate_pct": round(r.pass_count / max(r.inspection_count, 1) * 100, 1),
        }
        for r in results
    ]


@router.get("/analytics/defect-frequency")
def defect_frequency(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("qc", "view")),
):
    """缺陷頻率分析"""
    q = db.query(QCInspection)
    if date_from:
        q = q.filter(QCInspection.inspection_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(QCInspection.inspection_datetime <= datetime.combine(date_to, datetime.max.time()))

    inspections = q.all()
    defect_totals = {}
    for insp in inspections:
        if insp.defect_summary and isinstance(insp.defect_summary, dict):
            for defect, count in insp.defect_summary.items():
                defect_totals[defect] = defect_totals.get(defect, 0) + count

    return {
        "total_inspections": len(inspections),
        "defects": dict(sorted(defect_totals.items(), key=lambda x: -x[1])),
    }


@router.get("/analytics/batch-recommendation/{batch_id}")
def batch_recommendation(
    batch_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "view")),
):
    """基於歷史 QC 數據，為批次提供品質建議"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 取得同供應商的歷史 QC 記錄
    from models.purchase import PurchaseOrder
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == batch.purchase_order_id).first()
    if not po:
        return {"recommendations": [], "historical_avg_score": None}

    historical = (
        db.query(QCInspection)
        .join(Batch, QCInspection.batch_id == Batch.id)
        .join(PurchaseOrder, Batch.purchase_order_id == PurchaseOrder.id)
        .filter(
            PurchaseOrder.supplier_id == po.supplier_id,
            Batch.id != batch_id,
        )
        .order_by(QCInspection.inspection_datetime.desc())
        .limit(10)
        .all()
    )

    recommendations = []
    defect_history = {}
    scores = []

    for insp in historical:
        if insp.overall_score:
            scores.append(float(insp.overall_score))
        if insp.defect_summary and isinstance(insp.defect_summary, dict):
            for defect, count in insp.defect_summary.items():
                defect_history[defect] = defect_history.get(defect, 0) + count
        # 收集上一批的注意事項
        if insp.next_batch_notes:
            recommendations.append(f"[{insp.inspection_no}] {insp.next_batch_notes}")

    # 檢查連續缺陷
    if defect_history:
        top_defect = max(defect_history.items(), key=lambda x: x[1])
        if top_defect[1] >= 3:
            recommendations.insert(0, f"⚠️ 此供應商連續出現「{top_defect[0]}」缺陷（累計 {top_defect[1]} 次），請重點檢查")

    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    return {
        "historical_avg_score": avg_score,
        "historical_inspections": len(historical),
        "top_defects": dict(sorted(defect_history.items(), key=lambda x: -x[1])[:5]),
        "recommendations": recommendations[:5],
    }
