"""حوكمة مسارات الاعتماد المالي والإداري (P3) — مشتركة بين طلبات المساعدة والمصروفات والمشتريات.

المبدأ: الخادم مصدر الحقيقة لكل انتقال حالة. تُفرض هنا:
- مسار حالات مسموح (آلة حالات): لا قفزات غير مشروعة ولا تعديل بعد حالة نهائية.
- بوابة الصرف/التنفيذ: الانتقال إلى حالة صرف يتطلّب صلاحية مدير الجمعية.
الإعفاء الوحيد هو مشغّل المنصّة (System Manager / كسر الزجاج)، ويبقى مُسجّلاً عبر «سجل التغييرات».
تُطبَّق القيود عند تغيير الحالة لسجل قائم فقط؛ الإدراج الأوّلي (البذور/الترحيل) غير مقيّد بالمسار.
"""

import frappe
from frappe import _

SUPER_ROLE = "System Manager"
ADMIN_ROLE = "Nonprofit Admin"


def current_roles():
    return set(frappe.get_roles(frappe.session.user))


def payer_separation_enabled(charity):
    """هل تُفعّل هذه الجمعية فصل الصرف عن الاعتماد؟ (إعداد على مستوى Charity، معطّل افتراضياً)."""
    if not charity:
        return False
    return bool(frappe.db.get_value("Charity", charity, "enforce_payer_separation"))


def guard_transition(
    doc,
    allowed,
    disburse_states=None,
    disburse_label="الصرف",
    payer_separation=False,
    approver_field="approved_by",
):
    """يفرض آلة الحالات عند تغيير حقل status لسجل قائم.

    allowed: dict[str, set[str]] — المفتاح حالة حالية، القيمة الحالات المسموح الانتقال إليها.
             الحالة النهائية تُمثَّل بمجموعة فارغة (لا انتقال منها).
    disburse_states: الحالات التي تمثّل «صرفاً/تنفيذاً» وتتطلّب صلاحية مدير الجمعية.
    payer_separation: عند True، يُمنع المُعتمِد (approver_field) من تنفيذ الصرف بنفسه.
    approver_field: اسم الحقل الذي يحمل مُعتمِد الطلب (افتراضياً approved_by).
    """
    if doc.is_new() or not doc.has_value_changed("status"):
        return
    roles = current_roles()
    if SUPER_ROLE in roles:
        return  # كسر الزجاج لمشغّل المنصّة — يبقى في سجل التغييرات
    before = doc.get_doc_before_save()
    old = before.status if before else None
    if old is None:
        return
    new = doc.status
    if new == old:
        return
    if new not in allowed.get(old, set()):
        frappe.throw(
            _("انتقال غير مسموح للحالة: من «{0}» إلى «{1}».").format(old, new),
            frappe.PermissionError,
        )
    if disburse_states and new in disburse_states:
        if ADMIN_ROLE not in roles:
            frappe.throw(
                _("{0} يتطلّب صلاحية مدير الجمعية.").format(disburse_label),
                frappe.PermissionError,
            )
        if payer_separation:
            approver = doc.get(approver_field)
            if approver and approver == frappe.session.user:
                frappe.throw(
                    _(
                        "فصل الصرف عن الاعتماد: لا يُنفّذ «{0}» مَن اعتمد الطلب "
                        "(الصارف يجب أن يكون غير المُعتمِد)."
                    ).format(disburse_label),
                    frappe.PermissionError,
                )
