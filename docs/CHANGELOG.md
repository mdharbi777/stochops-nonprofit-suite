# CHANGELOG

جميع التغييرات المهمة لهذا المشروع تُوثَّق هنا.

## [Unreleased]

### Sprint 0 — 2026-10-17
- تهيئة هيكل المشروع ومجلداته (`docs/`, `scripts/`).
- ملفات الجذر: `README.md`, `.gitignore`, `.env.example`, `LICENSE` (معلّق).
- الوثائق الأساسية: 00_SCOPE، 01_REQUIREMENTS، 02_ARCHITECTURE، 03_DATA_DICTIONARY، 04_ROLES_PERMISSIONS، 05_TEST_PLAN، 06_DEPLOYMENT، 07_BACKUP_RESTORE، 08_USER_GUIDE_AR، 09_HANDOVER، 10_PRIVACY_SECURITY، TECH_STACK، BACKLOG.
- تثبيت النطاق والحدود الثابتة من خطة البناء (إصدار 1.0).
- **قرار تقني موثّق:** إعادة تسمية حقل `owner` (المتعارض مع حقل Frappe القياسي) إلى `decision_owner` / `initiative_owner`.
- **لم يُبنَ أي DocType بعد** (DocTypes الوحدة 1 = Sprint 1).

### Sprint 0 — بيئة التطوير — 2026-10-18
- **WSL2 + Ubuntu 26.04 LTS** (resolute, نواة 6.18، systemd) على ويندوز 11.
- **Docker Engine 29.9.1 + Compose v5.6.0** داخل WSL (مفتوح المصدر، بلا Docker Desktop؛ hello-world نجح).
- **frappe_docker** (devcontainer) — حاويات شغّالة: frappe + mariadb 11.8 + redis-cache + redis-queue.
- **Frappe v15.123.1** (فرع version-15) عبر `bench init` — **Python 3.12.15 + Node 22** (تجنّب 3.14/Node24 غير المتوافقَين مع v15).
- موقع **nonprofit.localhost** مُنشأ ومربوط بـ mariadb/redis، `developer_mode=1`.
- تطبيق **stochops_nonprofit 0.0.1** مُنشأ (`bench new-app --no-git`) ومثبّت على الموقع؛ `migrate` نجح.
- اختبار دخان: `frappe.ping → "pong"` ✅.
- تصحيح: `license.txt` للتطبيق ظهر MIT افتراضياً أثناء scaffold → استُبدل بإشعار «الرخصة معلّقة» (الرخصة لم تُحسم).
- موقع الكود حالياً: `~/frappe_docker/development/frappe-bench/apps/stochops_nonprofit` داخل WSL (منفصل عن مجلد الوثائق في Documents — **قرار توحيد المستودع معلّق**).

### Sprint 1 — الوحدة الأولى: القرارات واللجان — 2026-10-18
- **DocTypes (4):** `Committee`، `Meeting`، `Decision`، `Decision Follow-up` (جدول فرعي) — JSON + controllers، متزامنة عبر `migrate`.
- **الأدوار (4):** Nonprofit Admin / Executive Viewer / Committee Coordinator / Program Coordinator (تُنشأ تلقائياً عبر `after_install` + `setup/roles.py`).
- **الصلاحيات:** مصفوفة لكل DocType (Admin كامل، Coordinator إنشاء/تعديل، Viewer قراءة) — مفروضة على الخادم.
- **منطق العمل:** منع الإكمال دون ملاحظة؛ تاريخ الإكمال خادمي؛ تسجيل متابعة تلقائي عند تغيّر الحالة + تحديث آخر متابعة؛ اعتماد الاجتماع يملأ المعتمِد/التاريخ خادمياً؛ قفل تعديل المحضر المعتمد لغير الإداري؛ التأخير **صفة مشتقة** (غير مخزّنة).
- **حقل مُضاف (موثّق):** `committee` على Decision (مجلوب من الاجتماع، للقراءة) — يُمكّن عزل السجلات عبر User Permissions.
- **التقارير (2):** `Overdue Decisions`، `Decisions by Committee` (Script Reports تستخدم `frappe.get_list` فتحترم الصلاحيات) + فلاتر.
- **بيانات تجريبية:** `setup/seed_demo.py` (run/clear) — 2 لجان + 2 اجتماعات + 5 قرارات موسومة (عيّنة)، بلا بيانات مستفيدين.
- **الاختبارات:** 13 اختباراً آلياً — **13/13 PASS** (حقول، إكمال، تأخير مشتق، اعتماد، قفل المحضر، عزل اللجان عبر API، القراءة فقط للتنفيذي).
- **تصحيح:** `app_license` في hooks.py كان mit → `Proprietary` (الرخصة معلّقة).
- **GATE 1: PASS** — بانتظار موافقة المالك على الانتقال للوحدة الثانية.

### الإصدارات المخطّطة
- `v0.1.0` — بعد الوحدة 1 (القرارات واللجان) واجتياز GATE 1.
- `v0.2.0` — بعد الوحدة 2 (البرامج والمبادرات) واجتياز GATE 2.
- `v0.3.0` — بعد الوحدة 3 (المؤشرات والتقارير) واجتياز GATE 3.
