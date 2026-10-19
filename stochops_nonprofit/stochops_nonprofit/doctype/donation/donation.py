import frappe
from frappe import _
from frappe.model.document import Document


class Donation(Document):
    """تبرّع مُسجَّل (نقدي/عيني/تعهّد). «المبلغ» قيمة مُسجّلة فقط — لا بوابة دفع
    ولا تحصيل إلكتروني ولا حركة أموال. معزول بالجمعية."""

    def validate(self):
        if self.amount and float(self.amount) < 0:
            frappe.throw(_("المبلغ لا يكون سالباً."))
        self._guard_donor_same_charity()

    def _guard_donor_same_charity(self):
        if self.donor and self.charity:
            donor_charity = frappe.db.get_value("Donor", self.donor, "charity")
            if donor_charity and donor_charity != self.charity:
                frappe.throw(_("المتبرّع لا ينتمي لجمعيتك."), frappe.PermissionError)
