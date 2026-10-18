import frappe
from frappe.tests.utils import FrappeTestCase


class TestCommittee(FrappeTestCase):
    def test_requires_name_and_coordinator(self):
        # U1-02: منع الحفظ بدون الحقول الإلزامية.
        # اسم اللجنة مفتاح التسمية، فغيابه يرفع ValidationError (وهو الأعمّ لـ MandatoryError).
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({"doctype": "Committee", "committee_type": "لجنة"}).insert()

    def test_create_and_archive(self):
        c = frappe.get_doc(
            {
                "doctype": "Committee",
                "committee_name": f"لجنة اختبار الوحدات {frappe.generate_hash(length=6)}",
                "committee_type": "لجنة",
                "coordinator": "Administrator",
            }
        ).insert()
        self.assertEqual(c.status, "نشطة")
        c.status = "مؤرشفة"
        c.save()
        self.assertEqual(frappe.db.get_value("Committee", c.name, "status"), "مؤرشفة")
