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
