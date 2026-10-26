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
