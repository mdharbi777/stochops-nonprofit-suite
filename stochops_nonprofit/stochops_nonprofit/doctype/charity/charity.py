import frappe
from frappe.model.document import Document


class Charity(Document):
    def validate(self):
        if self.max_accounts is None or int(self.max_accounts) <= 0:
            self.max_accounts = 5
