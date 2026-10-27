"""واجهة المحاسبة للجمعية (المرحلة 2.2) — عرض القيود المحاسبية واعتماد المسودات.

القيود تُولَّد تلقائياً من جسر صرف المساعدة (erpnext_bridge) كمسودات (docstatus=0).
هنا يعرضها مدير/محاسب الجمعية ويعتمد المسودة (يرحّلها docstatus 0→1 = ترحيل محاسبي).

العزل: كل العمليات مقيّدة بشركة جمعية المستخدم فقط (لا يرى/يعتمد قيود جمعية أخرى) —
نتحقّق يدوياً من الشركة قبل أي إجراء ثم ننفّذ بتجاوز صلاحيات ERPNext (لتفادي منح
أدوار محاسبية خام على الديسك). فصل المهام: عند تفعيل `enforce_payer_separation` لا
يعتمد القيدَ من أنشأه (الصارف) — يعتمده شخص آخر. كل اعتماد يُسجَّل في سجل الوصول.
"""
import frappe
from frappe import _

from stochops_nonprofit.multitenancy import get_user_charity

# أدوار يحقّ لها عرض/اعتماد قيود الجمعية (مدير الجمعية بصفة محاسب + المشغّل)
ACCOUNTANT_ROLES = {"Nonprofit Admin", "System Manager"}
STATUS_AR = {0: "مسودة", 1: "معتمد", 2: "ملغى"}


def _require_company():
    user = frappe.session.user
    if not (ACCOUNTANT_ROLES & set(frappe.get_roles(user))):
        frappe.throw(_("عرض المحاسبة يتطلّب صلاحية مدير/محاسب الجمعية."), frappe.PermissionError)
    charity = get_user_charity(user)
    is_super = "System Manager" in frappe.get_roles(user)
    if not charity and not is_super:
        frappe.throw(_("حسابك غير مرتبط بجمعية."), frappe.PermissionError)
    # حقل الشركة يُضاف فقط مع erpnext؛ نتفادى الاستعلام عنه إن لم يوجد (مواقع بلا erpnext)
    company = None
    if charity and frappe.get_meta("Charity").has_field("company"):
        company = frappe.db.get_value("Charity", charity, "company")
    if not company:
        frappe.throw(_("لم تُفعَّل المحاسبة لجمعيتك بعد."))
    return charity, company


def _je_available():
    return bool(frappe.db.exists("DocType", "Journal Entry"))


def _entry_accounts(name):
    accts = frappe.get_all(
        "Journal Entry Account",
        filters={"parent": name},
        fields=["account", "debit_in_account_currency", "credit_in_account_currency"],
        ignore_permissions=True,
    )
    debit = next((a.account for a in accts if a.debit_in_account_currency), "")
    credit = next((a.account for a in accts if a.credit_in_account_currency), "")
    return debit, credit


@frappe.whitelist()
def list_journal_entries(status=None, limit=50):
    """قيود شركة الجمعية (معزولة)، أحدث أولاً. status: draft/submitted/cancelled."""
    charity, company = _require_company()
    if not _je_available():
        return {"company": company, "entries": []}
    try:
        limit = max(1, min(int(limit), 200))
    except (ValueError, TypeError):
        limit = 50
    filters = {"company": company}
    ds = {"draft": 0, "submitted": 1, "cancelled": 2}.get(status)
    if ds is not None:
        filters["docstatus"] = ds
    rows = frappe.get_all(
        "Journal Entry",
        filters=filters,
        fields=["name", "posting_date", "user_remark", "total_debit", "docstatus", "owner"],
        order_by="posting_date desc, creation desc",
        limit_page_length=limit,
        ignore_permissions=True,
    )
    for r in rows:
        r["status"] = STATUS_AR.get(r["docstatus"], "—")
        r["debit_account"], r["credit_account"] = _entry_accounts(r["name"])
        r["can_approve"] = r["docstatus"] == 0
    return {"company": company, "entries": rows}


@frappe.whitelist()
def finance_summary():
    """ملخّص مالي لشركة الجمعية: إجمالي المُرحّل + عدد المسودات + إجمالي القيود."""
    charity, company = _require_company()
    if not _je_available():
        return {"company": company, "total_posted": 0, "draft_count": 0, "total_count": 0}
    posted = frappe.db.get_value(
        "Journal Entry", {"company": company, "docstatus": 1}, "sum(total_debit)"
    )
    return {
        "company": company,
        "total_posted": float(posted or 0),
        "draft_count": frappe.db.count("Journal Entry", {"company": company, "docstatus": 0}),
        "total_count": frappe.db.count("Journal Entry", {"company": company, "docstatus": ["!=", 2]}),
    }


@frappe.whitelist()
def financial_report(kind=None, filters=None):
    """تقرير مالي معزول بشركة الجمعية — يعيد {columns, result} بنفس شكل تقارير المنصة.

    kind: spend_by_account (إجمالي المدين المُرحّل حسب الحساب) أو
          entries_by_status (عدد القيود وإجماليها حسب الحالة).
    """
    charity, company = _require_company()
    if not _je_available():
        return {"columns": [], "result": []}
    if kind == "entries_by_status":
        columns = [
            {"label": "الحالة", "fieldname": "status", "fieldtype": "Data"},
            {"label": "عدد القيود", "fieldname": "count", "fieldtype": "Int"},
            {"label": "الإجمالي (ريال)", "fieldname": "total", "fieldtype": "Currency"},
        ]
        result = []
        for ds, label in ((0, "مسودة"), (1, "معتمد")):
            cnt = frappe.db.count("Journal Entry", {"company": company, "docstatus": ds})
            tot = frappe.db.get_value("Journal Entry", {"company": company, "docstatus": ds}, "sum(total_debit)")
            result.append({"status": label, "count": cnt, "total": float(tot or 0)})
        return {"columns": columns, "result": result}
    # الافتراضي: إجمالي الصرف المُرحّل حسب الحساب (مدين)
    columns = [
        {"label": "الحساب", "fieldname": "account", "fieldtype": "Data"},
        {"label": "إجمالي المدين المُرحّل (ريال)", "fieldname": "debit", "fieldtype": "Currency"},
    ]
    result = frappe.db.sql(
        """select jea.account as account, sum(jea.debit_in_account_currency) as debit
           from `tabJournal Entry Account` jea
           join `tabJournal Entry` je on je.name = jea.parent
           where je.company = %s and je.docstatus = 1 and jea.debit_in_account_currency > 0
           group by jea.account order by debit desc""",
        company,
        as_dict=True,
    )
    return {"columns": columns, "result": [dict(r) for r in result]}


@frappe.whitelist()
def approve_journal_entry(name):
    """يعتمد (يرحّل) قيداً مسودة لشركة الجمعية. معزول + فصل مهام + تسجيل."""
    charity, company = _require_company()
    name = (name or "").strip()
    je_company = frappe.db.get_value("Journal Entry", name, "company")
    if not je_company:
        frappe.throw(_("القيد غير موجود."))
    if je_company != company:
        frappe.throw(_("لا تملك صلاحية على هذا القيد."), frappe.PermissionError)
    doc = frappe.get_doc("Journal Entry", name)
    if doc.docstatus != 0:
        frappe.throw(_("القيد ليس مسودة (رُحِّل أو أُلغي)."))
    # فصل المهام: عند تفعيله، لا يعتمد القيدَ من أنشأه (الصارف)
    if frappe.db.get_value("Charity", charity, "enforce_payer_separation") and doc.owner == frappe.session.user:
        frappe.throw(_("فصل المهام: لا يعتمد القيدَ من سجّله. يعتمده محاسب آخر."))
    doc.flags.ignore_permissions = True
    doc.submit()
    frappe.db.commit()
    try:
        from stochops_nonprofit.privacy_core import log_sensitive_access

        log_sensitive_access("approve", "Journal Entry", name, note="submit", charity=charity)
    except Exception:
        pass
    return {"name": name, "status": "معتمد"}
