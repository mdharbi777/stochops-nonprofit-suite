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
    {
        "document_type": "Privacy Rights Request", "event": "Days Before", "date": "due_date", "days": 5,
        "field": "assigned_to", "condition": "doc.status not in ['مكتمل', 'مرفوض جزئياً', 'مرفوض']",
        "subject": "طلب حق يقترب موعده النظامي: {{ doc.name }}",
        "message": "نوع الطلب: {{ doc.request_type }} — الاستحقاق: {{ doc.due_date }}",
    },
    # --- تنبيهات بريدية مختصرة للطاقم (P6.3) — معرّف السجل ورابط الدخول فقط، بلا بيانات مستفيد/مبالغ/أسماء ---
    {
        "channel": "Email", "document_type": "Decision", "event": "New", "field": "decision_owner",
        "subject": "منصة الفاضل: عنصر مُسند إليك",
        "message": "أُسند إليك عنصر ({{ doc.name }}). ادخل منصّة الفاضل للتفاصيل: {{ frappe.utils.get_url() }}/nos",
    },
    {
        "channel": "Email", "document_type": "Initiative Task", "event": "New", "field": "assigned_to",
        "subject": "منصة الفاضل: مهمة مُسندة إليك",
        "message": "أُسندت إليك مهمة ({{ doc.name }}). ادخل منصّة الفاضل للتفاصيل: {{ frappe.utils.get_url() }}/nos",
    },
    {
        "channel": "Email", "document_type": "Decision", "event": "Days Before", "date": "due_date", "days": 2,
        "field": "decision_owner", "condition": "doc.status not in ['Completed', 'Cancelled']",
        "subject": "منصة الفاضل: موعد عنصر يقترب",
        "message": "لديك عنصر يقترب موعده ({{ doc.name }}). ادخل للمتابعة: {{ frappe.utils.get_url() }}/nos",
    },
    {
        "channel": "Email", "document_type": "Initiative Task", "event": "Days Before", "date": "due_date", "days": 2,
        "field": "assigned_to", "condition": "doc.status not in ['Completed', 'Cancelled']",
        "subject": "منصة الفاضل: موعد مهمة يقترب",
        "message": "لديك مهمة يقترب موعدها ({{ doc.name }}). ادخل للمتابعة: {{ frappe.utils.get_url() }}/nos",
    },
    {
        "channel": "Email", "document_type": "Expense Request", "event": "Value Change", "value_changed": "status",
        "field": "requested_by", "condition": "doc.status in ['معتمد', 'مرفوض']",
        "subject": "منصة الفاضل: تم البتّ في طلبك",
        "message": "تم البتّ في طلبك ({{ doc.name }}). ادخل للتفاصيل: {{ frappe.utils.get_url() }}/nos",
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
                "channel": n.get("channel", "System Notification"),
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
        if n.get("value_changed"):
            doc.value_changed = n["value_changed"]
        if n.get("condition"):
            doc.condition = n["condition"]
        doc.insert(ignore_permissions=True)
        created.append(doc.name)
    frappe.db.commit()
    return {"created": created, "total": len(NOTIFICATIONS)}
