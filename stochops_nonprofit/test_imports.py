import json

import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.imports import MAX_ROWS, bulk_import, get_import_schema
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


class TestBulkImport(FrappeTestCase):
    """الاستيراد الجماعي: عزل تلقائي لكل صفّ + تحقّق مستقلّ + قائمة حقول بيضاء."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية أ {self.tok}")
        self.cb = make_charity(f"جمعية ب {self.tok}")
        self.ua = make_charity_user(f"impa_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"impb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"impv_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        frappe.db.commit()  # يُثبِّت بيانات التهيئة قبل أي تراجع صفٍّ داخل الاستيراد

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Beneficiary", "Donor"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub, self.viewer):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def _as(self, user, fn, *a, **k):
        frappe.set_user(user)
        try:
            return fn(*a, **k)
        finally:
            frappe.set_user("Administrator")

    def test_schema_requires_role(self):
        s = self._as(self.ua, get_import_schema, "Beneficiary")
        self.assertEqual(s["doctype"], "Beneficiary")
        self.assertTrue(any(f["field"] == "beneficiary_name" and f["required"] for f in s["fields"]))
        with self.assertRaises(frappe.PermissionError):
            self._as(self.viewer, get_import_schema, "Beneficiary")

    def test_unsupported_doctype_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self._as(self.ua, get_import_schema, "Committee")

    def test_import_inserts_and_auto_scopes_charity(self):
        rows = [
            {"beneficiary_name": f"مستفيد ١ {self.tok}", "phone": "0500000001", "gender": "ذكر"},
            {"beneficiary_name": f"مستفيد ٢ {self.tok}", "family_members_count": "3"},
        ]
        res = self._as(self.ua, bulk_import, "Beneficiary", json.dumps(rows))
        self.assertEqual(res["inserted"], 2)
        self.assertEqual(res["failed"], [])
        names = frappe.get_all("Beneficiary", filters={"charity": self.ca}, pluck="name")
        self.assertEqual(len(names), 2)
        # عزل: مدير الجمعية ب لا يرى مستفيدي أ
        visible_b = self._as(self.ub, lambda: frappe.get_list("Beneficiary", pluck="name", limit_page_length=0))
        self.assertFalse(set(names) & set(visible_b))

    def test_whitelist_ignores_injected_fields(self):
        # محاولة حقن جمعية أخرى وحالة غير مسموحة عبر الملف → تُتجاهَل
        rows = [{"beneficiary_name": f"حقن {self.tok}", "charity": self.cb, "status": "مؤرشف",
                 "case_worker": "x@y.z"}]
        res = self._as(self.ua, bulk_import, "Beneficiary", json.dumps(rows))
        self.assertEqual(res["inserted"], 1)
        name = frappe.get_all("Beneficiary", filters={"charity": self.ca}, pluck="name")[0]
        self.assertEqual(frappe.db.get_value("Beneficiary", name, "charity"), self.ca)  # ليست cb

    def test_per_row_validation_does_not_block_others(self):
        rows = [
            {"beneficiary_name": f"صالح {self.tok}"},
            {"beneficiary_name": "", "phone": "05"},                 # الاسم مطلوب
            {"beneficiary_name": f"هوية {self.tok}", "national_id": "12"},  # هوية غير صحيحة
            {"beneficiary_name": f"فئة {self.tok}", "social_category": "خطأ"},  # خيار غير مقبول
        ]
        res = self._as(self.ua, bulk_import, "Beneficiary", json.dumps(rows))
        self.assertEqual(res["inserted"], 1)
        self.assertEqual(len(res["failed"]), 3)
        self.assertEqual(sorted(f["row"] for f in res["failed"]), [2, 3, 4])
        self.assertEqual(len(frappe.get_all("Beneficiary", filters={"charity": self.ca})), 1)

    def test_int_field_clamped_non_negative(self):
        rows = [{"beneficiary_name": f"سالب {self.tok}", "family_members_count": "-5"}]
        self._as(self.ua, bulk_import, "Beneficiary", json.dumps(rows))
        name = frappe.get_all("Beneficiary", filters={"charity": self.ca}, pluck="name")[0]
        self.assertEqual(frappe.db.get_value("Beneficiary", name, "family_members_count"), 0)

    def test_donor_import_with_options(self):
        rows = [
            {"donor_name": f"متبرع {self.tok}", "donor_type": "فرد", "email": "d@x.local"},
            {"donor_name": f"سيئ {self.tok}", "donor_type": "غير-موجود"},  # نوع غير مقبول
        ]
        res = self._as(self.ua, bulk_import, "Donor", json.dumps(rows))
        self.assertEqual(res["inserted"], 1)
        self.assertEqual(len(res["failed"]), 1)

    def test_empty_and_oversize_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self._as(self.ua, bulk_import, "Beneficiary", json.dumps([]))
        big = [{"beneficiary_name": f"n{i}"} for i in range(MAX_ROWS + 1)]
        with self.assertRaises(frappe.ValidationError):
            self._as(self.ua, bulk_import, "Beneficiary", json.dumps(big))

    def test_non_role_user_cannot_import(self):
        with self.assertRaises(frappe.PermissionError):
            self._as(self.viewer, bulk_import, "Beneficiary",
                     json.dumps([{"beneficiary_name": "x"}]))
