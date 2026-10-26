"""تفعيل الجمعية بعد الاعتماد وقبول الاتفاقيات (P3).

لا يُنشأ حساب إنتاج إلا عبر هذا المسار المحوكم:
1) إصدار تفعيل (مشغّل): يتطلّب طلباً معتمَداً ووجود شروط استخدام وDPA منشورتين؛ يُهيّئ مساحة
   الجمعية (Suspended) ويُرسل رابط قبول محدوداً لممثّل الجمعية.
2) قبول الاتفاقيات (الممثّل): مربّعان مستقلّان غير مؤشّرين مسبقاً + إقرار تمثيل؛ يُنشئ سجلّي
   قبول إلكتروني (دليل) لكل وثيقة بإصدارها وبصمتها.
3) تفعيل (مشغّل): يُنشئ حساب المدير (بدعوة لضبط كلمة المرور) ويُفعّل الجمعية.
"""
import json

import frappe
from frappe import _
from frappe.utils import get_url, now_datetime

from stochops_nonprofit import signup
from stochops_nonprofit.stochops_nonprofit.doctype.legal_document.legal_document import get_published

OPERATOR_ROLES = {"System Manager", "Stochops Admin"}


def _require_operator():
    if not (OPERATOR_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("هذه العملية مقصورة على مشغّل المنصّة (STOCHOPS)."), frappe.PermissionError)


def _truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on")


@frappe.whitelist()
def issue_activation(application):
    """مشغّل: يصدر رابط قبول وتفعيل لطلب معتمَد. يشترط نشر شروط الاستخدام وDPA."""
    _require_operator()
    app = frappe.get_doc("Association Application", application)
    if app.status != "Approved":
        frappe.throw(_("لا يُصدر التفعيل إلا لطلب معتمَد."), frappe.PermissionError)
    if not (get_published("terms") and get_published("dpa")):
        frappe.throw(_("يجب نشر «شروط الاستخدام المجاني» و«اتفاقية المعالجة (DPA)» قبل إصدار التفعيل."))
    existing = frappe.get_all(
        "Association Approval",
        filters={"application": application, "status": ["!=", "Revoked"]},
        pluck="name",
    )
    if existing:
        frappe.throw(_("يوجد قرار اعتماد قائم لهذا الطلب: {0}").format(existing[0]))

    charity = signup.create_charity(
        app.association_name, registration_number=app.license_number,
        contact_email=app.official_email, contact_mobile=app.phone, status="Suspended",
    )
    appr = frappe.get_doc(
        {
            "doctype": "Association Approval", "application": app.name, "charity": charity.name,
            "status": "Awaiting Acceptance", "representative_name": app.applicant_name,
            "representative_title": app.applicant_title, "representative_email": app.official_email,
            "acceptance_token": frappe.generate_hash(length=24), "max_accounts": 5,
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()

    link = get_url("/nos/accept-agreements?token=" + appr.acceptance_token)
    _send_acceptance(app.official_email, app.applicant_name, link)
    out = {"approval": appr.name, "charity": charity.name}
    if frappe.conf.get("developer_mode"):
        out["acceptance_url"] = link
    return out


def _provision_accounting(charity, admin_user):
    """ينشئ شركة ERPNext معزولة للجمعية ويربط مدير الجمعية بها (User Permission).

    محميّ بوجود erpnext؛ أي فشل يُسجَّل ولا يُفشِل التفعيل (المحاسبة تُهيّأ لاحقاً يدوياً).
    """
    try:
        from stochops_nonprofit.erpnext_bridge import erpnext_enabled, provision_charity_company
        from stochops_nonprofit.multitenancy import sync_user_company_permission

        if not erpnext_enabled():
            return
        company = provision_charity_company(charity)
        if company:
            sync_user_company_permission(admin_user, company)
    except Exception:
        frappe.log_error(f"provision accounting failed for {charity}", "stochops_nonprofit.activation")


def _send_acceptance(email, name, link):
    try:
        frappe.sendmail(
            recipients=[email], sender=signup.SENDER_EMAIL,
            subject=_("قبول الاتفاقيات وتفعيل جمعيتك — منصة الفاضل"),
            message=_(
                "مرحباً {0}،<br><br>تمت الموافقة على طلب جمعيتك للاستفادة من «منصة الفاضل».<br>"
                "لإتمام التفعيل، اطّلع على شروط الاستخدام المجاني واتفاقية معالجة البيانات ووافق عليهما عبر الرابط:<br>"
                "<a href='{1}'>{1}</a>"
            ).format(name or "", link),
            now=False,
        )
    except Exception:
        frappe.log_error("فشل إرسال رابط قبول الاتفاقيات")


def _find_approval(token, status="Awaiting Acceptance"):
    name = frappe.db.get_value(
        "Association Approval", {"acceptance_token": (token or "").strip(), "status": status}, "name"
    )
    if not name:
        frappe.throw(_("رابط القبول غير صالح أو مُستخدم."), frappe.PermissionError)
    return frappe.get_doc("Association Approval", name)


@frappe.whitelist(allow_guest=True)
def get_acceptance_context(token):
    """سياق صفحة القبول: اسم الجمعية + وثيقتا الشروط وDPA المنشورتان (للعرض قبل الموافقة)."""
    appr = _find_approval(token)
    terms, dpa = get_published("terms"), get_published("dpa")
    if not (terms and dpa):
        frappe.throw(_("الاتفاقيات غير منشورة حالياً — تواصل مع المشغّل."))
    assoc = frappe.db.get_value("Association Application", appr.application, "association_name")
    return {
        "approval": appr.name,
        "association_name": assoc,
        "representative_name": appr.representative_name,
        "terms": terms,
        "dpa": dpa,
    }


@frappe.whitelist(allow_guest=True)
def accept_agreements(token, accept_terms, accept_dpa, representative_name, representative_title=None, declaration=None):
    """قبول الاتفاقيتين بمربّعين مستقلّين + إقرار تمثيل. يُنشئ سجلّي قبول إلكتروني (دليل)."""
    appr = _find_approval(token)
    if not (_truthy(accept_terms) and _truthy(accept_dpa)):
        frappe.throw(_("يجب الموافقة على شروط الاستخدام واتفاقية المعالجة كلتيهما."))
    if not _truthy(declaration):
        frappe.throw(_("يجب إقرار تمثيلك للجمعية وتفويضك بالموافقة."))
    if not (representative_name or "").strip():
        frappe.throw(_("اسم الممثّل مطلوب."))

    terms, dpa = get_published("terms"), get_published("dpa")
    if not (terms and dpa):
        frappe.throw(_("الاتفاقيات غير منشورة."))
    sess = (getattr(frappe.local, "request_ip", "") or "")
    decl = "إقرار إلكتروني بتمثيل الجمعية والتفويض بالموافقة على الاتفاقيتين."

    def _accept(doc):
        return frappe.get_doc(
            {
                "doctype": "Legal Acceptance", "charity": appr.charity, "document": doc["name"],
                "representative_name": representative_name.strip(),
                "representative_title": (representative_title or "").strip(),
                "verification_method": "رابط قبول محدود الصلاحية",
                "acceptance_text": decl, "session_info": sess,
            }
        ).insert(ignore_permissions=True)

    ta = _accept(terms)
    da = _accept(dpa)
    appr.terms_acceptance = ta.name
    appr.dpa_acceptance = da.name
    appr.representative_name = representative_name.strip()
    if representative_title:
        appr.representative_title = representative_title.strip()
    appr.accepted_on = now_datetime()
    appr.status = "Accepted"
    appr.save(ignore_permissions=True)
    frappe.db.commit()
    return {"approval": appr.name, "accepted": True}


@frappe.whitelist()
def activate(approval):
    """مشغّل: يفعّل الجمعية بعد قبول الاتفاقيات — ينشئ حساب المدير (بدعوة) ويُفعّل المساحة."""
    _require_operator()
    appr = frappe.get_doc("Association Approval", approval)
    if appr.status != "Accepted":
        frappe.throw(_("لا يُفعّل إلا بعد قبول الاتفاقيات."), frappe.PermissionError)
    app = frappe.get_doc("Association Application", appr.application)
    admin_email = (app.proposed_admin_email or app.official_email or "").strip().lower()
    admin_name = (app.proposed_admin_name or app.applicant_name or "").strip()

    user = signup.create_charity_admin(admin_email, admin_name, appr.charity, mobile=app.phone, enabled=0)
    frappe.db.set_value("Charity", appr.charity, "status", "Active")
    appr.admin_user = user.name
    appr.activated_on = now_datetime()
    appr.status = "Activated"
    appr.save(ignore_permissions=True)
    frappe.db.commit()

    # المرحلة 2.1: تهيئة المحاسبة المعزولة — شركة للجمعية + User Permission للمدير.
    # يُتخطّى بأمان إن لم تُفعّل محاسبة ERPNext في البيئة (توافق خلفي).
    _provision_accounting(appr.charity, user.name)

    # دعوة المدير لضبط كلمة مروره بنفسه (لا كلمة مرور في البريد)
    from stochops_nonprofit.accounts import _invite_token, _send_invite

    link = get_url("/nos/accept-invite?token=" + _invite_token(admin_email, appr.charity))
    _send_invite(admin_email, admin_name, link)
    out = {"charity": appr.charity, "admin": user.name}
    if frappe.conf.get("developer_mode"):
        out["invite_url"] = link
    return out
