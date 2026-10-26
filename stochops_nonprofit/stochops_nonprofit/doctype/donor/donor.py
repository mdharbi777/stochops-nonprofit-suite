import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address

from stochops_nonprofit.governance import guard_transition

# آلة حالات المتبرّع: أرشفة قابلة للاستعادة (نشط ⇄ مؤرشف).
STATUS_FLOW = {"نشط": {"مؤرشف"}, "مؤرشف": {"نشط"}}


class Donor(Document):
    """متبرّع (فرد/جهة) — بيانات تواصل أدنى، معزول بالجمعية."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
        if self.email:
            self.email = self.email.strip().lower()
            validate_email_address(self.email, throw=True)
