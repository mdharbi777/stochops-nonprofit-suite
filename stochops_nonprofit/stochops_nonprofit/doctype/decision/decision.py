import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate, today

from stochops_nonprofit.governance import guard_transition

CLOSED_STATES = ("Completed", "Cancelled")

# آلة حالات القرار: لا قفزة غير مشروعة، و«ملغى» نهائية. يُسمح بإعادة فتح المكتمل.
STATUS_FLOW = {
    "Open": {"In Progress", "Completed", "Cancelled"},
    "In Progress": {"Open", "Completed", "Cancelled"},
    "Completed": {"In Progress"},
    "Cancelled": set(),
}


class Decision(Document):
    def validate(self):
        guard_transition(self, STATUS_FLOW)
        self._validate_completion()
        self._log_status_change()
        self._stamp_followups_and_last()

    def _validate_completion(self):
        """لا يُغلق القرار (Completed) دون ملاحظة إكمال؛ تاريخ الإكمال يُملأ خادمياً."""
        if self.status == "Completed":
            if not (self.completion_note and self.completion_note.strip()):
                frappe.throw(_("لا يمكن إكمال القرار دون ملاحظة إكمال (completion_note)."))
            if not self.completion_date:
                self.completion_date = nowdate()
        else:
            # إن لم يعد مكتملاً، نُفرغ تاريخ الإكمال لتجنّب التناقض
            self.completion_date = None

    def _log_status_change(self):
        """يضيف صف متابعة تلقائياً عند تغيّر الحالة (Audit Trail)."""
        before = self.get_doc_before_save()
        if not before:
            return
        old_status = before.status
        if old_status != self.status:
            self.append(
                "follow_ups",
                {
                    "followup_date": now_datetime(),
                    "update_text": _("تغيّرت الحالة من {0} إلى {1}").format(
                        old_status or "-", self.status or "-"
                    ),
                    "updated_by": frappe.session.user,
                    "previous_status": old_status,
                    "new_status": self.status,
                },
            )

    def _stamp_followups_and_last(self):
        """يملأ الحقول الخادمية لأي صف متابعة جديد، ويحدّث تاريخ آخر متابعة."""
        latest = None
        for row in self.follow_ups or []:
            if not row.followup_date:
                row.followup_date = now_datetime()
            if not row.updated_by:
                row.updated_by = frappe.session.user
            row_date = getdate(row.followup_date)
            if latest is None or row_date > latest:
                latest = row_date
        if latest:
            self.last_followup = latest

    @property
    def is_overdue(self):
        """التأخير صفة مشتقة (لا تُخزَّن): مستحق سابقاً والحالة ليست مكتملة/ملغاة."""
        return bool(
            self.due_date
            and self.status not in CLOSED_STATES
            and getdate(self.due_date) < getdate(today())
        )
