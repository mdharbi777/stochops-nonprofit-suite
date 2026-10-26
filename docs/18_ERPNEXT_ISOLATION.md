# 18 — عزل جداول ERPNext المالية (المرحلة 2.1)

النموذج: **شركة لكل جمعية** (Company per Charity) على موقع واحد. الموارد البشرية **مستثناة**.
المبدأ: **deny-by-default**، لا تسرّب بين الجمعيات في أي جدول مالي، كسر زجاج لمشغّل المنصّة فقط.

## الطبقات الثلاث (defense-in-depth)
1. **User Permission على Company** (أصيلة، واسعة): لكل مستخدم جمعية سجلّ `User Permission {allow:"Company", for_value:<شركته>, apply_to_all_doctypes:1}` يُنشأ عبر `multitenancy.sync_user_company_permission`. يُقيّد تلقائياً كل جدول مرتبط بالشركة في ERPNext. يُضبط عند إنشاء أي مستخدم جمعية (`accounts._new_user`) وعند التفعيل (`activation.activate`).
2. **هوكات العزل الخاصة** (دفاع عميق، deny-by-default) على الجداول المالية الحرجة:
   `permission_query_conditions` (`*_query`) + `has_permission` (`has_erpnext_permission`) بشرط `company = شركة المستخدم`. القائمة في `multitenancy.ERPNEXT_FINANCIAL_DOCTYPES`: GL Entry، Journal Entry، Payment Entry، Sales/Purchase Invoice، Account، Cost Center، Budget، Payment Ledger Entry، Bank Account، Bank Transaction.
3. **فرض الشركة عند الإنشاء** (`multitenancy.set_company`, before_insert): يفرض شركة المستخدم ويتجاهل أي قيمة واردة (نظير H1). من بلا شركة لا يُنشئ سجلاً مالياً.

## الربط بالجمعية
- حقل `Charity.company` (Link→Company) يُنشأ فقط عند وجود erpnext (`ensure_charity_company_field`).
- `provision_charity_company(charity)` (في `erpnext_bridge`): ينشئ Company (SAR، السعودية، دليل حسابات قياسي)، يربطها، ويضمن حساب مصروف «مساعدات المستفيدين». يُستدعى من `activation.activate`.
- كل شيء محميّ بوجود erpnext ⇒ التطبيق يبقى قابلاً للتثبيت على bench بلا erpnext (التطوير)، والجمعيات غير المُفعَّلة محاسبياً تعمل كالسابق (توافق خلفي).

## جسر: مساعدة مصروفة ← قيد محاسبي
`erpnext_bridge.assistance_on_update`: عند انتقال `Assistance Request` إلى «مصروف» (طلب مالي، مبلغ>0، شركة موجودة) يُولَّد **Journal Entry مسودة** (مدين: مصروف المساعدات، دائن: نقد الشركة)، مربوط بالمستفيد/البرنامج، ومخزّن في `Assistance Request.journal_entry` (منع التكرار). مسودة ⇒ يعتمدها محاسب الجمعية (فصل المهام). يُتخطّى بصمت إن لم تُفعّل المحاسبة.

## الاختبار
- **منطقي (bench بلا erpnext):** `test_erpnext_isolation.py` (15 اختباراً) — الشرط/الصلاحية/الفرض + اكتمال الهوكات. تشغيل: `run-tests --module stochops_nonprofit.test_erpnext_isolation`.
- **حيّ (بيئة بها erpnext):** جمعيتان + قيود فعلية — راجع `alfadil-docs/phase2.1-erpnext-isolation-design.md` §6-7.

## حالة النشر
الكود في git (main). **لا يُطبَّق على alfadil الإنتاجية حتى يُثبَت العزل حيًّا على بيئة/clone بها erpnext**، ثم يُنشر بإعادة بناء الصورة بإجراء erp2 المُختبَر + `bench migrate`.
