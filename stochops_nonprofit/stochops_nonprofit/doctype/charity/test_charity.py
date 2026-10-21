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


def decision_as(user, committee, owner, title, due):
    frappe.set_user(user)
    try:
        mtg = frappe.get_doc(
            {"doctype": "Meeting", "committee": committee, "title": "اجتماع", "meeting_date": frappe.utils.today()}
        ).insert().name
        return frappe.get_doc(
            {"doctype": "Decision", "meeting": mtg, "title": title,
             "decision_owner": owner, "due_date": due, "status": "Open"}
        ).insert().name
    finally:
        frappe.set_user("Administrator")


def task_as(user, owner, title, due):
    frappe.set_user(user)
    try:
        ini = frappe.get_doc(
            {"doctype": "Initiative", "title": "مبادرة", "initiative_owner": owner, "objective": "هدف",
             "start_date": frappe.utils.today(), "end_date": frappe.utils.add_days(frappe.utils.today(), 30),
             "status": "Active"}
        ).insert().name
        return frappe.get_doc(
            {"doctype": "Initiative Task", "initiative": ini, "title": title,
             "assigned_to": owner, "due_date": due, "status": "Open"}
        ).insert().name
    finally:
        frappe.set_user("Administrator")


class TestUIIntegration(FrappeTestCase):
    """تكامل الواجهة: «المهام المطلوبة مني» + إعدادات هوية الجمعية (معزولة، للمدير فقط)."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية أ {self.tok}")
        self.cb = make_charity(f"جمعية ب {self.tok}")
        self.ua = make_charity_user(f"uia_{self.tok}@test.local", self.ca, ["Nonprofit Admin"])
        self.ub = make_charity_user(f"uib_{self.tok}@test.local", self.cb, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"uiv_{self.tok}@test.local", self.ca, ["Executive Viewer"])
        self.coma = committee_as(self.ua, f"لجنة أ {self.tok}")
        self.comb = committee_as(self.ub, f"لجنة ب {self.tok}")

    def tearDown(self):
        frappe.set_user("Administrator")
        for dt in ("Initiative Task", "Initiative", "Decision", "Meeting", "Committee"):
            for n in frappe.get_all(dt, filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
                frappe.delete_doc(dt, n, force=1, ignore_permissions=True)
        for e in (self.ua, self.ub, self.viewer):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_my_work_returns_my_open_items(self):
        from stochops_nonprofit.dashboard_metrics import get_my_work

        dec = decision_as(self.ua, self.coma, self.ua, f"قراري {self.tok}", frappe.utils.today())
        tsk = task_as(self.ua, self.ua, f"مهمتي {self.tok}", frappe.utils.today())
        frappe.set_user(self.ua)
        try:
            w = get_my_work()
        finally:
            frappe.set_user("Administrator")
        self.assertIn(dec, [d["name"] for d in w["decisions"]])
        self.assertIn(tsk, [t["name"] for t in w["tasks"]])

    def test_my_work_excludes_closed_and_others(self):
        from stochops_nonprofit.dashboard_metrics import get_my_work

        # قرار لي لكنه مكتمل (يُستبعد) + قرار لمدير آخر (معزول)
        done = decision_as(self.ua, self.coma, self.ua, f"منجز {self.tok}", frappe.utils.today())
        frappe.db.set_value("Decision", done, "status", "Completed")
        other = decision_as(self.ub, self.comb, self.ub, f"قرار ب {self.tok}", frappe.utils.today())
        frappe.set_user(self.ua)
        try:
            names = [d["name"] for d in get_my_work()["decisions"]]
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(done, names)
        self.assertNotIn(other, names)

    def test_charity_settings_admin_only(self):
        from stochops_nonprofit.accounts import get_charity_settings

        frappe.set_user(self.ua)
        try:
            s = get_charity_settings()
            self.assertEqual(s["charity_name"], self.ca)
        finally:
            frappe.set_user("Administrator")
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                get_charity_settings()
        finally:
            frappe.set_user("Administrator")

    def test_update_charity_settings_scoped_and_validated(self):
        from stochops_nonprofit.accounts import update_charity_settings

        frappe.set_user(self.ua)
        try:
            update_charity_settings(registration_number="REG-123", contact_email=f"info_{self.tok}@ca.local")
            with self.assertRaises(frappe.ValidationError):  # بريد غير صالح
                update_charity_settings(contact_email="not-an-email")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Charity", self.ca, "registration_number"), "REG-123")
        self.assertEqual(frappe.db.get_value("Charity", self.cb, "registration_number"), None)
        # غير المدير لا يُحدّث
        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                update_charity_settings(registration_number="HACK")
        finally:
            frappe.set_user("Administrator")


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
        # القبول انتقائي (P3): التسجيل الذاتي متوقّف — نهيّئ الجمعية والمدير مباشرة
        # لاختبار إدارة الحسابات التي تلي التفعيل.
        charity = make_charity(f"جمعية تسجيل {self.tok}{suffix}")
        email = f"regadmin_{self.tok}{suffix}@reg.local"
        admin = make_charity_user(email, charity, ["Nonprofit Admin"])
        self.created_charities.append(charity)
        self.created_users.append(admin)
        return {"charity": charity, "admin": admin}

    def test_self_signup_disabled(self):
        from stochops_nonprofit.signup import register_charity

        with self.assertRaises(frappe.PermissionError):
            register_charity(f"جمعية {self.tok}", "مدير", f"x_{self.tok}@reg.local", "password123")

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


class TestAccountInvites(FrappeTestCase):
    """وحدة P2: الحسابات بدعوات بريدية (لا كلمة مرور في البريد) + استعادة غير مُفشية."""

    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.ca = make_charity(f"جمعية دعوة {self.tok}")
        self.admin = make_charity_user(f"inv_admin_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.viewer = make_charity_user(f"inv_view_{self.tok}@t.local", self.ca, ["Executive Viewer"])
        self.created = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for e in self.created + [self.admin, self.viewer]:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        if frappe.db.exists("Charity", self.ca):
            frappe.delete_doc("Charity", self.ca, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_invite_creates_disabled_then_accept_enables(self):
        from stochops_nonprofit.accounts import accept_invite, invite_account

        email = f"invitee_{self.tok}@t.local"
        frappe.set_user(self.admin)
        try:
            res = invite_account("عضو مدعو", email, "Program Coordinator")
        finally:
            frappe.set_user("Administrator")
        self.created.append(res["account"])
        self.assertTrue(res.get("invited"))
        # أُنشئ معطّلاً بلا تفعيل حتى يقبل الدعوة
        self.assertEqual(frappe.db.get_value("User", email, "enabled"), 0)
        self.assertIn("Program Coordinator", frappe.get_roles(email))
        self.assertEqual(frappe.db.get_value("User", email, "charity"), self.ca)
        # تُسجَّل كتغيير صلاحية
        self.assertTrue(frappe.get_all("Sensitive Access Log",
                        filters={"event_type": "permission_change", "reference_name": email}, limit=1))
        # قبول الدعوة يفعّل الحساب
        token = res["invite_url"].split("token=")[1]
        accept_invite(token, "Invitee#2026")
        self.assertEqual(frappe.db.get_value("User", email, "enabled"), 1)

    def test_accept_invalid_token_rejected(self):
        from stochops_nonprofit.accounts import accept_invite

        with self.assertRaises(frappe.ValidationError):
            accept_invite("not-a-valid-token", "Whatever#2026")

    def test_non_admin_cannot_invite(self):
        from stochops_nonprofit.accounts import invite_account

        frappe.set_user(self.viewer)
        try:
            with self.assertRaises(frappe.PermissionError):
                invite_account("x", f"x_{self.tok}@t.local", "Executive Viewer")
        finally:
            frappe.set_user("Administrator")

    def test_password_reset_does_not_disclose(self):
        from stochops_nonprofit.accounts import request_password_reset

        res = request_password_reset(f"nobody_{self.tok}@nowhere.local")  # بريد غير موجود
        self.assertTrue(res["ok"])  # رسالة عامة دون كشف وجود الحساب
