from frappe.model.document import Document
from frappe.utils import today

from stochops_nonprofit.governance import guard_transition

# آلة حالات الموافقة: السحب نهائي (الموافقة الجديدة سجلّ جديد).
STATUS_FLOW = {"ممنوحة": {"مسحوبة"}, "مسحوبة": set()}


class ConsentRecord(Document):
    """سجل موافقة (عندما تكون الموافقة أساساً قانونياً) — نسخة الإشعار والغرض والطريقة
    والحالة وقابلية السحب (وثيقة PDPL §4). معزول بالجمعية."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
        if self.status == "مسحوبة" and not self.withdrawn_on:
            self.withdrawn_on = today()
        if self.status == "ممنوحة":
            self.withdrawn_on = None
