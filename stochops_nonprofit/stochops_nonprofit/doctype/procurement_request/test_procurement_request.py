import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def proc_as(user, title, amount, status="مقدّم"):
    frappe.set_user(user)
    try:
        return (
            frappe.get_doc(
                {
                    "doctype": "Procurement Request",
                    "title": title,
                    "amount": amount,
                    "request_date": today(),
                    "status": status,
                }
            )
            .insert()
            .name
        )
    finally:
        frappe.set_user("Administrator")


class TestProcurementControl(FrappeTestCase):
    """وحدة المشتريات — عزل، فصل واجبات، حدّ اعتماد بالدور، مسار حالات محوكم، بوابة تنفيذ."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية شراء أ {self.tok}")
        self.cb = make_charity(f"جمعية شراء ب {self.tok}")
        frappe.db.set_value("Charity", self.ca, "expense_approval_limit", 50000)
        self.ua = make_charity_user(f"pa_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ua2 = make_charity_user(f"pa2_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"pb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.coord = make_charity_user(f"pc_{self.tok}@t.local", self.ca, ["Program Coordinator"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Procurement Request", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Procurement Request", n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ua2, self.ub, self.coord):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_set_charity_and_isolation(self):
        a = proc_as(self.ua, f"أ {self.tok}", 100)
        self.assertEqual(frappe.db.get_value("Procurement Request", a, "charity"), self.ca)
        self.assertEqual(frappe.db.get_value("Procurement Request", a, "requested_by"), self.ua)
        frappe.set_user(self.ub)
        try:
            vis = frappe.get_list("Procurement Request", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(a, vis)

    def test_segregation_of_duties(self):
        req = proc_as(self.ua, f"طلبي {self.tok}", 1000)
        frappe.set_user(self.ua)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "أوافق على طلبي"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_other_admin_approves_within_limit(self):
        req = proc_as(self.ua, f"ضمن الحد {self.tok}", 40000)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "مطابق"
            d.save()
            d.reload()
            self.assertEqual(d.approved_by, self.ua2)
            self.assertTrue(d.approved_on)
        finally:
            frappe.set_user("Administrator")

    def test_approval_exceeds_role_limit(self):
        req = proc_as(self.ua, f"فوق الحد {self.tok}", 60000)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "كبير"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_decision_note_required(self):
        req = proc_as(self.ua, f"بلا ملاحظة {self.tok}", 100)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            with self.assertRaises(frappe.ValidationError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_coordinator_cannot_approve(self):
        req = proc_as(self.ua, f"منسّق {self.tok}", 100)
        frappe.set_user(self.coord)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "x"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_illegal_transition_blocked(self):
        # لا يُقفز من «مقدّم» إلى «مُنفّذ» دون اعتماد (آلة الحالات)
        req = proc_as(self.ua, f"قفزة {self.tok}", 100)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "مُنفّذ"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_execute_requires_admin_from_approved(self):
        req = proc_as(self.ua, f"تنفيذ {self.tok}", 1000)
        # اعتماد بمدير آخر
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "موافق"
            d.save()
        finally:
            frappe.set_user("Administrator")
        # منسّق لا ينفّذ (بوابة التنفيذ تتطلّب مدير الجمعية)
        frappe.set_user(self.coord)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "مُنفّذ"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")
        # مدير ينفّذ
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "مُنفّذ"
            d.save()
            d.reload()
            self.assertEqual(d.status, "مُنفّذ")
        finally:
            frappe.set_user("Administrator")
