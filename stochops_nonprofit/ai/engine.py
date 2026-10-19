"""محرك المساعد الذكي — نقطة الدخول الوحيدة (whitelisted).

ضوابط الوثيقة (القسم ح + تصميم PDPL):
- موقوف افتراضياً؛ لا يعمل إلا إذا فُعّل في إعدادات المنصّة.
- يرسل الحد الأدنى من البيانات المصرّح بها فقط؛ لا مرفقات ولا أسماء/بيانات مستفيدين.
- البيانات تُقرأ عبر طبقة التقارير/get_list فتُطبَّق الصلاحيات والعزل بالجمعية.
- المحرك لا يعدّل قاعدة البيانات أبداً؛ يعيد نصاً مقترحاً (مسودة) فقط.
- النص الملصق يُعامَل بياناتٍ لا تعليماتٍ (آمن ضد حقن التعليمات).
- يسجّل كل تشغيل (نوع/حالة/مستخدم) بلا تخزين المحتوى أو payload حسّاس.
"""
import frappe
from frappe import _
from frappe.utils import now_datetime

from stochops_nonprofit.ai.provider import MAX_LINES, MAX_TEXT, TASK_LABELS, TASK_TYPES, get_provider
from stochops_nonprofit.dashboard_metrics import compute
from stochops_nonprofit.multitenancy import get_user_charity

AI_ROLES = ("Nonprofit Admin",)


def _settings():
    return {
        "ai_enabled": bool(frappe.db.get_single_value("Nonprofit AI Settings", "ai_enabled")),
        "provider": frappe.db.get_single_value("Nonprofit AI Settings", "provider") or "Mock",
    }


@frappe.whitelist()
def get_ai_status():
    s = _settings()
    return {
        "enabled": s["ai_enabled"],
        "provider": s["provider"],
        "tasks": [{"key": k, "label": TASK_LABELS[k]} for k in TASK_TYPES],
    }


def _require_ai():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("يجب تسجيل الدخول."), frappe.PermissionError)
    roles = set(frappe.get_roles(user))
    if "System Manager" not in roles and not (roles & set(AI_ROLES)):
        frappe.throw(_("استخدام المساعد يتطلّب صلاحية مدير الجمعية."), frappe.PermissionError)
    s = _settings()
    if not s["ai_enabled"]:
        frappe.throw(_("المساعد الذكي موقوف. يُفعَّل من إعدادات المنصّة أولاً."))
    return s


def _clean_lines(text):
    text = (text or "").strip()[:MAX_TEXT]
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[:MAX_LINES]


def _build_context(task_type, text, from_date, to_date):
    if task_type == "decision_extraction":
        lines = _clean_lines(text)
        return {"lines": lines, "ref": f"نص ملصق ({len(lines)} سطر)"}
    if task_type == "status_summary":
        m = compute()
        return {"metrics": m, "charity": get_user_charity(), "ref": "مؤشرات الجمعية"}
    if task_type == "monthly_report_draft":
        m = compute(from_date, to_date)
        return {"metrics": m, "ref": f"ملخص الفترة {m.get('from_date', '')}→{m.get('to_date', '')}"}
    frappe.throw(_("نوع مهمة غير مدعوم."))


def _log(task_type, provider, status, ref):
    try:
        frappe.get_doc(
            {
                "doctype": "AI Run Log",
                "task_type": task_type,
                "provider": provider,
                "status": status,
                "ai_user": frappe.session.user,
                "run_on": now_datetime(),
                "context_ref": (ref or "")[:140],
            }
        ).insert(ignore_permissions=True)  # charity يُضبط عبر before_insert
    except Exception:
        frappe.log_error("AI run log failed", "stochops_nonprofit.ai")


@frappe.whitelist()
def run_task(task_type, text=None, from_date=None, to_date=None):
    s = _require_ai()
    if task_type not in TASK_TYPES:
        frappe.throw(_("نوع مهمة غير مدعوم."))
    context = _build_context(task_type, text, from_date, to_date)
    provider = get_provider(s["provider"])
    try:
        draft = provider.generate(task_type, context)
    except Exception:
        _log(task_type, s["provider"], "Error", context.get("ref"))
        raise
    _log(task_type, s["provider"], "Success", context.get("ref"))
    return {
        "task_type": task_type,
        "label": TASK_LABELS[task_type],
        "provider": s["provider"],
        "draft": draft,
        "caveat": _("مسودة من المساعد — راجِعها بشرياً قبل الاعتماد. لا تُحفظ تلقائياً، ولا تتضمّن بيانات مستفيدين."),
    }
