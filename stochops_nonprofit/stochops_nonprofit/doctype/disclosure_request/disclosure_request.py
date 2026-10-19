import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

DECISION_STATES = ("معتمد", "مرفوض")
APPROVER_ROLES = {"Nonprofit Admin", "System Manager"}


class DisclosureRequest(Document):
    """طلب إفصاح/مشاركة بيانات خارج حدود الجمعية — deny-by-default (وثيقة PDPL §9).
    الاعتماد يتطلّب ملاحظة قرار وصلاحية مدير الجمعية ويُختم، ويُسجَّل كحدث مشاركة.
    معزول بالجمعية."""

    def validate(self):
        if self.status in DECISION_STATES and self.has_value_changed("status"):
            if not (self.decision_note or "").strip():
                frappe.throw(_("ملاحظة القرار مطلوبة عند الاعتماد أو الرفض."))
            if not (APPROVER_ROLES & set(frappe.get_roles(frappe.session.user))):
                frappe.throw(_("البتّ في الإفصاح يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
            self.approved_by = frappe.session.user
            self.approved_on = now_datetime()

    def on_update(self):
        if self.status == "معتمد" and self.has_value_changed("status"):
            try:
                from stochops_nonprofit.privacy_core import log_sensitive_access

                log_sensitive_access("share", "Disclosure Request", self.name,
                                     note=f"recipient:{self.recipient}", charity=self.charity)
            except Exception:
                pass
