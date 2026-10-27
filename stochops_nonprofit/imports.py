"""استيراد جماعي محوكم للبيانات الأساسية (CSV) — مستفيدون/متبرعون.

مبدأ العزل: كل سجلّ يُدخَل عبر ORM (`frappe.get_doc(...).insert()`) فتُطبَّق خطّافات
العزل (`before_insert set_charity`) تلقائياً — فلا يمكن حقن سجلّ لجمعية أخرى مهما كان
محتوى الملف. تُقبل الحقول المسموح بها فقط لكل دكتايب (قائمة بيضاء على الخادم)، فلا يمكن
تمرير `charity` أو `status` أو `case_worker` من الملف. كل صفّ يُتحقَّق منه مستقلاً؛ أخطاء
صفٍّ لا توقف البقية، وتُجمَع في تقرير. الحدّ الأقصى للدفعة يمنع الإساءة.

الصلاحية: مدير الجمعية أو منسّق البرامج (أو System Manager للتشغيل) على جمعيته فقط —
نفس صلاحية الإضافة المفردة؛ الإدراج يحترم `has_permission` دون تجاوز.
"""
import json
import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from stochops_nonprofit.multitenancy import get_user_charity

MAX_ROWS = 500

# القائمة البيضاء: الدكتايبات القابلة للاستيراد وحقولها المسموح بها فقط.
# مصدر وحيد للحقيقة: تبني الواجهة منه القالب والتحقّق، ويعيد الخادم التحقّق منه دائماً.
IMPORT_SCHEMAS = {
    "Beneficiary": {
        "label": "المستفيدون",
        "roles": {"Nonprofit Admin", "System Manager", "Program Coordinator"},
        "fields": [
            {"field": "beneficiary_name", "label": "الاسم", "required": True},
            {"field": "national_id", "label": "رقم الهوية (10 أرقام)",
             "pattern": r"^\d{10}$", "pattern_msg": "رقم الهوية يجب أن يكون 10 أرقام."},
            {"field": "phone", "label": "الجوال"},
            {"field": "gender", "label": "الجنس", "options": ["ذكر", "أنثى"]},
            {"field": "social_category", "label": "الفئة",
             "options": ["أرملة", "أيتام", "دخل محدود", "كبار السن", "ذوو إعاقة", "أخرى"]},
            {"field": "family_members_count", "label": "عدد أفراد الأسرة", "type": "int"},
        ],
    },
    "Donor": {
        "label": "المتبرعون",
        "roles": {"Nonprofit Admin", "System Manager", "Program Coordinator"},
        "fields": [
            {"field": "donor_name", "label": "الاسم", "required": True},
            {"field": "donor_type", "label": "النوع", "options": ["فرد", "جهة"]},
            {"field": "phone", "label": "الجوال"},
            {"field": "email", "label": "البريد الإلكتروني"},
            {"field": "notes", "label": "ملاحظات"},
        ],
    },
}


def _require_import_access(doctype):
    schema = IMPORT_SCHEMAS.get(doctype)
    if not schema:
        frappe.throw(_("هذا النوع غير مدعوم للاستيراد."))
    user = frappe.session.user
    if not (schema["roles"] & set(frappe.get_roles(user))):
        frappe.throw(_("الاستيراد الجماعي يتطلّب صلاحية مدير الجمعية أو منسّق البرامج."),
                     frappe.PermissionError)
    charity = get_user_charity(user)
    if not charity and "System Manager" not in frappe.get_roles(user):
        frappe.throw(_("حسابك غير مرتبط بجمعية."), frappe.PermissionError)
    return schema


def _public_schema(schema):
    """نسخة الحقول للواجهة (بلا مجموعة الأدوار الداخلية)."""
    out = []
    for f in schema["fields"]:
        item = {"field": f["field"], "label": f["label"],
                "required": bool(f.get("required")), "type": f.get("type", "text")}
        if f.get("options"):
            item["options"] = f["options"]
        if f.get("pattern"):
            item["pattern"] = f["pattern"]
        out.append(item)
    return out


@frappe.whitelist()
def get_import_schema(doctype):
    """مخطّط الاستيراد لنوعٍ ما — تبني منه الواجهة القالب والحقول. مقيّد بالصلاحية."""
    schema = _require_import_access(doctype)
    return {
        "doctype": doctype,
        "label": schema["label"],
        "max_rows": MAX_ROWS,
        "fields": _public_schema(schema),
    }


def _validate_value(f, raw):
    """يتحقّق من قيمة حقلٍ ويعيدها منقّاة، أو يرفع خطأً بالعربية."""
    v = (raw or "").strip()
    if not v:
        if f.get("required"):
            raise ValueError(_("{0} مطلوب.").format(f["label"]))
        return None
    if f.get("type") == "int":
        try:
            n = int(float(v))
        except (ValueError, TypeError):
            raise ValueError(_("{0} يجب أن يكون رقماً.").format(f["label"]))
        return max(0, n)  # لا قيم سالبة (أعداد/مبالغ)
    if f.get("pattern") and not re.match(f["pattern"], v):
        raise ValueError(f.get("pattern_msg") or _("{0}: قيمة غير صحيحة.").format(f["label"]))
    if f.get("options") and v not in f["options"]:
        raise ValueError(_("{0}: قيمة غير مقبولة (المسموح: {1}).").format(f["label"], "، ".join(f["options"])))
    return v


@frappe.whitelist()
@rate_limit(limit=20, seconds=3600)
def bulk_import(doctype, rows):
    """يستورد دفعةً من السجلّات. `rows` قائمة JSON من القواميس (حقول → قيم).

    يعيد تقريراً: {total, inserted, failed:[{row, error}]}. كل صفّ مستقلّ.
    العزل مفروض بالخطّافات؛ تُقبل الحقول المسموح بها فقط.
    """
    schema = _require_import_access(doctype)
    if isinstance(rows, str):
        rows = json.loads(rows or "[]")
    if not isinstance(rows, list):
        frappe.throw(_("صيغة البيانات غير صحيحة."))
    if not rows:
        frappe.throw(_("لا توجد صفوف للاستيراد."))
    if len(rows) > MAX_ROWS:
        frappe.throw(_("الحدّ الأقصى للدفعة الواحدة {0} صفّاً. قسّم الملف.").format(MAX_ROWS))

    fields = schema["fields"]
    inserted, failed = 0, []
    for idx, raw_row in enumerate(rows, start=1):
        if not isinstance(raw_row, dict):
            failed.append({"row": idx, "error": _("صفّ غير صالح.")})
            continue
        try:
            doc = {"doctype": doctype}
            for f in fields:
                val = _validate_value(f, raw_row.get(f["field"]))
                if val is not None:
                    doc[f["field"]] = val
            # before_insert (العزل) يضبط charity من جلسة المستخدم تلقائياً.
            frappe.get_doc(doc).insert()
            # إثبات كل صفّ ناجح فوراً: يضمن ألا يتراجع عنه فشلُ صفٍّ لاحق.
            frappe.db.commit()
            inserted += 1
        except Exception as exc:
            # تراجع عن عمل الصفّ الفاشل فقط (آخر commit حفظ ما قبله).
            frappe.db.rollback()
            msg = str(getattr(exc, "message", None) or exc) or _("تعذّر الحفظ.")
            failed.append({"row": idx, "error": re.sub(r"<[^>]+>", "", msg).strip()[:200]})
    return {"total": len(rows), "inserted": inserted, "failed": failed}
