# TECH STACK — المنصة والإصدارات

> يُثبّت هنا الإصدار المعتمد قبل التثبيت الفعلي. لا يُعتمد فرع `develop` في الإنتاج.

## 1. المنصة
| المكوّن | الاختيار | ملاحظة |
|---|---|---|
| إطار العمل | **Frappe Framework** (Custom App) | بدون ERPNext افتراضياً |
| اللغة | Python + JavaScript المدمجان في Frappe | لا React/Next.js، لا backend إضافي، لا microservices، لا Kubernetes |
| قاعدة البيانات | **MariaDB** | المرافقة لبيئة Frappe |
| الكاش/الطوابير | **Redis** | المرافق لبيئة Frappe |
| بيئة التطوير | **Docker Compose محلي** (`frappe/frappe_docker` — مسار التطوير) أو Bench محلي | لا يُعتمد `pwd.yml` التجريبي للتطوير أو الإنتاج |
| إدارة الكود | Git + GitHub **private** | لحفظ الكود/الاختبارات/الوثائق فقط — ليس استضافة ولا قاعدة بيانات حية |

## 2. إصدار Frappe (قرار مطلوب قبل التثبيت)
تحقّق محدّث (2026-10-17):
- **v14** — انتهى الدعم (EOL) يناير 2026 → لا يُستخدم.
- **v15** — مستقر، مدعوم حتى نهاية 2027 (تقريباً). **موصى به لتجربة مستقرة طويلة المدى.**
- **v16** — مستقر أحدث، مدعوم حتى 2029 (تقريباً). خيار صالح لو رُغب الأحدث.
- **v17** — develop، غير مستقر → ممنوع للإنتاج.

> **TODO (قرار المالك):** ثبّت أحد الخيارين. التوصية المبدئية: **Frappe v15** (أنضج دعماً وأقل مفاجآت). يُحدّث هذا الجدول برقم الإصدار الدقيق (مثل `v15.x.x`) عند التثبيت، بعد مطابقته بصفحة الإصدارات الرسمية.

## 3. متطلبات البيئة على ويندوز (هذا الجهاز: Windows 11)
Frappe/Bench **لا يعمل أصلاً على ويندوز** (أداة Bench مبنية لأنظمة Unix). المسار المعتمد:
1. **WSL2** + توزيعة Ubuntu: `wsl --install` من PowerShell بصلاحية مدير.
2. **Docker Desktop** مع backend WSL2 (اختر مسار WSL2 عند التثبيت).
3. احتفظ بمجلد bench على نظام ملفات Linux (مثل `/home/<user>/frappe-bench`) **وليس** على `/mnt/c/` (أداء وصلاحيات).
4. ويندوز 11 يحلّ أسماء `*.localhost` تلقائياً عادةً (على ويندوز 10 قد تحتاج تعديل hosts).

### حالة التحقق في بيئة الأداة
- [ ] WSL2 مثبّت ومفعّل.
- [ ] Docker Desktop (WSL2 backend) يعمل.
- [ ] إصدار Frappe مثبّت ومُطابَق بالوثائق الرسمية.

> حتى تُستوفى الخانات أعلاه، يُكتب الكود والاختبارات والوثائق القابلة للفحص، ويُصرَّح بوضوح أن التطبيق **غير مُشغّل فعلياً** (لا ادّعاء بأنه إنتاجي).

## 4. ما هو مجاني وما ليس مضموناً
- Frappe Framework مفتوح المصدر (MIT)، استضافة ذاتية بلا رسوم ترخيص.
- GitHub private repo ضمن الخطة المجانية وحدودها (لا ضمان CI/تخزين غير محدود).
- التطوير المحلي مجاني من رسوم الاستضافة الخارجية لكنه يحتاج جهازاً ووقتاً واتصالاً.
- **لاحقاً** قد توجد تكاليف: خادم داخل السعودية، نطاق/SSL، SMTP، تخزين نسخ احتياطية، مراقبة، وAI إن فُعّل.
- لا Frappe Cloud ولا ERPNext مدفوع ولا OpenAI API الآن.

## 5. مراجع رسمية
- Frappe Framework: https://docs.frappe.io/framework/user/en
- تثبيت Frappe/Bench: https://docs.frappe.io/framework-git/getting-started/installation
- Frappe Docker: https://github.com/frappe/frappe_docker
- DocTypes: https://docs.frappe.io/framework/user/en/basics/doctypes
- Permissions: https://docs.frappe.io/framework/user/en/basics/users-and-permissions
- Reports: https://docs.frappe.io/framework-git/desk/reports
- Licenses: https://docs.frappe.io/legal/others/license-and-trademark
