import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

LOCKED_AFTER_INSERT = (
    "charity", "document", "document_hash", "document_version",
    "representative_name", "acceptance_text", "accepted_on",
)


class LegalAcceptance(Document):
    """سجلّ قبول إلكتروني لوثيقة قانونية منشورة. غير قابل للتعديل بعد إنشائه (دليل إثبات):
    يُثبَّت فيه الإصدار وبصمته ووقت القبول. القبول لا يصحّ إلا لوثيقة Published."""

    def validate(self):
        if self.is_new():
            self._bind_document()
            if not self.accepted_on:
                self.accepted_on = now_datetime()
        else:
            self._guard_immutable()

    def _bind_document(self):
        doc = frappe.db.get_value(
            "Legal Document", self.document, ["status", "version", "title", "content_hash"], as_dict=True
        )
        if not doc:
            frappe.throw(_("الوثيقة غير موجودة."))
        if doc.status != "Published":
            frappe.throw(_("لا يُقبَل إلا إصدار منشور من الوثيقة."), frappe.PermissionError)
        self.document_version = doc.version
        self.document_title = doc.title
        self.document_hash = doc.content_hash

    def _guard_immutable(self):
        before = self.get_doc_before_save()
        if not before:
            return
        changed = [f for f in LOCKED_AFTER_INSERT if self.has_value_changed(f)]
        if changed:
            frappe.throw(
                _("سجلّ القبول دليل إثبات غير قابل للتعديل. الحقول المقفلة: {0}").format("، ".join(changed)),
                frappe.PermissionError,
            )
