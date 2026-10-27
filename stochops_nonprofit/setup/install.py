"""خطوات ما بعد التثبيت — تُستدعى من hooks.after_install (idempotent)."""
import frappe

from stochops_nonprofit.multitenancy import ensure_charity_company_field, ensure_user_charity_field
from stochops_nonprofit.setup.localization import ensure_arabic
from stochops_nonprofit.setup.notifications import ensure_notifications
from stochops_nonprofit.setup.roles import ensure_roles


def after_install():
    ensure_roles()
    ensure_user_charity_field()
    ensure_notifications()
    ensure_arabic()
    _ensure_privacy_core()
    _ensure_erpnext_integration()
    _ensure_branding()


BRAND_LOGO = "/assets/stochops_nonprofit/nos/brand-logo.svg"
BRAND_NAME = "منصة الفاضل"


def _ensure_branding():
    """يفرض هوية «منصة الفاضل» على صفحة الدخول وإعدادات الموقع (idempotent).

    يُعاد تطبيقه في كل ترحيل (after_migrate) فلا تُفقد الهوية عند أي تثبيت يعيد
    الافتراضي (مثل install-app erpnext الذي يُرجِع شعار Frappe). يُعيّن فقط الحقول
    الموجودة فعلاً في Website Settings / Navbar Settings (توافق بين الإصدارات).
    """
    try:
        desired = {
            "app_name": BRAND_NAME,       # نص «تسجيل الدخول إلى منصة الفاضل»
            "app_logo": BRAND_LOGO,       # شعار صفحة الدخول
            "banner_image": BRAND_LOGO,   # شعار شريط الموقع
            "splash_image": BRAND_LOGO,   # شاشة التحميل
            "disable_signup": 1,          # لا تسجيل عام عبر Frappe
        }
        meta_fields = {f.fieldname for f in frappe.get_meta("Website Settings").fields}
        ws = frappe.get_doc("Website Settings")
        changed = False
        for key, val in desired.items():
            if key in meta_fields and ws.get(key) != val:
                ws.set(key, val)
                changed = True
        if changed:
            ws.flags.ignore_permissions = True
            ws.save(ignore_permissions=True)
        # شعار لوحة التحكم (الديسك)
        if frappe.db.exists("DocType", "Navbar Settings"):
            nb_fields = {f.fieldname for f in frappe.get_meta("Navbar Settings").fields}
            if "app_logo" in nb_fields and frappe.db.get_value("Navbar Settings", "Navbar Settings", "app_logo") != BRAND_LOGO:
                frappe.db.set_value("Navbar Settings", "Navbar Settings", "app_logo", BRAND_LOGO)
        frappe.db.commit()
    except Exception:
        frappe.log_error("ensure_branding failed", "stochops_nonprofit.setup")


def _ensure_erpnext_integration():
    """حقول تكامل ERPNext (المرحلة 2.1) — تُنشَأ فقط عند وجود erpnext؛ تُتخطّى بأمان."""
    try:
        ensure_charity_company_field()
        from stochops_nonprofit.erpnext_bridge import ensure_assistance_journal_field

        ensure_assistance_journal_field()
    except Exception:
        frappe.log_error("ensure_erpnext_integration failed", "stochops_nonprofit.setup")


def _ensure_privacy_core():
    # يُستدعى بعد مزامنة الـDocTypes؛ يتجاهل بأمان قبل توفّرها (أول تثبيت/ترحيل).
    try:
        from stochops_nonprofit.privacy_core import ensure_privacy_core

        if frappe.db.exists("DocType", "Regulatory Rule"):
            ensure_privacy_core()
    except Exception:
        frappe.log_error("ensure_privacy_core failed", "stochops_nonprofit.setup")
