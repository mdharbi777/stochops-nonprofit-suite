import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class Personnel(Document):
    """موظف/متطوّع — بيانات HR أدنى، بلا رواتب فعلية ولا تكامل تأمينات.
    رقم الهوية حقل مشفّر ومحجوب (يُكشف بصلاحية إدارية). معزول بالجمعية."""

    def validate(self):
        nid = self.get("national_id")
        if nid and nid.isdigit() and len(nid) != 10:
            frappe.throw(_("رقم الهوية يجب أن يكون 10 أرقام."))
        if self.email:
            self.email = self.email.strip().lower()
            validate_email_address(self.email, throw=True)
