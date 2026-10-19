# تشغيل البريد عبر Resend (P6.3) — التجربة التقنية

> المزوّد المعتمد: **Resend** (الموجود بالفعل). **لا Brevo، ولا مزوّد جديد.** الحالة: `PILOT_SANDBOX` — بيانات مصطنعة، عناوين اختبارية يملكها الفريق.
> **المفتاح لا يُحفظ في المستودع** — يُضبط عبر إعداد الموقع/حساب البريد فقط.

## 1. إعداد Frappe SMTP (Resend)

### الطريقة المعتمدة في هذه البيئة: إعداد الموقع عبر **المنفذ 587 (STARTTLS)**
> **مهم:** مسار «إعداد الموقع» في Frappe (`mail_server`/`mail_port`/…) **لا يدعم المنفذ 465 (SSL الضمني)**؛
> فدالة `get_account_details_from_site_config` تُطبّق `use_tls` فقط وتتجاهل `use_ssl`. لذلك يجب استخدام
> **المنفذ 587 مع STARTTLS**، وإلا يفتح Frappe اتصال SMTP نصّيّاً على منفذ TLS ضمني فينتهي بمهلة
> «Connection unexpectedly closed: timed out». (تأكّد عملياً — انظر §5.)

```bash
bench --site <site> set-config -g mail_server smtp.resend.com
bench --site <site> set-config -g mail_port 587
bench --site <site> set-config -g use_tls 1
bench --site <site> set-config -g use_ssl 0
bench --site <site> set-config -g mail_login resend
bench --site <site> set-config mail_password "<RESEND_API_KEY>"   # سرّي — في site_config فقط، لا في git
bench --site <site> set-config auto_email_id ops@stochops.com
```

### بديل للإنتاج: **Email Account** في الواجهة (يدعم 465 SSL)
Desk → Email Account (مسار doctype يدعم `use_ssl_for_outgoing`، فيعمل المنفذ 465 الضمني):

| الحقل | القيمة |
|---|---|
| Email Address / From | `ops@stochops.com` (بعد توثيق نطاق stochops.com والمرسِل في Resend) |
| Outgoing (SMTP) | مفعّل |
| SMTP Server | `smtp.resend.com` |
| Port | `587` + **STARTTLS** (أو `465` + **Use SSL** عبر Email Account) |
| Username | `resend` |
| Password | **مفتاح Resend API للإرسال** (SMTP) — يُدخل في الواجهة فقط، لا في git |
| Default Outgoing | نعم |

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

## 5. نتيجة التجربة الفعلية (2026-10-19 — `nonprofit.localhost`)
- **اتصال الشبكة:** المنافذ 465/587/2587 مفتوحة من الحاوية، والمنفذ 25 محجوب.
- **المنفذ 465 (SSL عبر إعداد الموقع):** **فشل** — `Invalid Outgoing Mail Server or Port: Connection unexpectedly closed: timed out` (مسار إعداد الموقع لا يستخدم `SMTP_SSL`).
- **المنفذ 587 (STARTTLS):** **نجح** — سجلّ Email Queue بحالة **Sent** بلا أخطاء؛ وصلت رسالة اختبار تقنية (بلا بيانات شخصية) إلى عنوان الفريق.
- `production_privacy_gate` لا يزال **false** و`deployment_mode = PILOT_SANDBOX` — لم يتغيّرا.

> المرجع: https://resend.com/docs/send-with-smtp · https://resend.com/pricing
