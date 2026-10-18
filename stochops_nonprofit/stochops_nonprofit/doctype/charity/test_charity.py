import frappe
from frappe.tests.utils import FrappeTestCase


def make_charity(name):
    return frappe.get_doc(
        {"doctype": "Charity", "charity_name": name}
    ).insert(ignore_permissions=True).name


def make_charity_user(email, charity, roles):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=1)
    user = frappe.get_doc(
        {"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
    ).insert(ignore_permissions=True)
    user.add_roles(*roles)
    frappe.db.set_value("User", email, "charity", charity)
    return email


def committee_as(user, name):
    frappe.set_user(user)
    try:
        return frappe.get_doc(
            {"doctype": "Committee", "committee_name": name, "committee_type": "لجنة", "coordinator": user}
        ).insert().name
    finally:
        frappe.set_user("Administrator")


class TestMultiTenancy(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية أ {self.tok}")
        self.cb = make_charity(f"جمعية ب {self.tok}")
        self.ua = make_charity_user(f"a_{self.tok}@test.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"b_{self.tok}@test.local", self.cb, ["Nonprofit Admin"])

    def test_set_charity_auto_assigns_from_user(self):
        name = committee_as(self.ua, f"لجنة أ {self.tok}")
        self.assertEqual(frappe.db.get_value("Committee", name, "charity"), self.ca)

    def test_list_isolation_between_charities(self):
        a = committee_as(self.ua, f"لجنة أ {self.tok}")
        b = committee_as(self.ub, f"لجنة ب {self.tok}")
        frappe.set_user(self.ua)
        try:
            visible = frappe.get_list("Committee", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(a, visible)
        self.assertNotIn(b, visible)

    def test_record_isolation_has_permission(self):
        b = committee_as(self.ub, f"لجنة ب {self.tok}")
        frappe.set_user(self.ua)
        try:
            can_read = frappe.has_permission("Committee", "read", doc=b)
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(can_read)

    def test_user_without_charity_sees_nothing(self):
        committee_as(self.ua, f"لجنة أ {self.tok}")
        orphan = make_charity_user(f"orphan_{self.tok}@test.local", None, ["Nonprofit Admin"])
        frappe.set_user(orphan)
        try:
            visible = frappe.get_list("Committee", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(visible, [])

    def test_charity_entity_isolation(self):
        # جمعية أ ترى سجلّ جمعيتها فقط من كيان Charity
        frappe.set_user(self.ua)
        try:
            visible = frappe.get_list("Charity", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertIn(self.ca, visible)
        self.assertNotIn(self.cb, visible)

    def test_administrator_sees_all(self):
        a = committee_as(self.ua, f"لجنة أ {self.tok}")
        b = committee_as(self.ub, f"لجنة ب {self.tok}")
        visible = frappe.get_list("Committee", pluck="name", limit_page_length=0)
        self.assertIn(a, visible)
        self.assertIn(b, visible)


class TestSignupAccounts(FrappeTestCase):
    """التسجيل الذاتي + حد 5 حسابات + تقييد الأدوار والجمعية."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.created_users = []
        self.created_charities = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for e in self.created_users:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in self.created_charities:
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def _register(self, suffix=""):
        from stochops_nonprofit.signup import register_charity

        res = register_charity(
            f"جمعية تسجيل {self.tok}{suffix}",
            "مدير الجمعية",
            f"regadmin_{self.tok}{suffix}@reg.local",
            "password123",
        )
        self.created_charities.append(res["charity"])
        self.created_users.append(res["admin"])
        return res

    def test_register_creates_charity_and_admin(self):
        res = self._register()
        self.assertTrue(frappe.db.exists("Charity", res["charity"]))
        self.assertEqual(frappe.db.get_value("User", res["admin"], "charity"), res["charity"])
        self.assertIn("Nonprofit Admin", frappe.get_roles(res["admin"]))

    def test_register_rejects_duplicate_and_bad_input(self):
        self._register()
        from stochops_nonprofit.signup import register_charity

        with self.assertRaises(frappe.ValidationError):  # duplicate charity name
            register_charity(f"جمعية تسجيل {self.tok}", "x", f"other_{self.tok}@reg.local", "password123")
        with self.assertRaises(frappe.ValidationError):  # existing email
            register_charity(f"أخرى {self.tok}", "x", f"regadmin_{self.tok}@reg.local", "password123")
        with self.assertRaises(frappe.ValidationError):  # short password
            register_charity(f"قصيرة {self.tok}", "x", f"short_{self.tok}@reg.local", "123")

    def test_five_account_limit_and_scoping(self):
        from stochops_nonprofit.accounts import create_account

        res = self._register()
        frappe.set_user(res["admin"])
        try:
            for i in range(4):  # admin(1) + 4 = 5 (الحد)
                r = create_account(f"عضو {i}", f"m{i}_{self.tok}@reg.local", "Committee Coordinator", "password123")
                self.created_users.append(r["account"])
                self.assertEqual(frappe.db.get_value("User", r["account"], "charity"), res["charity"])
            with self.assertRaises(frappe.ValidationError):  # السادس يتجاوز الحد
                create_account("زائد", f"over_{self.tok}@reg.local", "Executive Viewer", "password123")
        finally:
            frappe.set_user("Administrator")

    def test_disallowed_role_rejected(self):
        from stochops_nonprofit.accounts import create_account

        res = self._register()
        frappe.set_user(res["admin"])
        try:
            with self.assertRaises(frappe.ValidationError):
                create_account("x", f"baddrole_{self.tok}@reg.local", "Stochops Admin", "password123")
        finally:
            frappe.set_user("Administrator")

    def test_non_admin_cannot_create_account(self):
        from stochops_nonprofit.accounts import create_account

        res = self._register()
        frappe.set_user(res["admin"])
        try:
            r = create_account("مشاهد", f"viewer_{self.tok}@reg.local", "Executive Viewer", "password123")
            self.created_users.append(r["account"])
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(f"viewer_{self.tok}@reg.local")
        try:
            with self.assertRaises(frappe.PermissionError):
                create_account("y", f"y_{self.tok}@reg.local", "Executive Viewer", "password123")
        finally:
            frappe.set_user("Administrator")
