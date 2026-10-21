import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def make_ben(user, name):
    frappe.set_user(user)
    try:
        return frappe.get_doc({"doctype": "Beneficiary", "beneficiary_name": name}).insert().name
    finally:
        frappe.set_user("Administrator")


def request_as(user, beneficiary, rtype="مالية", amount=100, status="مقدم"):
    frappe.set_user(user)
    try:
        return (
            frappe.get_doc(
                {
                    "doctype": "Assistance Request",
                    "beneficiary": beneficiary,
                    "request_type": rtype,
                    "amount": amount,
                    "status": status,
                }
            )
            .insert()
            .name
        )
    finally:
        frappe.set_user("Administrator")


class TestAssistanceControl(FrappeTestCase):
    """وحدة طلبات المساعدة — عزل، فصل واجبات (لا يبتّ المُنشئ)، بوابة مدير الجمعية،
    ملاحظة قرار، مسار حالات محوكم، وربط المستفيد بالجمعية نفسها."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية مساعدة أ {self.tok}")
        self.cb = make_charity(f"جمعية مساعدة ب {self.tok}")
        self.ua = make_charity_user(f"aa_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ua2 = make_charity_user(f"aa2_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"ab_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.coord = make_charity_user(f"ac_{self.tok}@t.local", self.ca, ["Program Coordinator"])
        self.ben_a = make_ben(self.ua, f"مستفيد أ {self.tok}")
        self.ben_b = make_ben(self.ub, f"مستفيد ب {self.tok}")

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Assistance Request", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Assistance Request", n, force=1, ignore_permissions=True)
        for n in frappe.get_all("Beneficiary", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Beneficiary", n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ua2, self.ub, self.coord):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_set_charity_and_isolation(self):
        a = request_as(self.ua, self.ben_a)
        self.assertEqual(frappe.db.get_value("Assistance Request", a, "charity"), self.ca)
        frappe.set_user(self.ub)
        try:
            vis = frappe.get_list("Assistance Request", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(a, vis)

    def test_creator_cannot_approve_own(self):
        req = request_as(self.ua, self.ben_a)
        frappe.set_user(self.ua)
        try:
            d = frappe.get_doc("Assistance Request", req)
            d.status = "معتمد"
            d.decision_note = "أوافق على طلبي"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_other_admin_approves_and_stamps(self):
        req = request_as(self.ua, self.ben_a)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Assistance Request", req)
            d.status = "معتمد"
            d.decision_note = "مستوفٍ للشروط"
            d.save()
            d.reload()
            self.assertEqual(d.approved_by, self.ua2)
            self.assertTrue(d.approved_on)
        finally:
            frappe.set_user("Administrator")

    def test_decision_note_required(self):
        req = request_as(self.ua, self.ben_a)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Assistance Request", req)
            d.status = "معتمد"
            with self.assertRaises(frappe.ValidationError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_coordinator_cannot_approve(self):
        req = request_as(self.ua, self.ben_a)
        frappe.set_user(self.coord)
        try:
            d = frappe.get_doc("Assistance Request", req)
            d.status = "معتمد"
            d.decision_note = "x"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_illegal_transition_blocked(self):
        req = request_as(self.ua, self.ben_a)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Assistance Request", req)
            d.status = "مصروف"  # قفزة من «مقدم» إلى الصرف دون اعتماد
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_beneficiary_must_be_same_charity(self):
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc(
                    {
                        "doctype": "Assistance Request",
                        "beneficiary": self.ben_b,  # مستفيد من جمعية أخرى
                        "request_type": "مالية",
                        "amount": 100,
                        "status": "مقدم",
                    }
                ).insert()
        finally:
            frappe.set_user("Administrator")
