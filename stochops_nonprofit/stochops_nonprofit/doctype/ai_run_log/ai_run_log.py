from frappe.model.document import Document


class AIRunLog(Document):
    """سجل تشغيل المساعد الذكي — بيانات وصفية فقط (نوع/حالة/مستخدم/وقت)،
    بلا تخزين المحتوى أو أي payload حسّاس. معزول بالجمعية مثل بقية البيانات."""

    pass
