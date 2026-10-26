import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def beneficiary_as(user, name, nid=None):
    frappe.set_user(user)
    try:
        doc = {"doctype": "Beneficiary", "beneficiary_name": name}
        if nid:
            doc["national_id"] = nid
        return frappe.get_doc(doc).insert().name
    finally:
        frappe.set_user("Administrator")


class TestBeneficiaryAssistance(FrappeTestCase):
    """وحدة N2: المستفيدون وطلبات المساعدة — عزل، تشفير/حجب الهوية، مسار اعتماد، تقليل."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية ن2أ {self.tok}")
        self.cb = make_charity(f"جمعية ن2ب {self.tok}")
        self.ua = make_charity_user(f"n2a_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"n2b_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"n2v_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        self.coord = make_charity_user(f"n2c_{self.tok}@t.local", self.ca, ["Program Coordinator"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Assistance Request", "Beneficiary"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub, self.viewer, self.coord):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_set_charity_and_isolation(self):
        a = beneficiary_as(self.ua, f"أ {self.tok}")
        b = beneficiary_as(self.ub, f"ب {self.tok}")
        self.assertEqual(frappe.db.get_value("Beneficiary", a, "charity"), self.ca)
        frappe.set_user(self.ua)
        try:
            vis = frappe.get_list("Beneficiary", pluck="name", limit_page_length=0)
            can_read_b = frappe.has_permission("Beneficiary", "read", doc=b)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(a, vis)
        self.assertNotIn(b, vis)
        self.assertFalse(can_read_b)

    def test_national_id_encrypted_and_reveal_admin_only(self):
        from stochops_nonprofit.beneficiaries import reveal_national_id

        ben = beneficiary_as(self.ua, f"هوية {self.tok}", nid="1234567890")
        # لا يُخزَّن رقم الهوية كنص صريح في عمود الوثيقة
        self.assertNotEqual(frappe.db.get_value("Beneficiary", ben, "national_id"), "1234567890")
        # المدير يكشف القيمة الحقيقية
        frappe.set_user(self.ua)
        try:
            self.assertEqual(reveal_national_id(ben)["national_id"], "1234567890")
        finally:
            frappe.set_user("Administrator")
        # المطّلع التنفيذي لا يملك كشف الهوية
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                reveal_national_id(ben)
        finally:
            frappe.set_user("Administrator")

    def test_minimization_and_encrypted_field(self):
        meta = frappe.get_meta("Beneficiary")
        fields = {f.fieldname for f in meta.fields}
        forbidden = {"bank_account", "iban", "salary", "income_amount", "family_members", "religion"}
        self.assertFalse(fields & forbidden, "لا تُخزَّن حقول حسّاسة/مالية غير ضرورية")
        self.assertEqual(meta.get_field("national_id").fieldtype, "Password")

    def test_viewer_cannot_create_beneficiary(self):
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc({"doctype": "Beneficiary", "beneficiary_name": f"x {self.tok}"}).insert()
        finally:
            frappe.set_user("Administrator")

    def test_assistance_approval_note_and_authority(self):
        ben = beneficiary_as(self.ua, f"مستفيد {self.tok}")
        # المنسّق ينشئ طلباً
        frappe.set_user(self.coord)
        try:
            req = frappe.get_doc(
                {"doctype": "Assistance Request", "beneficiary": ben, "request_type": "مالية", "amount": 500}
            ).insert().name
            # المنسّق لا يملك البتّ (اعتماد)
            d = frappe.get_doc("Assistance Request", req)
            d.status = "معتمد"
            d.decision_note = "موافقة"
            with self.assertRaises(frappe.PermissionError):
                d.save()
        finally:
            frappe.set_user("Administrator")
        # المدير يعتمد لكن يلزم ملاحظة قرار
        frappe.set_user(self.ua)
        try:
            d = frappe.get_doc("Assistance Request", req)
            d.status = "معتمد"
            with self.assertRaises(frappe.ValidationError):  # ملاحظة القرار مطلوبة
                d.save()
            d.reload()
            d.status = "معتمد"
            d.decision_note = "مستوفٍ للشروط"
            d.save()
            d.reload()
            self.assertEqual(d.approved_by, self.ua)
            self.assertTrue(d.approved_on)
        finally:
            frappe.set_user("Administrator")

    def test_assistance_rejects_cross_charity_beneficiary(self):
        ben_a = beneficiary_as(self.ua, f"أ {self.tok}")
        doc = frappe.get_doc(
            {"doctype": "Assistance Request", "beneficiary": ben_a, "request_type": "مالية", "charity": self.cb}
        )
        with self.assertRaises(frappe.PermissionError):
            doc.insert()

    def test_amount_is_recording_only_non_negative(self):
        ben = beneficiary_as(self.ua, f"مبلغ {self.tok}")
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.ValidationError):  # المبلغ غير سالب
                frappe.get_doc(
                    {"doctype": "Assistance Request", "beneficiary": ben, "request_type": "مالية", "amount": -5}
                ).insert()
        finally:
            frappe.set_user("Administrator")

    def test_beneficiary_archive_reversible(self):
        """آلة حالات المستفيد: أرشفة قابلة للاستعادة (نشط ⇄ مؤرشف) بلا قفزة غير مشروعة."""
        ben = beneficiary_as(self.ua, f"أرشفة {self.tok}")
        frappe.set_user(self.ua)
        try:
            b = frappe.get_doc("Beneficiary", ben)
            b.status = "مؤرشف"
            b.save()
            b.reload()
            b.status = "نشط"
            b.save()
            self.assertEqual(frappe.db.get_value("Beneficiary", ben, "status"), "نشط")
        finally:
            frappe.set_user("Administrator")

    def test_assistance_payer_separation_configurable(self):
        """فصل الصرف عن الاعتماد (قابل للتفعيل): عند التفعيل لا يصرف المُعتمِد ما اعتمده،
        ويصرفه مدير آخر. (ملاحظة المالك #14؛ الضابط معطّل افتراضياً.)"""
        frappe.db.set_value("Charity", self.ca, "enforce_payer_separation", 1)
        admin2 = make_charity_user(f"n2a2_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        try:
            ben = beneficiary_as(self.ua, f"فصل {self.tok}")
            # المنشئ (منسّق) ≠ المُعتمِد
            frappe.set_user(self.coord)
            try:
                req = frappe.get_doc(
                    {"doctype": "Assistance Request", "beneficiary": ben, "request_type": "مالية", "amount": 200}
                ).insert().name
            finally:
                frappe.set_user("Administrator")
            # ua يعتمد → approved_by = ua
            frappe.set_user(self.ua)
            try:
                d = frappe.get_doc("Assistance Request", req)
                d.status = "معتمد"
                d.decision_note = "موافقة"
                d.save()
            finally:
                frappe.set_user("Administrator")
            # ua (المُعتمِد) يحاول الصرف → ممنوع عند تفعيل الفصل
            frappe.set_user(self.ua)
            try:
                d = frappe.get_doc("Assistance Request", req)
                d.status = "مصروف"
                with self.assertRaises(frappe.PermissionError):
                    d.save()
            finally:
                frappe.set_user("Administrator")
            # مدير آخر (غير المُعتمِد) يصرف → مسموح
            frappe.set_user(admin2)
            try:
                d = frappe.get_doc("Assistance Request", req)
                d.status = "مصروف"
                d.save()
            finally:
                frappe.set_user("Administrator")
            self.assertEqual(frappe.db.get_value("Assistance Request", req, "status"), "مصروف")
        finally:
            frappe.db.set_value("Charity", self.ca, "enforce_payer_separation", 0)
            if frappe.db.exists("User", admin2):
                frappe.delete_doc("User", admin2, force=1, ignore_permissions=True)
