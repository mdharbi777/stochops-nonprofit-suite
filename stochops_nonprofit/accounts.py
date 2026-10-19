"""إدارة حسابات الجمعية — مدير الجمعية ينشئ/يدير حتى `max_accounts` (5) حسابات.

كل العمليات مقيّدة بجمعية المستخدم، وبأدوار مسموحة فقط (لا Stochops Admin).
"""
import frappe
from frappe import _
from frappe.utils import validate_email_address

from stochops_nonprofit.multitenancy import get_user_charity

ALLOWED_ROLES = [
    "Nonprofit Admin",
    "Executive Viewer",
    "Committee Coordinator",
    "Program Coordinator",
]
MIN_PASSWORD = 8


def _require_charity_admin():
    user = frappe.session.user
    if "Nonprofit Admin" not in frappe.get_roles(user):
        frappe.throw(_("هذه العملية تتطلب صلاحية مدير الجمعية."), frappe.PermissionError)
    charity = get_user_charity(user)
    if not charity:
        frappe.throw(_("حسابك غير مرتبط بجمعية."), frappe.PermissionError)
    return charity


def _charity_roles(email):
    roles = set(frappe.get_roles(email))
    return [r for r in ALLOWED_ROLES if r in roles]


@frappe.whitelist()
def list_accounts():
    charity = _require_charity_admin()
    max_accounts = frappe.db.get_value("Charity", charity, "max_accounts") or 5
    users = frappe.get_all(
        "User", filters={"charity": charity}, fields=["name", "full_name", "enabled"], order_by="creation asc"
    )
    for u in users:
        u["roles"] = _charity_roles(u["name"])
    return {
        "charity": charity,
        "max_accounts": max_accounts,
        "used": len(users),
        "remaining": max(0, max_accounts - len(users)),
        "accounts": users,
    }


@frappe.whitelist()
def create_account(full_name, email, role, password, mobile=None):
    charity = _require_charity_admin()
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()

    if role not in ALLOWED_ROLES:
        frappe.throw(_("الدور غير مسموح."))
    if not (full_name and email and password):
        frappe.throw(_("الاسم والبريد وكلمة المرور مطلوبة."))
    validate_email_address(email, throw=True)
    if len(password) < MIN_PASSWORD:
        frappe.throw(_("كلمة المرور يجب ألا تقل عن {0} أحرف.").format(MIN_PASSWORD))
    if frappe.db.exists("User", email):
        frappe.throw(_("هذا البريد مُستخدم مسبقاً."))

    max_accounts = frappe.db.get_value("Charity", charity, "max_accounts") or 5
    current = frappe.db.count("User", {"charity": charity})
    if current >= max_accounts:
        frappe.throw(_("بلغت الحد الأقصى لحسابات الجمعية ({0}).").format(max_accounts))

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "mobile_no": mobile,
            "language": "ar",
            "time_zone": "Asia/Riyadh",
            "send_welcome_email": 0,
            "new_password": password,
        }
    ).insert(ignore_permissions=True)
    user.add_roles(role)
    frappe.db.set_value("User", user.name, "charity", charity)
    frappe.db.commit()

    return {"account": user.name, "role": role, "remaining": max(0, max_accounts - (current + 1))}


@frappe.whitelist()
def get_charity_settings():
    """هوية الجمعية وإعداداتها (للعرض في صفحة الإعدادات). مدير الجمعية فقط."""
    charity = _require_charity_admin()
    data = frappe.db.get_value(
        "Charity",
        charity,
        ["charity_name", "registration_number", "status", "contact_email", "contact_mobile",
         "max_accounts", "expense_approval_limit"],
        as_dict=True,
    )
    data["used"] = frappe.db.count("User", {"charity": charity})
    return data


@frappe.whitelist()
def update_charity_settings(registration_number=None, contact_email=None, contact_mobile=None,
                            expense_approval_limit=None):
    """تحديث الحقول القابلة للتغيير في هوية الجمعية. مدير الجمعية فقط، على جمعيته فقط.
    الاسم/الحالة/حد الحسابات تُدار من منصّة STOCHOPS (غير قابلة للتعديل هنا)."""
    charity = _require_charity_admin()
    updates = {}
    if registration_number is not None:
        updates["registration_number"] = (registration_number or "").strip()
    if contact_email is not None:
        email = (contact_email or "").strip().lower()
        if email:
            validate_email_address(email, throw=True)
        updates["contact_email"] = email
    if contact_mobile is not None:
        updates["contact_mobile"] = (contact_mobile or "").strip()
    if expense_approval_limit is not None:
        limit = float(expense_approval_limit or 0)
        if limit < 0:
            frappe.throw(_("حدّ الاعتماد لا يكون سالباً."))
        updates["expense_approval_limit"] = limit
    if updates:
        frappe.db.set_value("Charity", charity, updates)
        frappe.db.commit()
    return {"charity": charity, "updated": list(updates.keys())}


@frappe.whitelist()
def set_account_enabled(email, enabled):
    charity = _require_charity_admin()
    email = (email or "").strip().lower()
    if frappe.db.get_value("User", email, "charity") != charity:
        frappe.throw(_("لا تملك صلاحية على هذا الحساب."), frappe.PermissionError)
    if email == frappe.session.user:
        frappe.throw(_("لا يمكنك تعطيل حسابك الحالي."))
    frappe.db.set_value("User", email, "enabled", 1 if int(enabled) else 0)
    frappe.db.commit()
    return {"email": email, "enabled": bool(int(enabled))}
