"""إشعارات داخل التطبيق (قناة System Notification — جرس Frappe).

تستخدم Notification DocType الجاهز من Frappe، بلا أي قناة مدفوعة (SMS/بريد).
تعمل إشعارات «قبل/بعد الموعد» عبر Scheduler؛ وإشعار الإسناد عند الإنشاء مباشرة.
idempotent — تُستدعى من after_install وقابلة لإعادة التشغيل.
"""
import frappe

NOTIFICATIONS = [
    {
        "document_type": "Decision", "event": "New", "field": "decision_owner",
        "subject": "أُسند إليك قرار: {{ doc.title }}",
        "message": "القرار {{ doc.name }} — تاريخ الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Decision", "event": "Days Before", "date": "due_date", "days": 2,
        "field": "decision_owner", "condition": "doc.status not in ['Completed', 'Cancelled']",
        "subject": "قرار يقترب موعده: {{ doc.title }}",
        "message": "الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Decision", "event": "Days After", "date": "due_date", "days": 1,
        "field": "decision_owner", "condition": "doc.status not in ['Completed', 'Cancelled']",
        "subject": "قرار متأخر: {{ doc.title }}",
        "message": "تجاوز تاريخ الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Initiative Task", "event": "New", "field": "assigned_to",
        "subject": "أُسندت إليك مهمة: {{ doc.title }}",
        "message": "المهمة {{ doc.name }} — تاريخ الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Initiative Task", "event": "Days Before", "date": "due_date", "days": 2,
        "field": "assigned_to", "condition": "doc.status not in ['Completed', 'Cancelled']",
        "subject": "مهمة يقترب موعدها: {{ doc.title }}",
        "message": "الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Initiative Task", "event": "Days After", "date": "due_date", "days": 1,
        "field": "assigned_to", "condition": "doc.status not in ['Completed', 'Cancelled']",
        "subject": "مهمة متأخرة: {{ doc.title }}",
        "message": "تجاوز تاريخ الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Compliance Obligation", "event": "Days Before", "date": "due_date", "days": 7,
        "field": "responsible", "condition": "doc.status not in ['مكتمل', 'ملغى']",
        "subject": "التزام يقترب موعده: {{ doc.title }}",
        "message": "الجهة: {{ doc.authority }} — الاستحقاق: {{ doc.due_date }}",
    },
    {
        "document_type": "Compliance Obligation", "event": "Days After", "date": "due_date", "days": 1,
        "field": "responsible", "condition": "doc.status not in ['مكتمل', 'ملغى']",
        "subject": "التزام متأخر: {{ doc.title }}",
        "message": "تجاوز تاريخ الاستحقاق: {{ doc.due_date }} — الجهة: {{ doc.authority }}",
    },
    {
        "document_type": "Contract", "event": "Days Before", "date": "end_date", "days": 30,
        "field": "responsible", "condition": "doc.status not in ['منتهٍ', 'ملغى']",
        "subject": "عقد يقترب انتهاؤه: {{ doc.contract_title }}",
        "message": "تاريخ الانتهاء: {{ doc.end_date }}",
    },
]


def ensure_notifications():
    created = []
    for n in NOTIFICATIONS:
        if frappe.db.exists(
            "Notification", {"subject": n["subject"], "document_type": n["document_type"]}
        ):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Notification",
                "enabled": 1,
                "channel": "System Notification",
                "document_type": n["document_type"],
                "event": n["event"],
                "subject": n["subject"],
                "message": n["message"],
                "recipients": [{"receiver_by_document_field": n["field"]}],
            }
        )
        if n.get("date"):
            doc.date_changed = n["date"]
            doc.days_in_advance = n["days"]
        if n.get("condition"):
            doc.condition = n["condition"]
        doc.insert(ignore_permissions=True)
        created.append(doc.name)
    frappe.db.commit()
    return {"created": created, "total": len(NOTIFICATIONS)}
