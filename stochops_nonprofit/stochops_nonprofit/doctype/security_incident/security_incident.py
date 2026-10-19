import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date


class SecurityIncident(Document):
    """حادثة أمن/خصوصية + تقييم خرق. تُحسب نافذة 72 ساعة من وقت العلم كتذكير فقط —
    **لا بلاغ حكومي آلي** (قرار الإشعار بشري من جهة التحكم). معزول بالجمعية (وثيقة PDPL §11)."""

    def validate(self):
        if not self.reporter:
            self.reporter = frappe.session.user
        if self.discovered_on:
            self.notice_window_deadline = add_to_date(self.discovered_on, hours=72)
