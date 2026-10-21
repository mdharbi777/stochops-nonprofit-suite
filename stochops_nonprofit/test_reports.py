import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from stochops_nonprofit import reports
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    committee_as,
    decision_as,
    make_charity,
    make_charity_user,
)


class TestReportExport(FrappeTestCase):
    """وحدة P4: تصدير التقارير — عزل بيانات التصدير بالجمعية، ملف صالح، تدقيق، وقائمة بيضاء."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية تقارير أ {self.tok}")
        self.cb = make_charity(f"جمعية تقارير ب {self.tok}")
        self.ua = make_charity_user(f"ra_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"rb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.coma = committee_as(self.ua, f"لجنة أ {self.tok}")
        self.comb = committee_as(self.ub, f"لجنة ب {self.tok}")
        self.deca = decision_as(self.ua, self.coma, self.ua, f"قرار أ {self.tok}", today())
        self.decb = decision_as(self.ub, self.comb, self.ub, f"قرار ب {self.tok}", today())

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Sensitive Access Log", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Sensitive Access Log", n, force=1, ignore_permissions=True)
        for dt in ("Decision", "Meeting", "Committee"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_export_data_isolated_by_charity(self):
        frappe.set_user(self.ua)
        try:
            cols, rows = reports._run("Decisions by Committee", {})
        finally:
            frappe.set_user("Administrator")
        names = [r.get("name") for r in rows]
        self.assertIn(self.deca, names)
        self.assertNotIn(self.decb, names)

    def test_export_excel_builds_file_and_audits(self):
        frappe.set_user(self.ua)
        try:
            frappe.local.response = frappe._dict()
            reports.export_report("Decisions by Committee", "Excel", "{}")
            self.assertTrue(frappe.response.get("filename", "").endswith(".xlsx"))
            self.assertTrue(frappe.response.get("filecontent"))
            self.assertEqual(frappe.response.get("type"), "binary")
        finally:
            frappe.set_user("Administrator")
        logged = frappe.get_all(
            "Sensitive Access Log",
            filters={"event_type": "export", "reference_name": "Decisions by Committee", "charity": self.ca},
            limit=1,
        )
        self.assertTrue(logged)

    def test_export_pdf_builds_file(self):
        frappe.set_user(self.ua)
        try:
            frappe.local.response = frappe._dict()
            reports.export_report("Executive Summary", "PDF", "{}")
            self.assertTrue(frappe.response.get("filename", "").endswith(".pdf"))
            self.assertTrue(frappe.response.get("filecontent"))
        finally:
            frappe.set_user("Administrator")

    def test_unknown_report_rejected(self):
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.PermissionError):
                reports.export_report("Hacker Report", "Excel", "{}")
        finally:
            frappe.set_user("Administrator")

    def test_pdf_html_contains_charity_and_label(self):
        html = reports._pdf_html("Decisions by Committee", [{"label": "اللجنة", "fieldname": "committee", "fieldtype": "Link"}], [], self.ca)
        self.assertIn("منصة الفاضل", html)
        self.assertIn("اللجنة", html)
        self.assertIn("لا توجد بيانات", html)  # صفوف فارغة تُعرض بأمان
