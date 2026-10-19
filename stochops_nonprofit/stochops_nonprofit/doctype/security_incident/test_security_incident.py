import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, now_datetime

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


class TestRetentionIncidentHolds(FrappeTestCase):
    """وحدة P5: الحوادث (نافذة 72 ساعة بلا بلاغ آلي) + الحجز القانوني + الاحتفاظ/المزوّدون + بوابة AI."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية خ5أ {self.tok}")
        self.cb = make_charity(f"جمعية خ5ب {self.tok}")
        self.admin = make_charity_user(f"p5_adm_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.adminb = make_charity_user(f"p5_admb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Security Incident", "Legal Hold"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.admin, self.adminb):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_incident_72h_window_and_isolation(self):
        disc = now_datetime()
        frappe.set_user(self.admin)
        try:
            d = frappe.get_doc(
                {"doctype": "Security Incident", "title": f"حادثة {self.tok}", "discovered_on": disc}
            ).insert()
            self.assertEqual(d.reporter, self.admin)
            self.assertEqual(get_datetime(d.notice_window_deadline), add_to_date(disc, hours=72))
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.adminb)
        try:
            vis = frappe.get_list("Security Incident", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(d.name, vis)

    def test_legal_hold_blocks_destruction(self):
        from stochops_nonprofit.privacy_core import assert_no_legal_hold, is_on_legal_hold

        target = f"BEN-TEST-{self.tok}"
        frappe.set_user(self.admin)
        try:
            h = frappe.get_doc(
                {"doctype": "Legal Hold", "hold_title": f"حجز {self.tok}", "reason": "نزاع",
                 "reference_doctype": "Beneficiary", "reference_name": target, "status": "نشط"}
            ).insert()
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(is_on_legal_hold("Beneficiary", target))
        with self.assertRaises(frappe.ValidationError):
            assert_no_legal_hold("Beneficiary", target)
        # رفع الحجز يرفع المنع
        frappe.set_user(self.admin)
        try:
            h.status = "مرفوع"
            h.save()
            h.reload()
            self.assertTrue(h.released_on)
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(is_on_legal_hold("Beneficiary", target))

    def test_platform_registries_seeded_and_restricted(self):
        self.assertTrue(frappe.get_all("Retention Schedule", filters={"status": "PENDING_DEFINITION"}, limit=1))
        self.assertTrue(frappe.db.count("Subprocessor Register") >= 1)
        frappe.set_user(self.admin)  # Nonprofit Admin ليس مشغّل منصّة
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc({"doctype": "Retention Schedule", "data_category": f"فئة {self.tok}"}).insert()
        finally:
            frappe.set_user("Administrator")

    def test_ai_external_gate_default_off(self):
        from stochops_nonprofit.privacy_core import assert_ai_external_allowed, is_ai_external_enabled

        frappe.db.set_single_value("Privacy Configuration", "ai_external_enabled", 0)
        self.assertFalse(is_ai_external_enabled())
        with self.assertRaises(frappe.ValidationError):
            assert_ai_external_allowed()
