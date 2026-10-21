import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit import activation, signup
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def pub(slug, tok):
    d = frappe.get_doc({"doctype": "Legal Document", "title": f"{slug} {tok}", "slug": slug,
                        "version": "1.0", "language": "ar", "status": "Draft", "content": "<p>نص الاتفاقية</p>"}).insert(ignore_permissions=True)
    for s in ("In Review", "Approved", "Published"):
        d.status = s
        d.save(ignore_permissions=True)
    return d


def make_app(tok, approved=True):
    doc = {"doctype": "Association Application", "association_name": f"جمعية تفعيل {tok}",
           "license_number": f"L{tok}", "official_email": f"act_{tok}@a.local", "applicant_name": "مقدّم",
           "proposed_admin_email": f"admin_{tok}@a.local", "proposed_admin_name": "مدير الجمعية"}
    if approved:
        doc.update({"status": "Approved", "decision_reason": "معتمد", "email_verified": 1, "license_verified": 1})
    return frappe.get_doc(doc).insert(ignore_permissions=True)


class TestActivation(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)

    def tearDown(self):
        frappe.set_user("Administrator")
        ch = frappe.get_all("Charity", filters={"charity_name": ["like", f"%{self.tok}%"]}, pluck="name")
        for c in ch:
            for la in frappe.get_all("Legal Acceptance", filters={"charity": c}, pluck="name"):
                frappe.delete_doc("Legal Acceptance", la, force=1, ignore_permissions=True)
        for n in frappe.get_all("Association Approval", filters={"application": ["like", "%"]}, pluck="name"):
            if frappe.db.get_value("Association Approval", n, "charity") in ch:
                frappe.delete_doc("Association Approval", n, force=1, ignore_permissions=True)
        for n in frappe.get_all("Association Application", filters={"association_name": ["like", f"%{self.tok}%"]}, pluck="name"):
            frappe.delete_doc("Association Application", n, force=1, ignore_permissions=True)
        for u in (f"admin_{self.tok}@a.local",):
            if frappe.db.exists("User", u):
                frappe.delete_doc("User", u, force=1, ignore_permissions=True)
        for c in ch:
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        for n in frappe.get_all("Legal Document", filters={"title": ["like", f"%{self.tok}%"]}, pluck="name"):
            frappe.delete_doc("Legal Document", n, force=1, ignore_permissions=True)
        if getattr(self, "_extra_user", None) and frappe.db.exists("User", self._extra_user):
            frappe.delete_doc("User", self._extra_user, force=1, ignore_permissions=True)
        if getattr(self, "_extra_charity", None) and frappe.db.exists("Charity", self._extra_charity):
            frappe.delete_doc("Charity", self._extra_charity, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_self_signup_disabled(self):
        with self.assertRaises(frappe.PermissionError):
            signup.register_charity("جمعية", "مدير", f"x_{self.tok}@a.local", "password123")

    def test_issue_requires_published_agreements(self):
        app = make_app(self.tok)
        with self.assertRaises(frappe.ValidationError):  # لا شروط/DPA منشورة
            activation.issue_activation(app.name)

    def test_full_flow_issue_accept_activate(self):
        pub("terms", self.tok)
        pub("dpa", self.tok)
        app = make_app(self.tok)
        res = activation.issue_activation(app.name)
        charity = res["charity"]
        self.assertEqual(frappe.db.get_value("Charity", charity, "status"), "Suspended")
        appr = frappe.get_doc("Association Approval", res["approval"])
        self.assertEqual(appr.status, "Awaiting Acceptance")

        activation.accept_agreements(appr.acceptance_token, 1, 1, "ممثل الجمعية", "مدير", 1)
        appr.reload()
        self.assertEqual(appr.status, "Accepted")
        self.assertTrue(appr.terms_acceptance and appr.dpa_acceptance)
        self.assertEqual(frappe.db.count("Legal Acceptance", {"charity": charity}), 2)

        act = activation.activate(appr.name)
        appr.reload()
        self.assertEqual(appr.status, "Activated")
        self.assertEqual(frappe.db.get_value("Charity", charity, "status"), "Active")
        self.assertEqual(frappe.db.get_value("User", act["admin"], "charity"), charity)
        self.assertIn("Nonprofit Admin", frappe.get_roles(act["admin"]))

    def test_accept_requires_both_and_declaration(self):
        pub("terms", self.tok)
        pub("dpa", self.tok)
        app = make_app(self.tok)
        appr_name = activation.issue_activation(app.name)["approval"]
        token = frappe.db.get_value("Association Approval", appr_name, "acceptance_token")
        with self.assertRaises(frappe.ValidationError):  # DPA غير موافَق عليها
            activation.accept_agreements(token, 1, 0, "ممثل", "مدير", 1)
        with self.assertRaises(frappe.ValidationError):  # بلا إقرار تمثيل
            activation.accept_agreements(token, 1, 1, "ممثل", "مدير", 0)

    def test_non_operator_cannot_issue(self):
        pub("terms", self.tok)
        pub("dpa", self.tok)
        app = make_app(self.tok)
        self._extra_charity = make_charity(f"جمعية غير مشغّل {self.tok}")
        self._extra_user = make_charity_user(f"nonop_{self.tok}@t.local", self._extra_charity, ["Nonprofit Admin"])
        frappe.set_user(self._extra_user)
        try:
            with self.assertRaises(frappe.PermissionError):
                activation.issue_activation(app.name)
        finally:
            frappe.set_user("Administrator")
