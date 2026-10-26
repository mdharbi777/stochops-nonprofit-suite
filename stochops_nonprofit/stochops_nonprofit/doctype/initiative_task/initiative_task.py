import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from stochops_nonprofit.governance import guard_transition

# آلة حالات المهمة: «Cancelled» نهائية. يُسمح بإعادة فتح المكتملة.
STATUS_FLOW = {
    "Open": {"In Progress", "Completed", "Cancelled"},
    "In Progress": {"Open", "Completed", "Cancelled"},
    "Completed": {"In Progress"},
    "Cancelled": set(),
}


class InitiativeTask(Document):
    def validate(self):
        guard_transition(self, STATUS_FLOW)
        if self.status == "Completed":
            if not (self.completion_note and self.completion_note.strip()):
                frappe.throw(_("لا يمكن إكمال المهمة دون ملاحظة إكمال (completion_note)."))
            if not self.completed_on:
                self.completed_on = nowdate()
        else:
            self.completed_on = None
