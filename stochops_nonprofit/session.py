"""توجيه ما بعد الدخول.

مستخدمو الجمعية (بأدوار المنصة، وبلا System Manager) يُوجَّهون تلقائياً إلى
الواجهة المحوكمة «/nos» بدل لوحة Frappe التقنية «/app». الإداريون التقنيون
(System Manager / Administrator) يبقون على سلوك Frappe الافتراضي.
"""
import frappe

PORTAL_ROLES = {
    "Nonprofit Admin",
    "Executive Viewer",
    "Committee Coordinator",
    "Program Coordinator",
}


def route_charity_users_to_nos(login_manager=None):
    """on_session_creation hook: يضبط صفحة البداية إلى /nos لمستخدمي الجمعية."""
    try:
        user = frappe.session.user
        if not user or user in ("Guest", "Administrator"):
            return
        roles = set(frappe.get_roles(user))
        if "System Manager" in roles:
            return
        if roles & PORTAL_ROLES:
            frappe.local.response["home_page"] = "/nos"
    except Exception:
        # لا نُعطّل الدخول مهما حدث
        pass
