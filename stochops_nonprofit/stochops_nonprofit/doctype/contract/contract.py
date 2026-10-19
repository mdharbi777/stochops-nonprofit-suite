import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

CLOSED = ("منتهٍ", "ملغى")


class Contract(Document):
    """عقد عمل/خدمات بمدة وتنبيه انتهاء داخل النظام. القيمة تسجيل فقط — لا رواتب/دفع.
    معزول بالجمعية."""

    def validate(self):
        if self.value and float(self.value) < 0:
            frappe.throw(_("قيمة العقد لا تكون سالبة."))
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("تاريخ الانتهاء لا يكون قبل البداية."))

    @property
    def is_expiring(self):
        return bool(self.end_date and self.status not in CLOSED and getdate(self.end_date) >= getdate(today()))
