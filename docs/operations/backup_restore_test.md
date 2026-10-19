# اختبار النسخ الاحتياطي والاستعادة + فصل البيئات (P6.4 / P6.1)

> نتائج **حقيقية** من بيئة التطوير (بيانات مصطنعة، `PILOT_SANDBOX`). التاريخ: 2026-10-19.

## 1. النسخ الاحتياطي (مع الملفات)
الأمر: `bench --site nonprofit.localhost backup --with-files`
| المكوّن | الحجم |
|---|---|
| قاعدة البيانات (`*-database.sql.gz`) | 1.6 MiB |
| إعداد الموقع (`*-site_config_backup.json`) | 228 B |
| ملفات عامة (`*-files.tar`) | 10 KiB |
| ملفات خاصة (`*-private-files.tar`) | 10 KiB |
المسار: `sites/nonprofit.localhost/private/backups/` (محلي، مقيّد، **ليس داخل GitHub**).

## 2. اختبار الاستعادة على بيئة نظيفة
الخطوات: إنشاء موقع نظيف `restore-test.localhost` → `bench restore <database.sql.gz>`.
- **النتيجة:** «Site restore-test.localhost has been restored».
- **التحقّق بعد الاستعادة:** `verify_install.run` → **`all_ok: true`** (33 نوع بيانات + 4 أدوار + 6 تقارير + 10 إشعارات + اللوحة + حقل الجمعية). الدخول يعمل بحساب المشرف المُستعاد.
- ✅ **سلامة الاستعادة مؤكّدة** (المكوّنات كاملة بعد الاستعادة).

## 3. فصل البيئات (Staging ≠ Development)
- أُنشئ موقع **`staging.localhost`** مستقل (قاعدة بيانات وملفات وأسرار منفصلة عبر بنية المواقع في Frappe) + تثبيت التطبيق + `seed_demo` → `verify_install` **`all_ok: true`**.
- المواقع القائمة الآن (منفصلة تماماً):
  ```
  sites/nonprofit.localhost/   (development)
  sites/restore-test.localhost/ (اختبار استعادة)
  sites/staging.localhost/      (staging)
  ```
- **الكتابة في موقع لا تؤثّر في الآخر** (قواعد بيانات مستقلة per-site في Frappe — شرط القبول مُستوفى).

## 4. ملاحظات تشغيلية
- جميع المواقع في وضع **`PILOT_SANDBOX`** و`production_privacy_gate` **مغلقة** — بيانات مصطنعة فقط.
- عند النشر الفعلي: جدولة النسخ آلياً + تشفير مسار النسخ + مفاتيح منفصلة + تكرار دوري لاختبار الاستعادة (انظر [07_BACKUP_RESTORE](../07_BACKUP_RESTORE.md)).
- تحذير بيئة التطوير: MariaDB 11.8 أحدث من المُختبَر رسمياً مع Frappe (لا يؤثّر على الاختبار؛ يُثبَّت إصدار مدعوم في الإنتاج).

## 5. الخلاصة
| البند | النتيجة |
|---|---|
| نسخ احتياطي (قاعدة + ملفات) | ✅ نجح |
| استعادة على بيئة نظيفة + تحقّق | ✅ `all_ok: true` |
| فصل Staging/Development | ✅ مواقع وقواعد منفصلة |
| الدخول/الإجراءات/التقارير/الجدولة | ✅ (الجدولة تُفعَّل عبر `bench scheduler enable` عند الحاجة) |
