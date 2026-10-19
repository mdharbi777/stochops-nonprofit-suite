from frappe.model.document import Document


class RegulatoryRule(Document):
    """قاعدة/مرجع تنظيمي بمصدر وإصدار وتاريخ مراجعة. الحالة الافتراضية
    LEGAL_REVIEW_REQUIRED ولا تتحوّل تلقائياً إلى «متوافق» (وثيقة PDPL §1)."""

    pass
