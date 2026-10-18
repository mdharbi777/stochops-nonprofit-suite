# 03 — قاموس البيانات (DATA DICTIONARY)

> يصف DocTypes وحقولها. **الوحدة 1 فقط تُبنى في Sprint 1**؛ الوحدة 2 مرجعية حتى Sprint 2؛ الوحدة 3 لا تُنشئ جداول موازية (تقارير فقط).

## ⚠️ تنبيه تقني مهم — حقل `owner` محجوز في Frappe
`owner` حقل **قياسي محجوز** في كل DocType في Frappe (يمثّل المستخدم الذي أنشأ السجل). لذلك **لا نستخدم اسم `owner`** لحقل مخصّص. في خطة البناء ورد `owner` على `Decision` و`Initiative` — نستبدله بـ:
- في Decision → `decision_owner` (المسمّى في الواجهة: «المسؤول»).
- في Initiative → `initiative_owner` (المسمّى في الواجهة: «المسؤول»).

كذلك نتجنّب أسماء Frappe القياسية الأخرى لحقولنا: `name, owner, creation, modified, modified_by, docstatus, idx, parent, parentfield, parenttype`.

---

# الوحدة 1 — القرارات واللجان (Sprint 1)

## 1. Committee (لجنة)
| الحقل | النوع | قيود |
|---|---|---|
| `committee_name` | Data | إلزامي، فريد لكل موقع |
| `committee_type` | Select | مجلس إدارة / لجنة / فريق عمل / أخرى |
| `status` | Select | نشطة / مؤرشفة (افتراضي: نشطة) |
| `coordinator` | Link → User | إلزامي |
| `description` | Small Text | اختياري |

## 2. Meeting (اجتماع)
| الحقل | النوع | قيود |
|---|---|---|
| `committee` | Link → Committee | إلزامي |
| `title` | Data | إلزامي |
| `meeting_date` | Date | إلزامي |
| `meeting_reference` | Data | اختياري |
| `minutes_attachment` | Attach (Private) | اختياري، محكوم بالصلاحيات |
| `status` | Select | Draft / Approved (افتراضي: Draft) |
| `approved_by` | Link → User | يُملأ **خادمياً** عند الاعتماد (read-only) |
| `approved_on` | Datetime | يُملأ **خادمياً** عند الاعتماد (read-only) |
| `notes` | Small Text | اختياري |

**قاعدة:** منع تحرير محضر `Approved` إلا بصلاحية إدارية موثّقة أو عبر إجراء تصحيح مع Audit Trail — مفروض **على الخادم** لا بإخفاء الأزرار.
> **خيار معماري مطروح (قرار لاحق):** استخدام Frappe **submittable** (`docstatus`) بدل Draft/Approved يدوي يعطي تجميداً بعد الاعتماد + Amendment جاهزين. يُحسم في بداية Sprint 1؛ الافتراضي الحالي حقل `status` كما في الخطة.

## 3. Decision (قرار)
| الحقل | النوع | قيود |
|---|---|---|
| `decision_no` | Data (Naming Series) | فريد، تلقائي |
| `meeting` | Link → Meeting | إلزامي |
| `title` | Data | إلزامي |
| `description` | Text | اختياري |
| `decision_owner` | Link → User | إلزامي *(كان `owner` في الخطة — مُعاد تسميته)* |
| `due_date` | Date | إلزامي |
| `status` | Select | Open / In Progress / Completed / Cancelled |
| `priority` | Select | Normal / High (افتراضي: Normal) |
| `completion_note` | Text | **إلزامي عند Completed** |
| `completion_date` | Date | يُملأ خادمياً عند الإكمال |
| `evidence` | Attach (Private) | اختياري (غير مفروض) |
| `last_followup` | Date | read-only، يُحدَّث من السجل |

**التأخير صفة مشتقة** (لا تُخزَّن): `due_date < today` و`status ∉ {Completed, Cancelled}`.

## 4. Decision Follow-up (متابعة قرار) — Child Table
| الحقل | النوع | قيود |
|---|---|---|
| `followup_date` | Datetime | يُملأ خادمياً |
| `update_text` | Small Text | إلزامي |
| `updated_by` | Link → User | يُملأ خادمياً |
| `previous_status` | Data/Select | read-only |
| `new_status` | Data/Select | read-only |

---

# الوحدة 2 — البرامج والمبادرات (مرجعي — يُبنى Sprint 2)

## Initiative (مبادرة)
أبرز الحقول: `initiative_id` (تلقائي فريد)، `title` (إلزامي)، `program_name` (Data اختياري — **لا DocType للبرنامج**)، `initiative_owner` (Link User إلزامي — *كان `owner`*)، `objective` (إلزامي)، `start_date`/`end_date` (إلزامي، النهاية ليست قبل البداية)، `status` (Planned/Active/On Hold/Completed/Cancelled)، `planned_budget_sar` / `actual_spend_sar` (Currency ≥ 0، اختياري — **رقم إجمالي يدخله المخوّل، ليس دفتر حسابات**)، `target_count`/`actual_count` (Int ≥ 0)، `target_unit` (نشاط/مستفيد [عدد إجمالي فقط]/مخرج/أخرى)، `summary`، `closing_note` (إلزامي عند Completed)، `closing_document` (Attach Private).

## Initiative Task (مهمة مبادرة)
`initiative` (Link إلزامي)، `title` (إلزامي)، `assigned_to` (Link User إلزامي)، `due_date` (إلزامي)، `status` (Open/In Progress/Completed/Cancelled)، `completion_note` (إلزامي عند الإكمال)، `completed_on` (خادمي).

> **ممنوع إنشاء:** supplier, invoice, donor, beneficiary, payment, purchase order. **وممنوع تخزين أسماء مستفيدين أو أرقام هويات أو بيانات أسر أو حالة اجتماعية.**

---

# الوحدة 3 — المؤشرات والتقارير
لا DocTypes جديدة. تُنفَّذ عبر Frappe Reports و query/script reports فقط. انظر [01_REQUIREMENTS](01_REQUIREMENTS.md) و[05_TEST_PLAN](05_TEST_PLAN.md).
