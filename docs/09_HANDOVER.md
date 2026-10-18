# 09 — وثيقة التسليم (HANDOVER)

> الحالة: **الوحدات الثلاث مكتملة (Sprints 0–3) + تقوية وتسليم (Sprint 4)**. لم يُنفَّذ نشر إنتاجي (Sprint 5 مؤجّل حتى توفّر استضافة سعودية).

## 1. ما الذي سُلّم
تطبيق Frappe مخصّص واحد `stochops_nonprofit` (Frappe v15) بثلاث وحدات فقط:
1. **القرارات واللجان** — Committee, Meeting, Decision, Decision Follow-up.
2. **البرامج والمبادرات** — Initiative, Initiative Task.
3. **المؤشرات والتقارير** — لوحة `/app/nonprofit-dashboard` + تقارير (Executive Summary, Overdue Decisions, Decisions by Committee, Initiatives Overview).

أربعة أدوار: Nonprofit Admin / Executive Viewer / Committee Coordinator / Program Coordinator.

- **المستودع:** https://github.com/mdharbi777/stochops-nonprofit-suite (خاص). الوسوم: `v0.1.0`, `v0.2.0`, `v0.3.0`.
- **الاختبارات:** 29/29 ناجحة.

## 2. التثبيت على بيئة تطوير (موثّق ومختبَر)
المتطلبات في [TECH_STACK](TECH_STACK.md): WSL2 + Docker + Frappe v15 (Python 3.12 + Node 22). ثم:
```bash
bench new-app stochops_nonprofit          # أو: bench get-app <repo-url>
bench --site <site> install-app stochops_nonprofit
bench --site <site> migrate
```
- `after_install` ينشئ الأدوار الأربعة تلقائياً.
- التحقّق من سلامة التثبيت:
```bash
bench --site <site> execute stochops_nonprofit.setup.verify_install.run
```
يجب أن يعيد `all_ok: true` (6 DocTypes + 4 أدوار + 4 تقارير + لوحة المؤشرات).

### ✅ اختبار التثبيت النظيف (U1-13) — تم (2026-10-18)
على موقع جديد تماماً: install-app ← migrate ← `verify_install` = **all_ok** ← `frappe.ping` = pong ← **29/29 اختباراً ناجحة**. أي: التطبيق قابل للتثبيت من مستودع نظيف دون إعداد مخفي.

## 3. بيانات تجريبية (آمنة)
```bash
bench --site <site> execute stochops_nonprofit.setup.seed_demo.run     # إنشاء عيّنة
bench --site <site> execute stochops_nonprofit.setup.seed_demo.clear   # حذف العيّنة
```
بيانات وهمية موسومة «(عيّنة)» — **بلا أي أسماء/هويات/بيانات مستفيدين** (أعداد إجمالية فقط).

## 4. التشغيل
```bash
bench start      # ثم افتح http://<site>:8000  (مستخدم Administrator)
```

## 5. ملخّص الأمان (Sprint 4)
- لا أسرار في المستودع؛ `.gitignore` يغطّي `.env`, `*.key`, `*.pem`, `sites/`, backups, logs.
- لا تبعيات مخصّصة (pyproject بلا dependencies؛ Frappe يديرها).
- الصلاحيات مفروضة على الخادم (مختبَرة UI/API/report/export عبر 29 اختباراً، منها العزل بين اللجان/المبادرات).
- التقارير واللوحة تحترم الصلاحيات ولا تكشف ما لا يحق للمستخدم. تفاصيل في [10_PRIVACY_SECURITY](10_PRIVACY_SECURITY.md).

## 6. حالة محتويات التسليم (مرجع §س)
| # | البند | الحالة |
|---|---|---|
| 1 | مستودع خاص منظّم قابل للتثبيت | ✅ |
| 2 | تطبيق واحد بثلاث وحدات فقط | ✅ |
| 3 | أوامر تجهيز محلي موثّقة ومختبرة | ✅ |
| 4 | بيانات تجريبية تُنشأ وتُحذف بأمان | ✅ |
| 5 | دليل مستخدم عربي | ✅ [08_USER_GUIDE_AR](08_USER_GUIDE_AR.md) |
| 6 | جدول الصلاحيات + الاختبارات ونتائجها | ✅ [04](04_ROLES_PERMISSIONS.md) + [05](05_TEST_PLAN.md) |
| 7 | مسودة بيان تسليم للجمعية | ✅ (أدناه) |
| 8 | خطة نقل إلى VPS سعودي | ⏳ موثّقة وغير منفّذة [06_DEPLOYMENT](06_DEPLOYMENT.md) |
| 9 | وثيقة تشغيل/نسخ احتياطي/استعادة | ✅ [07_BACKUP_RESTORE](07_BACKUP_RESTORE.md) |
| 10 | Backlog مستقل | ✅ [BACKLOG](BACKLOG.md) |

## 7. المؤجّل (لا يبدأ إلا بقرار المالك)
- **إشعارات داخل التطبيق** (U1-09/12) — تحتاج Scheduler مفعّلاً.
- **Sprint 5 — النشر الإنتاجي** على استضافة سعودية يوفّرها المالك + اتفاق معالجة بيانات (PDPL).
- **Sprint 6 — AI** (Mock أولاً) — بموافقة مكتوبة وتكلفة محددة.

## مسودة بيان مجاني للجمعية (نطاق، وليس اتفاقاً موقّعاً)
«تقدّم STOCHOPS للجمعية نسخة تجريبية من نظام متابعة القرارات والمبادرات والتقارير دون رسوم تطوير، ضمن نطاق تجريبي متفق عليه. لا يشمل المشروع أنظمة التبرعات أو المستفيدين أو المحاسبة أو الرواتب أو التكاملات الخارجية. لا يتم إدخال بيانات فعلية أو إطلاق تشغيل إنتاجي إلا بعد الاتفاق على الملكية والصلاحيات والاستضافة وحماية البيانات والمسؤولية عن الدعم والنسخ الاحتياطية.»
