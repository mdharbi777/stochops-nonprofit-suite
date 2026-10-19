import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from stochops_nonprofit.dashboard_metrics import compute


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

        # ضمن نفس الجمعية: تقييد إضافي على مستوى اللجنة عبر User Permission
        ch = frappe.get_doc(
            {"doctype": "Charity", "charity_name": f"جمعية العزل {self.tok}"}
        ).insert(ignore_permissions=True).name
        for d in (dec_a, dec_b):
            frappe.db.set_value("Decision", d, "charity", ch)
        user = make_user("coord_a@test.local", ["Committee Coordinator"])
        frappe.db.set_value("User", user, "charity", ch)
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


class TestDashboardMetrics(FrappeTestCase):
    """الوحدة 3: المؤشرات — تطابق رقمي + حدود الفترة + الصلاحيات."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.committee = make_committee(f"لجنة لوحة {self.tok}")
        self.meeting = make_meeting(self.committee, "اجتماع لوحة")

    def _dec(self, status, due, note=None):
        d = frappe.get_doc(
            {"doctype": "Decision", "meeting": self.meeting, "title": f"قرار لوحة {self.tok}",
             "decision_owner": "Administrator", "due_date": due}
        ).insert()
        if status != "Open":
            d.status = status
            if status == "Completed":
                d.completion_note = note or "تم"
            d.save()
        return d

    def test_decision_counts_delta(self):
        base = compute()
        self._dec("Open", add_days(today(), -3))        # overdue
        self._dec("In Progress", add_days(today(), 5))
        self._dec("Cancelled", today())                 # excluded
        self._dec("Completed", add_days(today(), -1), "ok")  # completed today (in current month)
        after = compute()
        self.assertEqual(after["decisions_non_cancelled"] - base["decisions_non_cancelled"], 3)
        self.assertEqual(after["decisions_open_inprogress"] - base["decisions_open_inprogress"], 2)
        self.assertEqual(after["decisions_overdue"] - base["decisions_overdue"], 1)
        self.assertEqual(after["decisions_completed_in_period"] - base["decisions_completed_in_period"], 1)

    def test_budget_sums_exclude_missing(self):
        base = compute()
        frappe.get_doc(
            {"doctype": "Initiative", "title": f"ب {self.tok}", "initiative_owner": "Administrator",
             "objective": "x", "start_date": today(), "end_date": add_days(today(), 10),
             "planned_budget_sar": 1000, "actual_spend_sar": 400}
        ).insert()
        frappe.get_doc(
            {"doctype": "Initiative", "title": f"ب بلا ميزانية {self.tok}", "initiative_owner": "Administrator",
             "objective": "x", "start_date": today(), "end_date": add_days(today(), 10)}
        ).insert()
        after = compute()
        self.assertEqual(after["total_planned_budget"] - base["total_planned_budget"], 1000)
        self.assertEqual(after["total_actual_spend"] - base["total_actual_spend"], 400)
        self.assertEqual(after["initiatives_without_budget"] - base["initiatives_without_budget"], 1)

    def test_completed_outside_period_excluded(self):
        base = compute("2020-01-01", "2020-01-31")
        self._dec("Completed", today(), "ok")
        after = compute("2020-01-01", "2020-01-31")
        self.assertEqual(after["decisions_completed_in_period"], base["decisions_completed_in_period"])

    def test_permission_scope_zero_for_other_committee(self):
        self._dec("Open", today())
        user = make_user(f"dash_{self.tok}@test.local", ["Committee Coordinator"])
        other = make_committee(f"لجنة أخرى {self.tok}")
        frappe.get_doc(
            {"doctype": "User Permission", "user": user, "allow": "Committee",
             "for_value": other, "apply_to_all_doctypes": 1}
        ).insert(ignore_permissions=True)
        frappe.set_user(user)
        try:
            metrics = compute()
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(metrics["decisions_non_cancelled"], 0)


class TestNotifications(FrappeTestCase):
    """الإشعارات موجودة ومفعّلة: داخل التطبيق (System Notification) + تنبيهات بريد
    مختصرة للطاقم عبر Resend (P6). لا قنوات SMS/واتساب مدفوعة."""

    def test_notifications_present_and_enabled(self):
        from stochops_nonprofit.setup.notifications import NOTIFICATIONS

        for n in NOTIFICATIONS:
            exists = frappe.db.exists(
                "Notification",
                {
                    "subject": n["subject"],
                    "document_type": n["document_type"],
                    "channel": n.get("channel", "System Notification"),
                    "enabled": 1,
                },
            )
            self.assertTrue(exists, f"إشعار مفقود/معطّل: {n['subject']}")

    def test_no_sms_channels(self):
        # البريد مسموح (Resend، محتوى أدنى للطاقم)؛ لا SMS/واتساب مدفوعة
        paid = frappe.get_all(
            "Notification",
            filters={"channel": ["in", ["SMS", "WhatsApp"]], "document_type": ["like", "%"]},
            pluck="name",
        )
        self.assertEqual(paid, [])

    def test_staff_email_alerts_minimal_no_pii(self):
        # تنبيهات البريد للطاقم لا تحتوي حقولاً شخصية (اسم/هوية/مبلغ) في المتن
        from stochops_nonprofit.setup.notifications import NOTIFICATIONS

        forbidden = ["beneficiary_name", "national_id", "donor_name", "full_name", "amount", "title"]
        email_specs = [n for n in NOTIFICATIONS if n.get("channel") == "Email"]
        self.assertTrue(email_specs)
        for n in email_specs:
            body = n["message"] + n["subject"]
            for token in forbidden:
                self.assertNotIn(token, body, f"تسريب محتمل في تنبيه البريد: {n['subject']}")
