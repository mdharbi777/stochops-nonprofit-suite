import frappe
from frappe import _
from frappe.utils import getdate, today

# تقرير متابعة القرارات حسب اللجنة والمسؤول والحالة.
# يستخدم frappe.get_list لتطبيق الصلاحيات. التأخير محسوب (غير مخزّن).


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    conditions = []
    if filters.get("committee"):
        conditions.append(["committee", "=", filters["committee"]])
    if filters.get("decision_owner"):
        conditions.append(["decision_owner", "=", filters["decision_owner"]])
    if filters.get("status"):
        conditions.append(["status", "=", filters["status"]])

    rows = frappe.get_list(
        "Decision",
        filters=conditions,
        fields=[
            "name",
            "committee",
            "decision_owner",
            "title",
            "status",
            "priority",
            "due_date",
            "completion_date",
        ],
        order_by="committee asc, decision_owner asc, due_date asc",
    )

    t = getdate(today())
    for d in rows:
        overdue = (
            d.get("due_date")
            and d["status"] not in ("Completed", "Cancelled")
            and getdate(d["due_date"]) < t
        )
        d["is_overdue"] = _("نعم") if overdue else _("لا")

    return columns, rows


def get_columns():
    return [
        {"label": _("اللجنة"), "fieldname": "committee", "fieldtype": "Link", "options": "Committee", "width": 150},
        {"label": _("المسؤول"), "fieldname": "decision_owner", "fieldtype": "Link", "options": "User", "width": 170},
        {"label": _("القرار"), "fieldname": "name", "fieldtype": "Link", "options": "Decision", "width": 150},
        {"label": _("العنوان"), "fieldname": "title", "fieldtype": "Data", "width": 220},
        {"label": _("الحالة"), "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": _("الأولوية"), "fieldname": "priority", "fieldtype": "Data", "width": 90},
        {"label": _("تاريخ الاستحقاق"), "fieldname": "due_date", "fieldtype": "Date", "width": 120},
        {"label": _("متأخر؟"), "fieldname": "is_overdue", "fieldtype": "Data", "width": 80},
        {"label": _("تاريخ الإكمال"), "fieldname": "completion_date", "fieldtype": "Date", "width": 120},
    ]
