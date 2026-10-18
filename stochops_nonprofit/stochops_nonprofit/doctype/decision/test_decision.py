import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


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


def make_committee(name):
    return frappe.get_doc(
        {
            "doctype": "Committee",
            "committee_name": name,
            "committee_type": "لجنة",
            "coordinator": "Administrator",
        }
    ).insert().name


def make_meeting(committee, title="اجتماع"):
    return frappe.get_doc(
        {
            "doctype": "Meeting",
            "committee": committee,
            "title": title,
            "meeting_date": today(),
            "status": "Approved",
        }
    ).insert().name


class TestDecision(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.committee = make_committee(f"لجنة قرارات الاختبار أ {self.tok}")
        self.meeting = make_meeting(self.committee, "اجتماع أ")

    def _decision(self, **kw):
        base = {
            "doctype": "Decision",
            "meeting": self.meeting,
            "title": "قرار اختبار",
            "decision_owner": "Administrator",
            "due_date": today(),
        }
        base.update(kw)
        return frappe.get_doc(base)

    def test_requires_owner(self):
        # U1-02
        with self.assertRaises(frappe.MandatoryError):
            self._decision(decision_owner=None).insert()

    def test_requires_due_date(self):
        with self.assertRaises(frappe.MandatoryError):
            self._decision(due_date=None).insert()

    def test_cannot_complete_without_note(self):
        # U1-03
        d = self._decision().insert()
        d.status = "Completed"
        with self.assertRaises(frappe.ValidationError):
            d.save()

    def test_complete_sets_date_and_logs_followup(self):
        d = self._decision().insert()
        d.status = "Completed"
        d.completion_note = "تم التنفيذ"
        d.save()
        self.assertTrue(d.completion_date)
        self.assertGreaterEqual(len(d.follow_ups), 1)
        self.assertTrue(d.last_followup)
        last = d.follow_ups[-1]
        self.assertEqual(last.new_status, "Completed")
        self.assertEqual(last.updated_by, "Administrator")

    def test_overdue_is_derived(self):
        # U1-04: التأخير محسوب لا مخزّن
        d = self._decision(due_date=add_days(today(), -2)).insert()
        self.assertTrue(d.is_overdue)
        d.status = "Completed"
        d.completion_note = "منجز"
        d.save()
        self.assertFalse(d.is_overdue)

    def test_committee_fetched_from_meeting(self):
        d = self._decision().insert()
        self.assertEqual(d.committee, self.committee)

    def test_committee_isolation_via_api(self):
        # U1-05/06/07: منسق لجنة أ لا يرى قرارات لجنة ب عبر get_list (API/export path)
        dec_a = self._decision().insert().name
        committee_b = make_committee(f"لجنة قرارات الاختبار ب {self.tok}")
        meeting_b = make_meeting(committee_b, "اجتماع ب")
        dec_b = frappe.get_doc(
            {
                "doctype": "Decision",
                "meeting": meeting_b,
                "title": "قرار لجنة ب",
                "decision_owner": "Administrator",
                "due_date": today(),
            }
        ).insert().name

        user = make_user("coord_a@test.local", ["Committee Coordinator"])
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Committee",
                "for_value": self.committee,
                "apply_to_all_doctypes": 1,
            }
        ).insert(ignore_permissions=True)

        frappe.set_user(user)
        try:
            visible = frappe.get_list("Decision", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")

        self.assertIn(dec_a, visible)
        self.assertNotIn(dec_b, visible)

    def test_executive_viewer_is_read_only(self):
        # U1-08: التنفيذي يقرأ ولا يعدّل
        d = self._decision().insert()
        user = make_user("viewer@test.local", ["Executive Viewer"])
        frappe.set_user(user)
        try:
            can_read = frappe.has_permission("Decision", "read", doc=d.name)
            can_write = frappe.has_permission("Decision", "write", doc=d.name)
            can_create = frappe.has_permission("Decision", "create")
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(can_read)
        self.assertFalse(can_write)
        self.assertFalse(can_create)
