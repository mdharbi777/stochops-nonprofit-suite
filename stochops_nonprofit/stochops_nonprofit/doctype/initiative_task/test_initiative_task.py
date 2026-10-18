import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today


class TestInitiativeTask(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.initiative = frappe.get_doc(
            {
                "doctype": "Initiative",
                "title": f"مبادرة مهام {self.tok}",
                "initiative_owner": "Administrator",
                "objective": "x",
                "start_date": today(),
                "end_date": add_days(today(), 10),
            }
        ).insert().name

    def _task(self, **kw):
        base = {
            "doctype": "Initiative Task",
            "initiative": self.initiative,
            "title": f"مهمة {self.tok}",
            "assigned_to": "Administrator",
            "due_date": today(),
        }
        base.update(kw)
        return frappe.get_doc(base)

    def test_requires_fields(self):
        with self.assertRaises(frappe.MandatoryError):
            self._task(assigned_to=None).insert()

    def test_completion_requires_note(self):
        t = self._task().insert()
        t.status = "Completed"
        with self.assertRaises(frappe.ValidationError):
            t.save()

    def test_completed_on_set_server_side(self):
        t = self._task().insert()
        t.status = "Completed"
        t.completion_note = "تم"
        t.save()
        self.assertTrue(t.completed_on)
