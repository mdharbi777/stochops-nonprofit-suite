# STOCHOPS Nonprofit Operations Suite (NOS)

تطبيق **Frappe** مخصّص (Custom App) لإدارة عمليات الجمعيات الخيرية السعودية: متابعة القرارات واللجان، والبرامج والمبادرات، والمؤشرات والتقارير. منتج داخلي خفيف، واجهة عربية RTL أولاً، قابل لإعادة الاستخدام عبر موقع Frappe مستقل لكل جمعية.

- **الاسم التقني للتطبيق:** `stochops_nonprofit`
- **أول عميل تجريبي:** جمعية الإخلاص (بيانات وهمية فقط في مرحلة التطوير)
- **الوثيقة المرجعية الإلزامية:** خطة البناء الرئيسية (إصدار 1.0 — 17 أكتوبر 2026)
- **الحالة:** Sprint 0 — تهيئة الوثائق والهيكل. لم تُبنَ أي وحدة بعد.

> ⚠️ **GitHub ليس بيئة استضافة** لتطبيق Frappe حي ولا يحفظ قاعدة MariaDB الحية. يُستخدم لحفظ الشفرة والوثائق فقط.

## النطاق في سطر واحد
ثلاث وحدات فقط وبالترتيب الصارم مع بوابات قبول:
1. **القرارات واللجان** → GATE 1
2. **البرامج والمبادرات** → GATE 2
3. **المؤشرات والتقارير** → GATE 3

ما هو **خارج النطاق** (MVP): بوابة مستفيدين، منصة تبرعات، رواتب، محاسبة عامة، CRM، مشتريات/عقود، تكاملات حكومية/بنكية. أي فكرة إضافية → [`docs/BACKLOG.md`](docs/BACKLOG.md).

## الوثائق
| ملف | الغرض |
|---|---|
| [00_SCOPE](docs/00_SCOPE.md) | النطاق والافتراضات والحدود الثابتة |
| [01_REQUIREMENTS](docs/01_REQUIREMENTS.md) | المتطلبات الوظيفية للوحدات الثلاث |
| [02_ARCHITECTURE](docs/02_ARCHITECTURE.md) | المعمارية (Frappe custom app، موقع لكل جمعية) |
| [03_DATA_DICTIONARY](docs/03_DATA_DICTIONARY.md) | DocTypes والحقول |
| [04_ROLES_PERMISSIONS](docs/04_ROLES_PERMISSIONS.md) | الأدوار ومصفوفة الصلاحيات |
| [05_TEST_PLAN](docs/05_TEST_PLAN.md) | مصفوفة حالات الاختبار |
| [06_DEPLOYMENT](docs/06_DEPLOYMENT.md) | النشر (مؤجّل) |
| [07_BACKUP_RESTORE](docs/07_BACKUP_RESTORE.md) | النسخ الاحتياطي والاستعادة |
| [08_USER_GUIDE_AR](docs/08_USER_GUIDE_AR.md) | دليل المستخدم العربي |
| [09_HANDOVER](docs/09_HANDOVER.md) | وثيقة التسليم |
| [10_PRIVACY_SECURITY](docs/10_PRIVACY_SECURITY.md) | الخصوصية والأمان |
| [TECH_STACK](docs/TECH_STACK.md) | المنصة والإصدارات المثبّتة |
| [BACKLOG](docs/BACKLOG.md) | أفكار مؤجّلة خارج النطاق |
| [CHANGELOG](docs/CHANGELOG.md) | سجل التغييرات |

## التهيئة المحلية (ملخّص — التفاصيل في TECH_STACK و06_DEPLOYMENT)
> يحتاج Frappe بيئة Unix. على ويندوز: WSL2 + Docker Desktop (أو Bench داخل Ubuntu على WSL2).

1. جهّز WSL2 + Docker حسب [`docs/TECH_STACK.md`](docs/TECH_STACK.md).
2. ولّد التطبيق: `bench new-app stochops_nonprofit` (هذا يولّد `hooks.py`, `modules.txt`, `pyproject.toml` ... الفعلية — لا تُكتب يدوياً).
3. ثبّته على موقع محلي: `bench --site nonprofit.localhost install-app stochops_nonprofit`.
4. `bench migrate` ثم اختبار الدخول والصلاحيات.

## الترخيص
`LICENSE` معلّق حتى يُحسم قرار ملكية الكود. لا يُفترض أنه مفتوح المصدر.
