"""توجيه ما بعد الدخول.

كل المستخدمين — مستخدمو الجمعية والمشغّل — يُوجَّهون تلقائياً إلى الواجهة المحوكمة
«/nos/console» بدل لوحة Frappe التقنية «/app». يبقى Administrator وحده على سلوك
Frappe الافتراضي (لوحة الإدارة الكاملة). ويمكن للمشغّل فتح «/app» يدوياً عند الحاجة.
"""
import frappe


def route_charity_users_to_nos(login_manager=None):
    """on_session_creation hook: يضبط صفحة البداية إلى /nos/console لكل المستخدمين عدا Administrator."""
    try:
        user = frappe.session.user
        if not user or user in ("Guest", "Administrator"):
            return
        frappe.local.response["home_page"] = "/nos/console"
    except Exception:
        # لا نُعطّل الدخول مهما حدث
        pass
