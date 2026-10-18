"""مؤشرات الوحدة الثالثة — مصدر حساب واحد للوحة وللتقرير.

كل الأرقام من queries عبر frappe.get_list (تحترم صلاحيات المستخدم)، لا من أي LLM.
القيم غير المتوفّرة لا تُحتسب صفراً؛ الملغاة مستبعدة من المؤشرات المناسبة.
التأخير والمقارنات محسوبة لحظياً (غير مخزّنة). التوقيت Asia/Riyadh عبر today().
"""
import frappe
from frappe.utils import flt, get_first_day, get_last_day, getdate, today

CLOSED = ("Completed", "Cancelled")


def _period(from_date=None, to_date=None):
    if from_date and to_date:
        return getdate(from_date), getdate(to_date)
    t = getdate(today())
    return getdate(get_first_day(t)), getdate(get_last_day(t))


def _safe_list(doctype, fields):
    """get_list يحترم الصلاحيات؛ وإن لم يكن للمستخدم قراءة لهذا النوع، نعيد قائمة فارغة
    (يرى المستخدم مؤشرات ما يحق له فقط) دون كسر اللوحة ودون تجاوز الصلاحيات."""
    try:
        return frappe.get_list(doctype, fields=fields, limit_page_length=0)
    except frappe.PermissionError:
        return []


def compute(from_date=None, to_date=None):
    start, end = _period(from_date, to_date)
    t = getdate(today())

    decisions = _safe_list("Decision", ["name", "status", "due_date", "completion_date"])
    dec_non_cancelled = sum(1 for d in decisions if d.status != "Cancelled")
    dec_open_inprog = sum(1 for d in decisions if d.status in ("Open", "In Progress"))
    dec_overdue = sum(
        1 for d in decisions if d.due_date and d.status not in CLOSED and getdate(d.due_date) < t
    )
    dec_completed_period = sum(
        1
        for d in decisions
        if d.status == "Completed"
        and d.completion_date
        and start <= getdate(d.completion_date) <= end
    )

    initiatives = _safe_list("Initiative", ["name", "status", "planned_budget_sar", "actual_spend_sar"])
    init_active = sum(1 for i in initiatives if i.status == "Active")
    planned_vals = [flt(i.planned_budget_sar) for i in initiatives if flt(i.planned_budget_sar) > 0]
    actual_vals = [flt(i.actual_spend_sar) for i in initiatives if flt(i.actual_spend_sar) > 0]
    init_without_budget = sum(
        1 for i in initiatives if not flt(i.planned_budget_sar) and not flt(i.actual_spend_sar)
    )

    tasks = _safe_list("Initiative Task", ["name", "status", "due_date"])
    tasks_overdue = sum(
        1 for x in tasks if x.due_date and x.status not in CLOSED and getdate(x.due_date) < t
    )

    return {
        "from_date": str(start),
        "to_date": str(end),
        "decisions_non_cancelled": dec_non_cancelled,
        "decisions_open_inprogress": dec_open_inprog,
        "decisions_overdue": dec_overdue,
        "decisions_completed_in_period": dec_completed_period,
        "initiatives_active": init_active,
        "tasks_overdue": tasks_overdue,
        "total_planned_budget": sum(planned_vals),
        "total_actual_spend": sum(actual_vals),
        "initiatives_counted_planned": len(planned_vals),
        "initiatives_counted_actual": len(actual_vals),
        "initiatives_without_budget": init_without_budget,
    }


@frappe.whitelist()
def get_dashboard(from_date=None, to_date=None):
    return compute(from_date, to_date)
