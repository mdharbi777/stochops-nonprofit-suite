import frappe
from frappe.model.document import Document
from frappe.utils import today


class ConsentRecord(Document):
    """سجل موافقة (عندما تكون الموافقة أساساً قانونياً) — نسخة الإشعار والغرض والطريقة
    والحالة وقابلية السحب (وثيقة PDPL §4). معزول بالجمعية."""

    def validate(self):
        if self.status == "مسحوبة" and not self.withdrawn_on:
            self.withdrawn_on = today()
        if self.status == "ممنوحة":
            self.withdrawn_on = None
