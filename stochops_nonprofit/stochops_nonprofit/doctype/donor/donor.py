import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class Donor(Document):
    """متبرّع (فرد/جهة) — بيانات تواصل أدنى، معزول بالجمعية."""

    def validate(self):
        if self.email:
            self.email = self.email.strip().lower()
            validate_email_address(self.email, throw=True)
