import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

DECISION_STATES = ("معتمد", "مرفوض")
APPROVER_ROLES = {"Nonprofit Admin", "System Manager"}


class AssistanceRequest(Document):
    """طلب مساعدة لمستفيد، بمسار اعتماد محوكم. «المبلغ» تسجيل فقط — لا حركة أموال.
    البتّ (اعتماد/رفض) يتطلّب ملاحظة قرار وصلاحية مدير الجمعية (فصل الواجبات)،
    ويُختم البتّ خادمياً (من بتّ + متى). معزول بالجمعية."""

    def validate(self):
        if self.amount and float(self.amount) < 0:
            frappe.throw(_("المبلغ لا يكون سالباً."))
        self._guard_beneficiary_same_charity()
        if self.status in DECISION_STATES:
            if not (self.decision_note or "").strip():
                frappe.throw(_("ملاحظة القرار مطلوبة عند الاعتماد أو الرفض."))
            if self.has_value_changed("status"):
                self._require_approver()
                self.approved_by = frappe.session.user
                self.approved_on = now_datetime()

    def _guard_beneficiary_same_charity(self):
        """المستفيد يجب أن يكون من جمعية الطلب نفسها (دفاع إضافي فوق خطّافات العزل)."""
        if self.beneficiary and self.charity:
            ben_charity = frappe.db.get_value("Beneficiary", self.beneficiary, "charity")
            if ben_charity and ben_charity != self.charity:
                frappe.throw(_("المستفيد لا ينتمي لجمعيتك."), frappe.PermissionError)

    def _require_approver(self):
        if not (APPROVER_ROLES & set(frappe.get_roles(frappe.session.user))):
            frappe.throw(_("البتّ في الطلب (اعتماد/رفض) يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
