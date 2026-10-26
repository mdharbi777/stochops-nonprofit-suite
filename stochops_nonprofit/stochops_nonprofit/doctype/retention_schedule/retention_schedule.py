from frappe.model.document import Document

from stochops_nonprofit.governance import guard_transition

# آلة حالات جدول الاحتفاظ: يُعتمد ثم يمكن إعادته للتعريف عند المراجعة.
STATUS_FLOW = {
    "PENDING_DEFINITION": {"APPROVED"},
    "APPROVED": {"PENDING_DEFINITION"},
}


class RetentionSchedule(Document):
    """جدول احتفاظ لكل فئة بيانات — المدة والمصدر النظامي ونقطة البدء. لا تُخترع مدة
    موحّدة؛ الحالة الافتراضية PENDING_DEFINITION حتى يعتمدها المختص (وثيقة PDPL §10)."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
