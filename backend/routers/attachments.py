"""
附件管理 API
GET    /attachments            - 查詢附件（依 entity_type + entity_id）
POST   /attachments            - 新增附件記錄
POST   /attachments/upload     - 真實檔案上傳（multipart/form-data）
GET    /attachments/{id}       - 附件詳情
DELETE /attachments/{id}       - 刪除附件
"""
import os
import shutil
from uuid import UUID, uuid4
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from config import settings
from database import get_db
from models.user import User
from models.attachment import Attachment, AttachmentTag
from schemas.attachment import AttachmentCreate, AttachmentOut
from utils.dependencies import check_permission

# 允許的 tag 清單
VALID_TAGS = [
    'receiving_photo', 'qc_photo', 'packing_photo', 'loading_photo',
    'cold_storage_photo', 'temperature_photo', 'shipping_photo', 'document_scan',
]

router = APIRouter(prefix="/attachments", tags=["附件"])


@router.get("", response_model=List[AttachmentOut])
def list_attachments(
    entity_type: str  = Query(...),
    entity_id:   UUID = Query(...),
    limit:       int  = Query(50, le=200),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("attachment", "read")),
):
    """依實體類型與 ID 查詢附件"""
    return (
        db.query(Attachment)
        .options(joinedload(Attachment.tags))
        .filter(Attachment.entity_type == entity_type, Attachment.entity_id == entity_id)
        .order_by(Attachment.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{attachment_id}", response_model=AttachmentOut)
def get_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("attachment", "read")),
):
    att = (
        db.query(Attachment)
        .options(joinedload(Attachment.tags))
        .filter(Attachment.id == attachment_id)
        .first()
    )
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    return att


@router.post("/upload", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file:        UploadFile = File(...),
    entity_type: str        = Form(...),
    entity_id:   str        = Form(...),
    tags:        str        = Form(""),
    db:          Session    = Depends(get_db),
    current_user: User      = Depends(check_permission("attachment", "create")),
):
    """
    真實檔案上傳端點
    - 接收 multipart/form-data 格式的檔案
    - 儲存到 {UPLOAD_DIR}/{entity_type}/{entity_id}/{uuid}.{ext}
    - 在資料庫建立 Attachment 記錄並回傳
    """
    # ── 驗證 entity_id 為合法 UUID ──
    try:
        entity_uuid = UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="entity_id 必須是有效的 UUID")

    # ── 計算儲存路徑 ──
    # 保留原始副檔名，用 uuid4 生成新檔名避免衝突
    original_filename = file.filename or "upload"
    ext = Path(original_filename).suffix.lower()  # 例如 ".jpg"
    new_filename = f"{uuid4()}{ext}"

    # 相對路徑（儲存到資料庫）
    relative_path = f"{entity_type}/{entity_id}/{new_filename}"
    # 絕對路徑（實際寫入磁碟）
    abs_dir = Path(settings.UPLOAD_DIR) / entity_type / entity_id
    abs_dir.mkdir(parents=True, exist_ok=True)
    abs_path = abs_dir / new_filename

    # ── 寫入檔案 ──
    try:
        with open(abs_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案寫入失敗：{e}")
    finally:
        await file.close()

    # ── 解析 tags（逗號分隔，只保留白名單內的值）──
    raw_tags = [t.strip() for t in tags.split(",") if t.strip()]
    valid_tag_list = [t for t in raw_tags if t in VALID_TAGS]

    # ── 建立資料庫記錄 ──
    att = Attachment(
        entity_type=entity_type,
        entity_id=entity_uuid,
        file_name=original_filename,
        storage_path=relative_path,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=current_user.id,
    )
    db.add(att)
    db.flush()

    # 新增標籤
    for tag in valid_tag_list:
        db.add(AttachmentTag(attachment_id=att.id, tag=tag))

    db.commit()

    return (
        db.query(Attachment)
        .options(joinedload(Attachment.tags))
        .filter(Attachment.id == att.id)
        .first()
    )


@router.post("", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
def create_attachment(
    payload:      AttachmentCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("attachment", "create")),
):
    """新增附件記錄（檔案上傳由前端或其他服務處理，此處僅記錄 metadata）"""
    data = payload.model_dump(exclude={"tags"})
    att = Attachment(**data, uploaded_by=current_user.id)
    db.add(att)
    db.flush()

    # 新增標籤
    for tag in payload.tags:
        db.add(AttachmentTag(attachment_id=att.id, tag=tag))

    db.commit()
    return (
        db.query(Attachment)
        .options(joinedload(Attachment.tags))
        .filter(Attachment.id == att.id)
        .first()
    )


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("attachment", "read")),
):
    """安全下載附件（需登入）。取代原本的公開 /uploads 靜態路由。"""
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    file_path = Path(settings.UPLOAD_DIR) / att.storage_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="檔案不存在於伺服器")

    return FileResponse(
        path=str(file_path),
        media_type=att.mime_type or "application/octet-stream",
        filename=att.file_name,
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("attachment", "delete")),
):
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    db.delete(att)
    db.commit()
