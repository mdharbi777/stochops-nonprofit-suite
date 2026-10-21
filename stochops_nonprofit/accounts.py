"""إدارة حسابات الجمعية — مدير الجمعية ينشئ/يدير حتى `max_accounts` (5) حسابات.

كل العمليات مقيّدة بجمعية المستخدم، وبأدوار مسموحة فقط (لا Stochops Admin).
"""
import time

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_url, validate_email_address

from stochops_nonprofit.multitenancy import get_user_charity

ALLOWED_ROLES = [
    "Nonprofit Admin",
    "Executive Viewer",
    "Committee Coordinator",
    "Program Coordinator",
]
MIN_PASSWORD = 8
INVITE_TTL = 3 * 24 * 3600  # 3 أيام


def _log_perm(email, note):
    try:
        from stochops_nonprofit.privacy_core import log_sensitive_access

        log_sensitive_access("permission_change", "User", email, note=(note or "")[:140])
    except Exception:
        pass


def _require_charity_admin():
    user = frappe.session.user
    if "Nonprofit Admin" not in frappe.get_roles(user):
        frappe.throw(_("هذه العملية تتطلب صلاحية مدير الجمعية."), frappe.PermissionError)
    charity = get_user_charity(user)
    if not charity:
        frappe.throw(_("حسابك غير مرتبط بجمعية."), frappe.PermissionError)
    return charity


def _charity_roles(email):
    roles = set(frappe.get_roles(email))
    return [r for r in ALLOWED_ROLES if r in roles]


@frappe.whitelist()
def list_accounts():
    charity = _require_charity_admin()
    max_accounts = frappe.db.get_value("Charity", charity, "max_accounts") or 5
    users = frappe.get_all(
        "User", filters={"charity": charity}, fields=["name", "full_name", "enabled"], order_by="creation asc"
    )
    for u in users:
        u["roles"] = _charity_roles(u["name"])
    return {
        "charity": charity,
        "max_accounts": max_accounts,
        "used": len(users),
        "remaining": max(0, max_accounts - len(users)),
        "accounts": users,
    }


def _precheck_account(charity, full_name, email, role):
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    if role not in ALLOWED_ROLES:
        frappe.throw(_("الدور غير مسموح."))
    if not (full_name and email):
        frappe.throw(_("الاسم والبريد مطلوبان."))
    validate_email_address(email, throw=True)
    if frappe.db.exists("User", email):
        frappe.throw(_("هذا البريد مُستخدم مسبقاً."))
    max_accounts = frappe.db.get_value("Charity", charity, "max_accounts") or 5
    current = frappe.db.count("User", {"charity": charity})
    if current >= max_accounts:
        frappe.throw(_("بلغت الحد الأقصى لحسابات الجمعية ({0}).").format(max_accounts))
    return full_name, email, max_accounts, current


def _new_user(email, full_name, role, charity, mobile=None, password=None, enabled=1):
    doc = {
        "doctype": "User", "email": email, "first_name": full_name, "mobile_no": mobile,
        "language": "ar", "time_zone": "Asia/Riyadh", "send_welcome_email": 0, "enabled": enabled,
    }
    if password:
        doc["new_password"] = password
    user = frappe.get_doc(doc).insert(ignore_permissions=True)
    user.add_roles(role)
    frappe.db.set_value("User", user.name, "charity", charity)
    _log_perm(user.name, f"create {role} ({'invite' if not password else 'direct'})")
    frappe.db.commit()
    return user


@frappe.whitelist()
def create_account(full_name, email, role, password=None, mobile=None):
    """متوافق للخلف: مع كلمة مرور يُنشئ حساباً مفعّلاً مباشرة؛ وبدونها يحوّل لمسار الدعوة (P2)."""
    charity = _require_charity_admin()
    if not password:
        return invite_account(full_name, email, role, mobile=mobile)
    full_name, email, max_accounts, current = _precheck_account(charity, full_name, email, role)
    if len(password) < MIN_PASSWORD:
        frappe.throw(_("كلمة المرور يجب ألا تقل عن {0} أحرف.").format(MIN_PASSWORD))
    user = _new_user(email, full_name, role, charity, mobile=mobile, password=password, enabled=1)
    return {"account": user.name, "role": role, "remaining": max(0, max_accounts - (current + 1))}


def _invite_token(email, charity):
    from stochops_nonprofit.signup import _sign

    return _sign({"k": "invite", "email": email, "charity": charity, "exp": int(time.time()) + INVITE_TTL})


@frappe.whitelist()
def invite_account(full_name, email, role, mobile=None):
    """المسار المفضّل (PDPL §8): ينشئ الحساب معطّلاً بلا كلمة مرور ويرسل دعوة
    برابط أحادي ليضبط المدعو كلمة مروره بنفسه — دون إرسال كلمة مرور في البريد."""
    charity = _require_charity_admin()
    full_name, email, max_accounts, current = _precheck_account(charity, full_name, email, role)
    user = _new_user(email, full_name, role, charity, mobile=mobile, password=None, enabled=0)
    link = get_url("/nos/accept-invite?token=" + _invite_token(email, charity))
    _send_invite(email, full_name, link)
    out = {"account": user.name, "role": role, "remaining": max(0, max_accounts - (current + 1)), "invited": True}
    if frappe.conf.get("developer_mode"):
        out["invite_url"] = link
    return out


def _send_invite(email, full_name, link):
    from stochops_nonprofit.signup import SENDER_EMAIL

    try:
        frappe.sendmail(
            recipients=[email], sender=SENDER_EMAIL,
            subject=_("دعوة للانضمام إلى جمعيتك على منصة الفاضل"),
            message=_(
                "مرحباً {0}،<br><br>تمت دعوتك للانضمام إلى فريق جمعيتك على «منصة الفاضل».<br>"
                "اضبط كلمة مرورك عبر الرابط التالي (صالح 3 أيام، لمرة واحدة):<br>"
                "<a href='{1}'>{1}</a>"
            ).format(full_name, link),
            now=False,
        )
    except Exception:
        frappe.log_error("فشل إرسال دعوة الحساب")  # يحتاج SMTP مُعدّاً لـ ops@stochops.com


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=3600)
def accept_invite(token, password):
    from stochops_nonprofit.signup import _unsign

    p = _unsign(token)
    if not p or p.get("k") != "invite":
        frappe.throw(_("رابط الدعوة غير صالح."))
    if int(time.time()) > p.get("exp", 0):
        frappe.throw(_("انتهت صلاحية الدعوة — اطلب دعوة جديدة."))
    email = p["email"]
    if not frappe.db.exists("User", email):
        frappe.throw(_("الحساب غير موجود."))
    if len(password or "") < MIN_PASSWORD:
        frappe.throw(_("كلمة المرور يجب ألا تقل عن {0} أحرف.").format(MIN_PASSWORD))
    user = frappe.get_doc("User", email)
    user.new_password = password
    user.enabled = 1
    user.save(ignore_permissions=True)
    frappe.db.commit()
    return {"email": email, "activated": True}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=3600)
def request_password_reset(email):
    """استعادة كلمة المرور عبر رابط Frappe الآمن (أحادي، قصير العمر) دون إفشاء وجود الحساب."""
    email = (email or "").strip().lower()
    generic = {"ok": True, "message": _("إن كان البريد مسجّلاً فستصلك رسالة لإعادة التعيين.")}
    if not email or not frappe.db.exists("User", email):
        return generic
    try:
        frappe.get_doc("User", email).reset_password(send_email=True)
    except Exception:
        frappe.log_error("password reset request failed")
    return generic


@frappe.whitelist()
def get_charity_settings():
    """هوية الجمعية وإعداداتها (للعرض في صفحة الإعدادات). مدير الجمعية فقط."""
    charity = _require_charity_admin()
    data = frappe.db.get_value(
        "Charity",
        charity,
        ["charity_name", "registration_number", "status", "contact_email", "contact_mobile",
         "max_accounts", "expense_approval_limit"],
        as_dict=True,
    )
    data["used"] = frappe.db.count("User", {"charity": charity})
    return data


@frappe.whitelist()
def update_charity_settings(registration_number=None, contact_email=None, contact_mobile=None,
                            expense_approval_limit=None):
    """تحديث الحقول القابلة للتغيير في هوية الجمعية. مدير الجمعية فقط، على جمعيته فقط.
    الاسم/الحالة/حد الحسابات تُدار من منصّة STOCHOPS (غير قابلة للتعديل هنا)."""
    charity = _require_charity_admin()
    updates = {}
    if registration_number is not None:
        updates["registration_number"] = (registration_number or "").strip()
    if contact_email is not None:
        email = (contact_email or "").strip().lower()
        if email:
            validate_email_address(email, throw=True)
        updates["contact_email"] = email
    if contact_mobile is not None:
        updates["contact_mobile"] = (contact_mobile or "").strip()
    if expense_approval_limit is not None:
        limit = float(expense_approval_limit or 0)
        if limit < 0:
            frappe.throw(_("حدّ الاعتماد لا يكون سالباً."))
        updates["expense_approval_limit"] = limit
    if updates:
        frappe.db.set_value("Charity", charity, updates)
        frappe.db.commit()
    return {"charity": charity, "updated": list(updates.keys())}


@frappe.whitelist()
def onboarding_status():
    """حالة رحلة التهيئة للجمعية (مدير الجمعية فقط، معزولة). تُحتسب من البيانات دون حقل مخزّن:
    - الهوية: رقم التسجيل + بريد التواصل.
    - حدّ الاعتماد المالي: expense_approval_limit > 0.
    - الفريق: دعوة عضو واحد على الأقل (اختياري، لا يمنع الاكتمال).
    «مكتملة» = الهوية + حدّ الاعتماد (الأساسيان)."""
    charity = _require_charity_admin()
    data = frappe.db.get_value(
        "Charity",
        charity,
        ["charity_name", "registration_number", "contact_email", "contact_mobile",
         "expense_approval_limit", "max_accounts", "onboarding_completed"],
        as_dict=True,
    )
    used = frappe.db.count("User", {"charity": charity})
    identity_done = bool((data.get("registration_number") or "").strip() and (data.get("contact_email") or "").strip())
    limit_done = float(data.get("expense_approval_limit") or 0) > 0
    team_done = used > 1
    steps_done = sum([identity_done, limit_done, team_done])
    return {
        "charity": charity,
        "charity_name": data.get("charity_name"),
        "registration_number": data.get("registration_number") or "",
        "contact_email": data.get("contact_email") or "",
        "contact_mobile": data.get("contact_mobile") or "",
        "expense_approval_limit": data.get("expense_approval_limit") or 0,
        "accounts_used": used,
        "max_accounts": data.get("max_accounts") or 5,
        "identity_done": identity_done,
        "limit_done": limit_done,
        "team_done": team_done,
        "steps_done": steps_done,
        "steps_total": 3,
        "can_finish": identity_done,
        "complete": bool(data.get("onboarding_completed")),
    }


@frappe.whitelist()
def complete_onboarding():
    """يُنهي رحلة التهيئة (مدير الجمعية فقط). يشترط ضبط هوية الجمعية أولاً.
    حدّ الاعتماد له قيمة افتراضية معقولة يراجعها المدير في الرحلة."""
    charity = _require_charity_admin()
    reg, email = frappe.db.get_value("Charity", charity, ["registration_number", "contact_email"])
    if not ((reg or "").strip() and (email or "").strip()):
        frappe.throw(_("أكمل هوية الجمعية (رقم التسجيل وبريد التواصل) قبل إنهاء التهيئة."))
    frappe.db.set_value("Charity", charity, "onboarding_completed", 1)
    frappe.db.commit()
    return {"charity": charity, "complete": True}


@frappe.whitelist()
def set_account_enabled(email, enabled):
    charity = _require_charity_admin()
    email = (email or "").strip().lower()
    if frappe.db.get_value("User", email, "charity") != charity:
        frappe.throw(_("لا تملك صلاحية على هذا الحساب."), frappe.PermissionError)
    if email == frappe.session.user:
        frappe.throw(_("لا يمكنك تعطيل حسابك الحالي."))
    frappe.db.set_value("User", email, "enabled", 1 if int(enabled) else 0)
    _log_perm(email, "enable" if int(enabled) else "disable")
    frappe.db.commit()
    return {"email": email, "enabled": bool(int(enabled))}
