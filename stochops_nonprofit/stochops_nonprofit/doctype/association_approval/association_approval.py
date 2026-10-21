import frappe
from frappe.model.document import Document


class AssociationApproval(Document):
    """قرار اعتماد جمعية: مساحة مُهيّأة (Suspended) بانتظار قبول الاتفاقيات ثم التفعيل.
    يُدار تدفّق الحالة عبر وحدة activation (إصدار/قبول/تفعيل) بصلاحيات مشغّل المنصّة."""

    pass
