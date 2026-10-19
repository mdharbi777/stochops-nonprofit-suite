import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today

CLOSED = ("مكتمل", "مرفوض جزئياً", "مرفوض")


class PrivacyRightsRequest(Document):
    """طلب حق لصاحب البيانات — مهلة 30 يوماً من الاستلام، وتمديد حتى 30 يوماً بمبرر
    (وثيقة PDPL §5 / المادة 3 من اللائحة). التأخير مشتق. معزول بالجمعية.
    لا يُرَدّ آلياً — تبقى المعالجة بشرية بإشراف مسؤول الخصوصية."""

    def validate(self):
        if self.received_on and not self.due_date:
            self.due_date = add_days(getdate(self.received_on), 30)
        if self.extended:
            if not (self.extension_reason or "").strip():
                frappe.throw(_("مبرر التمديد مطلوب."))
            if self.due_date and not self.extended_due:
                self.extended_due = add_days(getdate(self.due_date), 30)
        else:
            self.extended_due = None
        if self.status in CLOSED and not self.resolved_on:
            self.resolved_on = today()
        if self.status not in CLOSED:
            self.resolved_on = None

    @property
    def effective_due(self):
        return self.extended_due or self.due_date

    @property
    def is_overdue(self):
        due = self.effective_due
        return bool(due and self.status not in CLOSED and getdate(due) < getdate(today()))
