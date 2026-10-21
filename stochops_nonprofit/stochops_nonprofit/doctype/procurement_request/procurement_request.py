import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from stochops_nonprofit.governance import guard_transition

DECISION_STATES = ("معتمد", "مرفوض")

# مسار الشراء المحوكم (آلة حالات). «مُنفّذ» حالة صرف/تنفيذ نهائية.
STATUS_FLOW = {
    "مسودة": {"مقدّم", "ملغى"},
    "مقدّم": {"قيد المراجعة", "معتمد", "مرفوض", "ملغى"},
    "قيد المراجعة": {"معتمد", "مرفوض", "ملغى"},
    "معتمد": {"مُنفّذ", "ملغى"},
    "مرفوض": set(),
    "مُنفّذ": set(),
    "ملغى": set(),
}
DISBURSE_STATES = {"مُنفّذ"}


class ProcurementRequest(Document):
    """طلب شراء محوكم — تقدير مُسجّل، لا دفع بنكي. نفس ضوابط الرقابة المالية:
    فصل الواجبات (لا يبتّ المُقدّم)، حدّ اعتماد الجمعية بالدور، ملاحظة بتّ + ختم، تدقيق.
    معزول بالجمعية."""

    def validate(self):
        if self.amount and float(self.amount) < 0:
            frappe.throw(_("القيمة لا تكون سالبة."))
        if self.is_new() and not self.requested_by:
            self.requested_by = frappe.session.user
        guard_transition(self, STATUS_FLOW, DISBURSE_STATES, disburse_label="التنفيذ/الصرف")
        if self.status in DECISION_STATES and self.has_value_changed("status"):
            if not (self.decision_note or "").strip():
                frappe.throw(_("ملاحظة البتّ مطلوبة عند الاعتماد أو الرفض."))
            self._authorize_decision()
            self.approved_by = frappe.session.user
            self.approved_on = now_datetime()

    def _authorize_decision(self):
        user = frappe.session.user
        roles = set(frappe.get_roles(user))
        is_super = "System Manager" in roles
        if self.requested_by and user == self.requested_by and not is_super:
            frappe.throw(_("فصل الواجبات: لا يبتّ مُقدّم الطلب في طلبه."), frappe.PermissionError)
        if is_super:
            return
        if "Nonprofit Admin" not in roles:
            frappe.throw(_("البتّ في الشراء يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
        if self.status == "معتمد":
            limit = frappe.db.get_value("Charity", self.charity, "expense_approval_limit") or 0
            if limit and float(self.amount or 0) > float(limit):
                frappe.throw(
                    _("قيمة الطلب تتجاوز حدّ اعتمادك ({0} ريال)؛ يتطلّب تصعيداً لمشغّل المنصّة.").format(
                        f"{float(limit):,.0f}"
                    ),
                    frappe.PermissionError,
                )
