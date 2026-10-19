"""التسجيل الذاتي للجمعية — ينشئ كياناً Charity + أول حساب مدير (Nonprofit Admin).

allow_guest=True ليعمل من صفحة التسجيل العامة. يُنشئ عبر ignore_permissions.
ملاحظة أمان للإنتاج: أضِف captcha + تحديد معدّل (rate limit) + تأكيد بريد قبل
الكشف العام، لمنع إساءة الاستخدام.
"""
import frappe
from frappe import _
from frappe.utils import validate_email_address

ADMIN_ROLE = "Nonprofit Admin"
MIN_PASSWORD = 8


@frappe.whitelist(allow_guest=True)
def register_charity(charity_name, admin_full_name, admin_email, password, admin_mobile=None, registration_number=None):
    charity_name = (charity_name or "").strip()
    admin_full_name = (admin_full_name or "").strip()
    admin_email = (admin_email or "").strip().lower()

    if not (charity_name and admin_full_name and admin_email and password):
        frappe.throw(_("الحقول المطلوبة: اسم الجمعية، اسم المدير، البريد، كلمة المرور."))
    validate_email_address(admin_email, throw=True)
    if len(password) < MIN_PASSWORD:
        frappe.throw(_("كلمة المرور يجب ألا تقل عن {0} أحرف.").format(MIN_PASSWORD))
    if frappe.db.exists("Charity", charity_name):
        frappe.throw(_("اسم الجمعية مُستخدم مسبقاً."))
    if frappe.db.exists("User", admin_email):
        frappe.throw(_("هذا البريد مُستخدم مسبقاً."))

    charity = frappe.get_doc(
        {
            "doctype": "Charity",
            "charity_name": charity_name,
            "registration_number": registration_number,
            "contact_email": admin_email,
            "contact_mobile": admin_mobile,
            "status": "Active",
        }
    ).insert(ignore_permissions=True)

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": admin_email,
            "first_name": admin_full_name,
            "mobile_no": admin_mobile,
            "language": "ar",
            "time_zone": "Asia/Riyadh",
            "send_welcome_email": 0,
            "new_password": password,
        }
    ).insert(ignore_permissions=True)
    user.add_roles(ADMIN_ROLE)
    frappe.db.set_value("User", user.name, "charity", charity.name)
    frappe.db.commit()

    return {"charity": charity.name, "admin": user.name}
