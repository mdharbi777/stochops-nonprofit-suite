import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


def make_user(email, roles):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=1)
    user = frappe.get_doc(
        {"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
    ).insert(ignore_permissions=True)
    user.add_roles(*roles)
    return user.name


def make_initiative(title, **kw):
    base = {
        "doctype": "Initiative",
        "title": title,
        "initiative_owner": "Administrator",
        "objective": "هدف تجريبي",
        "start_date": today(),
        "end_date": add_days(today(), 30),
    }
    base.update(kw)
    return frappe.get_doc(base).insert()


class TestInitiative(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)

    def test_end_before_start_blocked(self):
        with self.assertRaises(frappe.ValidationError):
            make_initiative(f"مبادرة {self.tok}", end_date=add_days(today(), -5))

    def test_negative_budget_blocked(self):
        with self.assertRaises(frappe.ValidationError):
            make_initiative(f"مبادرة {self.tok}", planned_budget_sar=-100)

    def test_remaining_allows_overspend(self):
        ini = make_initiative(f"مبادرة {self.tok}", planned_budget_sar=1000, actual_spend_sar=1500)
        self.assertEqual(ini.remaining_budget, -500)

    def test_remaining_none_when_missing(self):
        ini = make_initiative(f"مبادرة {self.tok}", planned_budget_sar=1000)
        self.assertIsNone(ini.remaining_budget)

    def test_closing_requires_note(self):
        ini = make_initiative(f"مبادرة {self.tok}")
        ini.status = "Completed"
        with self.assertRaises(frappe.ValidationError):
            ini.save()

    def test_target_achievement(self):
        ini = make_initiative(f"مبادرة {self.tok}", target_count=50, actual_count=20)
        self.assertEqual(ini.target_achievement, 40.0)
        ini2 = make_initiative(f"مبادرة بلا مستهدف {self.tok}")
        self.assertIsNone(ini2.target_achievement)

    def test_task_completion_percentage(self):
        ini = make_initiative(f"مبادرة {self.tok}")
        self.assertIsNone(ini.task_completion)
        for i, status in enumerate(["Completed", "Open"]):
            t = frappe.get_doc(
                {"doctype": "Initiative Task", "initiative": ini.name, "title": f"م{i} {self.tok}",
                 "assigned_to": "Administrator", "due_date": today()}
            ).insert()
            if status == "Completed":
                t.status = "Completed"
                t.completion_note = "x"
                t.save()
        self.assertEqual(ini.task_completion, 50.0)

    def test_isolation_via_api(self):
        a = make_initiative(f"مبادرة أ {self.tok}").name
        b = make_initiative(f"مبادرة ب {self.tok}").name
        # ضمن نفس الجمعية: تقييد إضافي على مستوى المبادرة عبر User Permission
        ch = frappe.get_doc(
            {"doctype": "Charity", "charity_name": f"جمعية العزل {self.tok}"}
        ).insert(ignore_permissions=True).name
        for i in (a, b):
            frappe.db.set_value("Initiative", i, "charity", ch)
        user = make_user(f"pcoord_{self.tok}@test.local", ["Program Coordinator"])
        frappe.db.set_value("User", user, "charity", ch)
        frappe.get_doc(
            {"doctype": "User Permission", "user": user, "allow": "Initiative",
             "for_value": a, "apply_to_all_doctypes": 1}
        ).insert(ignore_permissions=True)
        frappe.set_user(user)
        try:
            visible = frappe.get_list("Initiative", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(a, visible)
        self.assertNotIn(b, visible)

    def test_executive_viewer_read_only(self):
        ini = make_initiative(f"مبادرة {self.tok}")
        user = make_user(f"iviewer_{self.tok}@test.local", ["Executive Viewer"])
        frappe.set_user(user)
        try:
            can_read = frappe.has_permission("Initiative", "read", doc=ini.name)
            can_write = frappe.has_permission("Initiative", "write", doc=ini.name)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(can_read)
        self.assertFalse(can_write)
