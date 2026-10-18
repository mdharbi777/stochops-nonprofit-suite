import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today


def make_user(email, roles):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=1)
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": email.split("@")[0],
            "send_welcome_email": 0,
        }
    ).insert(ignore_permissions=True)
    user.add_roles(*roles)
    return user.name


class TestMeeting(FrappeTestCase):
    def setUp(self):
        self.committee = frappe.get_doc(
            {
                "doctype": "Committee",
                "committee_name": f"لجنة اجتماعات الاختبار {frappe.generate_hash(length=6)}",
                "committee_type": "لجنة",
                "coordinator": "Administrator",
            }
        ).insert().name

    def _meeting(self, status="Draft"):
        return frappe.get_doc(
            {
                "doctype": "Meeting",
                "committee": self.committee,
                "title": "اجتماع اختبار",
                "meeting_date": today(),
                "status": status,
            }
        )

    def test_approval_stamps_user(self):
        # U1: الاعتماد يملأ معتمِد/تاريخ خادمياً
        m = self._meeting("Approved").insert()
        self.assertTrue(m.approved_by)
        self.assertTrue(m.approved_on)

    def test_draft_has_no_approver(self):
        m = self._meeting("Draft").insert()
        self.assertFalse(m.approved_by)

    def test_approved_minutes_locked_for_non_admin(self):
        # U1-11: منع تعديل محضر معتمد إلا بصلاحية إدارية — مفروض على الخادم
        m = self._meeting("Approved").insert()
        user = make_user("mtg_coord@test.local", ["Committee Coordinator"])
        frappe.set_user(user)
        try:
            m2 = frappe.get_doc("Meeting", m.name)
            m2.title = "عنوان معدّل بعد الاعتماد"
            with self.assertRaises(frappe.PermissionError):
                m2.save()
        finally:
            frappe.set_user("Administrator")
