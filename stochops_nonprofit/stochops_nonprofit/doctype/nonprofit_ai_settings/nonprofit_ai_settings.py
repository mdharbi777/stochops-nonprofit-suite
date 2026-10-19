import frappe
from frappe import _
from frappe.model.document import Document


class NonprofitAISettings(Document):
    """إعدادات المساعد الذكي على مستوى المنصّة. موقوف افتراضياً (GATE AI)."""

    def validate(self):
        # تفعيل أي مزوّد حقيقي (غير Mock) يتطلّب إقرار اتفاق معالجة البيانات.
        if self.ai_enabled and self.provider != "Mock" and not self.data_processing_ack:
            frappe.throw(_("تفعيل مزوّد حقيقي يتطلّب إقرار اتفاق معالجة البيانات ومنطقتها (GATE AI)."))
