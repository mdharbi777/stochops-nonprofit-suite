import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.compliance_template.compliance_template import list_templates
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


class TestComplianceTemplates(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self._extra = None

    def tearDown(self):
        frappe.set_user("Administrator")
        if self._extra and frappe.db.exists("Compliance Template", self._extra):
            frappe.delete_doc("Compliance Template", self._extra, force=1, ignore_permissions=True)
        for u in frappe.get_all("User", filters={"email": ["like", f"%{self.tok}%"]}, pluck="name"):
            frappe.delete_doc("User", u, force=1, ignore_permissions=True)
        for c in frappe.get_all("Charity", filters={"charity_name": ["like", f"%{self.tok}%"]}, pluck="name"):
            frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_library_seeded_and_published(self):
        rows = list_templates()
        keys = [r["template_key"] for r in rows]
        # بُذرت القوالب الأساسية ومنشورة بمسارات ملفات ثابتة
        for k in ("ropa", "retention_schedule", "dpia", "beneficiary_privacy_notice"):
            self.assertIn(k, keys)
        for r in rows:
            self.assertTrue(r["file_path"].startswith("/assets/stochops_nonprofit/compliance-templates/"))
            self.assertIn(r["file_format"], ("DOCX", "XLSX"))

    def test_draft_excluded_from_library(self):
        self._extra = frappe.get_doc(
            {"doctype": "Compliance Template", "template_key": f"draft_{self.tok}",
             "template_name": f"مسودة {self.tok}", "category": "اختبار", "file_format": "DOCX", "status": "Draft"}
        ).insert(ignore_permissions=True).name
        keys = [r["template_key"] for r in list_templates()]
        self.assertNotIn(self._extra, keys)

    def test_readable_by_charity_roles(self):
        charity = make_charity(f"جمعية قوالب {self.tok}")
        user = make_charity_user(f"tpl_{self.tok}@t.local", charity, ["Nonprofit Admin"])
        frappe.set_user(user)
        try:
            self.assertTrue(frappe.has_permission("Compliance Template", "read"))
        finally:
            frappe.set_user("Administrator")
