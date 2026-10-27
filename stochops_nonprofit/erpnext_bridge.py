"""جسور تكامل ERPNext للمرحلة 2.1 (منصة الفاضل) — شركة لكل جمعية + مساعدة←قيد.

كل ما هنا محميّ بوجود erpnext (دكتايب Company): يُتخطّى بأمان على bench بلا erpnext
وعلى الجمعيات التي لم تُفعّل المحاسبة بعد (توافق خلفي كامل).

- provision_charity_company: ينشئ Company للجمعية ويربطها ويضمن حساب مصروف المساعدات.
- assistance_on_update: عند انتقال طلب المساعدة إلى «مصروف» يُولّد Journal Entry مسودة.

التصميم: alfadil-docs/phase2.1-erpnext-isolation-design.md
"""
import frappe
from frappe import _

ASSISTANCE_DISBURSED_STATE = "مصروف"
ASSISTANCE_EXPENSE_ACCOUNT_NAME = "مساعدات المستفيدين"
DEFAULT_CURRENCY = "SAR"
DEFAULT_COUNTRY = "Saudi Arabia"


def erpnext_enabled():
    """هل بيئة التشغيل تحوي محاسبة ERPNext؟ (دكتايب Company موجود)."""
    return bool(frappe.db.exists("DocType", "Company"))


# ----------------------------------------------------------------------
# إعداد الشركة لكل جمعية
# ----------------------------------------------------------------------
def _company_abbr(charity_name):
    """اختصار شركة من اسم الجمعية (أحرف/أرقام فقط، حتى 5)، فريد."""
    base = "".join(ch for ch in (charity_name or "") if ch.isalnum())[:5] or "CHR"
    abbr, i = base, 1
    while frappe.db.exists("Company", {"abbr": abbr}):
        i += 1
        abbr = f"{base[:4]}{i}"
    return abbr


def _ensure_erpnext_masters():
    """يضمن مسترات ERPNext الدنيا اللازمة لإنشاء Company (قد تغيب إن لم يكتمل معالج
    التهيئة setup wizard). idempotent. حالياً: Warehouse Type «Transit» المطلوب لإنشاء
    مستودع العبور الافتراضي عند إنشاء الشركة."""
    if frappe.db.exists("DocType", "Warehouse Type") and not frappe.db.exists(
        "Warehouse Type", "Transit"
    ):
        frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(
            ignore_permissions=True
        )


def provision_charity_company(charity):
    """ينشئ/يضمن Company لجمعية ويربطها بحقل Charity.company. idempotent.

    يعيد اسم الشركة، أو None إن لم تكن المحاسبة مفعّلة في البيئة.
    """
    if not erpnext_enabled():
        return None
    from stochops_nonprofit.multitenancy import ensure_charity_company_field

    ensure_charity_company_field()
    _ensure_erpnext_masters()
    charity_doc = frappe.get_doc("Charity", charity)
    existing = frappe.db.get_value("Charity", charity, "company")
    if existing and frappe.db.exists("Company", existing):
        _ensure_assistance_expense_account(existing)
        return existing

    company_name = charity_doc.charity_name
    if frappe.db.exists("Company", company_name):
        company = company_name
    else:
        company = (
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": company_name,
                    "abbr": _company_abbr(company_name),
                    "default_currency": DEFAULT_CURRENCY,
                    "country": DEFAULT_COUNTRY,
                }
            )
            .insert(ignore_permissions=True)
            .name
        )
    frappe.db.set_value("Charity", charity, "company", company)
    _ensure_assistance_expense_account(company)
    frappe.db.commit()
    return company


def _ensure_assistance_expense_account(company):
    """يضمن حساب مصروف «مساعدات المستفيدين» تحت الشركة (idempotent)."""
    abbr = frappe.db.get_value("Company", company, "abbr")
    acc_name = f"{ASSISTANCE_EXPENSE_ACCOUNT_NAME} - {abbr}"
    if frappe.db.exists("Account", acc_name):
        return acc_name
    # الأب: مجموعة المصروفات الرئيسية للشركة
    parent = frappe.db.get_value(
        "Account",
        {"company": company, "root_type": "Expense", "is_group": 1},
        "name",
        order_by="lft",
    )
    if not parent:
        return None
    frappe.get_doc(
        {
            "doctype": "Account",
            "account_name": ASSISTANCE_EXPENSE_ACCOUNT_NAME,
            "parent_account": parent,
            "company": company,
            "root_type": "Expense",
            "account_type": "Expense Account",
            "is_group": 0,
        }
    ).insert(ignore_permissions=True)
    return acc_name


# ----------------------------------------------------------------------
# جسر: مساعدة مصروفة ← قيد محاسبي (Journal Entry مسودة)
# ----------------------------------------------------------------------
def ensure_assistance_journal_field():
    """حقل مخصّص `journal_entry` (Link→Journal Entry) على Assistance Request —
    فقط عند وجود erpnext (idempotent). يمنع تكرار توليد القيد."""
    if not erpnext_enabled():
        return
    if not frappe.db.exists("Custom Field", {"dt": "Assistance Request", "fieldname": "journal_entry"}):
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Assistance Request",
                "fieldname": "journal_entry",
                "label": "القيد المحاسبي (Journal Entry)",
                "fieldtype": "Link",
                "options": "Journal Entry",
                "insert_after": "charity",
                "read_only": 1,
                "description": "يُولَّد تلقائياً (مسودة) عند صرف المساعدة.",
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()


def assistance_on_update(doc, method=None):
    """on_update لطلب المساعدة: عند انتقاله إلى «مصروف» يُولّد قيداً محاسبياً مرة واحدة.

    يُتخطّى بأمان إن: لم تُفعّل المحاسبة في البيئة، أو لا شركة للجمعية، أو المبلغ صفر،
    أو نوع الطلب غير «مالية»، أو وُلِّد قيد سابقاً.
    """
    if not erpnext_enabled():
        return
    if doc.status != ASSISTANCE_DISBURSED_STATE:
        return
    if doc.get("journal_entry"):
        return  # لا تكرار
    # لا يُولّد إلا عند الانتقال الفعلي إلى «مصروف» (لا عند إعادة حفظ سجلّ مصروف قديم)
    if not doc.is_new():
        before = doc.get_doc_before_save()
        if before and before.status == ASSISTANCE_DISBURSED_STATE:
            return
    amount = float(doc.amount or 0)
    if amount <= 0:
        return
    if (doc.request_type or "") != "مالية":
        return  # العيني/الخدمي لا يُولّد قيد صرف نقدي
    company = frappe.db.get_value("Charity", doc.charity, "company")
    if not company:
        return  # الجمعية لم تُفعّل المحاسبة ⇒ وضع تشغيلي فقط

    try:
        je = _create_assistance_journal_entry(doc, company, amount)
    except Exception:
        frappe.log_error(
            f"فشل توليد القيد المحاسبي لصرف المساعدة {doc.name}",
            "stochops_nonprofit.erpnext_bridge",
        )
        frappe.throw(
            _("تعذّر توليد القيد المحاسبي لهذا الصرف؛ لم يُسجَّل الصرف. راجع إعداد الحسابات أو المشغّل.")
        )
    doc.db_set("journal_entry", je, update_modified=False)


def _resolve_accounts(company):
    """يعيد (حساب مدين=مصروف المساعدات، حساب دائن=نقد/بنك افتراضي) للشركة."""
    abbr = frappe.db.get_value("Company", company, "abbr")
    debit = f"{ASSISTANCE_EXPENSE_ACCOUNT_NAME} - {abbr}"
    if not frappe.db.exists("Account", debit):
        debit = _ensure_assistance_expense_account(company)
    credit = frappe.db.get_value("Company", company, "default_cash_account")
    if not credit:
        credit = frappe.db.get_value(
            "Account",
            {"company": company, "account_type": "Cash", "is_group": 0},
            "name",
        )
    if not (debit and credit):
        frappe.throw(_("لم يُعثر على حسابات المصروف/النقد للشركة؛ أكمل إعداد دليل الحسابات."))
    return debit, credit


def _create_assistance_journal_entry(doc, company, amount):
    """ينشئ Journal Entry مسودة (docstatus=0) لصرف المساعدة. يعيد اسم القيد."""
    debit, credit = _resolve_accounts(company)
    # تقليل البيانات (PDPL): نشير في الدفتر المالي بمعرّف BEN المستعار فقط — لا نُكرّر
    # اسم المستفيد الصريح في النظام المحاسبي. الهوية تبقى في سجلّ المستفيد المعزول،
    # ويحلّها محاسب الجمعية عند الحاجة. يبسّط ذلك «الحق في المحو»: المحو/الإخفاء يجري
    # في سجلّ المستفيد، والقيد يحمل مرجعاً مستعاراً فقط (يُحتفظ به لمقتضيات الدفاتر النظامية).
    program = doc.get("initiative") or ""
    remark = _("صرف مساعدة — طلب {0} — المستفيد {1}{2}").format(
        doc.name, doc.beneficiary, _(" — البرنامج ") + program if program else ""
    )
    je = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "company": company,
            "posting_date": frappe.utils.nowdate(),
            "user_remark": remark,
            "accounts": [
                {"account": debit, "debit_in_account_currency": amount},
                {"account": credit, "credit_in_account_currency": amount},
            ],
        }
    )
    je.insert(ignore_permissions=True)  # مسودة: يعتمدها محاسب الجمعية (فصل المهام)
    return je.name
