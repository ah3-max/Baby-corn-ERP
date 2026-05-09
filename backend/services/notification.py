"""
多通路通知服務

支援三種通知管道：
1. In-app：寫入 Notification 資料表（即時顯示於前端）
2. LINE Notify：透過 LINE Notify API 發送（需 LINE_NOTIFY_TOKEN 環境變數）
3. Email SMTP：透過 SMTP 發送 HTML 郵件

使用方式：
    from services.notification import notify, notify_managers, notify_by_role

    # 通知單一使用者
    notify(db, [user_id], title="新訂單", message={"order_no": "SO-xxx"}, category="sales")

    # 通知所有管理員
    notify_managers(db, title="庫存警告", message={"batch": "BT-xxx", "days": 3})

    # 通知指定角色
    notify_by_role(db, roles=["finance", "gm"], title="逾期帳款", message={...})
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def notify(
    db: Session,
    user_ids: list[UUID],
    title: str,
    message: Optional[Any] = None,
    *,
    link_url: Optional[str] = None,
    category: str = "system",       # system/sales/finance/logistics/quality/hr
    priority: str = "normal",       # low/normal/high/urgent
    notification_type: str = "system_alert",
    send_line: bool = False,
    send_email: bool = False,
    email_body_html: Optional[str] = None,
) -> None:
    """
    發送通知給指定使用者清單。

    Args:
        db:                 SQLAlchemy Session
        user_ids:           接收通知的 user_id 清單
        title:              通知標題
        message:            結構化內容 dict 或字串
        link_url:           點擊跳轉連結
        category:           通知分類
        priority:           優先級
        notification_type:  通知類型（符合 Notification.notification_type CheckConstraint）
        send_line:          是否同時發送 LINE Notify
        send_email:         是否同時發送 Email
        email_body_html:    Email HTML 內容（None 時使用 title 作為純文字）
    """
    from models.notification import Notification

    # 訊息標準化
    if isinstance(message, str):
        msg_dict = {"text": message, "category": category, "priority": priority}
    elif isinstance(message, dict):
        msg_dict = {**message, "category": category, "priority": priority}
        if link_url:
            msg_dict["link_url"] = link_url
    else:
        msg_dict = {"category": category, "priority": priority}

    # in-app 通知
    for uid in user_ids:
        try:
            notif = Notification(
                recipient_user_id=uid,
                notification_type=notification_type,
                title=title,
                message=msg_dict,
            )
            db.add(notif)
        except Exception as exc:
            logger.warning("in-app 通知寫入失敗 user_id=%s: %s", uid, exc)

    # LINE Notify
    if send_line:
        _send_line_notify(title=title, message=str(message or ""))

    # Email
    if send_email:
        _send_email_to_users(db, user_ids, title, email_body_html or title)


def notify_managers(
    db: Session,
    title: str,
    message: Optional[Any] = None,
    **kwargs,
) -> None:
    """通知所有管理員角色（gm, admin, sales_manager, th_manager）"""
    from models.user import User, Role

    manager_roles = {"gm", "admin", "sales_manager", "th_manager", "tw_manager"}
    users = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.code.in_(manager_roles), User.is_active == True)
        .all()
    )
    user_ids = [u.id for u in users]
    if user_ids:
        notify(db, user_ids, title, message, **kwargs)


def notify_by_role(
    db: Session,
    roles: list[str],
    title: str,
    message: Optional[Any] = None,
    **kwargs,
) -> None:
    """通知指定角色代碼清單的所有使用者"""
    from models.user import User, Role

    users = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.code.in_(roles), User.is_active == True)
        .all()
    )
    user_ids = [u.id for u in users]
    if user_ids:
        notify(db, user_ids, title, message, **kwargs)


# ─── LINE Notify ──────────────────────────────────────────

def _send_line_notify(title: str, message: str) -> None:
    """透過 LINE Notify API 發送訊息（最多 1000 字）"""
    try:
        import os
        import urllib.request
        import urllib.parse

        token = os.getenv("LINE_NOTIFY_TOKEN", "")
        if not token:
            return

        text = f"【玉米筍ERP】{title}\n{message}"[:1000]
        data = urllib.parse.urlencode({"message": text}).encode("utf-8")
        req = urllib.request.Request(
            "https://notify-api.line.me/api/notify",
            data=data,
            headers={"Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                logger.warning("LINE Notify 發送失敗 status=%d", resp.status)
    except Exception as exc:
        logger.warning("LINE Notify 例外：%s", exc)


# ─── Email SMTP ───────────────────────────────────────────

def _send_email_to_users(
    db: Session,
    user_ids: list[UUID],
    subject: str,
    html_body: str,
) -> None:
    """取得使用者 email 並發送 HTML 郵件"""
    try:
        import os
        from models.user import User

        smtp_host = os.getenv("SMTP_HOST", "")
        if not smtp_host:
            return

        users = db.query(User).filter(User.id.in_(user_ids), User.is_active == True).all()
        recipients = [u.email for u in users if u.email]
        if not recipients:
            return

        _send_smtp_email(recipients, subject, html_body)
    except Exception as exc:
        logger.warning("Email 發送準備失敗：%s", exc)


def _send_smtp_email(
    to_emails: list[str],
    subject: str,
    html_body: str,
) -> None:
    """透過 SMTP 發送 HTML 郵件"""
    try:
        import os

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        smtp_from_name = os.getenv("SMTP_FROM_NAME", "玉米筍ERP系統")

        if not smtp_host or not smtp_user:
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{smtp_from_name} <{smtp_from}>"
        msg["To"]      = ", ".join(to_emails)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, to_emails, msg.as_string())
    except Exception as exc:
        logger.warning("SMTP 發送失敗：%s", exc)
