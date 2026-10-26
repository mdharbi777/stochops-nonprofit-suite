import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address

from stochops_nonprofit.governance import guard_transition

# آلة حالات شؤون الأفراد: «منتهٍ» نهائية (انتهاء العلاقة)؛ الإيقاف قابل للاستئناف.
STATUS_FLOW = {
    "نشط": {"موقوف", "منتهٍ"},
    "موقوف": {"نشط", "منتهٍ"},
    "منتهٍ": set(),
}


class Personnel(Document):
    """موظف/متطوّع — بيانات HR أدنى، بلا رواتب فعلية ولا تكامل تأمينات.
    رقم الهوية حقل مشفّر ومحجوب (يُكشف بصلاحية إدارية). معزول بالجمعية."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
        nid = self.get("national_id")
        if nid and nid.isdigit() and len(nid) != 10:
            frappe.throw(_("رقم الهوية يجب أن يكون 10 أرقام."))
        if self.email:
            self.email = self.email.strip().lower()
            validate_email_address(self.email, throw=True)
