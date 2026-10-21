import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit import accounts
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


class TestOnboarding(FrappeTestCase):
    """وحدة P5: رحلة التهيئة — تقدّم الخطوات، الاكتمال، عزل بالجمعية، ومدير الجمعية فقط."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية تهيئة أ {self.tok}")
        self.cb = make_charity(f"جمعية تهيئة ب {self.tok}")
        self.ua = make_charity_user(f"oa_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"ob_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"ov_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        self.extra = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for e in self.extra + [self.ua, self.ub, self.viewer]:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_status_progresses_and_completes(self):
        frappe.set_user(self.ua)
        try:
            st = accounts.onboarding_status()
            self.assertFalse(st["identity_done"])
            self.assertFalse(st["can_finish"])
            self.assertFalse(st["complete"])

            # لا يمكن الإنهاء قبل ضبط الهوية
            with self.assertRaises(frappe.ValidationError):
                accounts.complete_onboarding()

            accounts.update_charity_settings(registration_number="REG-1", contact_email=f"info_{self.tok}@ca.local")
            st = accounts.onboarding_status()
            self.assertTrue(st["identity_done"])
            self.assertTrue(st["can_finish"])
            self.assertFalse(st["complete"])  # لم يُنهِ بعد

            accounts.complete_onboarding()
            self.assertTrue(accounts.onboarding_status()["complete"])
        finally:
            frappe.set_user("Administrator")

    def test_team_step_after_invite(self):
        cc = make_charity(f"جمعية فرد {self.tok}")
        uc = make_charity_user(f"oc_{self.tok}@t.local", cc, ["Nonprofit Admin"])
        frappe.set_user(uc)
        try:
            self.assertFalse(accounts.onboarding_status()["team_done"])  # مدير واحد فقط
            res = accounts.invite_account("عضو جديد", f"mem_{self.tok}@cc.local", "Program Coordinator")
            self.extra.append(res["account"])
            st = accounts.onboarding_status()
            self.assertTrue(st["team_done"])
            self.assertEqual(st["accounts_used"], 2)
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", uc):
                frappe.delete_doc("User", uc, force=1, ignore_permissions=True)
            if frappe.db.exists("Charity", cc):
                frappe.delete_doc("Charity", cc, force=1, ignore_permissions=True)

    def test_admin_only(self):
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                accounts.onboarding_status()
        finally:
            frappe.set_user("Administrator")

    def test_scoped_to_own_charity(self):
        frappe.set_user(self.ua)
        try:
            accounts.update_charity_settings(registration_number="REG-A", contact_email=f"a_{self.tok}@ca.local")
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.ub)
        try:
            st = accounts.onboarding_status()
            self.assertEqual(st["charity"], self.cb)
            self.assertFalse(st["identity_done"])  # جمعية ب لم تُضبط
        finally:
            frappe.set_user("Administrator")
