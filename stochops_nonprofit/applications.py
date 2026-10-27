"""طلبات الاستفادة (القبول الانتقائي P2).

التقديم عام (مع كابتشا وحدّ معدل) ولا يُنشئ حساب إنتاج ولا يطلب بيانات مستفيدين.
متابعة الطلب بالرقم + رمز المتابعة + البريد الرسمي، وتعرض الحالة فقط دون درجات التقييم الداخلية.
البتّ (مراجعة/تقييم/قرار) من مشغّل المنصّة عبر صلاحيات الخادم (DocType)، ويُختم ويُسجَّل.
"""
import json
import time

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_url, now_datetime, validate_email_address

APP_VERIFY_TTL = 3 * 24 * 3600  # 3 أيام

# الحقول المسموح استقبالها من النموذج العام فقط (لا بيانات مستفيدين ولا حقول داخلية)
PUBLIC_FIELDS = [
    "association_name", "license_number", "supervisory_authority", "region", "city",
    "official_email", "phone", "website", "applicant_name", "applicant_title",
    "proposed_admin_name", "proposed_admin_email", "work_size", "current_systems",
    "challenges", "needs",
]
REQUIRED = ("association_name", "license_number", "official_email", "applicant_name")

STATUS_AR = {
    "Submitted": "تم استلام الطلب",
    "Under Review": "قيد المراجعة",
    "Information Required": "يتطلّب استكمال معلومات",
    "Waitlisted": "في قائمة الانتظار",
    "Approved": "مقبول",
    "Rejected": "غير مقبول",
}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=3600)
def submit_application(data, captcha_token, captcha_answer):
    """يستقبل طلب استفادة عام. لا يُنشئ حساباً؛ يعيد رقم الطلب ورمز المتابعة."""
    from stochops_nonprofit.signup import _check_captcha

    _check_captcha(captcha_token, captcha_answer)
    payload = json.loads(data) if isinstance(data, str) else (data or {})
    doc = {"doctype": "Association Application"}
    for f in PUBLIC_FIELDS:
        v = payload.get(f)
        if v is not None:
            doc[f] = str(v).strip()
    for f in ("official_email", "proposed_admin_email"):
        if doc.get(f):
            doc[f] = doc[f].lower()
    for req in REQUIRED:
        if not doc.get(req):
            frappe.throw(_("الحقول الأساسية (اسم الجمعية، الترخيص، البريد الرسمي، اسم مقدّم الطلب) مطلوبة."))
    validate_email_address(doc["official_email"], throw=True)
    app = frappe.get_doc(doc).insert(ignore_permissions=True)
    frappe.db.commit()
    # تحقّق بريد آلي: يُرسَل رابط للبريد الرسمي ليؤكّد المتقدّم ملكيته (لا يحجب التقديم).
    link = _send_app_verification(app.name, doc["official_email"], doc.get("association_name") or "")
    out = {"application": app.name, "access_code": app.access_code, "verification_sent": True}
    if frappe.conf.get("developer_mode"):
        out["verify_url"] = link
    return out


def _app_verify_token(application, email):
    from stochops_nonprofit.signup import _sign

    return _sign({"k": "app_verify", "app": application, "email": email,
                  "exp": int(time.time()) + APP_VERIFY_TTL})


def _send_app_verification(application, email, association_name):
    from stochops_nonprofit.signup import SENDER_EMAIL

    link = get_url("/nos/verify-application?token=" + _app_verify_token(application, email))
    try:
        frappe.sendmail(
            recipients=[email],
            sender=SENDER_EMAIL,
            subject=_("تأكيد البريد الرسمي لطلب الاستفادة — منصة الفاضل"),
            message=_(
                "مرحباً،<br><br>تلقّينا طلب استفادة باسم «{0}» (المرجع {1}).<br>"
                "لتأكيد ملكية هذا البريد الرسمي للجمعية — وهو شرط مستقلّ ضمن مراجعة الطلب — اضغط الرابط التالي:<br>"
                "<a href='{2}'>{2}</a><br><br>الرابط صالح لمدة 3 أيام. إن لم تتقدّم بهذا الطلب فتجاهل هذه الرسالة."
            ).format(association_name or "—", application, link),
            now=False,
        )
    except Exception:
        frappe.log_error("فشل إرسال بريد تأكيد الطلب")  # يحتاج SMTP مُعدّاً لـ ops@stochops.com
    return link


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=3600)
def verify_application_email(token):
    """يؤكّد المتقدّم ملكية البريد الرسمي عبر الرابط الموقّع — يضبط email_verified تلقائياً.

    لا يكشف وجود الطلب لرابط غير صالح، وعملية إعادة التأكيد غير ضارّة (idempotent).
    """
    from stochops_nonprofit.signup import _unsign

    p = _unsign(token)
    if not p or p.get("k") != "app_verify":
        frappe.throw(_("رابط التأكيد غير صالح."))
    if int(time.time()) > p.get("exp", 0):
        frappe.throw(_("انتهت صلاحية رابط التأكيد — تواصل مع المنصّة."))
    row = frappe.db.get_value(
        "Association Application",
        {"name": p.get("app"), "official_email": (p.get("email") or "").lower()},
        ["name", "association_name", "email_verified"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("رابط التأكيد غير صالح."))
    if not row.email_verified:
        frappe.db.set_value("Association Application", row.name,
                            {"email_verified": 1, "email_verified_on": now_datetime()},
                            update_modified=False)
        frappe.db.commit()
    return {"verified": True, "association_name": row.association_name}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=3600)
def get_application_status(application, access_code, email):
    """متابعة حالة الطلب بالرقم + رمز المتابعة + البريد الرسمي. لا تُفشى الدرجات الداخلية."""
    row = frappe.db.get_value(
        "Association Application",
        {
            "name": (application or "").strip(),
            "access_code": (access_code or "").strip().upper(),
            "official_email": (email or "").strip().lower(),
        },
        ["name", "association_name", "status", "submitted_on", "decision_reason"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("لا يوجد طلب مطابق — تحقّق من رقم الطلب ورمز المتابعة والبريد."))
    out = {
        "application": row.name,
        "association_name": row.association_name,
        "status": row.status,
        "status_label": STATUS_AR.get(row.status, row.status),
        "submitted_on": str(row.submitted_on) if row.submitted_on else None,
    }
    # تُعرض الملاحظة فقط عند الحاجة لاستكمال معلومات أو عند الرفض (شفافية للمتقدّم)
    if row.status in ("Information Required", "Rejected"):
        out["note"] = row.decision_reason or ""
    return out
