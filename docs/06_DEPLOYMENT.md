# 06 — النشر (DEPLOYMENT) — مؤجّل حتى توفّر استضافة سعودية

> في MVP: تطوير محلي فقط. النشر الإنتاجي = Sprint 5 المؤجّل، يبدأ عندما يوفّر المالك استضافة داخل السعودية.

## التطوير المحلي (الآن)
انظر [TECH_STACK](TECH_STACK.md): WSL2 + Docker Desktop (أو Bench في WSL2). خطوات موجزة:
1. تجهيز البيئة وإصدار Frappe المعتمد.
2. `bench new-app stochops_nonprofit`.
3. `bench --site nonprofit.localhost install-app stochops_nonprofit`.
4. `bench migrate` ثم smoke test ودخول واختبار صلاحيات.

## النشر الإنتاجي (مؤجّل — قائمة تحقّق)
1. مواصفات الخادم: ذاكرة/تخزين/معمارية/نسخ احتياطية/DNS/Firewall/حزم Docker متوافقة.
2. **staging أولاً** على بيانات تجريبية، ثم production منفصل.
3. نشر Frappe الرسمي المدعوم بـ image versions ثابتة، دون بيانات افتراضية مفتوحة.
4. ربط GitHub عبر deploy key/token مقيّد — لا أسرار في git.
5. اختبار: `install-app`, migrate, jobs, logs, permissions, backup/restore, HTTPS.
6. runbook لتحديث الإصدار والتراجع عن تحديث فاشل.
7. اعتماد الجمعية على اتفاق معالجة البيانات وحدود الدعم قبل إدخال بياناتها.
8. موقع مستقل لكل جمعية جديدة — لا نسخ بيانات بين المواقع.

**يُحظر** اعتبار GitHub Pages/Actions بيئة استضافة لتطبيق Frappe حقيقي بقاعدة بيانات مستمرة.
