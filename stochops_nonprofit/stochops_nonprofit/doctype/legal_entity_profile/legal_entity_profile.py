import frappe
from frappe.model.document import Document


class LegalEntityProfile(Document):
    """هوية المشغّل القانونية (مفرد). لا يُعلَن اعتماد قانوني قبل التحقّق الفعلي،
    ولا يُعرض رقم هوية المالك في الصفحات العامة — يُعرض الاسم المعروض علناً فقط."""

    pass
