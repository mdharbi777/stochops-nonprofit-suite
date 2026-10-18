import frappe
from frappe import _
from frappe.utils import flt, getdate, today

# نظرة عامة على المبادرات: ميزانية إدارية (مُدخلة يدوياً) + إنجاز المهام (كمّي) + تحقيق المستهدف (كمّي).
# القيم غير المتوفّرة تظهر "غير متوفّر" لا صفر. النِّسب كمّية وليست قياس أثر.
# يستخدم frappe.get_list للمبادرات فتُطبَّق الصلاحيات.


def execute(filters=None):
    filters = filters or {}
    conditions = {}
    if filters.get("status"):
        conditions["status"] = filters["status"]
    if filters.get("initiative_owner"):
        conditions["initiative_owner"] = filters["initiative_owner"]

    initiatives = frappe.get_list(
        "Initiative",
        filters=conditions,
        fields=[
            "name", "title", "status", "initiative_owner", "start_date", "end_date",
            "planned_budget_sar", "actual_spend_sar",
            "target_count", "actual_count",
        ],
        order_by="start_date desc",
    )

    na = _("غير متوفّر")
    t = getdate(today())
    data = []
    for i in initiatives:
        tasks = frappe.get_all(
            "Initiative Task", filters={"initiative": i["name"]}, fields=["status", "due_date"]
        )
        actionable = [x for x in tasks if x["status"] != "Cancelled"]
        completed = len([x for x in actionable if x["status"] == "Completed"])
        overdue = len(
            [
                x
                for x in tasks
                if x.get("due_date")
                and x["status"] not in ("Completed", "Cancelled")
                and getdate(x["due_date"]) < t
            ]
        )
        task_pct = f"{round(completed / len(actionable) * 100, 1)}%" if actionable else na
        if i.get("target_count") and int(i["target_count"]) > 0:
            target_pct = f"{round(flt(i['actual_count']) / int(i['target_count']) * 100, 1)}%"
        else:
            target_pct = na

        # ملاحظة: حقول Currency تُخزَّن 0 عند عدم الإدخال، فلا يمكن تمييز None.
        # المتبقّي (قيمة مشتقة) يظهر "غير متوفّر" ما لم تُدخَل ميزانية فعلية (مخطط أو مصروف > 0).
        has_budget = bool(flt(i.get("planned_budget_sar"))) or bool(flt(i.get("actual_spend_sar")))
        remaining = (
            f"{flt(i['planned_budget_sar']) - flt(i['actual_spend_sar']):,.2f}" if has_budget else na
        )

        data.append(
            {
                "name": i["name"],
                "title": i["title"],
                "status": i["status"],
                "initiative_owner": i["initiative_owner"],
                "start_date": i["start_date"],
                "end_date": i["end_date"],
                "planned_budget_sar": i["planned_budget_sar"],
                "actual_spend_sar": i["actual_spend_sar"],
                "remaining": remaining,
                "tasks_total": len(tasks),
                "tasks_completed": completed,
                "task_pct": task_pct,
                "overdue_tasks": overdue,
                "target_pct": target_pct,
            }
        )

    return get_columns(), data


def get_columns():
    return [
        {"label": _("المبادرة"), "fieldname": "name", "fieldtype": "Link", "options": "Initiative", "width": 140},
        {"label": _("العنوان"), "fieldname": "title", "fieldtype": "Data", "width": 190},
        {"label": _("الحالة"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": _("المسؤول"), "fieldname": "initiative_owner", "fieldtype": "Link", "options": "User", "width": 150},
        {"label": _("البداية"), "fieldname": "start_date", "fieldtype": "Date", "width": 100},
        {"label": _("النهاية"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
        {"label": _("المخطط (ريال)"), "fieldname": "planned_budget_sar", "fieldtype": "Currency", "width": 120},
        {"label": _("المصروف (ريال)"), "fieldname": "actual_spend_sar", "fieldtype": "Currency", "width": 120},
        {"label": _("المتبقّي (ريال)"), "fieldname": "remaining", "fieldtype": "Data", "width": 120},
        {"label": _("مهام"), "fieldname": "tasks_total", "fieldtype": "Int", "width": 70},
        {"label": _("مكتملة"), "fieldname": "tasks_completed", "fieldtype": "Int", "width": 70},
        {"label": _("إنجاز المهام"), "fieldname": "task_pct", "fieldtype": "Data", "width": 100},
        {"label": _("مهام متأخرة"), "fieldname": "overdue_tasks", "fieldtype": "Int", "width": 90},
        {"label": _("تحقيق المستهدف (كمّي)"), "fieldname": "target_pct", "fieldtype": "Data", "width": 130},
    ]
