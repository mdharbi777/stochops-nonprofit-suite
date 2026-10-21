"""تقارير معزولة بالجمعية + تصدير محوكم (Excel/PDF) مع تدقيق (P4).

المبدأ: الخادم مصدر الحقيقة. التصدير يُشغّل التقرير ضمن جلسة المستخدم عبر
frappe.desk.query_report.run، فيَرِث صلاحية التقرير وعزل الجمعية (كل تقاريرنا
تبني صفوفها عبر frappe.get_list). كل تصدير يُسجَّل حدث «export» في سجل الوصول الحسّاس.
لا تُصدَّر إلا التقارير المُدرَجة صراحةً، وبلا معرّفات لا يُتيحها التقرير أصلاً.
"""

import json

import frappe
from frappe import _
from frappe.utils import today
from frappe.utils.pdf import get_pdf
from frappe.utils.xlsxutils import make_xlsx

from stochops_nonprofit.multitenancy import get_user_charity
from stochops_nonprofit.privacy_core import log_sensitive_access

# التقارير المسموح تصديرها (قائمة بيضاء). الأسماء تطابق سجل التقارير.
ALLOWED_REPORTS = {
    "Executive Summary",
    "Overdue Decisions",
    "Decisions by Committee",
    "Initiatives Overview",
    "Compliance Obligations",
    "Beneficiary Categories",
}


def _normalize_columns(columns):
    out = []
    for c in columns or []:
        if isinstance(c, str):
            parts = c.split(":")
            out.append({"label": parts[0], "fieldname": parts[0], "fieldtype": parts[1] if len(parts) > 1 else "Data"})
        else:
            fn = c.get("fieldname") or c.get("label")
            out.append({"label": c.get("label") or fn, "fieldname": fn, "fieldtype": c.get("fieldtype") or "Data"})
    return out


def _run(report_name, filters):
    if report_name not in ALLOWED_REPORTS:
        frappe.throw(_("تقرير غير معروف أو غير متاح للتصدير."), frappe.PermissionError)
    from frappe.desk.query_report import run as run_report

    # يحترم صلاحية التقرير وعزل الجمعية (التقارير تبني صفوفها عبر get_list)
    res = run_report(report_name, filters=filters) or {}
    return _normalize_columns(res.get("columns")), (res.get("result") or [])


def _value(row, col):
    return row.get(col["fieldname"]) if isinstance(row, dict) else None


def _cell_text(val):
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    return str(val)


@frappe.whitelist()
def export_report(report_name, file_format="Excel", filters=None):
    """يصدّر تقريراً معزولاً إلى Excel أو PDF، ويسجّل حدث التصدير. يعيد الملف للتنزيل."""
    if isinstance(filters, str):
        filters = json.loads(filters or "{}")
    columns, rows = _run(report_name, filters or {})
    charity = get_user_charity()
    log_sensitive_access("export", "Report", report_name, note=file_format, charity=charity)

    base = frappe.scrub(report_name) + "-" + today()
    headers = [c["label"] for c in columns]

    if file_format == "Excel":
        data = [headers]
        for r in rows:
            data.append([_cell_text(_value(r, c)) for c in columns])
        xlsx = make_xlsx(data, "Report")
        frappe.response["filename"] = base + ".xlsx"
        frappe.response["filecontent"] = xlsx.getvalue()
        frappe.response["type"] = "binary"
    elif file_format == "PDF":
        html = _pdf_html(report_name, columns, rows, charity)
        frappe.response["filename"] = base + ".pdf"
        frappe.response["filecontent"] = get_pdf(html)
        frappe.response["type"] = "pdf"
    else:
        frappe.throw(_("صيغة تصدير غير مدعومة."), frappe.ValidationError)


def _pdf_html(report_name, columns, rows, charity):
    charity_name = frappe.db.get_value("Charity", charity, "charity_name") if charity else ""
    label = frappe.db.get_value("Report", report_name, "report_name") or report_name
    head = "".join("<th>%s</th>" % frappe.utils.escape_html(c["label"]) for c in columns)
    body = ""
    for r in rows:
        tds = "".join("<td>%s</td>" % frappe.utils.escape_html(str(_value(r, c) if _value(r, c) is not None else "—")) for c in columns)
        body += "<tr>%s</tr>" % tds
    if not rows:
        body = '<tr><td colspan="%d" style="text-align:center;color:#777">لا توجد بيانات</td></tr>' % max(1, len(columns))
    return """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>
  *{{font-family:"Tajawal","Noto Naskh Arabic",sans-serif}}
  body{{color:#111;margin:24px}}
  .hd{{border-bottom:2px solid #0b1220;padding-bottom:8px;margin-bottom:14px}}
  .hd h1{{font-size:18px;margin:0 0 2px}} .hd .m{{color:#555;font-size:12px}}
  table{{width:100%;border-collapse:collapse;font-size:11px}}
  th,td{{border:1px solid #cbd5e1;padding:6px 8px;text-align:right}}
  th{{background:#0b1220;color:#fff;font-weight:600}}
  tr:nth-child(even) td{{background:#f1f5f9}}
  .ft{{margin-top:12px;color:#777;font-size:10px}}
</style></head><body>
  <div class="hd"><h1>{label}</h1><div class="m">{charity_name} — تاريخ الإصدار: {date}</div></div>
  <table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
  <div class="ft">منصة الفاضل — تقرير معزول بالجمعية. أرقام مُسجّلة للرقابة الإدارية، ليست قيوداً محاسبية.</div>
</body></html>""".format(
        label=frappe.utils.escape_html(label),
        charity_name=frappe.utils.escape_html(charity_name or ""),
        date=today(),
        head=head,
        body=body,
    )
