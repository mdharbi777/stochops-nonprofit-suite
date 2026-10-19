import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class Grant(Document):
    """منحة من جهة مانحة بشروطها وقيمتها وموعد تقريرها، وربطها بمبادرة.
    القيم المستلمة تسجيل فقط — لا حركة أموال. معزولة بالجمعية."""

    def validate(self):
        for f in ("amount", "amount_received"):
            if self.get(f) and float(self.get(f)) < 0:
                frappe.throw(_("القيم لا تكون سالبة."))
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("تاريخ النهاية لا يكون قبل البداية."))
