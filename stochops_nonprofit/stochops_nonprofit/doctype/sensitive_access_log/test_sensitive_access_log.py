import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)
from stochops_nonprofit.stochops_nonprofit.doctype.beneficiary.test_beneficiary import beneficiary_as


class TestPrivacyCore(FrappeTestCase):
    """وحدة P1: Privacy Core — بوابة الإنتاج، عزل سجلّات الخصوصية، تسجيل كشف الهوية،
    تهيئة المرجعية والكتالوج، وتقييد المرجعية التنظيمية بمشغّل المنصّة."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.g_prev = frappe.db.get_single_value("Privacy Configuration", "production_privacy_gate")
        self.ca = make_charity(f"جمعية خ1 {self.tok}")
        self.cb = make_charity(f"جمعية خ2 {self.tok}")
        self.ua = make_charity_user(f"pc_a_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"pc_b_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("Privacy Configuration", "production_privacy_gate", self.g_prev or 0)
        for dt in ("Sensitive Access Log", "Processing Activity Record", "Beneficiary"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_gate_closed_by_default(self):
        from stochops_nonprofit.privacy_core import assert_gate_open, is_gate_open

        frappe.db.set_single_value("Privacy Configuration", "production_privacy_gate", 0)
        self.assertFalse(is_gate_open())
        with self.assertRaises(frappe.ValidationError):
            assert_gate_open()

    def test_gate_open_requires_officer_and_policy(self):
        cfg = frappe.get_single("Privacy Configuration")
        cfg.default_privacy_officer = None
        cfg.platform_privacy_policy_version = ""
        cfg.production_privacy_gate = 1
        with self.assertRaises(frappe.ValidationError):
            cfg.save(ignore_permissions=True)
        # مع المتطلبات تُفتح وتُختم
        cfg.reload()
        cfg.default_privacy_officer = "Administrator"
        cfg.platform_privacy_policy_version = "v1"
        cfg.production_privacy_gate = 1
        cfg.save(ignore_permissions=True)
        from stochops_nonprofit.privacy_core import is_gate_open
        self.assertTrue(is_gate_open())
        self.assertTrue(frappe.db.get_single_value("Privacy Configuration", "gate_opened_on"))

    def test_sensitive_log_isolation_and_reveal(self):
        from stochops_nonprofit.beneficiaries import reveal_national_id

        ben = beneficiary_as(self.ua, f"هوية {self.tok}", nid="1090000001")
        frappe.set_user(self.ua)
        try:
            reveal_national_id(ben)
        finally:
            frappe.set_user("Administrator")
        logs_a = frappe.get_all(
            "Sensitive Access Log",
            filters={"charity": self.ca, "event_type": "reveal", "reference_name": ben},
            pluck="name",
        )
        self.assertTrue(logs_a, "كشف الهوية يجب أن يُسجَّل")
        # عزل: مدير جمعية ب لا يرى سجلّ جمعية أ
        frappe.set_user(self.ub)
        try:
            visible = frappe.get_list("Sensitive Access Log", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(logs_a[0], visible)

    def test_processing_activity_isolation(self):
        frappe.set_user(self.ua)
        try:
            a = frappe.get_doc(
                {"doctype": "Processing Activity Record", "activity_name": f"نشاط {self.tok}", "purpose": "اختبار"}
            ).insert().name
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Processing Activity Record", a, "charity"), self.ca)
        frappe.set_user(self.ub)
        try:
            visible = frappe.get_list("Processing Activity Record", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(a, visible)

    def test_regulatory_rule_platform_only(self):
        frappe.set_user(self.ua)  # Nonprofit Admin — ليس مشغّل منصّة
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc(
                    {"doctype": "Regulatory Rule", "rule_title": f"قاعدة {self.tok}"}
                ).insert()
        finally:
            frappe.set_user("Administrator")

    def test_ensure_seeds_catalog_and_rules(self):
        from stochops_nonprofit.privacy_core import ensure_privacy_core

        ensure_privacy_core()
        self.assertTrue(frappe.db.exists("Data Field Catalog", "Beneficiary.national_id"))
        self.assertTrue(
            frappe.db.exists("Regulatory Rule", {"status": "LEGAL_REVIEW_REQUIRED"}),
            "يجب زرع قواعد تنظيمية بحالة مراجعة قانونية",
        )
