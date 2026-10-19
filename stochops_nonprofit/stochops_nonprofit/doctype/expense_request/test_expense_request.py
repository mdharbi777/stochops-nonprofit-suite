import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def expense_as(user, title, amount):
    frappe.set_user(user)
    try:
        return frappe.get_doc(
            {"doctype": "Expense Request", "title": title, "amount": amount, "request_date": today(), "status": "مقدّم"}
        ).insert().name
    finally:
        frappe.set_user("Administrator")


class TestExpenseControl(FrappeTestCase):
    """وحدة N4: المصروفات والرقابة المالية — عزل، فصل واجبات، حدّ اعتماد بالدور، تدقيق."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية ن4أ {self.tok}")
        self.cb = make_charity(f"جمعية ن4ب {self.tok}")
        frappe.db.set_value("Charity", self.ca, "expense_approval_limit", 50000)
        self.ua = make_charity_user(f"n4a_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ua2 = make_charity_user(f"n4a2_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"n4b_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"n4v_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        self.coord = make_charity_user(f"n4c_{self.tok}@t.local", self.ca, ["Program Coordinator"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Expense Request", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Expense Request", n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ua2, self.ub, self.viewer, self.coord):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_set_charity_and_isolation(self):
        a = expense_as(self.ua, f"أ {self.tok}", 100)
        self.assertEqual(frappe.db.get_value("Expense Request", a, "charity"), self.ca)
        self.assertEqual(frappe.db.get_value("Expense Request", a, "requested_by"), self.ua)
        frappe.set_user(self.ub)
        try:
            vis = frappe.get_list("Expense Request", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(a, vis)

    def test_segregation_of_duties(self):
        req = expense_as(self.ua, f"طلبي {self.tok}", 1000)
        frappe.set_user(self.ua)
        try:
            d = frappe.get_doc("Expense Request", req)
            d.status = "معتمد"
            d.decision_note = "أوافق على طلبي"
            with self.assertRaises(frappe.PermissionError):  # لا يبتّ المُقدّم في طلبه
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_other_admin_approves_within_limit(self):
        req = expense_as(self.ua, f"ضمن الحد {self.tok}", 40000)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Expense Request", req)
            d.status = "معتمد"
            d.decision_note = "مطابق للميزانية"
            d.save()
            d.reload()
            self.assertEqual(d.approved_by, self.ua2)
            self.assertTrue(d.approved_on)
        finally:
            frappe.set_user("Administrator")

    def test_approval_exceeds_role_limit(self):
        req = expense_as(self.ua, f"فوق الحد {self.tok}", 60000)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Expense Request", req)
            d.status = "معتمد"
            d.decision_note = "مبلغ كبير"
            with self.assertRaises(frappe.PermissionError):  # يتجاوز حدّ الاعتماد
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_decision_note_required(self):
        req = expense_as(self.ua, f"بلا ملاحظة {self.tok}", 100)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Expense Request", req)
            d.status = "معتمد"
            with self.assertRaises(frappe.ValidationError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_coordinator_cannot_approve(self):
        req = expense_as(self.ua, f"منسّق {self.tok}", 100)
        frappe.set_user(self.coord)
        try:
            d = frappe.get_doc("Expense Request", req)
            d.status = "معتمد"
            d.decision_note = "x"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_amount_non_negative_and_viewer_cannot_create(self):
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.ValidationError):
                frappe.get_doc(
                    {"doctype": "Expense Request", "title": f"سالب {self.tok}", "amount": -1, "request_date": today()}
                ).insert()
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc(
                    {"doctype": "Expense Request", "title": f"ممنوع {self.tok}", "amount": 10, "request_date": today()}
                ).insert()
        finally:
            frappe.set_user("Administrator")
