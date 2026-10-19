"""واجهة برمجية صغيرة للمستفيدين — كشف رقم الهوية المشفّر بصلاحية إدارية فقط.

العمليات العامة (إنشاء/قائمة/تعديل) تمرّ عبر frappe.client فتُطبَّق خطّافات العزل
تلقائياً. رقم الهوية حقل Password لا يُجلب في القوائم؛ كشفه هنا مقيّد بمدير الجمعية
وعلى مستفيدي جمعيته فقط (PDPL: أدنى وصول).
"""
import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password

from stochops_nonprofit.multitenancy import get_user_charity

ADMIN_ROLES = {"Nonprofit Admin", "System Manager"}


@frappe.whitelist()
def reveal_national_id(beneficiary):
    user = frappe.session.user
    if not (ADMIN_ROLES & set(frappe.get_roles(user))):
        frappe.throw(_("كشف رقم الهوية يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
    charity = frappe.db.get_value("Beneficiary", beneficiary, "charity")
    if not charity:
        frappe.throw(_("المستفيد غير موجود."))
    if "System Manager" not in frappe.get_roles(user) and charity != get_user_charity(user):
        frappe.throw(_("لا تملك صلاحية على هذا المستفيد."), frappe.PermissionError)
    nid = get_decrypted_password("Beneficiary", beneficiary, "national_id", raise_exception=False)
    # سجل الاطّلاع الحسّاس (وثيقة PDPL §7-8) — بلا تخزين القيمة
    from stochops_nonprofit.privacy_core import log_sensitive_access

    log_sensitive_access("reveal", "Beneficiary", beneficiary, field="national_id", charity=charity)
    return {"beneficiary": beneficiary, "national_id": nid or ""}
