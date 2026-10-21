import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# آلة حالات طلب الاستفادة. الحالة النهائية = مجموعة فارغة.
STATUS_FLOW = {
    "Submitted": {"Under Review", "Information Required", "Rejected"},
    "Under Review": {"Information Required", "Waitlisted", "Approved", "Rejected"},
    "Information Required": {"Under Review", "Waitlisted", "Rejected"},
    "Waitlisted": {"Under Review", "Approved", "Rejected"},
    "Approved": set(),
    "Rejected": set(),
}
DECISION_STATES = ("Approved", "Rejected")
SCORE_CAPS = {
    "score_need": 25, "score_readiness": 20, "score_scale": 15,
    "score_governance": 20, "score_manager": 10, "score_fit": 10,
}


class AssociationApplication(Document):
    """طلب استفادة من الفاضل (قبول انتقائي). التقديم لا يُنشئ حساب إنتاج؛ يمرّ بتحقّق وتقييم
    واعتماد بشري موثّق. الترخيص شرط إلزامي مستقل لا تعوّضه الدرجات. كل قرار يُختم (من/متى/مبرّر)."""

    def validate(self):
        before = self.get_doc_before_save()
        if self.is_new():
            if not self.access_code:
                self.access_code = frappe.generate_hash(length=10).upper()
            if not self.submitted_on:
                self.submitted_on = now_datetime()
            if not self.status:
                self.status = "Submitted"
        self._cap_scores()
        self.score_total = sum(int(self.get(f) or 0) for f in SCORE_CAPS)
        self._guard_transition(before)
        if self.status in DECISION_STATES and (not before or before.status != self.status):
            self._finalize_decision()

    def _cap_scores(self):
        for field, cap in SCORE_CAPS.items():
            v = int(self.get(field) or 0)
            if v < 0 or v > cap:
                frappe.throw(_("قيمة «{0}» يجب أن تكون بين 0 و{1}.").format(self.meta.get_label(field), cap))

    def _guard_transition(self, before):
        if self.is_new() or not self.has_value_changed("status"):
            return
        old = before.status if before else None
        if old is None:
            return
        if self.status != old and self.status not in STATUS_FLOW.get(old, set()):
            frappe.throw(
                _("انتقال غير مسموح لحالة الطلب: من «{0}» إلى «{1}».").format(old, self.status),
                frappe.PermissionError,
            )

    def _finalize_decision(self):
        if not (self.decision_reason or "").strip():
            frappe.throw(_("مبرّر القرار مطلوب عند الاعتماد أو الرفض."))
        if self.status == "Approved":
            # الترخيص وتحقّق البريد شرط إلزامي مستقل قبل القبول (لا تعوّضه الدرجات)
            if not self.license_verified or not self.email_verified:
                frappe.throw(
                    _("لا يُعتمد الطلب قبل تحقّق الترخيص والبريد الرسمي (شرط إلزامي مستقل)."),
                    frappe.PermissionError,
                )
        self.decided_by = frappe.session.user
        self.decided_on = now_datetime()
        if not self.reviewer:
            self.reviewer = frappe.session.user
