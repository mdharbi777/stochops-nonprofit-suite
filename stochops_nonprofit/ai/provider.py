"""طبقة مزوّد الذكاء الاصطناعي — قابلة للاستبدال.

- MockAIProvider: محاكاة محلية بالكامل، بلا أي اتصال خارجي وبلا تكلفة.
- المزوّد يعيد نصاً مقترحاً (مسودة) فقط — لا يعدّل قاعدة البيانات ولا يستدعي أي دالة.
- GATE AI: ربط مزوّد حقيقي مؤجّل إلى قرار مستقل بعد إقرار سياسة البيانات والتكاليف.
"""
import frappe
from frappe import _

TASK_TYPES = ("decision_extraction", "status_summary", "monthly_report_draft")

TASK_LABELS = {
    "decision_extraction": "استخراج مسودة قرارات من نص محضر",
    "status_summary": "تلخيص حالة التنفيذ",
    "monthly_report_draft": "مسودة تقرير شهري",
}

MAX_TEXT = 6000
MAX_LINES = 40


class AIProvider:
    name = "Base"
    online = False

    def generate(self, task_type, context):
        raise NotImplementedError


class MockAIProvider(AIProvider):
    """يعيد قالباً عربياً تجريبياً من السياق الآمن المُعدّ مسبقاً. لا اتصال، لا تكلفة."""

    name = "Mock"
    online = False

    def generate(self, task_type, context):
        if task_type == "decision_extraction":
            return self._decisions(context)
        if task_type == "status_summary":
            return self._status(context)
        if task_type == "monthly_report_draft":
            return self._monthly(context)
        frappe.throw(_("نوع مهمة غير مدعوم."))

    def _decisions(self, ctx):
        lines = ctx.get("lines") or []
        if not lines:
            return "لا يوجد نص كافٍ لاستخراج مسودة قرارات."
        out = ["مسودة قرارات مُستخرَجة (محاكاة — راجِعها وعدّلها، لا تُحفظ تلقائياً):", ""]
        for idx, ln in enumerate(lines, 1):
            out.append(f"{idx}) قرار مقترح: {ln}")
            out.append("   - المسؤول: (يُحدَّد يدوياً) · تاريخ الاستحقاق: (يُحدَّد يدوياً)")
        out.append("")
        out.append("ملاحظة: النص أعلاه مسودة من المساعد ولا يمثّل قراراً معتمداً.")
        return "\n".join(out)

    def _status(self, ctx):
        m = ctx.get("metrics") or {}
        charity = ctx.get("charity") or ""
        return "\n".join([
            f"ملخص حالة التنفيذ — {charity} (محاكاة):",
            "",
            f"- القرارات غير الملغاة: {m.get('decisions_non_cancelled', 0)}",
            f"- المفتوحة وقيد العمل: {m.get('decisions_open_inprogress', 0)}",
            f"- القرارات المتأخرة: {m.get('decisions_overdue', 0)}",
            f"- المبادرات النشطة: {m.get('initiatives_active', 0)}",
            f"- المهام المتأخرة: {m.get('tasks_overdue', 0)}",
            "",
            "توصية (مسودة): راجع القرارات المتأخرة وأسندها، وحدّث حالة المهام المتأخرة.",
            "ملاحظة: الأرقام من قاعدة البيانات ضمن صلاحياتك؛ النص مسودة تحتاج مراجعة بشرية.",
        ])

    def _monthly(self, ctx):
        m = ctx.get("metrics") or {}
        fr = m.get("from_date", "")
        to = m.get("to_date", "")
        return "\n".join([
            f"مسودة تقرير شهري ({fr} إلى {to}) — محاكاة:",
            "",
            f"خلال الفترة بلغت القرارات المكتملة {m.get('decisions_completed_in_period', 0)}،",
            f"مع {m.get('decisions_overdue', 0)} قراراً متأخراً و{m.get('initiatives_active', 0)} مبادرة نشطة.",
            f"إجمالي الميزانيات المخططة {m.get('total_planned_budget', 0)} ريال،",
            f"والصرف المسجّل {m.get('total_actual_spend', 0)} ريال (أرقام تشغيلية يدوية، ليست محاسبية).",
            "",
            "ملاحظة: مسودة مبنية على أرقام طبقة التقارير فقط — لا تُضاف أرقام غير مُدخلة. راجِعها قبل الاعتماد.",
        ])


def get_provider(name="Mock"):
    if name == "Mock":
        return MockAIProvider()
    frappe.throw(_("المزوّد «{0}» غير متاح في هذا الإصدار (GATE AI).").format(name))
