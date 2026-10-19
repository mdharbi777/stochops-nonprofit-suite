# تشغيل البريد عبر Resend (P6.3) — التجربة التقنية

> المزوّد المعتمد: **Resend** (الموجود بالفعل). **لا Brevo، ولا مزوّد جديد.** الحالة: `PILOT_SANDBOX` — بيانات مصطنعة، عناوين اختبارية يملكها الفريق.
> **المفتاح لا يُحفظ في المستودع** — يُضبط عبر إعداد الموقع/حساب البريد فقط.

## 1. إعداد Frappe SMTP (Resend)
الطريقة الموصى بها: **Email Account** في Frappe (Desk → Email Account) بالقيم:

| الحقل | القيمة |
|---|---|
| Email Address / From | `ops@stochops.com` (بعد توثيق نطاق stochops.com والمرسِل في Resend) |
| Outgoing (SMTP) | مفعّل |
| SMTP Server | `smtp.resend.com` |
| Port | `465` + **SSL مفعّل** (أو منفذ TLS وفق توثيق Resend) |
| Username | `resend` |
| Password | **مفتاح Resend API للإرسال** (SMTP) — يُدخل في الواجهة فقط، لا في git |
| Default Outgoing | نعم |

بديل عبر ملف الموقع (لا يوضع في git):
```bash
bench --site <site> set-config -g mail_server smtp.resend.com
bench --site <site> set-config -g mail_port 465
bench --site <site> set-config -g use_ssl 1
bench --site <site> set-config -g mail_login resend
bench --site <site> set-config mail_password "<RESEND_API_KEY>"   # سرّي
bench --site <site> set-config auto_email_id ops@stochops.com
```
> **SPF/DKIM:** اضبطها من لوحة Resend لنطاق stochops.com. Resend للإرسال فقط — إن لزمت الردود فصندوق `ops@stochops.com` يحتاج مزوّد بريد وارد منفصل.

## 2. الرسائل الست الواجب اختبارها (بعناوين الفريق)
النظام يبنيها أصلاً من `ops@stochops.com` ببيانات أدنى:
1. **دعوة مستخدم** — `accounts.invite_account` → رابط `/nos/accept-invite` (بلا كلمة مرور في البريد).
2. **تأكيد البريد** — `signup.register_charity` → `/nos/verify`.
3. **إعادة كلمة المرور** — `accounts.request_password_reset` (رابط Frappe أحادي قصير العمر، لا يُفشي الحساب).
4. **إسناد مهمة/قرار + تنبيه موافقة** — إشعارات Notification (قناة System + بريد عند التفعيل).
5. **تذكير دوري** — Scheduler (قبل الموعد/بعد التأخّر/انتهاء العقد/استحقاق التزام أو حق).
6. **سجل إخفاق الإرسال + إعادة المحاولة** — Email Queue في Frappe (ضمن حدود آمنة).

## 3. ضوابط إلزامية
- **لا بيانات مستفيد/مانح/حالة مالية** في العنوان أو المتن أو الرابط — استخدم معرّف الطلب + رابطاً داخلياً يستلزم تسجيل الدخول (مطبّق).
- أرسل **لعناوين يملكها الفريق أو وافق أصحابها** فقط؛ **لا ترسل إلى `demo@nos.local`**.
- اضبط **حدود المعدّل** (مطبّقة على التسجيل/الدعوة/الاستعادة عبر `@rate_limit`).
- راجع حدود خطة Resend الحالية قبل اختبار الأحمال.

## 4. التحقّق في التطوير (بلا SMTP)
بلا مفتاح Resend لا يُرسَل بريد فعلي؛ تُصفّ الرسائل في **Email Queue** ويُعاد رابط التحقّق في `developer_mode`. عند توفّر المفتاح، كرّر الرسائل الست لعناوين الفريق وسجّل النتائج.

> المرجع: https://resend.com/docs/send-with-smtp · https://resend.com/pricing
