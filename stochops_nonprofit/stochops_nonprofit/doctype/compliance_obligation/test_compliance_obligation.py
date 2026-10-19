import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def obligation_as(user, title, due, status="قادم"):
    frappe.set_user(user)
    try:
        return frappe.get_doc(
            {"doctype": "Compliance Obligation", "title": title, "due_date": due, "status": status}
        ).insert().name
    finally:
        frappe.set_user("Administrator")


class TestComplianceObligation(FrappeTestCase):
    """وحدة N5: الالتزامات المحكومة — عزل، تأخير مشتق، إكمال خادمي، لا تكامل حكومي."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية ن5أ {self.tok}")
        self.cb = make_charity(f"جمعية ن5ب {self.tok}")
        self.ua = make_charity_user(f"n5a_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"n5b_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"n5v_{self.tok}@t.local", self.ca, ["Executive Viewer"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Compliance Obligation", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Compliance Obligation", n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub, self.viewer):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_set_charity_and_isolation(self):
        a = obligation_as(self.ua, f"أ {self.tok}", add_days(today(), 10))
        b = obligation_as(self.ub, f"ب {self.tok}", add_days(today(), 10))
        self.assertEqual(frappe.db.get_value("Compliance Obligation", a, "charity"), self.ca)
        frappe.set_user(self.ua)
        try:
            vis = frappe.get_list("Compliance Obligation", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(a, vis)
        self.assertNotIn(b, vis)

    def test_completed_on_server_side(self):
        name = obligation_as(self.ua, f"إكمال {self.tok}", add_days(today(), 5))
        frappe.set_user(self.ua)
        try:
            d = frappe.get_doc("Compliance Obligation", name)
            d.status = "مكتمل"
            d.save()
            d.reload()
            self.assertEqual(str(d.completed_on), str(today()))
            # الرجوع عن الإكمال يمسح تاريخ الإكمال
            d.status = "قيد الإعداد"
            d.save()
            d.reload()
            self.assertFalse(d.completed_on)
        finally:
            frappe.set_user("Administrator")

    def test_overdue_is_derived(self):
        past = obligation_as(self.ua, f"متأخر {self.tok}", add_days(today(), -3), status="قادم")
        done = obligation_as(self.ua, f"منجز {self.tok}", add_days(today(), -3), status="مكتمل")
        self.assertTrue(frappe.get_doc("Compliance Obligation", past).is_overdue)
        self.assertFalse(frappe.get_doc("Compliance Obligation", done).is_overdue)
        # لا حقل حالة «متأخر» مخزّن
        self.assertNotIn("overdue", {f.fieldname for f in frappe.get_meta("Compliance Obligation").fields})

    def test_report_runs_scoped(self):
        obligation_as(self.ua, f"تقرير {self.tok}", add_days(today(), 2))
        frappe.set_user(self.ua)
        try:
            cols, rows = frappe.get_attr(
                "stochops_nonprofit.stochops_nonprofit.report.compliance_obligations.compliance_obligations.execute"
            )()
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(cols)
        titles = [r.get("title") for r in rows]
        self.assertIn(f"تقرير {self.tok}", titles)

    def test_viewer_cannot_create(self):
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc(
                    {"doctype": "Compliance Obligation", "title": f"v {self.tok}", "due_date": today()}
                ).insert()
        finally:
            frappe.set_user("Administrator")
