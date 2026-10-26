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


def legal_acceptance_query(user):
    return _condition(user, "Legal Acceptance")


def association_approval_query(user):
    # شبكة أمان: Association Approval مُدار من المشغّل؛ العزل يضمن ألا ترى جمعية
    # سجلّ اعتماد جمعية أخرى حتى لو مُنحت صلاحية قراءة مستقبلاً.
    return _condition(user, "Association Approval")


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
        # دفاع عميق: لا يُنشئ غير المشغّل سجلاً بجمعية غير جمعيته (تُفرَض لاحقاً في set_charity)
        c = doc.get("charity") or None
        if c and c != get_user_charity(user):
            return False
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
    """يضبط ويَفرِض حقل charity من جمعية المستخدم عند الإنشاء.

    أمان (H1): لغير مشغّل المنصّة تُفرَض جمعية المستخدم دائماً وتُتجاهَل أي قيمة واردة
    من العميل، لمنع زرع سجلات في جمعية أخرى عبر الـ API. من بلا جمعية لا يُنشئ سجلاً.
    يحتفظ المشغّل (break-glass) بإمكان ضبط الجمعية صراحةً.
    """
    if is_data_super():
        return
    charity = get_user_charity()
    if not charity:
        frappe.throw(frappe._("حسابك غير مرتبط بجمعية؛ لا يمكن إنشاء السجل."), frappe.PermissionError)
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


# ========================================================================
# المرحلة 2.1 — عزل جداول ERPNext المالية بنموذج «شركة لكل جمعية»
# ------------------------------------------------------------------------
# ثلاث طبقات (defense-in-depth، بنفس صرامة المرحلة الأولى، deny-by-default):
#   1) User Permission على Company لكل مستخدم جمعية (العزل الأصيل الواسع).
#   2) permission_query_conditions + has_permission على الجداول المالية (دفاع عميق).
#   3) set_company (before_insert): يفرض شركة المستخدم ويمنع الزرع في شركة أخرى.
# كسر الزجاج: System Manager / Administrator (is_data_super).
# التفاصيل: alfadil-docs/phase2.1-erpnext-isolation-design.md
# ========================================================================

# الجداول المالية الأساسية المعزولة (كلها تحوي حقل `company` قياسياً في ERPNext v15).
# التوسعة بسطر واحد. الجداول الأبناء تُعزَل عبر آبائها، وبقية جداول ERPNext المرتبطة
# بالشركة يغطّيها العزل الأصيل (الطبقة 1).
ERPNEXT_FINANCIAL_DOCTYPES = (
    "GL Entry",
    "Journal Entry",
    "Payment Entry",
    "Sales Invoice",
    "Purchase Invoice",
    "Account",
    "Cost Center",
    "Budget",
    "Payment Ledger Entry",
    "Bank Account",
    "Bank Transaction",
)


def _charity_has_company_field():
    """هل حقل Charity.company موجود؟ (غائب على bench بلا erpnext ⇒ المحاسبة معطّلة)."""
    try:
        return bool(frappe.db.has_column("Charity", "company"))
    except Exception:
        return False


def get_user_company(user=None):
    """شركة ERPNext لجمعية المستخدم. يفشل مغلقاً: بلا حقل/بلا شركة ⇒ None."""
    charity = get_user_charity(user)
    if not charity:
        return None
    if not _charity_has_company_field():
        return None
    return frappe.db.get_value("Charity", charity, "company")


def _company_condition(user, doctype):
    """شرط عزل مالي: السجلّ يخصّ شركة جمعية المستخدم. deny-by-default."""
    if is_data_super(user):
        return ""
    company = get_user_company(user)
    if not company:
        return "1=0"  # لا شركة مُسندة ⇒ لا يرى أي سجلّ مالي
    return f"`tab{doctype}`.`company` = {frappe.db.escape(company)}"


def erpnext_financial_query(user, doctype):
    """permission_query_conditions مشترك للجداول المالية (الاسم يُمرَّر عبر الغلاف)."""
    return _company_condition(user, doctype)


def has_erpnext_permission(doc, ptype=None, user=None, permission_type=None):
    """has_permission على مستوى السجلّ المالي: السجلّ يخصّ شركة جمعية المستخدم.

    عند الإنشاء: دفاع عميق — لا يُنشئ غير المشغّل سجلاً بشركة غير شركته (تُفرَض
    لاحقاً في set_company). من بلا شركة لا يرى/لا يُنشئ شيئاً (deny-by-default).
    """
    ptype = ptype or permission_type
    user = user or frappe.session.user
    if is_data_super(user):
        return True
    company = get_user_company(user)
    if not company:
        return False
    if ptype == "create" or _is_new(doc):
        c = doc.get("company") or None
        return not (c and c != company)
    return (doc.get("company") or None) == company


def set_company(doc, method=None):
    """يفرض حقل company من شركة جمعية المستخدم عند الإنشاء (نظير set_charity، H1).

    لغير المشغّل تُفرَض شركة المستخدم دائماً وتُتجاهَل أي قيمة واردة من العميل،
    لمنع زرع سجلّ مالي في شركة جمعية أخرى عبر الـAPI. من بلا شركة لا يُنشئ سجلاً.
    """
    if is_data_super():
        return
    company = get_user_company()
    if not company:
        frappe.throw(
            frappe._("حسابك غير مرتبط بشركة محاسبية؛ لا يمكن إنشاء السجلّ المالي."),
            frappe.PermissionError,
        )
    doc.company = company


# دوال permission_query_conditions لكل جدول مالي (Frappe يمرّر `user` فقط).
def gl_entry_query(user):
    return erpnext_financial_query(user, "GL Entry")


def journal_entry_query(user):
    return erpnext_financial_query(user, "Journal Entry")


def payment_entry_query(user):
    return erpnext_financial_query(user, "Payment Entry")


def sales_invoice_query(user):
    return erpnext_financial_query(user, "Sales Invoice")


def purchase_invoice_query(user):
    return erpnext_financial_query(user, "Purchase Invoice")


def account_query(user):
    return erpnext_financial_query(user, "Account")


def cost_center_query(user):
    return erpnext_financial_query(user, "Cost Center")


def budget_query(user):
    return erpnext_financial_query(user, "Budget")


def payment_ledger_entry_query(user):
    return erpnext_financial_query(user, "Payment Ledger Entry")


def bank_account_query(user):
    return erpnext_financial_query(user, "Bank Account")


def bank_transaction_query(user):
    return erpnext_financial_query(user, "Bank Transaction")


def ensure_charity_company_field():
    """حقل مخصّص `company` (Link→Company) على Charity — فقط عند وجود erpnext (idempotent).

    يُبقي التطبيق قابلاً للتثبيت على bench بلا erpnext (بيئة التطوير): لا يُنشَأ الحقل
    ما لم يوجد دكتايب Company.
    """
    if not frappe.db.exists("DocType", "Company"):
        return
    if not frappe.db.exists("Custom Field", {"dt": "Charity", "fieldname": "company"}):
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Charity",
                "fieldname": "company",
                "label": "الشركة المحاسبية (ERPNext Company)",
                "fieldtype": "Link",
                "options": "Company",
                "insert_after": "registration_number",
                "read_only": 1,
                "description": "تُنشأ تلقائياً عند التفعيل؛ أساس عزل البيانات المالية.",
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()


def sync_user_company_permission(user, company=None):
    """الطبقة 1: يضمن User Permission على Company للمستخدم (العزل المالي الأصيل).

    idempotent. يتطلّب وجود erpnext (دكتايب Company). يُقيّد المستخدم تلقائياً لكل
    جدول مرتبط بالشركة في ERPNext. يُتخطّى بأمان إن لم تُسنَد شركة بعد.
    """
    if not frappe.db.exists("DocType", "Company"):
        return
    if user in ("Administrator", "Guest"):
        return
    company = company or get_user_company(user)
    if not company:
        return
    exists = frappe.db.exists(
        "User Permission",
        {"user": user, "allow": "Company", "for_value": company},
    )
    if exists:
        return
    frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": "Company",
            "for_value": company,
            "apply_to_all_doctypes": 1,
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
