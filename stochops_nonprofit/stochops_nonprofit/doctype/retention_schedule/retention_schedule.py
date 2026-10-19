from frappe.model.document import Document


class RetentionSchedule(Document):
    """جدول احتفاظ لكل فئة بيانات — المدة والمصدر النظامي ونقطة البدء. لا تُخترع مدة
    موحّدة؛ الحالة الافتراضية PENDING_DEFINITION حتى يعتمدها المختص (وثيقة PDPL §10)."""

    pass
