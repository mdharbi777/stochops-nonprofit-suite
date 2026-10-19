import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def personnel_as(user, name, nid=None):
    frappe.set_user(user)
    try:
        doc = {"doctype": "Personnel", "full_name": name}
        if nid:
            doc["national_id"] = nid
        return frappe.get_doc(doc).insert().name
    finally:
        frappe.set_user("Administrator")


def procurement_as(user, title, amount):
    frappe.set_user(user)
    try:
        return frappe.get_doc(
            {"doctype": "Procurement Request", "title": title, "amount": amount, "request_date": today(), "status": "مقدّم"}
        ).insert().name
    finally:
        frappe.set_user("Administrator")


class TestPersonnelContractsProcurement(FrappeTestCase):
    """وحدة N6: الموظفون/المتطوعون/العقود/المشتريات — عزل، هوية مشفّرة، تنبيه عقد،
    مشتريات بفصل واجبات وحدّ اعتماد. بلا رواتب فعلية."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية ن6أ {self.tok}")
        self.cb = make_charity(f"جمعية ن6ب {self.tok}")
        frappe.db.set_value("Charity", self.ca, "expense_approval_limit", 50000)
        self.ua = make_charity_user(f"n6a_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ua2 = make_charity_user(f"n6a2_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"n6b_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"n6v_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        self.coord = make_charity_user(f"n6c_{self.tok}@t.local", self.ca, ["Program Coordinator"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Procurement Request", "Contract", "Personnel"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ua2, self.ub, self.viewer, self.coord):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_personnel_isolation_and_no_salary(self):
        a = personnel_as(self.ua, f"أ {self.tok}")
        b = personnel_as(self.ub, f"ب {self.tok}")
        self.assertEqual(frappe.db.get_value("Personnel", a, "charity"), self.ca)
        frappe.set_user(self.ua)
        try:
            vis = frappe.get_list("Personnel", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(a, vis)
        self.assertNotIn(b, vis)
        fields = {f.fieldname for f in frappe.get_meta("Personnel").fields}
        self.assertFalse(fields & {"salary", "basic_salary", "wage", "gosi"})  # بلا رواتب/تأمينات
        self.assertEqual(frappe.get_meta("Personnel").get_field("national_id").fieldtype, "Password")

    def test_national_id_reveal_admin_only(self):
        from stochops_nonprofit.personnel import reveal_national_id

        p = personnel_as(self.ua, f"هوية {self.tok}", nid="1050000009")
        self.assertNotEqual(frappe.db.get_value("Personnel", p, "national_id"), "1050000009")
        frappe.set_user(self.ua)
        try:
            self.assertEqual(reveal_national_id(p)["national_id"], "1050000009")
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                reveal_national_id(p)
        finally:
            frappe.set_user("Administrator")

    def test_contract_dates(self):
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.ValidationError):
                frappe.get_doc(
                    {"doctype": "Contract", "contract_title": f"ع {self.tok}",
                     "start_date": today(), "end_date": add_days(today(), -5)}
                ).insert()
            c = frappe.get_doc(
                {"doctype": "Contract", "contract_title": f"عقد {self.tok}", "contract_type": "عمل",
                 "start_date": today(), "end_date": add_days(today(), 90), "status": "ساري"}
            ).insert()
            self.assertEqual(frappe.db.get_value("Contract", c.name, "charity"), self.ca)
        finally:
            frappe.set_user("Administrator")

    def test_procurement_sod_and_limit(self):
        req = procurement_as(self.ua, f"طلبي {self.tok}", 40000)  # requested_by = ua
        # المُقدّم لا يبتّ
        frappe.set_user(self.ua)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "أوافق"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")
        # مدير آخر يعتمد ضمن الحد
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", req)
            d.status = "معتمد"
            d.decision_note = "ضمن الميزانية"
            d.save()
            d.reload()
            self.assertEqual(d.approved_by, self.ua2)
        finally:
            frappe.set_user("Administrator")

    def test_procurement_exceeds_limit_and_coordinator(self):
        big = procurement_as(self.ua, f"كبير {self.tok}", 60000)
        frappe.set_user(self.ua2)
        try:
            d = frappe.get_doc("Procurement Request", big)
            d.status = "معتمد"
            d.decision_note = "فوق الحد"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")
        small = procurement_as(self.ua, f"صغير {self.tok}", 100)
        frappe.set_user(self.coord)
        try:
            d = frappe.get_doc("Procurement Request", small)
            d.status = "معتمد"
            d.decision_note = "x"
            with self.assertRaises(frappe.PermissionError):  # المنسّق لا يعتمد
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_viewer_cannot_create_personnel(self):
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc({"doctype": "Personnel", "full_name": f"v {self.tok}"}).insert()
        finally:
            frappe.set_user("Administrator")
