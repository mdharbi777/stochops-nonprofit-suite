from frappe.model.document import Document


class SensitiveAccessLog(Document):
    """سجل اطّلاع/تصدير/كشف على البيانات الحسّاسة — بيانات وصفية فقط بلا محتوى
    (وثيقة PDPL §7-8). يُنشأ خادمياً، للقراءة فقط، معزول بالجمعية."""

    pass
