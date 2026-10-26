import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from stochops_nonprofit.governance import guard_transition

# آلة حالات المنحة: «مرفوضة» و«مغلقة» نهائيتان.
STATUS_FLOW = {
    "مقترحة": {"مقدَّمة", "معتمدة", "مرفوضة", "مغلقة"},
    "مقدَّمة": {"معتمدة", "مرفوضة", "مغلقة"},
    "معتمدة": {"مغلقة"},
    "مرفوضة": set(),
    "مغلقة": set(),
}


class Grant(Document):
    """منحة من جهة مانحة بشروطها وقيمتها وموعد تقريرها، وربطها بمبادرة.
    القيم المستلمة تسجيل فقط — لا حركة أموال. معزولة بالجمعية."""

    def validate(self):
        guard_transition(self, STATUS_FLOW)
        for f in ("amount", "amount_received"):
            if self.get(f) and float(self.get(f)) < 0:
                frappe.throw(_("القيم لا تكون سالبة."))
        if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
            frappe.throw(_("تاريخ النهاية لا يكون قبل البداية."))
