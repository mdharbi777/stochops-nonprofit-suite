import frappe
from frappe import _

# تقرير مُجهّل: توزيع المستفيدين حسب الفئة — أعداد مجمّعة فقط بلا أي معرّفات،
# مع إخفاء الخلايا الصغيرة (أقل من العتبة) لتفادي إعادة تحديد الهوية (وثيقة PDPL §9).
# يستخدم frappe.get_list فيحترم الصلاحيات والعزل بالجمعية وACL الحالة.


def execute(filters=None):
    threshold = int(frappe.db.get_single_value("Privacy Configuration", "small_cell_threshold") or 5)
    rows = frappe.get_list("Beneficiary", fields=["social_category"], limit_page_length=0)
    counts = {}
    for b in rows:
        key = b.get("social_category") or _("غير محدّد")
        counts[key] = counts.get(key, 0) + 1

    data = []
    for cat, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n >= threshold:
            data.append({"category": cat, "count_display": str(n)})
        else:
            data.append({"category": cat, "count_display": _("محجوب (< {0})").format(threshold)})

    columns = [
        {"label": _("الفئة"), "fieldname": "category", "fieldtype": "Data", "width": 240},
        {"label": _("العدد (مُجمّع)"), "fieldname": "count_display", "fieldtype": "Data", "width": 160},
    ]
    return columns, data
