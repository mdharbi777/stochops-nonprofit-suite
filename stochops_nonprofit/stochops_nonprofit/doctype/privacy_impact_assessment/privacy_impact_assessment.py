import frappe
from frappe import _
from frappe.model.document import Document


class PrivacyImpactAssessment(Document):
    """تقييم أثر حماية البيانات (DPIA) للأنشطة عالية المخاطر (وثيقة PDPL §6/§12).
    قبول الخطر قرار بشري من المخوّل — لا يُعتمد بلا جهة اعتماد. معزول بالجمعية."""

    def validate(self):
        if self.status == "معتمد" and not (self.approved_by or "").strip():
            frappe.throw(_("اعتماد تقييم الأثر يتطلّب جهة اعتماد بشرية (لا يصدر من الأداة)."))
