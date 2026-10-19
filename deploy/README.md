# حزمة النشر الإنتاجي — STOCHOPS Nonprofit Suite

> **لم يُنفَّذ أي نشر.** هذه قوالب وrunbook جاهزة للتنفيذ **لحظة توفّر استضافة سعودية** يوفّرها المالك، بعد الموافقة على التكلفة واتفاق حماية البيانات (PDPL). بصفر إنفاق حتى التنفيذ.

## المتطلبات قبل البدء (يوفّرها المالك)
- [ ] خادم/VPS **داخل السعودية** (موصى: 2 vCPU، 4 GB RAM فأكثر، 40 GB تخزين، Ubuntu LTS).
- [ ] نطاق (مثل `nonprofit.example.sa`) + صلاحية DNS.
- [ ] موافقة مكتوبة على التكاليف (خادم، نطاق/SSL، نسخ احتياطية، بريد SMTP إن لزم).
- [ ] **اتفاق معالجة بيانات (PDPL)** بين الجمعية وSTOCHOPS قبل إدخال أي بيانات فعلية.
- [ ] Deploy key / token مقيّد لقراءة المستودع الخاص وقت البناء (لا أسرار داخل git).

## المنهج
بناء **صورة Docker مخصّصة** (Frappe v15 + تطبيقنا) عبر `frappe_docker`، ثم تشغيل production compose. مصدر الملفات: https://github.com/frappe/frappe_docker

### 1) على الخادم: تجهيز
```bash
# Docker + Compose plugin، ثم:
git clone https://github.com/frappe/frappe_docker
cd frappe_docker
```

### 2) بناء الصورة المخصّصة (apps.json)
استخدم [`apps.json`](apps.json) من هذه الحزمة (Frappe version-15 + مستودعنا). للمستودع الخاص، أدرج token في رابط المستودع **وقت البناء فقط**:
```bash
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag=ghcr.io/<owner>/stochops-nonprofit:v0.5.0 \
  --file=images/layered/Containerfile .
```
ثم ادفع الصورة إلى سجلّ خاص (أو ابنِها مباشرة على الخادم).

### 3) إعداد البيئة
انسخ [`env.production.example`](env.production.example) إلى `.env` واملأه (كلمات مرور قوية عبر secret manager؛ لا أسرار في git).

### 4) تشغيل (staging أولاً ثم production منفصل)
```bash
docker compose \
  -f compose.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.https.yaml \
  --env-file .env up -d
```

### 5) إنشاء الموقع وتثبيت التطبيق
```bash
docker compose exec backend \
  bench new-site nonprofit.example.sa \
    --db-root-password "$DB_PASSWORD" \
    --admin-password "__SET_STRONG_ADMIN_PW__" \
    --install-app stochops_nonprofit
docker compose exec backend bench --site nonprofit.example.sa scheduler enable
```
`after_install` ينشئ الأدوار والإشعارات تلقائياً.

### 6) التحقّق بعد النشر
```bash
docker compose exec backend bench --site nonprofit.example.sa execute stochops_nonprofit.setup.verify_install.run
# يجب أن يعيد all_ok: true
```
- [ ] HTTPS يعمل (شهادة صالحة).
- [ ] تسجيل الدخول + صلاحيات الأدوار الأربعة.
- [ ] الـ Scheduler نشط (إشعارات قبل/بعد الموعد).
- [ ] MariaDB/Redis **غير مكشوفة** على الإنترنت (خلف الشبكة الداخلية فقط).
- [ ] **بريد SMTP مُعدّ** — مطلوب لإرسال روابط تأكيد التسجيل الذاتي (المستخدم يُنشأ معطّلاً حتى يؤكّد بريده). بدونه لن تصل رسائل التأكيد.
- [ ] تجربة **نسخ احتياطي واستعادة** حقيقية (انظر [07_BACKUP_RESTORE](../docs/07_BACKUP_RESTORE.md)).

> **تقوية التسجيل العام (مفعّلة):** captcha حسابي + تحديد معدّل (8 طلبات/ساعة/IP) + تأكيد بريد إلزامي. أضِف SMTP قبل فتح التسجيل للعامة.

## تعدّد الجمعيات
لكل جمعية **موقع مستقل** (`bench new-site`) + نسخ احتياطي واستعادة مستقلّة. **لا تُنسخ بيانات** من موقع إلى آخر.

## التحديث والتراجع (Runbook)
- تحديث: ابنِ صورة بوسم جديد ← `docker compose pull` ← `up -d` ← `bench --site <site> migrate`.
- تراجع: أعد وسم الصورة السابق في `.env` ← `up -d` ← استعِد نسخة ما قبل التحديث إن لزم تغيّر مخطط.
- جرّب أي تحديث على **staging** قبل production.

> يُحظر اعتبار GitHub Pages/Actions استضافةً لتطبيق Frappe حي بقاعدة بيانات مستمرة.
