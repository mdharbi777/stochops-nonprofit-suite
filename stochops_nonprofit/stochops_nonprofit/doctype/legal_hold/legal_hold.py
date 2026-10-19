import frappe
from frappe.model.document import Document
from frappe.utils import today


class LegalHold(Document):
    """حجز قانوني يمنع إتلاف السجلات أثناء نزاع/متطلب نظامي (وثيقة PDPL §10).
    معزول بالجمعية. يُفحص عبر privacy_core.assert_no_legal_hold قبل أي إتلاف."""

    def validate(self):
        if not self.placed_on:
            self.placed_on = today()
        if not self.placed_by:
            self.placed_by = frappe.session.user
        if self.status == "مرفوع" and not self.released_on:
            self.released_on = today()
        if self.status == "نشط":
            self.released_on = None
