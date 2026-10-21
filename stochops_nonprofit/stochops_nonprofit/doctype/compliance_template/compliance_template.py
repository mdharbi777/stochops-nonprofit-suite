import frappe
from frappe.model.document import Document


class ComplianceTemplate(Document):
    """قالب امتثال قابل للتنزيل (هيكل بتعليمات تعبئة). الجمعية مسؤولة عن تعبئته والتحقّق منه
    واعتماده؛ لا يُعدّ معتمداً من STOCHOPS. يديره مشغّل المنصّة؛ تقرؤه حسابات الجمعية."""

    pass


@frappe.whitelist()
def list_templates():
    """قوالب الامتثال المنشورة (لأي مستخدم مُصادَق). مجمّعة حسب الفئة في الواجهة."""
    return frappe.get_all(
        "Compliance Template",
        filters={"status": "Published"},
        fields=["template_key", "template_name", "category", "file_format", "version",
                "file_path", "description", "fill_instructions", "required_approver", "source_ref"],
        order_by="category asc, template_name asc",
        limit_page_length=0,
    )
