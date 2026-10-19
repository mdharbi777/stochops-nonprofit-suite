# 15 — النشر التجريبي المجاني على Oracle Cloud (جدة) — ببيانات مصطنعة

> **الغرض:** نسخة تجريبية من منصة الفاضل على خادم **داخل السعودية (منطقة جدة)** بـ**صفر تكلفة** (Oracle Cloud «Always Free»)، لتجرّبها الجمعية **ببيانات مصطنعة فقط**.
> **الحالة الإلزامية:** `production_privacy_gate` تبقى **مغلقة**؛ **لا بيانات حقيقية** (مطابق لتفويض الـSandbox و[14_COMPLIANCE_CONTROLS_STATUS](14_COMPLIANCE_CONTROLS_STATUS.md)). التشغيل الفعلي ببيانات حقيقية يحتاج DPA + DPIA + فتح البوابة (انظر القسم 10).
> **ما لا أستطيع فعله نيابةً عنك:** إنشاء حساب Oracle أو إدخال بطاقة أو تشغيل أوامر على خادمك. هذا دليل تُنفّذه أنت، وأساعدك عند كل خطوة.

---

## 0. تنبيهات مهمة قبل البدء
- **Always Free مجاني** ضمن حدوده، لكنه **يتطلّب بطاقة للتحقّق** عند التسجيل (لا يُخصم ما لم ترفع الحساب إلى Paid). أي تكلفة تبقى بموافقتك.
- **توفّر خوادم ARM المجانية (Ampere A1) في جدة متذبذب** أحياناً؛ إن تعذّر الإنشاء، أعد المحاولة لاحقاً أو استخدم جهاز AMD المجاني الأصغر (أبطأ) أو Frappe Cloud trial (خارج السعودية، للواجهة فقط).
- المستودع **خاص**؛ البناء يحتاج **Deploy Token** يُدرج **وقت البناء فقط** (لا يُخزَّن في git).

## 1. المتطلبات
- [ ] حساب Oracle Cloud (Always Free).
- [ ] **GitHub Personal Access Token** (قراءة فقط لمستودع `mdharbi777/stochops-nonprofit-suite`) — يُستخدم وقت البناء.
- [ ] (اختياري) نطاق خاص. بدونه سنستخدم **hostname مجاني عبر `sslip.io`** مربوط بعنوان IP العام لنحصل على شهادة HTTPS.

## 2. إنشاء الخادم على Oracle (منطقة جدة)
1. سجّل الدخول إلى Oracle Cloud، واختر **Region = Saudi Arabia Central (Jeddah) / me-jeddah-1**.
2. **Compute → Instances → Create Instance:**
   - الاسم: `alfadil-trial`.
   - **Image:** Canonical **Ubuntu 22.04**.
   - **Shape:** `VM.Standard.A1.Flex` (Ampere ARM — ضمن Always Free). خصّص **2 OCPU + 12 GB RAM** (كافٍ لـFrappe، وضمن حدود المجاني 4 OCPU/24GB).
   - **Networking:** أنشئ/اختر VCN عاماً بـ**Public IP**.
   - **SSH Keys:** أضِف مفتاحك العام (أو نزّل مفتاحاً يولّده Oracle).
   - أنشئ.
3. **فتح المنافذ (Security List):** في شبكة الـVCN → Security List الافتراضية → Ingress Rules، أضِف:
   - Source `0.0.0.0/0`, TCP **80** (HTTP) و**443** (HTTPS).
4. دوّن **Public IP** للخادم (نسمّيه `SERVER_IP`).

## 3. تجهيز الخادم (SSH)
```bash
ssh ubuntu@SERVER_IP
sudo apt update && sudo apt -y upgrade
# جدار الحماية داخل أوبونتو (Oracle يحتاج أيضاً فتح iptables أحياناً)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
# Docker + Compose plugin
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && newgrp docker
docker version && docker compose version
```

## 4. بناء صورة مخصّصة (Frappe v15 + منصة الفاضل)
```bash
git clone https://github.com/frappe/frappe_docker ~/frappe_docker
cd ~/frappe_docker
# ملف apps.json من حزمة النشر (Frappe version-15 + مستودعنا)
cat > apps.json <<'EOF'
[
  { "url": "https://github.com/frappe/frappe", "branch": "version-15" },
  { "url": "https://github.com/mdharbi777/stochops-nonprofit-suite", "branch": "main" }
]
EOF
# للمستودع الخاص: أدرج التوكن في رابط مستودعنا داخل apps.json وقت البناء فقط
#   "url": "https://<GH_TOKEN>@github.com/mdharbi777/stochops-nonprofit-suite"
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag=alfadil/trial:latest \
  --file=images/layered/Containerfile .
```
> البناء على ARM قد يأخذ 15–30 دقيقة. بعده احذف `apps.json` الذي يحوي التوكن: `shred -u apps.json`.

## 5. تشغيل الإنتاج مع HTTPS
احصل على hostname مجاني: `SERVER_IP.sslip.io` (مثلاً `1.2.3.4.sslip.io`). ثم:
```bash
cd ~/frappe_docker
cp example.env .env
# عدّل .env:
#   CUSTOM_IMAGE=alfadil/trial ; CUSTOM_TAG=latest ; PULL_POLICY=never
#   DB_PASSWORD=<كلمة قوية> ; SITES=`SERVER_IP.sslip.io`
#   LETSENCRYPT_EMAIL=ops@stochops.com
docker compose \
  -f compose.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.https.yaml \
  --env-file .env up -d
```

## 6. إنشاء الموقع + تثبيت التطبيق
```bash
SITE=SERVER_IP.sslip.io
docker compose exec backend bench new-site $SITE \
  --db-root-password "$DB_PASSWORD" \
  --admin-password "__ضع_كلمة_قوية__" \
  --install-app stochops_nonprofit
docker compose exec backend bench --site $SITE scheduler enable
docker compose exec backend bench --site $SITE execute stochops_nonprofit.setup.verify_install.run   # all_ok: true
```
> `after_install` ينشئ الأدوار والإشعارات وبذور الخصوصية تلقائياً.

## 7. بيانات مصطنعة + تأكيد إغلاق البوابة
```bash
docker compose exec backend bench --site $SITE execute stochops_nonprofit.setup.seed_demo.run
# تأكيد أن بوابة الإنتاج مغلقة (يجب أن تُرجع 0/None)
docker compose exec backend bench --site $SITE execute \
  "frappe.db.get_single_value" --args "['Privacy Configuration','production_privacy_gate']"
```
> اترك البوابة **مغلقة**. التجربة ببيانات مصطنعة فقط.

## 8. التحقّق
- افتح `https://SERVER_IP.sslip.io/nos` (شهادة صالحة من Let's Encrypt).
- سجّل جمعية تجريبية عبر `/nos/register`، أو جرّب حساب الديمو إن استخدمت seed على مستأجر.
- تأكّد: الدخول، العزل بين جمعيتين، `verify_install = all_ok`، الـScheduler نشط.
- MariaDB/Redis **غير مكشوفة** للإنترنت (خلف الشبكة الداخلية فقط — الإعداد الافتراضي).

## 9. تسليم التجربة للجمعية (3–6 أشهر)
- أعطِ الجمعية: رابط `https://SERVER_IP.sslip.io/nos` + حساب مدير (أنشئه عبر الدعوة `/nos/accounts`).
- **بيان صريح:** نسخة تجريبية ببيانات مصطنعة، بلا بيانات فعلية، بلا دعم إنتاجي، قد تُعاد تهيئتها.
- راقب الاستخدام وجمّع الملاحظات.

## 10. الانتقال للتشغيل الفعلي (لاحقاً)
عند الرضا والرغبة ببيانات حقيقية:
1. **استضافة سعودية مدفوعة** (VPS سعودي أو Oracle Paid في جدة) — Always Free غير مضمون للإنتاج الجاد.
2. **DPA موقّع** + **اعتماد DPIA** (المسودات في [legal/](legal/)) + استيفاء [قائمة بوابة PDPL](11_PDPL_DESIGN.md).
3. إقرارات `Privacy Configuration`: `dpa_signed_ack` + `dpia_approved_ack` + `security_controls_ack` + مسؤول خصوصية + سياسة، ثم **فتح `production_privacy_gate` يدوياً**.
4. نسخ احتياطي مشفّر + تجربة استعادة + فحص اختراق قبل أي بيانات فعلية.

> **يُحظر** اعتبار هذه النسخة التجريبية بيئة إنتاج لبيانات حقيقية. البوابة تمنع ذلك برمجياً حتى اكتمال الخطوة 10.
