import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# الحقول التي تُقفل بعد اعتماد المحضر (لا تُعدّل إلا بدور إداري)
LOCKED_AFTER_APPROVAL = [
    "committee",
    "title",
    "meeting_date",
    "meeting_reference",
    "minutes_attachment",
    "notes",
]


class Meeting(Document):
    def validate(self):
        self._handle_approval_stamp()
        self._guard_approved_edit()

    def _handle_approval_stamp(self):
        """يملأ معتمِد/تاريخ الاعتماد خادمياً عند الاعتماد، ويمسحهما عند الرجوع لمسودة."""
        if self.status == "Approved":
            if not self.approved_by:
                self.approved_by = frappe.session.user
            if not self.approved_on:
                self.approved_on = now_datetime()
        else:
            self.approved_by = None
            self.approved_on = None

    def _guard_approved_edit(self):
        """منع تعديل محتوى محضر معتمد إلا بصلاحية إدارية — مفروض على الخادم."""
        if self.is_new():
            return
        before = self.get_doc_before_save()
        if not before or before.status != "Approved":
            return
        if "Nonprofit Admin" in frappe.get_roles(frappe.session.user):
            return
        changed = [
            f
            for f in LOCKED_AFTER_APPROVAL
            if (before.get(f) or "") != (self.get(f) or "")
        ]
        if changed:
            frappe.throw(
                _("لا يمكن تعديل محضر معتمد إلا بصلاحية إدارية (Nonprofit Admin). الحقول المتأثرة: {0}").format(
                    ", ".join(changed)
                ),
                frappe.PermissionError,
            )
