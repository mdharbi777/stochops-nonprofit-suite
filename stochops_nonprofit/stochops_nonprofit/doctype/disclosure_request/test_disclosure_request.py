import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def _ben(charity, name, category):
    frappe.set_user("Administrator")
    doc = frappe.get_doc(
        {"doctype": "Beneficiary", "beneficiary_name": name, "social_category": category, "charity": charity}
    ).insert(ignore_permissions=True)
    return doc.name


class TestDisclosureReports(FrappeTestCase):
    """وحدة P4: الإفصاح (deny-by-default) + سجل القوالب + تقرير مُجهّل بإخفاء الخلايا الصغيرة."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.thr_prev = frappe.db.get_single_value("Privacy Configuration", "small_cell_threshold")
        self.ca = make_charity(f"جمعية خ4أ {self.tok}")
        self.cb = make_charity(f"جمعية خ4ب {self.tok}")
        self.admin = make_charity_user(f"p4_adm_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.adminb = make_charity_user(f"p4_admb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("Privacy Configuration", "small_cell_threshold", self.thr_prev or 5)
        for dt in ("Disclosure Request", "Beneficiary"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.admin, self.adminb):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_disclosure_deny_default_and_approval_logged(self):
        frappe.set_user(self.admin)
        try:
            d = frappe.get_doc(
                {"doctype": "Disclosure Request", "purpose": "تقرير", "recipient": f"جهة {self.tok}"}
            ).insert()
            self.assertEqual(d.status, "مطلوب")  # deny-by-default
            d.status = "معتمد"
            with self.assertRaises(frappe.ValidationError):  # يلزم ملاحظة قرار
                d.save()
            d.reload()
            d.status = "معتمد"
            d.decision_note = "مصرّح بأساس نظامي"
            d.save()
            d.reload()
            self.assertEqual(d.approved_by, self.admin)
        finally:
            frappe.set_user("Administrator")
        # الاعتماد يُسجَّل كحدث مشاركة
        self.assertTrue(frappe.get_all("Sensitive Access Log",
                        filters={"event_type": "share", "reference_name": d.name}, limit=1))

    def test_disclosure_isolation(self):
        frappe.set_user(self.admin)
        try:
            a = frappe.get_doc({"doctype": "Disclosure Request", "purpose": "x", "recipient": f"ر {self.tok}"}).insert().name
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.adminb)
        try:
            vis = frappe.get_list("Disclosure Request", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(a, vis)

    def test_report_template_default_and_platform_only(self):
        # القوالب المزروعة تبدأ بحالة تحتاج تحقّقاً
        seeded = frappe.get_all("Report Template Registry", filters={"status": "TEMPLATE_REVALIDATION_REQUIRED"}, limit=1)
        self.assertTrue(seeded)
        # مدير الجمعية لا يملك إنشاء قالب (مشغّل المنصّة فقط)
        frappe.set_user(self.admin)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc({"doctype": "Report Template Registry", "template_name": f"قالب {self.tok}"}).insert()
        finally:
            frappe.set_user("Administrator")

    def test_beneficiary_categories_small_cell_suppression(self):
        frappe.db.set_single_value("Privacy Configuration", "small_cell_threshold", 3)
        _ben(self.ca, f"أ {self.tok}", "أيتام")
        _ben(self.ca, f"ب {self.tok}", "أيتام")  # عدد 2 < 3 → يُحجب
        run = frappe.get_attr(
            "stochops_nonprofit.stochops_nonprofit.report.beneficiary_categories.beneficiary_categories.execute"
        )
        frappe.set_user(self.admin)
        try:
            _, data = run()
            row = next(r for r in data if r["category"] == "أيتام")
            self.assertIn("محجوب", row["count_display"])  # خلية صغيرة محجوبة
            _ben(self.ca, f"ج {self.tok}", "أيتام")  # صار 3 ≥ 3
            _, data2 = run()
            row2 = next(r for r in data2 if r["category"] == "أيتام")
            self.assertEqual(row2["count_display"], "3")
        finally:
            frappe.set_user("Administrator")
