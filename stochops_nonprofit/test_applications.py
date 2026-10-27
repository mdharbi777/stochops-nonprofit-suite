import json

import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.applications import get_application_status, submit_application
from stochops_nonprofit.signup import _unsign, get_captcha
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def _cap():
    c = get_captcha()
    return c["token"], _unsign(c["token"])["s"]


class TestAssociationApplication(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Association Application", filters={"association_name": ["like", f"%{self.tok}%"]}, pluck="name"):
            frappe.delete_doc("Association Application", n, force=1, ignore_permissions=True)
        for e in getattr(self, "_users", []):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in getattr(self, "_charities", []):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def _submit(self, extra=None):
        t, a = _cap()
        payload = {
            "association_name": f"جمعية طلب {self.tok}",
            "license_number": f"LIC-{self.tok}",
            "official_email": f"App_{self.tok}@assoc.local",
            "applicant_name": "مقدّم الطلب",
        }
        if extra:
            payload.update(extra)
        return submit_application(json.dumps(payload), t, a)

    def test_submit_creates_submitted_and_code(self):
        res = self._submit()
        self.assertTrue(res["application"] and res["access_code"])
        d = frappe.db.get_value("Association Application", res["application"],
                                ["status", "official_email", "proposed_admin_email"], as_dict=True)
        self.assertEqual(d.status, "Submitted")
        self.assertEqual(d.official_email, f"app_{self.tok}@assoc.local")  # صُغّر

    def test_status_lookup_match_and_mismatch(self):
        res = self._submit()
        ok = get_application_status(res["application"], res["access_code"], f"app_{self.tok}@assoc.local")
        self.assertEqual(ok["status"], "Submitted")
        self.assertNotIn("score_need", ok)  # لا تُفشى الدرجات
        with self.assertRaises(frappe.ValidationError):
            get_application_status(res["application"], "WRONGCODE1", f"app_{self.tok}@assoc.local")

    def test_illegal_transition_blocked(self):
        res = self._submit()
        d = frappe.get_doc("Association Application", res["application"])
        d.status = "Approved"  # Submitted -> Approved غير مسموح
        with self.assertRaises(frappe.PermissionError):
            d.save()

    def test_approve_requires_verification_and_stamps(self):
        res = self._submit()
        d = frappe.get_doc("Association Application", res["application"])
        d.status = "Under Review"
        d.save()
        d.reload()
        d.status = "Approved"
        d.decision_reason = "مستوفٍ"
        with self.assertRaises(frappe.PermissionError):  # الترخيص/البريد غير محقّقين
            d.save()
        d.reload()
        d.email_verified = 1
        d.license_verified = 1
        d.status = "Approved"
        d.decision_reason = "مستوفٍ للشروط والترخيص محقّق"
        d.save()
        d.reload()
        self.assertEqual(d.status, "Approved")
        self.assertEqual(d.decided_by, "Administrator")
        self.assertTrue(d.decided_on)

    def test_decision_requires_reason(self):
        res = self._submit()
        d = frappe.get_doc("Association Application", res["application"])
        d.status = "Under Review"; d.save(); d.reload()
        d.email_verified = 1; d.license_verified = 1
        d.status = "Approved"  # بلا مبرّر
        with self.assertRaises(frappe.ValidationError):
            d.save()

    def test_score_total_and_cap(self):
        res = self._submit()
        d = frappe.get_doc("Association Application", res["application"])
        d.score_need = 20; d.score_readiness = 15; d.score_scale = 10
        d.score_governance = 15; d.score_manager = 8; d.score_fit = 7
        d.save(); d.reload()
        self.assertEqual(d.score_total, 75)
        d.score_need = 30  # يتجاوز 25
        with self.assertRaises(frappe.ValidationError):
            d.save()

    def test_non_operator_cannot_read(self):
        res = self._submit()
        self._charities = [make_charity(f"جمعية غير مشغّل {self.tok}")]
        self._users = [make_charity_user(f"nonop_{self.tok}@t.local", self._charities[0], ["Nonprofit Admin"])]
        frappe.set_user(self._users[0])
        try:
            self.assertFalse(frappe.has_permission("Association Application", "read"))
        finally:
            frappe.set_user("Administrator")

    def test_email_verification_sets_flag_via_link(self):
        from stochops_nonprofit.applications import _app_verify_token, verify_application_email

        res = self._submit()
        app = res["application"]
        self.assertEqual(frappe.db.get_value("Association Application", app, "email_verified"), 0)
        token = _app_verify_token(app, f"app_{self.tok}@assoc.local")
        out = verify_application_email(token)
        self.assertTrue(out["verified"])
        self.assertEqual(frappe.db.get_value("Association Application", app, "email_verified"), 1)
        self.assertTrue(frappe.db.get_value("Association Application", app, "email_verified_on"))

    def test_email_verification_invalid_token_rejected(self):
        from stochops_nonprofit.applications import verify_application_email

        with self.assertRaises(frappe.ValidationError):
            verify_application_email("not-a-valid-token")


class TestBeneficiarySearch(FrappeTestCase):
    """بحث المستفيدين (name→BEN) مقيّد بجمعية المستخدم."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية بحث أ {self.tok}")
        self.cb = make_charity(f"جمعية بحث ب {self.tok}")
        self.ua = make_charity_user(f"srcha_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"srchb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self._mk(self.ua, f"سعيد {self.tok}")
        self._mk(self.ua, f"سعاد {self.tok}")
        self._mk(self.ub, f"سعيد ب {self.tok}")
        frappe.db.commit()

    def _mk(self, user, name):
        frappe.set_user(user)
        try:
            return frappe.get_doc({"doctype": "Beneficiary", "beneficiary_name": name}).insert().name
        finally:
            frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Beneficiary", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Beneficiary", n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_search_scoped_to_charity(self):
        from stochops_nonprofit.beneficiaries import search_beneficiaries

        frappe.set_user(self.ua)
        try:
            labels = [r["label"] for r in search_beneficiaries(q="سع")]
        finally:
            frappe.set_user("Administrator")
        self.assertIn(f"سعيد {self.tok}", labels)
        self.assertIn(f"سعاد {self.tok}", labels)
        self.assertNotIn(f"سعيد ب {self.tok}", labels)  # جمعية أخرى — معزولة

    def test_search_by_ben_id(self):
        from stochops_nonprofit.beneficiaries import search_beneficiaries

        bid = self._mk(self.ua, f"فلان {self.tok}")
        frappe.set_user(self.ua)
        try:
            values = [r["value"] for r in search_beneficiaries(q=bid)]
        finally:
            frappe.set_user("Administrator")
        self.assertIn(bid, values)
