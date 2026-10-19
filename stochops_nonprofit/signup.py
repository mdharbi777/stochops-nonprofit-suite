"""التسجيل الذاتي للجمعية — مُقوّى للإطلاق.

الحماية: captcha حسابي مُوقّع (بلا خدمة خارجية) + تحديد معدّل (rate limit) +
تأكيد بريد عبر رابط مُوقّع (يُرسل بالبريد؛ يحتاج SMTP في الإنتاج).
المستخدم يُنشأ معطّلاً حتى يؤكّد بريده.
"""
import base64
import hashlib
import hmac
import json
import random
import time

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_url, validate_email_address

ADMIN_ROLE = "Nonprofit Admin"
MIN_PASSWORD = 8


# ---------- توقيع الرموز (HMAC، بلا حالة مخزّنة) ----------
def _secret():
    return (frappe.conf.get("encryption_key") or frappe.conf.get("secret_key") or "stochops-nos-fallback")


def _sign(payload):
    msg = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(_secret().encode(), msg, hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(msg).decode().rstrip("=") + "." + sig


def _unsign(token):
    try:
        b64, sig = (token or "").split(".")
        msg = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
        if not hmac.compare_digest(sig, hmac.new(_secret().encode(), msg, hashlib.sha256).hexdigest()):
            return None
        return json.loads(msg)
    except Exception:
        return None


# ---------- Captcha حسابي ----------
@frappe.whitelist(allow_guest=True)
def get_captcha():
    a, b = random.randint(1, 9), random.randint(1, 9)
    return {"question": f"{a} + {b} =", "token": _sign({"k": "captcha", "s": a + b, "exp": int(time.time()) + 600})}


def _check_captcha(token, answer):
    p = _unsign(token)
    if not p or p.get("k") != "captcha":
        frappe.throw(_("رمز التحقّق غير صالح — حدّث الصفحة."))
    if int(time.time()) > p.get("exp", 0):
        frappe.throw(_("انتهت صلاحية التحقّق — حدّث الصفحة."))
    try:
        ok = int(answer) == int(p["s"])
    except (ValueError, TypeError):
        ok = False
    if not ok:
        frappe.throw(_("إجابة التحقّق غير صحيحة."))


# ---------- تأكيد البريد ----------
def _verify_token(email):
    return _sign({"k": "verify", "email": email, "exp": int(time.time()) + 3 * 24 * 3600})


def _send_verification(email, full_name):
    link = get_url("/nos/verify?token=" + _verify_token(email))
    try:
        frappe.sendmail(
            recipients=[email],
            subject=_("تأكيد تسجيل جمعيتك — STOCHOPS"),
            message=_(
                "مرحباً {0}،<br><br>لتفعيل حساب جمعيتك اضغط الرابط التالي:<br>"
                "<a href='{1}'>{1}</a><br><br>الرابط صالح لمدة 3 أيام."
            ).format(full_name, link),
            now=False,
        )
    except Exception:
        frappe.log_error("فشل إرسال بريد التأكيد")  # الإرسال يحتاج SMTP مُعدّاً
    return link


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=8, seconds=3600)
def register_charity(
    charity_name, admin_full_name, admin_email, password,
    captcha_token=None, captcha_answer=None, admin_mobile=None, registration_number=None,
):
    _check_captcha(captcha_token, captcha_answer)

    charity_name = (charity_name or "").strip()
    admin_full_name = (admin_full_name or "").strip()
    admin_email = (admin_email or "").strip().lower()

    if not (charity_name and admin_full_name and admin_email and password):
        frappe.throw(_("الحقول المطلوبة: اسم الجمعية، اسم المدير، البريد، كلمة المرور."))
    validate_email_address(admin_email, throw=True)
    if len(password) < MIN_PASSWORD:
        frappe.throw(_("كلمة المرور يجب ألا تقل عن {0} أحرف.").format(MIN_PASSWORD))
    if frappe.db.exists("Charity", charity_name):
        frappe.throw(_("اسم الجمعية مُستخدم مسبقاً."))
    if frappe.db.exists("User", admin_email):
        frappe.throw(_("هذا البريد مُستخدم مسبقاً."))

    charity = frappe.get_doc(
        {
            "doctype": "Charity", "charity_name": charity_name, "registration_number": registration_number,
            "contact_email": admin_email, "contact_mobile": admin_mobile, "status": "Active",
        }
    ).insert(ignore_permissions=True)

    user = frappe.get_doc(
        {
            "doctype": "User", "email": admin_email, "first_name": admin_full_name, "mobile_no": admin_mobile,
            "language": "ar", "time_zone": "Asia/Riyadh", "enabled": 0,  # معطّل حتى تأكيد البريد
            "send_welcome_email": 0, "new_password": password,
        }
    ).insert(ignore_permissions=True)
    user.add_roles(ADMIN_ROLE)
    frappe.db.set_value("User", user.name, "charity", charity.name)
    frappe.db.commit()

    link = _send_verification(admin_email, admin_full_name)
    result = {"charity": charity.name, "admin": user.name, "pending_verification": True}
    if frappe.conf.get("developer_mode"):
        result["verify_url"] = link  # للتجربة محلياً فقط (بلا SMTP)
    return result


@frappe.whitelist(allow_guest=True)
def confirm_email(token):
    p = _unsign(token)
    if not p or p.get("k") != "verify":
        frappe.throw(_("رابط التأكيد غير صالح."))
    if int(time.time()) > p.get("exp", 0):
        frappe.throw(_("انتهت صلاحية رابط التأكيد — سجّل من جديد."))
    email = p["email"]
    if not frappe.db.exists("User", email):
        frappe.throw(_("الحساب غير موجود."))
    frappe.db.set_value("User", email, "enabled", 1)
    frappe.db.commit()
    return {"email": email, "verified": True}
