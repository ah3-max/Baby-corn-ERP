"""
WP2-4：QC 自動化推播邏輯

在 QC 檢驗完成時，自動發送通知給相關人員：
- QC 通過 → 通知老闆、業務經理
- QC 失敗 → 通知老闆、QC 主管
- 有條件通過 → 通知業務經理（建議降級銷售）
- 連續缺陷 → 通知 QC 主管、工廠
- 溫度異常 → 通知 QC 主管
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.notification import Notification
from models.user import User, Role
from models.batch import Batch
from models.qc_enhanced import QCInspection


def _get_admin_user_ids(db: Session) -> list:
    """取得所有系統管理員的 user_id"""
    admins = (
        db.query(User.id)
        .join(Role, User.role_id == Role.id)
        .filter(User.is_active == True, Role.is_system == True)
        .all()
    )
    return [a.id for a in admins]


def notify_qc_result(
    db: Session,
    inspection: QCInspection,
    batch: Batch,
    current_user: User,
):
    """QC 檢驗完成後自動推播通知"""
    admin_ids = _get_admin_user_ids(db)
    if not admin_ids:
        return

    batch_no = batch.batch_no
    result = inspection.overall_result
    grade = inspection.overall_grade or "N/A"
    score = float(inspection.overall_score) if inspection.overall_score else None
    score_str = f"{score}/100" if score else "未評分"

    # 1. 基本 QC 結果通知
    if result == "pass":
        title = f"✅ 批次 {batch_no} QC 通過（{grade} 級，{score_str}）"
        ntype = "qc_required"
    elif result == "fail":
        title = f"❌ 批次 {batch_no} QC 不通過"
        ntype = "qc_required"
    else:  # conditional_pass
        title = f"⚠️ 批次 {batch_no} QC 有條件通過（{grade} 級）"
        ntype = "qc_required"

    message_data = {
        "entity_type": "qc_inspection",
        "entity_id": str(inspection.id),
        "batch_id": str(batch.id),
        "batch_no": batch_no,
        "result": result,
        "grade": grade,
        "score": score,
        "defect_summary": inspection.defect_summary,
        "recommendation": inspection.recommendation,
    }

    for uid in admin_ids:
        db.add(Notification(
            recipient_user_id=uid,
            notification_type=ntype,
            title=title,
            message=message_data,
        ))

    # 2. 檢查連續缺陷（同供應商最近 3 批是否有相同缺陷）
    if inspection.defect_summary and isinstance(inspection.defect_summary, dict):
        _check_recurring_defects(db, inspection, batch, admin_ids)

    # 3. 溫度異常檢查
    if inspection.environment_temp_c:
        temp = float(inspection.environment_temp_c)
        # 玉米筍冷藏標準 2-8°C
        if temp > 8 or temp < 0:
            for uid in admin_ids:
                db.add(Notification(
                    recipient_user_id=uid,
                    notification_type="qc_required",
                    title=f"🌡️ 批次 {batch_no} 環境溫度異常：{temp}°C（規範 2-8°C）",
                    message={
                        "entity_type": "temperature_alert",
                        "batch_id": str(batch.id),
                        "batch_no": batch_no,
                        "temperature_c": temp,
                        "stage": inspection.inspection_stage,
                    },
                ))


def _check_recurring_defects(
    db: Session,
    current_inspection: QCInspection,
    batch: Batch,
    admin_ids: list,
):
    """檢查同供應商是否有連續出現的缺陷"""
    from models.purchase import PurchaseOrder

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == batch.purchase_order_id).first()
    if not po:
        return

    # 取得同供應商最近 5 筆檢驗
    recent = (
        db.query(QCInspection)
        .join(Batch, QCInspection.batch_id == Batch.id)
        .join(PurchaseOrder, Batch.purchase_order_id == PurchaseOrder.id)
        .filter(
            PurchaseOrder.supplier_id == po.supplier_id,
            QCInspection.id != current_inspection.id,
        )
        .order_by(QCInspection.inspection_datetime.desc())
        .limit(5)
        .all()
    )

    if not recent:
        return

    # 統計缺陷
    current_defects = set(current_inspection.defect_summary.keys()) if current_inspection.defect_summary else set()
    for insp in recent[:2]:  # 只看最近 2 筆
        if insp.defect_summary and isinstance(insp.defect_summary, dict):
            recurring = current_defects & set(insp.defect_summary.keys())
            if recurring:
                defect_list = "、".join(recurring)
                for uid in admin_ids:
                    db.add(Notification(
                        recipient_user_id=uid,
                        notification_type="qc_required",
                        title=f"🔄 供應商連續缺陷警告：「{defect_list}」已連續出現",
                        message={
                            "entity_type": "recurring_defect",
                            "batch_no": batch.batch_no,
                            "supplier_id": str(po.supplier_id),
                            "recurring_defects": list(recurring),
                            "suggestion": "建議加強該供應商的品質要求或增加抽樣比例",
                        },
                    ))
                break  # 只發一次
