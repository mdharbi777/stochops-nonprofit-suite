import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from stochops_nonprofit.governance import guard_transition

DECISION_STATES = ("معتمد", "مرفوض")
APPROVER_ROLES = {"Nonprofit Admin", "System Manager"}

# مسار الاعتماد المحوكم (آلة حالات). الحالة النهائية = مجموعة فارغة.
STATUS_FLOW = {
    "مقدم": {"قيد المراجعة", "معتمد", "مرفوض", "ملغى"},
    "قيد المراجعة": {"معتمد", "مرفوض", "ملغى"},
    "معتمد": {"مصروف", "ملغى"},
    "مرفوض": set(),
    "مصروف": set(),
    "ملغى": set(),
}
DISBURSE_STATES = {"مصروف"}


class AssistanceRequest(Document):
    """طلب مساعدة لمستفيد، بمسار اعتماد محوكم. «المبلغ» تسجيل فقط — لا حركة أموال.
    البتّ (اعتماد/رفض) يتطلّب ملاحظة قرار وصلاحية مدير الجمعية (فصل الواجبات)،
    ويُختم البتّ خادمياً (من بتّ + متى). معزول بالجمعية."""

    def validate(self):
        if self.amount and float(self.amount) < 0:
            frappe.throw(_("المبلغ لا يكون سالباً."))
        self._guard_beneficiary_same_charity()
        guard_transition(self, STATUS_FLOW, DISBURSE_STATES, disburse_label="الصرف")
        if self.status in DECISION_STATES:
            if not (self.decision_note or "").strip():
                frappe.throw(_("ملاحظة القرار مطلوبة عند الاعتماد أو الرفض."))
            if self.has_value_changed("status"):
                self._require_approver()
                self._require_segregation()
                self.approved_by = frappe.session.user
                self.approved_on = now_datetime()

    def _require_segregation(self):
        """فصل الواجبات: لا يبتّ مُنشئ الطلب في طلبه (يتجاوزه مشغّل المنصّة فقط)."""
        user = frappe.session.user
        if self.owner == user and "System Manager" not in set(frappe.get_roles(user)):
            frappe.throw(_("فصل الواجبات: لا يبتّ مُنشئ الطلب في طلبه."), frappe.PermissionError)

    def _guard_beneficiary_same_charity(self):
        """المستفيد يجب أن يكون من جمعية الطلب نفسها (دفاع إضافي فوق خطّافات العزل)."""
        if self.beneficiary and self.charity:
            ben_charity = frappe.db.get_value("Beneficiary", self.beneficiary, "charity")
            if ben_charity and ben_charity != self.charity:
                frappe.throw(_("المستفيد لا ينتمي لجمعيتك."), frappe.PermissionError)

    def _require_approver(self):
        if not (APPROVER_ROLES & set(frappe.get_roles(frappe.session.user))):
            frappe.throw(_("البتّ في الطلب (اعتماد/رفض) يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
