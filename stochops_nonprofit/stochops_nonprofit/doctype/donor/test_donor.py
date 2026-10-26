import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def donor_as(user, name):
    frappe.set_user(user)
    try:
        return frappe.get_doc({"doctype": "Donor", "donor_name": name}).insert().name
    finally:
        frappe.set_user("Administrator")


class TestDonorsGrants(FrappeTestCase):
    """وحدة N3: المتبرعون/المانحون/المنح — عزل، تسجيل فقط بلا بوابة دفع، قيود القيم."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية ن3أ {self.tok}")
        self.cb = make_charity(f"جمعية ن3ب {self.tok}")
        self.ua = make_charity_user(f"n3a_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"n3b_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"n3v_{self.tok}@t.local", self.ca, ["Executive Viewer"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Grant", "Donation", "Donor"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub, self.viewer):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_donor_set_charity_and_isolation(self):
        a = donor_as(self.ua, f"متبرّع أ {self.tok}")
        b = donor_as(self.ub, f"متبرّع ب {self.tok}")
        self.assertEqual(frappe.db.get_value("Donor", a, "charity"), self.ca)
        frappe.set_user(self.ua)
        try:
            vis = frappe.get_list("Donor", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(a, vis)
        self.assertNotIn(b, vis)

    def test_donation_non_negative_and_recording_only(self):
        donor = donor_as(self.ua, f"متبرّع {self.tok}")
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.ValidationError):
                frappe.get_doc(
                    {"doctype": "Donation", "donor": donor, "donation_date": today(), "amount": -10}
                ).insert()
            ok = frappe.get_doc(
                {"doctype": "Donation", "donor": donor, "donation_date": today(), "amount": 500, "status": "مستلم"}
            ).insert()
            self.assertEqual(frappe.db.get_value("Donation", ok.name, "charity"), self.ca)
        finally:
            frappe.set_user("Administrator")
        # لا حقول معالجة دفع/بوابة في النموذج (تسجيل فقط)
        fields = {f.fieldname for f in frappe.get_meta("Donation").fields}
        self.assertFalse(fields & {"gateway", "payment_id", "card_number", "transaction_id", "payment_token"})

    def test_donation_rejects_cross_charity_donor(self):
        donor_a = donor_as(self.ua, f"متبرّع أ {self.tok}")
        doc = frappe.get_doc(
            {"doctype": "Donation", "donor": donor_a, "donation_date": today(), "amount": 100, "charity": self.cb}
        )
        with self.assertRaises(frappe.PermissionError):
            doc.insert()

    def test_grant_dates_and_non_negative(self):
        frappe.set_user(self.ua)
        try:
            with self.assertRaises(frappe.ValidationError):  # النهاية قبل البداية
                frappe.get_doc(
                    {"doctype": "Grant", "grant_title": f"م {self.tok}", "grantor_name": "جهة",
                     "start_date": today(), "end_date": add_days(today(), -5)}
                ).insert()
            with self.assertRaises(frappe.ValidationError):  # قيمة سالبة
                frappe.get_doc(
                    {"doctype": "Grant", "grant_title": f"م2 {self.tok}", "grantor_name": "جهة", "amount": -1}
                ).insert()
            g = frappe.get_doc(
                {"doctype": "Grant", "grant_title": f"منحة {self.tok}", "grantor_name": "جهة مانحة",
                 "status": "معتمدة", "amount": 50000, "amount_received": 20000}
            ).insert()
            self.assertEqual(frappe.db.get_value("Grant", g.name, "charity"), self.ca)
        finally:
            frappe.set_user("Administrator")

    def test_viewer_cannot_create_donor(self):
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc({"doctype": "Donor", "donor_name": f"x {self.tok}"}).insert()
        finally:
            frappe.set_user("Administrator")

    def test_grant_isolation(self):
        frappe.set_user(self.ua)
        try:
            ga = frappe.get_doc({"doctype": "Grant", "grant_title": f"غ أ {self.tok}", "grantor_name": "ج"}).insert().name
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.ub)
        try:
            vis = frappe.get_list("Grant", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(ga, vis)

    def test_grant_terminal_state_frozen(self):
        """آلة حالات المنحة: المرفوضة (نهائية) لا تُعاد إلى معتمدة (كمدير جمعية)."""
        frappe.set_user(self.ua)
        try:
            g = frappe.get_doc(
                {"doctype": "Grant", "grant_title": f"نهائية {self.tok}", "grantor_name": "جهة"}
            ).insert()
            g.status = "مرفوضة"  # مقترحة → مرفوضة مسموح
            g.save()
            g.reload()
            g.status = "معتمدة"  # من حالة نهائية — ممنوع
            with self.assertRaises(frappe.PermissionError):
                g.save()
        finally:
            frappe.set_user("Administrator")

    def test_grant_break_glass_for_super(self):
        """كسر الزجاج: مشغّل المنصّة (Administrator = System Manager) يتجاوز آلة الحالات."""
        g = frappe.get_doc(
            {"doctype": "Grant", "grant_title": f"كسر {self.tok}", "grantor_name": "جهة", "charity": self.ca}
        ).insert(ignore_permissions=True)
        g.status = "مرفوضة"
        g.save()
        g.reload()
        g.status = "معتمدة"  # قفزة ممنوعة لغير المشغّل — تمرّ للمشغّل
        g.save()
        self.assertEqual(frappe.db.get_value("Grant", g.name, "status"), "معتمدة")
