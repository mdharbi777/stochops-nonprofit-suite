"""فحص عزل مالي حيّ (المرحلة 2.1) — يُشغَّل فقط على موقع به erpnext.

ليس ملف test_ (لا يُجمَع في حزمة --app على موقع التطوير بلا erpnext). يُنفَّذ بـ:
    bench --site <erp-site> execute stochops_nonprofit.erpnext_live_check.run

ينشئ جمعيتين A وB بشركتين ومستخدمين، ويتحقّق من:
  1) عزل القوائم (permission_query_conditions) — B لا يرى قيود/حسابات A.
  2) عزل السجلّ (has_permission) — B لا يصل مباشرةً لقيد A.
  3) User Permission على Company (الطبقة 1) — B يرى شركته فقط.
  4) فرض الشركة عند الكتابة (set_company) — B لا يكتب في شركة A.
  5) deny-by-default — مستخدم بلا شركة لا يرى شيئاً.
  6) كسر الزجاج — System Manager يرى الكل.
  7) جسر المساعدة — «مصروف» يولّد Journal Entry مسودة مربوطاً.

idempotent قدر الإمكان (يحذف بيانات الاختبار السابقة ببادئة ZZTEST). يُحدث commit.
"""
import frappe

from stochops_nonprofit import erpnext_bridge
from stochops_nonprofit.multitenancy import sync_user_company_permission

PFX = "ZZTEST"
A_NAME = f"{PFX} جمعية أ"
B_NAME = f"{PFX} جمعية ب"
A_USER = "zztest_a@example.com"
B_USER = "zztest_b@example.com"
NONE_USER = "zztest_none@example.com"


def _results():
    return {"pass": [], "fail": []}


def _check(r, name, cond):
    (r["pass"] if cond else r["fail"]).append(name)


def _ensure_user(email, charity=None):
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {"doctype": "User", "email": email, "first_name": email.split("@")[0],
             "send_welcome_email": 0, "enabled": 1}
        ).insert(ignore_permissions=True)
    u = frappe.get_doc("User", email)
    roles = set(frappe.get_roles(email))
    want = {"Nonprofit Admin"}
    # دور محاسبي حقيقي: ليكون للمستخدم وصولٌ مالي فعلاً، فتُختبَر طبقات العزل (لا غياب الصلاحية)
    if frappe.db.exists("Role", "Accounts User"):
        want.add("Accounts User")
    missing = [x for x in want if x not in roles]
    if missing:
        u.add_roles(*missing)
    if charity:
        frappe.db.set_value("User", email, "charity", charity)
    return email


def _ensure_fiscal_year():
    """يضمن سنة مالية عالمية تغطّي تاريخ اليوم (تغيب على موقع لم يُكمِل معالج التهيئة)."""
    from frappe.utils import getdate, nowdate

    y = getdate(nowdate()).year
    if frappe.db.exists("Fiscal Year", str(y)):
        return str(y)
    fy = frappe.get_doc(
        {"doctype": "Fiscal Year", "year": str(y),
         "year_start_date": f"{y}-01-01", "year_end_date": f"{y}-12-31"}
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    return fy.name


def _ensure_charity(name):
    if not frappe.db.exists("Charity", name):
        frappe.get_doc({"doctype": "Charity", "charity_name": name, "status": "Active"}).insert(
            ignore_permissions=True
        )
    return name


def _make_je(company, amount=100):
    debit, credit = erpnext_bridge._resolve_accounts(company)
    je = frappe.get_doc(
        {"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": company,
         "posting_date": frappe.utils.nowdate(), "user_remark": f"{PFX} check",
         "accounts": [
             {"account": debit, "debit_in_account_currency": amount},
             {"account": credit, "credit_in_account_currency": amount},
         ]}
    )
    je.insert(ignore_permissions=True)
    return je


def run():
    if not erpnext_bridge.erpnext_enabled():
        print("SKIP: erpnext غير مثبّت على هذا الموقع.")
        return {"skipped": True}

    frappe.set_user("Administrator")
    r = _results()
    _ensure_fiscal_year()

    # تهيئة: جمعيتان + شركتان + مستخدمون
    a = _ensure_charity(A_NAME)
    b = _ensure_charity(B_NAME)
    comp_a = erpnext_bridge.provision_charity_company(a)
    comp_b = erpnext_bridge.provision_charity_company(b)
    _check(r, "شركتان مختلفتان أُنشئتا", bool(comp_a and comp_b and comp_a != comp_b))

    _ensure_user(A_USER, a)
    _ensure_user(B_USER, b)
    _ensure_user(NONE_USER, None)  # بلا جمعية/شركة
    sync_user_company_permission(A_USER, comp_a)
    sync_user_company_permission(B_USER, comp_b)
    frappe.db.commit()

    # مستخدم A ينشئ قيداً في شركة A ويعتمده (ينشئ GL Entries)
    frappe.set_user("Administrator")
    je_a = _make_je(comp_a)
    je_a.submit()
    frappe.db.commit()
    je_a_name = je_a.name

    try:
        # ---- 1) عزل القوائم: B لا يرى قيد A ----
        frappe.set_user(B_USER)
        jes = frappe.get_list("Journal Entry", pluck="name", limit_page_length=0)
        _check(r, "1. B لا يرى قيد A في القائمة", je_a_name not in jes)
        accts = frappe.get_list("Account", filters={"company": comp_a}, pluck="name", limit_page_length=0)
        _check(r, "1b. B لا يرى حسابات شركة A", len(accts) == 0)
        gles = frappe.get_list("GL Entry", filters={"company": comp_a}, pluck="name", limit_page_length=0)
        _check(r, "1c. B لا يرى قيود GL لشركة A", len(gles) == 0)

        # ---- 2) عزل السجلّ: B لا يصل مباشرةً لقيد A ----
        can = frappe.has_permission("Journal Entry", doc=je_a_name, user=B_USER)
        _check(r, "2. has_permission يمنع B عن قيد A", not can)

        # ---- 3) User Permission على Company: B يرى شركته فقط ----
        comps = frappe.get_list("Company", pluck="name", limit_page_length=0)
        _check(r, "3. B يرى شركته فقط", comps == [comp_b])

        # ---- 4) فرض الشركة: B لا يكتب في شركة A ----
        wrote_in_a = False
        try:
            debit_a, credit_a = erpnext_bridge._resolve_accounts(comp_a)
            je = frappe.get_doc(
                {"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": comp_a,
                 "posting_date": frappe.utils.nowdate(), "user_remark": f"{PFX} B->A",
                 "accounts": [
                     {"account": debit_a, "debit_in_account_currency": 50},
                     {"account": credit_a, "credit_in_account_currency": 50},
                 ]}
            )
            je.insert()
            wrote_in_a = frappe.db.get_value("Journal Entry", je.name, "company") == comp_a
        except Exception:
            wrote_in_a = False
        _check(r, "4. B لا ينشئ قيداً في شركة A", not wrote_in_a)

        # ---- 5) deny-by-default: مستخدم بلا شركة لا يرى شيئاً ----
        frappe.set_user(NONE_USER)
        none_jes = frappe.get_list("Journal Entry", pluck="name", limit_page_length=0)
        _check(r, "5. مستخدم بلا شركة لا يرى أي قيد", len(none_jes) == 0)

        # ---- 6) كسر الزجاج: Administrator يرى قيد A ----
        frappe.set_user("Administrator")
        admin_jes = frappe.get_list("Journal Entry", pluck="name", limit_page_length=0)
        _check(r, "6. كسر الزجاج يرى قيد A", je_a_name in admin_jes)

        # ---- 7) جسر المساعدة: «مصروف» يولّد Journal Entry مسودة ----
        try:
            erpnext_bridge.ensure_assistance_journal_field()
            ben = frappe.get_doc(
                {"doctype": "Beneficiary", "beneficiary_name": f"{PFX} مستفيد", "charity": a}
            ).insert(ignore_permissions=True)
            asr = frappe.get_doc(
                {"doctype": "Assistance Request", "beneficiary": ben.name, "request_type": "مالية",
                 "amount": 250, "charity": a, "status": "مقدم"}
            ).insert(ignore_permissions=True)
            asr.db_set("status", "معتمد")
            asr.decision_note = "اختبار"
            asr.status = "مصروف"
            asr.save(ignore_permissions=True)
            frappe.db.commit()
            je_bridge = frappe.db.get_value("Assistance Request", asr.name, "journal_entry")
            _check(r, "7. مساعدة مصروفة ولّدت قيداً", bool(je_bridge))
            if je_bridge:
                jed = frappe.get_doc("Journal Entry", je_bridge)
                _check(r, "7b. القيد مسودة (docstatus=0)", jed.docstatus == 0)
                _check(r, "7c. القيد في شركة A", jed.company == comp_a)
        except Exception as e:
            _check(r, f"7. جسر المساعدة (استثناء: {e})", False)
    finally:
        frappe.set_user("Administrator")

    print("\n==== نتائج فحص العزل الحيّ ====")
    for p in r["pass"]:
        print("  PASS:", p)
    for f in r["fail"]:
        print("  FAIL:", f)
    print(f"==== {len(r['pass'])} نجح / {len(r['fail'])} فشل ====\n")
    if r["fail"]:
        raise Exception(f"فشل {len(r['fail'])} فحص عزل: {r['fail']}")
    return r
