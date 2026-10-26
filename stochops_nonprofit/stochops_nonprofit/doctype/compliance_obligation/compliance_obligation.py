import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today

from stochops_nonprofit.governance import guard_transition

CLOSED = ("مكتمل", "ملغى")

# آلة حالات الالتزام: «ملغى» نهائية. يُسمح بإعادة فتح المكتمل (التزامات متكرّرة).
STATUS_FLOW = {
    "قادم": {"قيد الإعداد", "مقدّم", "مكتمل", "ملغى"},
    "قيد الإعداد": {"قادم", "مقدّم", "مكتمل", "ملغى"},
    "مقدّم": {"قيد الإعداد", "مكتمل", "ملغى"},
    "مكتمل": {"قادم", "قيد الإعداد", "مقدّم"},
    "ملغى": set(),
}


class ComplianceObligation(Document):
    """التزام حوكمة/تنظيمي بموعد استحقاق وتذكير داخل النظام. لا تكامل حكومي مباشر.
    التأخير صفة مشتقّة (غير مخزّنة). معزول بالجمعية."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
        if self.status == "مكتمل" and not self.completed_on:
            self.completed_on = today()
        if self.status != "مكتمل":
            self.completed_on = None

    @property
    def is_overdue(self):
        return bool(self.due_date and self.status not in CLOSED and getdate(self.due_date) < getdate(today()))
