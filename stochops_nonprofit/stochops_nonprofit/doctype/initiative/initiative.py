import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

NON_NEGATIVE_FIELDS = [
    ("planned_budget_sar", "الميزانية المخططة"),
    ("actual_spend_sar", "الصرف الإداري"),
    ("target_count", "المستهدف"),
    ("actual_count", "المنجز"),
]


class Initiative(Document):
    def validate(self):
        self._validate_dates()
        self._validate_non_negative()
        self._validate_closing()

    def _validate_dates(self):
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("تاريخ النهاية لا يمكن أن يكون قبل تاريخ البداية."))

    def _validate_non_negative(self):
        for fieldname, label in NON_NEGATIVE_FIELDS:
            value = self.get(fieldname)
            if value is not None and flt(value) < 0:
                frappe.throw(_("{0} لا يمكن أن يكون سالباً.").format(label))

    def _validate_closing(self):
        # إغلاق المبادرة يتطلب ملاحظة إغلاق فقط (لا يلزم اكتمال الميزانية أو المستهدفات).
        if self.status == "Completed" and not (self.closing_note and self.closing_note.strip()):
            frappe.throw(_("إغلاق المبادرة يتطلب ملاحظة إغلاق (closing_note)."))

    @property
    def task_completion(self):
        """نسبة إنجاز المهام = المكتملة / المهام القابلة للتنفيذ (غير الملغاة). None عند غياب المهام.
        نسبة كمية لإنجاز المهام، ولا تُخلط بقياس الأثر أو المستفيدين."""
        tasks = frappe.get_all("Initiative Task", filters={"initiative": self.name}, fields=["status"])
        actionable = [t for t in tasks if t.status != "Cancelled"]
        if not actionable:
            return None
        completed = len([t for t in actionable if t.status == "Completed"])
        return round(completed / len(actionable) * 100, 1)

    @property
    def target_achievement(self):
        """نسبة تحقيق المستهدف (كمية فقط) — تُحسب فقط عند target_count > 0."""
        if self.target_count and int(self.target_count) > 0:
            return round(flt(self.actual_count) / int(self.target_count) * 100, 1)
        return None

    @property
    def remaining_budget(self):
        """المتبقّي = المخطط - المصروف، فقط عند توفّر الرقمين (وإلا None = غير متوفّر).
        صفة محسوبة غير مخزّنة — يُسمح بالسالب (تجاوز) دون حظر."""
        if self.planned_budget_sar is not None and self.actual_spend_sar is not None:
            return flt(self.planned_budget_sar) - flt(self.actual_spend_sar)
        return None
