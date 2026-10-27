"""اختبارات بوّابة المحاسبة (المرحلة 2.2) — الصلاحيات والعزل.

الاختبارات المعتمدة على ERPNext (توليد/اعتماد القيود) تُغطّى بفحص منطقي مستقلّ
وبالتجربة الحيّة؛ هنا نتحقّق من بوّابات الصلاحية التي تعمل في أي بيئة (قبل لمس
دكتايبات ERPNext).
"""
import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


class TestAccountingGate(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية محاسبة {self.tok}")
        self.admin = make_charity_user(f"acc_admin_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"acc_view_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")
        for e in (self.admin, self.viewer):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        if frappe.db.exists("Charity", self.ca):
            frappe.delete_doc("Charity", self.ca, force=1, ignore_permissions=True)
        frappe.db.commit()

    def _as(self, user, fn, *a, **k):
        frappe.set_user(user)
        try:
            return fn(*a, **k)
        finally:
            frappe.set_user("Administrator")

    def test_non_accountant_role_blocked(self):
        from stochops_nonprofit.accounting import finance_summary

        with self.assertRaises(frappe.PermissionError):
            self._as(self.viewer, finance_summary)

    def test_admin_without_company_blocked(self):
        from stochops_nonprofit.accounting import finance_summary, list_journal_entries

        # الجمعية لم تُفعّل المحاسبة (لا شركة) ⇒ تُرفض العملية بوضوح
        with self.assertRaises(frappe.ValidationError):
            self._as(self.admin, finance_summary)
        with self.assertRaises(frappe.ValidationError):
            self._as(self.admin, list_journal_entries)
