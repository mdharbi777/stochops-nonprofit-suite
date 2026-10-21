"""طلبات الاستفادة (القبول الانتقائي P2).

التقديم عام (مع كابتشا وحدّ معدل) ولا يُنشئ حساب إنتاج ولا يطلب بيانات مستفيدين.
متابعة الطلب بالرقم + رمز المتابعة + البريد الرسمي، وتعرض الحالة فقط دون درجات التقييم الداخلية.
البتّ (مراجعة/تقييم/قرار) من مشغّل المنصّة عبر صلاحيات الخادم (DocType)، ويُختم ويُسجَّل.
"""
import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address

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
    return {"application": app.name, "access_code": app.access_code}


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
