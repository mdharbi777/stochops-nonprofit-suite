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
# المُرسِل التشغيلي لرسائل النظام (بريد قائم عبر منتجات STOCHOPS). يحتاج حساب SMTP
# مُعدّاً لهذا العنوان في الإنتاج (انظر deploy/README). محلياً يُعاد الرابط مباشرة.
SENDER_EMAIL = "ops@stochops.com"


# ---------- توقيع الرموز (HMAC، بلا حالة مخزّنة) ----------
def _secret():
    # fail-closed: لا سرّ احتياطي ثابت (قابل للتخمين) — يُرفض التوقيع إن غاب المفتاح.
    key = frappe.conf.get("encryption_key") or frappe.conf.get("secret_key")
    if not key:
        frappe.throw(_("تعذّر توقيع الرمز: مفتاح التشفير غير مُهيّأ على الموقع."))
    return key


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
@rate_limit(limit=40, seconds=3600)
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
            sender=SENDER_EMAIL,
            subject=_("تأكيد تسجيل جمعيتك — منصة الفاضل"),
            message=_(
                "مرحباً {0}،<br><br>شكراً لتسجيلك في «منصة الفاضل» لإدارة الجمعيات الخيرية.<br>"
                "لتفعيل حساب جمعيتك اضغط الرابط التالي:<br>"
                "<a href='{1}'>{1}</a><br><br>الرابط صالح لمدة 3 أيام."
            ).format(full_name, link),
            now=False,
        )
    except Exception:
        frappe.log_error("فشل إرسال بريد التأكيد")  # الإرسال يحتاج SMTP مُعدّاً لـ ops@stochops.com
    return link


# ---------- تهيئة الجمعية والمدير (داخلي، يُعاد استخدامه في التفعيل المحوكم P3) ----------
def create_charity(charity_name, registration_number=None, contact_email=None, contact_mobile=None, status="Suspended"):
    """ينشئ كيان جمعية. الافتراضي Suspended (مساحة مُهيّأة غير مفعّلة حتى إتمام القبول والتفعيل)."""
    charity_name = (charity_name or "").strip()
    if not charity_name:
        frappe.throw(_("اسم الجمعية مطلوب."))
    if frappe.db.exists("Charity", charity_name):
        frappe.throw(_("اسم الجمعية مُستخدم مسبقاً."))
    return frappe.get_doc(
        {
            "doctype": "Charity", "charity_name": charity_name, "registration_number": registration_number,
            "contact_email": (contact_email or "").strip().lower() or None,
            "contact_mobile": contact_mobile, "status": status,
        }
    ).insert(ignore_permissions=True)


def create_charity_admin(email, full_name, charity, mobile=None, enabled=0):
    """ينشئ مدير جمعية (معطّلاً افتراضياً حتى يضبط كلمة مروره عبر دعوة). يربطه بالجمعية ودور المدير."""
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    if not (email and full_name):
        frappe.throw(_("اسم المدير وبريده مطلوبان."))
    validate_email_address(email, throw=True)
    if frappe.db.exists("User", email):
        frappe.throw(_("هذا البريد مُستخدم مسبقاً."))
    user = frappe.get_doc(
        {
            "doctype": "User", "email": email, "first_name": full_name, "mobile_no": mobile,
            "language": "ar", "time_zone": "Asia/Riyadh", "enabled": enabled, "send_welcome_email": 0,
        }
    ).insert(ignore_permissions=True)
    user.add_roles(ADMIN_ROLE)
    frappe.db.set_value("User", user.name, "charity", charity)
    return user


@frappe.whitelist(allow_guest=True)
def register_charity(*args, **kwargs):
    """التسجيل الذاتي متوقّف (P3): القبول انتقائي. لا يُنشأ حساب إنتاج إلا بعد اعتماد
    طلب الاستفادة وقبول الاتفاقيات والتفعيل من مشغّل المنصّة."""
    frappe.throw(
        _("التسجيل الذاتي متوقّف. تقدّم بطلب استفادة عبر /apply، ويُفعّل حسابك بعد الاعتماد وقبول الاتفاقيات."),
        frappe.PermissionError,
    )


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=3600)
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
