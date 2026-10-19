"""عزل متعدّد الجمعيات (multi-tenancy) — طبقة أمان المنصة.

كل سجلات البيانات مربوطة بحقل `charity`، ويُفرض العزل على مستويين:
- `permission_query_conditions`: يفلتر القوائم/التقارير/التصدير/API على مستوى الاستعلام.
- `has_permission`: يتحقّق على مستوى السجل الواحد (get_doc/الروابط المباشرة).
- `set_charity` (doc_events.before_insert): يضبط الجمعية تلقائياً من جمعية المستخدم.

تمييز الأدوار (احترام الخصوصية/PDPL):
- **بيانات التشغيل** (لجان/قرارات/مبادرات/مهام): يراها عبر الجمعيات فقط
  System Manager / Administrator (break-glass). **ليس** Stochops Admin.
- **كيان Charity** (إدارة المستأجرين): يراه Stochops Admin أيضاً (مشغّل المنصة).
المستخدم بلا جمعية لا يرى شيئاً من بيانات الجمعيات.
"""
import frappe


def is_data_super(user=None):
    """وصول break-glass لكل بيانات التشغيل عبر الجمعيات (بلا Stochops Admin)."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return "System Manager" in frappe.get_roles(user)


def is_platform_admin(user=None):
    """مشغّل المنصة — لإدارة كيان Charity (يشمل Stochops Admin)."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(set(frappe.get_roles(user)) & {"System Manager", "Stochops Admin"})


def get_user_charity(user=None):
    """جمعية المستخدم (حقل مخصّص على User). None إن لم تُسنَد."""
    user = user or frappe.session.user
    if user in ("Administrator", "Guest"):
        return None
    return frappe.db.get_value("User", user, "charity")


def _condition(user, doctype):
    if is_data_super(user):
        return ""
    charity = get_user_charity(user)
    if not charity:
        return "1=0"  # لا جمعية => لا يرى شيئاً
    return f"`tab{doctype}`.`charity` = {frappe.db.escape(charity)}"


# دوال permission_query_conditions لكل نوع (لا تتلقّى اسم النوع، فنفصلها)
def committee_query(user):
    return _condition(user, "Committee")


def meeting_query(user):
    return _condition(user, "Meeting")


def decision_query(user):
    return _condition(user, "Decision")


def initiative_query(user):
    return _condition(user, "Initiative")


def initiative_task_query(user):
    return _condition(user, "Initiative Task")


# أدوار ترى كل حالات الجمعية؛ المنسّقون (غيرها) يرون حالاتهم المُسندة فقط (PDPL §7)
CASE_FULL_ROLES = {"Nonprofit Admin", "Executive Viewer"}


def _is_case_restricted(user):
    if is_data_super(user):
        return False
    return not (set(frappe.get_roles(user)) & CASE_FULL_ROLES)


def _case_condition(user, doctype):
    base = _condition(user, doctype)
    if base in ("", "1=0"):
        return base
    if _is_case_restricted(user):
        return f"({base} and `tab{doctype}`.`case_worker` = {frappe.db.escape(user)})"
    return base


def beneficiary_query(user):
    return _case_condition(user, "Beneficiary")


def assistance_request_query(user):
    return _case_condition(user, "Assistance Request")


def donor_query(user):
    return _condition(user, "Donor")


def donation_query(user):
    return _condition(user, "Donation")


def grant_query(user):
    return _condition(user, "Grant")


def expense_request_query(user):
    return _condition(user, "Expense Request")


def compliance_obligation_query(user):
    return _condition(user, "Compliance Obligation")


def personnel_query(user):
    return _condition(user, "Personnel")


def contract_query(user):
    return _condition(user, "Contract")


def procurement_request_query(user):
    return _condition(user, "Procurement Request")


def ai_run_log_query(user):
    return _condition(user, "AI Run Log")


def processing_activity_record_query(user):
    return _condition(user, "Processing Activity Record")


def sensitive_access_log_query(user):
    return _condition(user, "Sensitive Access Log")


def consent_record_query(user):
    return _condition(user, "Consent Record")


def privacy_rights_request_query(user):
    return _condition(user, "Privacy Rights Request")


def privacy_impact_assessment_query(user):
    return _condition(user, "Privacy Impact Assessment")


def disclosure_request_query(user):
    return _condition(user, "Disclosure Request")


def legal_hold_query(user):
    return _condition(user, "Legal Hold")


def security_incident_query(user):
    return _condition(user, "Security Incident")


def charity_query(user):
    # كيان Charity: مشغّل المنصة يرى الكل، والجمعية ترى سجلّها فقط.
    if is_platform_admin(user):
        return ""
    charity = get_user_charity(user)
    if not charity:
        return "1=0"
    return f"`tabCharity`.`name` = {frappe.db.escape(charity)}"


def _is_new(doc):
    try:
        return bool(doc.get("__islocal")) or doc.is_new()
    except Exception:
        return not doc.get("name")


def has_charity_permission(doc, ptype=None, user=None, permission_type=None):
    """تحقّق على مستوى سجل بيانات التشغيل: السجل يخصّ جمعية المستخدم.

    ملاحظة: Frappe يمرّر نوع الصلاحية باسم `ptype`. عند الإنشاء (ptype=create أو
    سجل جديد) نسمح، لأن الجمعية تُسنَد لاحقاً عبر set_charity (before_insert).
    """
    ptype = ptype or permission_type
    user = user or frappe.session.user
    if is_data_super(user):
        return True
    if ptype == "create" or _is_new(doc):
        return True
    return (doc.get("charity") or None) == get_user_charity(user)


def has_charity_doc_permission(doc, ptype=None, user=None, permission_type=None):
    """لكيان Charity: مشغّل المنصة يرى الكل، والجمعية سجلّها فقط."""
    ptype = ptype or permission_type
    user = user or frappe.session.user
    if is_platform_admin(user):
        return True
    if ptype == "create":
        return True
    return doc.name == get_user_charity(user)


def has_case_permission(doc, ptype=None, user=None, permission_type=None):
    """تحقّق على مستوى الحالة (مستفيد/طلب مساعدة): فوق عزل الجمعية، المنسّق يرى
    حالاته المُسندة فقط؛ المدير والمطّلع وبريك-جلاس يرون كل حالات الجمعية (PDPL §7)."""
    ptype = ptype or permission_type
    user = user or frappe.session.user
    if not has_charity_permission(doc, ptype=ptype, user=user):
        return False
    if ptype == "create" or _is_new(doc) or not _is_case_restricted(user):
        return True
    return (doc.get("case_worker") or None) == user


def set_charity(doc, method=None):
    """يضبط حقل charity تلقائياً من جمعية المستخدم عند الإنشاء (إن لم يُحدَّد)."""
    if not doc.get("charity"):
        charity = get_user_charity()
        if charity:
            doc.charity = charity


def set_charity_case(doc, method=None):
    """للحالات (مستفيد/طلب مساعدة): يضبط الجمعية + مسؤول الحالة تلقائياً لمنشئ
    السجل إن كان منسّقاً (دوراً مقيّداً)، ليحتفظ بوصوله لحالته."""
    set_charity(doc, method)
    if not doc.get("case_worker"):
        user = frappe.session.user
        if user not in ("Administrator", "Guest") and _is_case_restricted(user):
            doc.case_worker = user


def ensure_user_charity_field():
    """حقل مخصّص `charity` على User لربط كل مستخدم بجمعيته (idempotent)."""
    if not frappe.db.exists("Custom Field", {"dt": "User", "fieldname": "charity"}):
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "User",
                "fieldname": "charity",
                "label": "الجمعية (Charity)",
                "fieldtype": "Link",
                "options": "Charity",
                "insert_after": "username",
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()
