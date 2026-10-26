from frappe.model.document import Document

from stochops_nonprofit.governance import guard_transition

# آلة حالات القاعدة التنظيمية: المراجعة القانونية تنتهي بـ«محقّقة» أو «غير منطبقة»،
# ويمكن إعادتها للمراجعة عند تغيّر المرجع.
STATUS_FLOW = {
    "LEGAL_REVIEW_REQUIRED": {"VERIFIED", "NOT_APPLICABLE"},
    "VERIFIED": {"LEGAL_REVIEW_REQUIRED"},
    "NOT_APPLICABLE": {"LEGAL_REVIEW_REQUIRED"},
}


class RegulatoryRule(Document):
    """قاعدة/مرجع تنظيمي بمصدر وإصدار وتاريخ مراجعة. الحالة الافتراضية
    LEGAL_REVIEW_REQUIRED ولا تتحوّل تلقائياً إلى «متوافق» (وثيقة PDPL §1)."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
