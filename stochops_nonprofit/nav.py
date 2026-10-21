"""سياق التنقّل للواجهة المحوكمة /nos.

يعيد أدوار المستخدم الحالي وجمعيته — مصدرها الخادم — ليُخفي الهيكل ما لا يحقّ عرضه.
الصلاحيات الفعلية مفروضة على الخادم عبر permission_query_conditions وhas_permission.
"""
import frappe


@frappe.whitelist(allow_guest=True)
def get_my_context():
    user = frappe.session.user
    roles = frappe.get_roles(user)
    charity = frappe.db.get_value("User", user, "charity") if user and user != "Guest" else None
    charity_name = frappe.db.get_value("Charity", charity, "charity_name") if charity else None
    return {
        "user": user,
        "roles": roles,
        "charity": charity,
        "charity_name": charity_name,
    }
