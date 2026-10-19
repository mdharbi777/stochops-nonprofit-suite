"""كشف رقم هوية الموظف/المتطوّع المشفّر — بصلاحية إدارية فقط وعلى منسوبي الجمعية.

العمليات العامة تمرّ عبر frappe.client (عزل تلقائي). رقم الهوية حقل Password لا يُجلب
في القوائم؛ كشفه مقيّد بمدير الجمعية (PDPL: أدنى وصول).
"""
import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password

from stochops_nonprofit.multitenancy import get_user_charity

ADMIN_ROLES = {"Nonprofit Admin", "System Manager"}


@frappe.whitelist()
def reveal_national_id(personnel):
    user = frappe.session.user
    if not (ADMIN_ROLES & set(frappe.get_roles(user))):
        frappe.throw(_("كشف رقم الهوية يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
    charity = frappe.db.get_value("Personnel", personnel, "charity")
    if not charity:
        frappe.throw(_("السجل غير موجود."))
    if "System Manager" not in frappe.get_roles(user) and charity != get_user_charity(user):
        frappe.throw(_("لا تملك صلاحية على هذا السجل."), frappe.PermissionError)
    nid = get_decrypted_password("Personnel", personnel, "national_id", raise_exception=False)
    return {"personnel": personnel, "national_id": nid or ""}
