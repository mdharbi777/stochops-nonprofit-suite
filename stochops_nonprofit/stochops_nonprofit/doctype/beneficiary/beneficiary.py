import frappe
from frappe import _
from frappe.model.document import Document


class Beneficiary(Document):
    """مستفيد — بيانات تعريف أدنى (data minimization). رقم الهوية حقل مشفّر (Password)
    يُخزَّن مشفّراً ويُحجب، ولا يُجلب في القوائم/الواجهة إلا بكشف إداري. معزول بالجمعية."""

    def validate(self):
        # تحقّق خفيف من صيغة رقم الهوية عند إدخاله فعلياً (10 أرقام) — نتجاهل القيمة المحجوبة.
        nid = self.get("national_id")
        if nid and nid.isdigit() and len(nid) != 10:
            frappe.throw(_("رقم الهوية يجب أن يكون 10 أرقام."))
