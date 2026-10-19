import frappe
from frappe import _
from frappe.utils import getdate, today

# تقرير الالتزامات المحكوم: يعرض الالتزامات وأيامها المتبقية والمتأخر منها.
# يستخدم frappe.get_list فيحترم الصلاحيات والعزل بالجمعية؛ التأخير محسوب لحظياً.

CLOSED = ("مكتمل", "ملغى")


def execute(filters=None):
    filters = filters or {}
    conditions = {}
    if filters.get("status"):
        conditions["status"] = filters["status"]
    if filters.get("obligation_type"):
        conditions["obligation_type"] = filters["obligation_type"]

    rows = frappe.get_list(
        "Compliance Obligation",
        filters=conditions,
        fields=["name", "title", "obligation_type", "authority", "responsible",
                "due_date", "status", "completed_on"],
        order_by="due_date asc",
    )
    t = getdate(today())
    for r in rows:
        if r.get("due_date"):
            days = (getdate(r["due_date"]) - t).days
            r["days_remaining"] = days
            r["overdue"] = _("نعم") if (days < 0 and r["status"] not in CLOSED) else _("لا")
        else:
            r["days_remaining"] = None
            r["overdue"] = _("لا")
    return get_columns(), rows


def get_columns():
    return [
        {"label": _("الالتزام"), "fieldname": "name", "fieldtype": "Link", "options": "Compliance Obligation", "width": 130},
        {"label": _("العنوان"), "fieldname": "title", "fieldtype": "Data", "width": 220},
        {"label": _("النوع"), "fieldname": "obligation_type", "fieldtype": "Data", "width": 120},
        {"label": _("الجهة"), "fieldname": "authority", "fieldtype": "Data", "width": 160},
        {"label": _("المسؤول"), "fieldname": "responsible", "fieldtype": "Link", "options": "User", "width": 160},
        {"label": _("الاستحقاق"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
        {"label": _("أيام متبقية"), "fieldname": "days_remaining", "fieldtype": "Int", "width": 90},
        {"label": _("متأخر؟"), "fieldname": "overdue", "fieldtype": "Data", "width": 80},
        {"label": _("الحالة"), "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]
