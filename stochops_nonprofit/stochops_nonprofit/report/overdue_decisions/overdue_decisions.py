import frappe
from frappe import _
from frappe.utils import getdate, today

# تقرير القرارات المتأخرة: مستحقة قبل اليوم والحالة ليست مكتملة/ملغاة.
# يستخدم frappe.get_list حتى تُطبَّق صلاحيات المستخدم (الدور + User Permissions)
# فلا يكشف بيانات لا يحق للمستخدم رؤيتها.


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    conditions = [
        ["status", "not in", ["Completed", "Cancelled"]],
        ["due_date", "<", today()],
    ]
    if filters.get("committee"):
        conditions.append(["committee", "=", filters["committee"]])
    if filters.get("decision_owner"):
        conditions.append(["decision_owner", "=", filters["decision_owner"]])

    rows = frappe.get_list(
        "Decision",
        filters=conditions,
        fields=["name", "title", "committee", "decision_owner", "due_date", "status", "priority"],
        order_by="due_date asc",
    )

    t = getdate(today())
    for d in rows:
        d["days_overdue"] = (t - getdate(d["due_date"])).days if d.get("due_date") else 0

    return columns, rows


def get_columns():
    return [
        {"label": _("القرار"), "fieldname": "name", "fieldtype": "Link", "options": "Decision", "width": 150},
        {"label": _("العنوان"), "fieldname": "title", "fieldtype": "Data", "width": 220},
        {"label": _("اللجنة"), "fieldname": "committee", "fieldtype": "Link", "options": "Committee", "width": 150},
        {"label": _("المسؤول"), "fieldname": "decision_owner", "fieldtype": "Link", "options": "User", "width": 170},
        {"label": _("الأولوية"), "fieldname": "priority", "fieldtype": "Data", "width": 90},
        {"label": _("تاريخ الاستحقاق"), "fieldname": "due_date", "fieldtype": "Date", "width": 120},
        {"label": _("أيام التأخير"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 100},
        {"label": _("الحالة"), "fieldname": "status", "fieldtype": "Data", "width": 110},
    ]
