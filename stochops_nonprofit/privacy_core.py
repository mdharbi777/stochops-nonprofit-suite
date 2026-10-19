"""طبقة الخصوصية المشتركة (privacy_core) — وثيقة PDPL التنفيذية §0/§13.

توفّر: حالة بوابة الإنتاج، تسجيل الاطّلاع الحسّاس، وتهيئة سجلّات المرجعية والكتالوج
(idempotent). تُستدعى من كل وحدة دون تكرار المنطق. لا تُخزَّن محتويات حسّاسة في السجل.
"""
import frappe
from frappe import _
from frappe.utils import now_datetime

from stochops_nonprofit.multitenancy import get_user_charity

# --- المرجعية التنظيمية (تُزرع بحالة LEGAL_REVIEW_REQUIRED؛ لا تتحوّل تلقائياً) ---
REGULATORY_SEED = [
    {"rule_title": "نظام حماية البيانات الشخصية PDPL (م/19 وتعديلاته م/148)",
     "source_url": "https://dgp.sdaia.gov.sa/wps/portal/pdp/knowledgecenter/details/PDPL"},
    {"rule_title": "اللائحة التنفيذية لنظام حماية البيانات الشخصية",
     "source_url": "https://dgp.sdaia.gov.sa/wps/portal/pdp/knowledgecenter/details/PDPL2"},
    {"rule_title": "لائحة نقل البيانات الشخصية إلى خارج المملكة",
     "source_url": "https://dgp.sdaia.gov.sa/wps/portal/pdp/knowledgecenter/details/RegulationonPersonalDataTransferOutsidetheKingdom"},
    {"rule_title": "قواعد السجل الوطني وتعيين مسؤول حماية البيانات",
     "source_url": "https://dgp.sdaia.gov.sa/wps/portal/pdp/knowledgecenter"},
    {"rule_title": "أنظمة ولوائح حوكمة الجمعيات — المركز الوطني للقطاع غير الربحي",
     "source_url": "https://ncnp.gov.sa/ar/regulations"},
    {"rule_title": "نظام جمع التبرعات واللوائح ذات الصلة",
     "source_url": "https://ncnp.gov.sa/ar/regulations"},
]

# --- كتالوج الحقول الشخصية/الحسّاسة (تصنيف مبدئي؛ يراجعه المختص) ---
FIELD_CATALOG_SEED = [
    ("Beneficiary", "beneficiary_name", "شخصي"),
    ("Beneficiary", "national_id", "حساس جداً"),
    ("Beneficiary", "phone", "شخصي"),
    ("Beneficiary", "social_category", "حساس"),
    ("Beneficiary", "family_members_count", "شخصي"),
    ("Assistance Request", "description", "حساس"),
    ("Assistance Request", "amount", "حساس"),
    ("Donor", "donor_name", "شخصي"),
    ("Donor", "email", "شخصي"),
    ("Donor", "phone", "شخصي"),
    ("Donation", "amount", "شخصي"),
    ("Personnel", "full_name", "شخصي"),
    ("Personnel", "national_id", "حساس جداً"),
    ("Personnel", "phone", "شخصي"),
    ("Contract", "value", "تشغيلي"),
    ("Expense Request", "amount", "تشغيلي"),
    ("Procurement Request", "amount", "تشغيلي"),
]


def get_config():
    return frappe.get_cached_doc("Privacy Configuration")


def is_gate_open():
    return bool(frappe.db.get_single_value("Privacy Configuration", "production_privacy_gate"))


def assert_gate_open():
    """تُستدعى قبل أي عملية ببيانات حقيقية/إنتاجية. تمنع ما لم تُفتح البوابة."""
    if not is_gate_open():
        frappe.throw(_("بوابة إنتاج البيانات الحقيقية مغلقة — تتطلّب اعتماد DPA وإشعار الخصوصية وDPIA."))


def log_sensitive_access(event_type, reference_doctype=None, reference_name=None, field=None, note=None, charity=None):
    """يسجّل حدث اطّلاع/كشف/تصدير على بيانات حسّاسة. بيانات وصفية فقط، بلا محتوى."""
    try:
        charity = charity or get_user_charity()
        if not charity and reference_doctype and reference_name:
            charity = frappe.db.get_value(reference_doctype, reference_name, "charity")
        frappe.get_doc(
            {
                "doctype": "Sensitive Access Log",
                "event_type": event_type,
                "accessed_by": frappe.session.user,
                "accessed_on": now_datetime(),
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "accessed_field": field,
                "note": (note or "")[:140],
                "charity": charity,
            }
        ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error("sensitive access log failed", "stochops_nonprofit.privacy_core")


def ensure_privacy_core():
    """تهيئة idempotent: إعدادات الخصوصية + المرجعية + كتالوج الحقول. تُستدعى بعد التثبيت/الترحيل."""
    # الإعدادات المفردة (البوابة مغلقة افتراضياً عبر default الحقل)
    if frappe.db.exists("DocType", "Privacy Configuration"):
        frappe.get_single("Privacy Configuration")  # يضمن وجود السجل المفرد

    created = {"rules": 0, "catalog": 0}
    for r in REGULATORY_SEED:
        if not frappe.db.exists("Regulatory Rule", r["rule_title"]):
            frappe.get_doc(
                {"doctype": "Regulatory Rule", "rule_title": r["rule_title"],
                 "source_url": r["source_url"], "status": "LEGAL_REVIEW_REQUIRED"}
            ).insert(ignore_permissions=True)
            created["rules"] += 1

    for dt, fn, cls in FIELD_CATALOG_SEED:
        key = f"{dt}.{fn}"
        if not frappe.db.exists("Data Field Catalog", key):
            frappe.get_doc(
                {"doctype": "Data Field Catalog", "entry_key": key, "doctype_name": dt,
                 "fieldname": fn, "classification": cls}
            ).insert(ignore_permissions=True)
            created["catalog"] += 1

    frappe.db.commit()
    return created


@frappe.whitelist()
def get_privacy_status():
    """حالة الخصوصية للوحة المبرندة (للمدير)."""
    return {
        "gate_open": is_gate_open(),
        "ai_external_enabled": bool(frappe.db.get_single_value("Privacy Configuration", "ai_external_enabled")),
        "privacy_officer": frappe.db.get_single_value("Privacy Configuration", "default_privacy_officer") or "",
        "policy_version": frappe.db.get_single_value("Privacy Configuration", "platform_privacy_policy_version") or "",
    }
