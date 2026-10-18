import frappe
from frappe import _

from stochops_nonprofit.dashboard_metrics import compute

# ملخص تنفيذي شهري — مؤشرات مُستمدة من الوحدتين 1 و2 (دون إدخال مزدوج).
# الأرقام من queries (frappe.get_list) فتحترم الصلاحيات؛ لا قيم مختلقة.


def execute(filters=None):
    filters = filters or {}
    d = compute(filters.get("from_date"), filters.get("to_date"))

    rows = [
        {"metric": _("مجموع القرارات غير الملغاة"), "value": d["decisions_non_cancelled"],
         "basis": _("الحالة ≠ ملغي (إجمالي حالي)")},
        {"metric": _("القرارات المفتوحة وقيد العمل"), "value": d["decisions_open_inprogress"],
         "basis": _("Open + In Progress (حالي)")},
        {"metric": _("القرارات المتأخرة"), "value": d["decisions_overdue"],
         "basis": _("الاستحقاق < اليوم وليست مكتملة/ملغاة")},
        {"metric": _("القرارات المكتملة خلال الفترة"), "value": d["decisions_completed_in_period"],
         "basis": _("تاريخ الإكمال ضمن الفترة ({0} إلى {1})").format(d["from_date"], d["to_date"])},
        {"metric": _("المبادرات النشطة"), "value": d["initiatives_active"],
         "basis": _("الحالة = Active (حالي)")},
        {"metric": _("المهام المتأخرة"), "value": d["tasks_overdue"],
         "basis": _("الاستحقاق < اليوم وليست مكتملة/ملغاة")},
        {"metric": _("إجمالي الميزانيات المخططة (ريال)"), "value": f"{d['total_planned_budget']:,.2f}",
         "basis": _("لـ {0} مبادرة لها قيمة — رقم تشغيلي يدوي").format(d["initiatives_counted_planned"])},
        {"metric": _("إجمالي الصرف المسجّل (ريال)"), "value": f"{d['total_actual_spend']:,.2f}",
         "basis": _("لـ {0} مبادرة لها قيمة — رقم تشغيلي يدوي").format(d["initiatives_counted_actual"])},
        {"metric": _("مبادرات بلا أرقام ميزانية"), "value": d["initiatives_without_budget"],
         "basis": _("لا تُحتسب صفراً في تفسير الميزانية")},
    ]

    columns = [
        {"label": _("المؤشر"), "fieldname": "metric", "fieldtype": "Data", "width": 300},
        {"label": _("القيمة"), "fieldname": "value", "fieldtype": "Data", "width": 150},
        {"label": _("الأساس / التعريف"), "fieldname": "basis", "fieldtype": "Data", "width": 330},
    ]
    return columns, rows
