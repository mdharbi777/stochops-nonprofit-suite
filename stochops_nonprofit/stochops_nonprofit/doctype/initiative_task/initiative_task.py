import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class InitiativeTask(Document):
    def validate(self):
        if self.status == "Completed":
            if not (self.completion_note and self.completion_note.strip()):
                frappe.throw(_("لا يمكن إكمال المهمة دون ملاحظة إكمال (completion_note)."))
            if not self.completed_on:
                self.completed_on = nowdate()
        else:
            self.completed_on = None
