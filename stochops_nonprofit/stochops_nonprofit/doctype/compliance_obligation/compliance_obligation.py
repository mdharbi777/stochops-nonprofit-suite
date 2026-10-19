import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today

CLOSED = ("مكتمل", "ملغى")


class ComplianceObligation(Document):
    """التزام حوكمة/تنظيمي بموعد استحقاق وتذكير داخل النظام. لا تكامل حكومي مباشر.
    التأخير صفة مشتقّة (غير مخزّنة). معزول بالجمعية."""

    def validate(self):
        if self.status == "مكتمل" and not self.completed_on:
            self.completed_on = today()
        if self.status != "مكتمل":
            self.completed_on = None

    @property
    def is_overdue(self):
        return bool(self.due_date and self.status not in CLOSED and getdate(self.due_date) < getdate(today()))
