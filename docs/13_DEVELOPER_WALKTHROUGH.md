# 13 — دليل المبرمج: ماذا بنينا وكيف (خطوة بخطوة)

> منصة الفاضل — `stochops_nonprofit` (تطبيق Frappe v15 مخصّص). هذا الدليل يشرح البنية والكود والتشغيل والاختبار كما يحتاجها مبرمج ينضم للمشروع.
> الإصدارات: **`v1.0.0`** (المنتج التشغيلي N1–N7) + **`v1.1.0`** (طبقة حماية البيانات PDPL P0–P5). الاختبارات: **108/108**.

---

## 0. لمحة سريعة
- **المنتج:** منصّة SaaS متعددة الجمعيات لإدارة عمليات الجمعيات الخيرية وحوكمتها، عربية RTL، تحت علامة «منصة الفاضل» من STOCHOPS.
- **التقنية:** Frappe Framework v15 (Python 3.12 + Node 22 + MariaDB + Redis)، تطبيق واحد مخصّص، بلا ERPNext وبلا React.
- **الأرقام:** ~33 DocType، 6 تقارير Script، 10 إشعارات داخلية، ~20 صفحة مبرندة تحت `/www/nos`، 108 اختباراً آلياً.
- **المستودع:** `stochops-nonprofit-suite` (خاص). الفرع `main`.

## 1. البيئة التقنية (كيف نشّطناها)
1. **WSL2 + Ubuntu** على ويندوز (لأن Frappe بيئة لينكس أصلاً).
2. **Docker Engine + Compose** داخل WSL (مفتوح المصدر، بلا Docker Desktop).
3. **frappe_docker** (devcontainer): حاويات frappe + mariadb + redis-cache + redis-queue.
4. **Frappe v15.123.1** عبر `bench init` مع **Python 3.12.15 (pyenv)** و**Node 22 (nvm)** — تجنّب 3.14/Node24 غير المتوافقَين.
5. موقع **`nonprofit.localhost`** + `developer_mode=1`، وتطبيق `stochops_nonprofit` مثبّت عليه.
- مسار الكود داخل WSL: `~/frappe_docker/development/frappe-bench/apps/stochops_nonprofit`.

## 2. المعمارية في سطور
- **تطبيق واحد** يخدم كل الجمعيات (multi-tenant داخل قاعدة واحدة) — كيان `Charity` + حقل `charity` على كل بيانات التشغيل.
- **العزل** مفروض على الخادم بثلاث آليات (القسم 3)، لا على الواجهة.
- **الواجهة المبرندة** صفحات `www/nos/*.html` مستقلة (بلا Frappe Desk)، تتحدث مع الـAPI عبر `frappe.client` ودوال whitelisted؛ العزل يُطبَّق تلقائياً.
- **طبقة `privacy_core`** مشتركة للخصوصية والامتثال (PDPL) فوق الطبقة التشغيلية.
- **عربي فقط:** System Settings language=ar + Asia/Riyadh + translations/ar.csv.

## 3. كيف يعمل العزل (الأهم) — `stochops_nonprofit/multitenancy.py`
ثلاث آليات مربوطة في `hooks.py`:
1. **`permission_query_conditions`** — دالة لكل DocType تُرجع شرط SQL يحصر القوائم/التقارير/التصدير/الـAPI بجمعية المستخدم:
   `` `tabX`.`charity` = '<charity>' `` ، أو `""` لمستخدم المنصّة/break-glass، أو `"1=0"` لمن بلا جمعية.
2. **`has_permission`** — تحقّق على مستوى السجل الواحد (`get_doc`/الروابط المباشرة): يطابق `doc.charity` بجمعية المستخدم.
3. **`doc_events.before_insert` → `set_charity`** — يضبط `charity` تلقائياً من جمعية المنشئ.
- **تمييز الأدوار العليا:** `is_data_super` (System Manager/Administrator فقط = break-glass لبيانات التشغيل)؛ `is_platform_admin` (+Stochops Admin، لإدارة كيان Charity فقط، احتراماً للخصوصية).
- **ACL على مستوى الحالة (P3):** للمستفيدين وطلبات المساعدة، `_case_condition` + `has_case_permission` يحصران المنسّق في حالاته المُسندة (`case_worker`)، بينما يرى المدير/المطّلع كل حالات الجمعية. يُضبط `case_worker` تلقائياً عبر `set_charity_case`.

## 4. الوحدات التشغيلية (المنتج — v1.0.0)
بُنيت مرحلة-مرحلة ببوابات قبول، وحدة واحدة في كل مرة:
- **القرارات واللجان:** `Committee` → `Meeting` → `Decision` (+ `Decision Follow-up` child). منطق: منع إكمال قرار بلا ملاحظة؛ التأخير صفة مشتقّة (غير مخزّنة)؛ قفل محضر معتمد؛ متابعة تلقائية عند تغيّر الحالة.
- **البرامج والمبادرات:** `Initiative` + `Initiative Task`. قيم محسوبة (المتبقّي/إنجاز المهام/تحقيق المستهدف) غير مخزّنة؛ الميزانية «رقم إداري» لا محاسبة.
- **المؤشرات والتقارير:** مصدر حساب واحد `dashboard_metrics.compute()` (يحترم الصلاحيات)؛ 6 تقارير Script؛ لوحة 8 بطاقات.
- **N1:** هوية «منصة الفاضل» + مُرسِل `ops@stochops.com`.
- **N2 المستفيدون وطلبات المساعدة:** `Beneficiary` (رقم الهوية حقل Password مشفّر ومحجوب؛ تقليل بيانات) + `Assistance Request` (مسار اعتماد + فصل واجبات). كشف الهوية إدارياً فقط عبر `beneficiaries.reveal_national_id` (مع تسجيل اطّلاع).
- **N3 المتبرعون/المانحون/المنح:** `Donor` + `Donation` (تسجيل فقط بلا بوابة دفع) + `Grant`.
- **N4 المصروفات والرقابة المالية:** `Expense Request` — فصل واجبات + حدّ اعتماد بالدور (`expense_approval_limit` على Charity) + ملاحظة بتّ + ختم + `track_changes` (تدقيق)؛ رقم إداري لا قيد محاسبي مزدوج ولا دفع.
- **N5 الالتزامات المحكومة:** `Compliance Obligation` (تأخير مشتق + تذكيرات) + تقرير `Compliance Obligations`. لا تكامل حكومي مباشر.
- **N6 الموارد البشرية:** `Personnel` (هوية مشفّرة، بلا رواتب/تأمينات) + `Contract` (تنبيه انتهاء) + `Procurement Request` (نفس ضوابط N4).
- **N7 المساعد الذكي:** `ai/provider.py` (`MockAIProvider` محلي) + `ai/engine.py` + `Nonprofit AI Settings` (موقوف افتراضياً) + `AI Run Log`. 3 مهام مسودات بمراجعة بشرية، بلا تعديل بيانات، آمن ضد حقن التعليمات، تسجيل بلا payload.

## 5. طبقة الـSaaS والواجهة
- **التسجيل الذاتي:** `signup.register_charity` (captcha حسابي موقّع + rate limit + تأكيد بريد؛ المستخدم معطّل حتى يؤكّد).
- **الحسابات بدعوات (P2):** `accounts.invite_account` ينشئ حساباً معطّلاً بلا كلمة مرور ويرسل رابطاً أحادياً (`/nos/accept-invite`)؛ `request_password_reset` لا يُفشي وجود الحساب. حدّ 5 حسابات/جمعية.
- **الصفحات المبرندة** (`www/nos`): index, register, verify, accept-invite, console, accounts, committees, meetings, decisions, initiatives, tasks, beneficiaries, assistance, donors, grants, expenses, compliance, personnel, procurement, ai, reports, settings, privacy, rights, disclosures, incidents, guide. النمط: `frappe.client.get_list/insert/set_value` + `X-Frappe-CSRF-Token`، والعزل تلقائي.

## 6. طبقة حماية البيانات PDPL (v1.1.0) — `privacy_core.py` + سجلّاتها
- **P0:** تحليل فجوات غير هادم (`docs/12_PDPL_GAP_ANALYSIS.md`).
- **P1 Privacy Core:** `Privacy Configuration` (Single — **`production_privacy_gate` مغلقة افتراضياً**؛ فتحها يتطلّب مسؤول خصوصية + إصدار سياسة؛ `assert_gate_open()` يمنع البيانات الحقيقية) + `Regulatory Rule` (افتراضي LEGAL_REVIEW_REQUIRED) + `Data Field Catalog` + `Processing Activity Record` (RoPA) + `Sensitive Access Log` (سجل اطّلاع/كشف/تصدير، بلا محتوى). تسجيل كشف الهوية مربوط.
- **P2:** الحسابات بدعوات (أعلاه) + تسجيل تغييرات الصلاحيات.
- **P3:** `Consent Record` + `Privacy Rights Request` (مهلة 30 يوماً مشتقّة + تمديد) + `Privacy Impact Assessment` (اعتماد بشري) + **ACL على مستوى الحالة**.
- **P4:** `Disclosure Request` (deny-by-default + تسجيل مشاركة) + `Report Template Registry` (مُرقّم، TEMPLATE_REVALIDATION_REQUIRED) + تقرير `Beneficiary Categories` مُجهّل بإخفاء الخلايا الصغيرة (`small_cell_threshold`).
- **P5:** `Retention Schedule` (PENDING_DEFINITION، لا مدد مخترعة) + `Legal Hold` (`assert_no_legal_hold` يمنع الإتلاف) + `Security Incident` (نافذة 72 ساعة كتذكير، بلا بلاغ آلي) + `Subprocessor Register` + بوابة AI الخارجي (`assert_ai_external_allowed`).
- **قاعدة حاكمة:** اجتياز الكود ليس امتثالاً قانونياً؛ لا بيانات فعلية قبل DPA/DPIA وفتح البوابة يدوياً.

## 7. هيكل المستودع
```text
stochops_nonprofit/
├── hooks.py                      # الربط: after_install/after_migrate + permission hooks + doc_events
├── multitenancy.py               # العزل (query/has_permission/set_charity/case-ACL)
├── dashboard_metrics.py          # مصدر حساب المؤشرات + my_work
├── signup.py / accounts.py       # التسجيل الذاتي + إدارة الحسابات والدعوات
├── beneficiaries.py / personnel.py  # كشف الهوية إدارياً + تسجيل الاطّلاع
├── privacy_core.py               # طبقة الخصوصية المشتركة + البذور + البوابات
├── ai/ (provider.py, engine.py)  # المساعد المحلي Mock
├── setup/ (install, roles, notifications, localization, seed_demo, verify_install)
├── stochops_nonprofit/doctype/*  # ~33 DocType (JSON + controller + test_*.py)
├── stochops_nonprofit/report/*   # 6 تقارير Script
├── www/nos/*.html                # الصفحات المبرندة
└── translations/ar.csv
docs/ (00..13, TECH_STACK, BACKLOG, CHANGELOG) · deploy/ (apps.json, env, README runbook)
```

## 8. التشغيل والاختبار محلياً
داخل حاوية frappe (مع بيئة pyenv/nvm)، من `/workspace/development/frappe-bench`:
```bash
bench --site nonprofit.localhost migrate            # مزامنة DocTypes + after_migrate (idempotent)
bench --site nonprofit.localhost run-tests --app stochops_nonprofit   # 108/108
bench --site nonprofit.localhost execute stochops_nonprofit.setup.seed_demo.run    # بيانات وهمية
bench --site nonprofit.localhost execute stochops_nonprofit.setup.seed_demo.clear  # حذفها
bench --site nonprofit.localhost execute stochops_nonprofit.setup.verify_install.run  # all_ok
bench --site nonprofit.localhost clear-cache
bench start                                          # الخادم (الواجهة على http://nonprofit.localhost:8000)
```
- **ملاحظة ترحيل:** الإشعارات/الأدوار/بذور الخصوصية تُنشأ عبر `after_install` و`after_migrate` (idempotent)؛ بعد إضافة DocType جديد شغّل `migrate` ثم `clear-cache`.

## 9. الأدوار والصلاحيات
- أدوار الجمعية: **Nonprofit Admin** (كامل)، **Executive Viewer** (قراءة)، **Committee Coordinator**، **Program Coordinator**. ودور منصّة **Stochops Admin** (إدارة المستأجرين فقط).
- كل الصلاحيات مفروضة على الخادم ومختبَرة (قراءة/كتابة/تصدير/عزل/ACL الحالة).

## 10. الإشعارات والـScheduler
10 إشعارات System Notification (جرس Frappe، بلا SMS/بريد مدفوع): إسناد/قبل الموعد/بعد التأخّر للقرارات والمهام، وقبل انتهاء العقد، وقبل استحقاق الالتزام وطلب الحق. تعمل «قبل/بعد الموعد» عبر Scheduler.

## 11. حدود ثابتة محفوظة (ثوابت لا تُخالَف)
لا حركة أموال/بوابة دفع · لا محاسبة مزدوجة · لا تكامل حكومي/بنكي مباشر · الـAI محلي Mock موقوف افتراضياً · لا بيانات مستفيدين حقيقية قبل DPA/DPIA وفتح البوابة · عزل تامّ بين الجمعيات · «غير متوفّر» لا صفر · التأخير مشتق · التوقيت Asia/Riyadh.

## 12. تجربة الديمو خطوة بخطوة (على `nonprofit.localhost`)
> الحساب التجريبي: `demo@nos.local` / `Demo#Nos2026` (جمعية «جمعية العرض»، مدير جمعية). شغّل `seed_demo.run` أولاً لملء البيانات.
1. **الدخول** → `/login` ثم `/nos/console`: تحقّق من «المهام المطلوبة مني» + المؤشرات + البطاقات.
2. **القرارات واللجان** `/nos/committees` → أنشئ لجنة → اجتماعاً → قراراً؛ جرّب تغيير الحالة (إكمال يطلب ملاحظة).
3. **المبادرات/المهام** `/nos/initiatives`, `/nos/tasks`.
4. **المستفيدون** `/nos/beneficiaries`: أضِف مستفيداً برقم هوية → لاحظ أنه محجوب في القائمة → «كشف الهوية» (يُسجَّل في سجل الاطّلاع).
5. **طلبات المساعدة** `/nos/assistance`: أنشئ طلباً ثم اعتمده بملاحظة (جرّب الاعتماد بحساب غير المنشئ لرؤية فصل الواجبات).
6. **المتبرعون/المنح** `/nos/donors`, `/nos/grants` · **المصروفات** `/nos/expenses` (جرّب تجاوز حدّ الاعتماد) · **المشتريات** `/nos/procurement` · **الالتزامات** `/nos/compliance`.
7. **الموارد البشرية** `/nos/personnel` (موظف + عقد بتنبيه انتهاء).
8. **المساعد الذكي** `/nos/ai`: فعّله من الإعدادات المفردة ثم ولّد «تلخيص حالة» (مسودة محلية).
9. **التقارير** `/nos/reports`: جرّب التبويبات، وتبويب «فئات المستفيدين (مُجهّل)» (إخفاء الخلايا الصغيرة).
10. **الخصوصية** `/nos/privacy` (حالة البوابة + سجل الاطّلاع + RoPA) · **الحقوق** `/nos/rights` (طلب حق يحسب 30 يوماً) · **الإفصاح** `/nos/disclosures` (deny-by-default) · **الحوادث** `/nos/incidents` (نافذة 72 ساعة + حجز قانوني).
11. **الحسابات** `/nos/accounts`: أرسل دعوة → افتح رابط `/nos/accept-invite` واضبط كلمة مرور → فعّل الحساب.
- **اختبار العزل:** سجّل جمعية ثانية (`/nos/register`) وأنشئ بياناتها، وتأكّد أن كل جمعية لا ترى الأخرى.

## 13. النشر (مؤجّل — P6، بيد المالك)
الحزمة جاهزة في [`deploy/`](../deploy/README.md): بناء صورة Frappe v15 + التطبيق عبر frappe_docker ← production compose ← إنشاء الموقع ← تفعيل Scheduler ← `verify_install`. **قبل أي بيانات فعلية:** استضافة داخل السعودية + DPA موقّع + اعتماد DPIA + SMTP لـ`ops@stochops.com` + فحص اختراق + **فتح `production_privacy_gate` يدوياً** + استيفاء قائمة [11_PDPL_DESIGN](11_PDPL_DESIGN.md).

## 14. سجل الإصدارات
`v0.1.0`–`v0.3.0` الوحدات الثلاث · `v0.4.0`–`v0.6.0` الجودة/الإشعارات/النشر · `v0.7.0` منتج SaaS مبرند · **`v1.0.0`** المنتج الكامل N1–N7 · **`v1.1.0`** طبقة PDPL P0–P5. التفاصيل الزمنية في [CHANGELOG](CHANGELOG.md).
