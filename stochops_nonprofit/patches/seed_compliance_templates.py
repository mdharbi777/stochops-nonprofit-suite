"""P4 — بذر سجلّات مكتبة قوالب الامتثال (idempotent). القوالب هياكل بتعليمات تعبئة؛
الجمعية مسؤولة عن تعبئتها واعتمادها. الملفات ثابتة تحت public/compliance-templates."""
import frappe

BASE = "/assets/stochops_nonprofit/compliance-templates/"
SRC = "نظام حماية البيانات الشخصية (PDPL) ولائحته التنفيذية — SDAIA"

TEMPLATES = [
    ("beneficiary_privacy_notice", "إشعار خصوصية المستفيدين", "إشعارات الخصوصية", "DOCX", "beneficiary_privacy_notice.docx", "مسؤول حماية البيانات"),
    ("donor_privacy_notice", "إشعار خصوصية المتبرعين", "إشعارات الخصوصية", "DOCX", "donor_privacy_notice.docx", "مسؤول حماية البيانات"),
    ("dpia", "تقييم أثر حماية البيانات (DPIA)", "تقييم الأثر وسجلّ المعالجة", "DOCX", "dpia.docx", "مسؤول حماية البيانات"),
    ("dpia_risk_register", "سجلّ مخاطر DPIA", "تقييم الأثر وسجلّ المعالجة", "XLSX", "dpia_risk_register.xlsx", "مسؤول حماية البيانات"),
    ("ropa", "سجلّ أنشطة المعالجة (ROPA)", "تقييم الأثر وسجلّ المعالجة", "XLSX", "ropa.xlsx", "مسؤول حماية البيانات"),
    ("retention_schedule", "جدول مدد الاحتفاظ", "الاحتفاظ والإتلاف", "XLSX", "retention_schedule.xlsx", "المختص + مسؤول حماية البيانات"),
    ("dpo_assessment", "تقييم وجوب تعيين مسؤول حماية البيانات", "مسؤول حماية البيانات", "DOCX", "dpo_assessment.docx", "مدير الجمعية"),
    ("dpo_appointment", "قرار تعيين مسؤول حماية البيانات", "مسؤول حماية البيانات", "DOCX", "dpo_appointment.docx", "مدير الجمعية"),
    ("incident_policy", "سياسة الاستجابة لحوادث البيانات", "الحوادث", "DOCX", "incident_policy.docx", "مسؤول حماية البيانات"),
    ("incident_register", "سجلّ الحوادث", "الحوادث", "XLSX", "incident_register.xlsx", "مسؤول حماية البيانات"),
    ("rights_procedure", "آلية التعامل مع حقوق أصحاب البيانات", "حقوق الأفراد", "DOCX", "rights_procedure.docx", "مسؤول حماية البيانات"),
    ("rights_request_register", "سجلّ طلبات أصحاب البيانات", "حقوق الأفراد", "XLSX", "rights_request_register.xlsx", "مسؤول حماية البيانات"),
    ("user_authorization", "تفويض المستخدمين والصلاحيات", "الصلاحيات", "DOCX", "user_authorization.docx", "مدير الجمعية"),
]

INSTR = "هيكل بتعليمات تعبئة؛ استبدل كل [ ... ] بمحتوى جمعيتك ولا تترك قيماً افتراضية كأنها حقائق. راجِع المصدر النظامي والمختص، ثم اعتمده داخل الجمعية."


def execute():
    for key, name, cat, fmt, fn, approver in TEMPLATES:
        values = {
            "template_name": name, "category": cat, "file_format": fmt,
            "file_path": BASE + fn, "description": name + " — قالب قابل للتعبئة.",
            "fill_instructions": INSTR, "required_approver": approver, "source_ref": SRC,
            "version": "1.0", "status": "Published",
        }
        if frappe.db.exists("Compliance Template", key):
            doc = frappe.get_doc("Compliance Template", key)
            doc.update(values)
            doc.save(ignore_permissions=True)
        else:
            d = {"doctype": "Compliance Template", "template_key": key}
            d.update(values)
            frappe.get_doc(d).insert(ignore_permissions=True)
    frappe.db.commit()
