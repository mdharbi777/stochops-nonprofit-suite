import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class PrivacyConfiguration(Document):
    """إعدادات الخصوصية على مستوى المنصّة + بوابة إنتاج البيانات الحقيقية.
    البوابة مغلقة افتراضياً؛ فتحها يتطلّب مسؤول خصوصية ونسخة سياسة، ويُختم خادمياً.
    اجتياز الكود ليس امتثالاً قانونياً (القسم 0-6 من وثيقة PDPL)."""

    def validate(self):
        # وضع التجربة لا يسمح بفتح بوابة الإنتاج إطلاقاً (حظر خادمي)
        if self.production_privacy_gate and (self.deployment_mode or "PILOT_SANDBOX") == "PILOT_SANDBOX":
            frappe.throw(
                _("وضع PILOT_SANDBOX لا يسمح بفتح بوابة الإنتاج. انتقل إلى PRODUCTION بعد استيفاء الاعتمادات.")
            )
        if self.production_privacy_gate:
            if not self.default_privacy_officer or not (self.platform_privacy_policy_version or "").strip():
                frappe.throw(
                    _("فتح بوابة الإنتاج يتطلّب تعيين مسؤول خصوصية وإصدار سياسة خصوصية معتمد أولاً.")
                )
            # لا يُفتح الإنتاج قبل توقيع الاتفاقيات واعتماد تقييمات الأثر وتوثيق الضوابط
            if not (self.dpa_signed_ack and self.dpia_approved_ack and self.security_controls_ack):
                frappe.throw(
                    _("فتح بوابة الإنتاج يتطلّب إقرار: توقيع DPA + اعتماد DPIA + توثيق ضوابط الأمن. لا يُتجاوز أي شرط.")
                )
            if self.has_value_changed("production_privacy_gate"):
                self.gate_opened_on = now_datetime()
                self.gate_opened_by = frappe.session.user
        else:
            self.gate_opened_on = None
            self.gate_opened_by = None
        # الأعلام الحقيقية لا تُفتح والبوابة مغلقة
        if not self.production_privacy_gate and (
            self.beneficiary_real_data_enabled or self.donor_real_data_enabled
        ):
            frappe.throw(_("لا يمكن تمكين بيانات حقيقية والبوابة مغلقة."))
