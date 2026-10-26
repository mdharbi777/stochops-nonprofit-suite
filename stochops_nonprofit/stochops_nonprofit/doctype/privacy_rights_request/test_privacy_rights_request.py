import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)
from stochops_nonprofit.stochops_nonprofit.doctype.beneficiary.test_beneficiary import beneficiary_as


class TestPrivacyRightsDpiaConsentCase(FrappeTestCase):
    """وحدة P3: حقوق الأفراد (30 يوماً) + الموافقة + DPIA + ACL على مستوى الحالة."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية خ3أ {self.tok}")
        self.cb = make_charity(f"جمعية خ3ب {self.tok}")
        self.admin = make_charity_user(f"p3_adm_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.adminb = make_charity_user(f"p3_admb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.c1 = make_charity_user(f"p3_c1_{self.tok}@t.local", self.ca, ["Program Coordinator"])
        self.c2 = make_charity_user(f"p3_c2_{self.tok}@t.local", self.ca, ["Program Coordinator"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Privacy Rights Request", "Consent Record", "Privacy Impact Assessment", "Beneficiary"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.admin, self.adminb, self.c1, self.c2):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_rights_due_date_and_extension(self):
        frappe.set_user(self.admin)
        try:
            d = frappe.get_doc(
                {"doctype": "Privacy Rights Request", "request_type": "وصول",
                 "subject_name": f"ط {self.tok}", "received_on": today()}
            ).insert()
            self.assertEqual(str(d.due_date), str(add_days(getdate(today()), 30)))
            d.extended = 1
            d.extension_reason = "تعقيد الطلب"
            d.save()
            d.reload()
            self.assertEqual(str(d.extended_due), str(add_days(getdate(d.due_date), 30)))
            # إغلاق يضبط تاريخ الإنجاز
            d.status = "مكتمل"
            d.save()
            d.reload()
            self.assertTrue(d.resolved_on)
        finally:
            frappe.set_user("Administrator")

    def test_rights_no_reopen_after_close(self):
        """آلة الحالات: الطلب المكتمل (نهائي) لا يُعاد إلى قيد المعالجة (كمدير جمعية)."""
        frappe.set_user(self.admin)
        try:
            d = frappe.get_doc(
                {"doctype": "Privacy Rights Request", "request_type": "وصول",
                 "subject_name": f"غلق {self.tok}", "received_on": today()}
            ).insert()
            d.status = "مكتمل"  # مستلم → مكتمل مسموح
            d.save()
            d.reload()
            d.status = "قيد المعالجة"  # إعادة فتح — ممنوع
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")

    def test_rights_isolation(self):
        frappe.set_user(self.admin)
        try:
            a = frappe.get_doc({"doctype": "Privacy Rights Request", "request_type": "شكوى",
                                "subject_name": f"أ {self.tok}", "received_on": today()}).insert().name
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.adminb)
        try:
            vis = frappe.get_list("Privacy Rights Request", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(a, vis)

    def test_consent_withdraw(self):
        frappe.set_user(self.admin)
        try:
            c = frappe.get_doc({"doctype": "Consent Record", "subject_type": "مستفيد",
                                "subject_ref": f"م {self.tok}", "status": "ممنوحة", "granted_on": today()}).insert()
            c.status = "مسحوبة"
            c.save()
            c.reload()
            self.assertTrue(c.withdrawn_on)
        finally:
            frappe.set_user("Administrator")

    def test_dpia_approval_requires_human(self):
        frappe.set_user(self.admin)
        try:
            d = frappe.get_doc({"doctype": "Privacy Impact Assessment", "activity_name": f"نشاط {self.tok}"}).insert()
            self.assertEqual(d.status, "مسودة")
            d.status = "معتمد"
            with self.assertRaises(frappe.ValidationError):  # يتطلّب جهة اعتماد بشرية
                d.save()
            d.reload()
            d.status = "معتمد"
            d.approved_by = "مدير الجمعية"
            d.save()
            self.assertEqual(frappe.db.get_value("Privacy Impact Assessment", d.name, "status"), "معتمد")
        finally:
            frappe.set_user("Administrator")

    def test_case_acl_coordinator_sees_only_own(self):
        # منسّق 1 ينشئ مستفيداً → يصبح مسؤول الحالة
        ben1 = beneficiary_as(self.c1, f"حالة1 {self.tok}")
        self.assertEqual(frappe.db.get_value("Beneficiary", ben1, "case_worker"), self.c1)
        # منسّق 1 يرى حالته
        frappe.set_user(self.c1)
        try:
            vis1 = frappe.get_list("Beneficiary", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(ben1, vis1)
        # منسّق 2 (نفس الجمعية) لا يرى حالة منسّق 1
        frappe.set_user(self.c2)
        try:
            vis2 = frappe.get_list("Beneficiary", pluck="name", limit_page_length=0)
            can2 = frappe.has_permission("Beneficiary", "read", doc=ben1)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(ben1, vis2)
        self.assertFalse(can2)
        # المدير يرى كل حالات الجمعية
        frappe.set_user(self.admin)
        try:
            visA = frappe.get_list("Beneficiary", pluck="name", limit_page_length=0)
            canA = frappe.has_permission("Beneficiary", "read", doc=ben1)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(ben1, visA)
        self.assertTrue(canA)
