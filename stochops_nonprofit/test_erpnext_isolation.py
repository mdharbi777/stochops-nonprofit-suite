"""اختبارات منطقية لعزل جداول ERPNext المالية (المرحلة 2.1).

تعمل على bench التطوير **بلا erpnext**: لا تستورد دكتايبات erpnext، وتختبر منطق
العزل (الشرط/الصلاحية/الفرض) عبر محاكاة الدوال المساعدة. الاختبار الحيّ الكامل
(جمعيتان + قيود فعلية) يُجرى على بيئة بها erpnext — راجع التصميم §6-7.

تشغيل: bench --site <site> run-tests --module stochops_nonprofit.test_erpnext_isolation
"""
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit import erpnext_bridge, multitenancy
from stochops_nonprofit import hooks


class _FakeDoc:
    """مستند صوري خفيف لاختبار has_permission/set_company بلا قاعدة بيانات."""

    def __init__(self, company=None, is_new=False, name=None):
        self._data = {"company": company, "name": name}
        self._is_new = is_new

    def get(self, key, default=None):
        return self._data.get(key, default)

    def is_new(self):
        return self._is_new

    def __setattr__(self, k, v):
        if k in ("_data", "_is_new"):
            super().__setattr__(k, v)
        else:
            self._data[k] = v

    @property
    def company(self):
        return self._data.get("company")


MOD = "stochops_nonprofit.multitenancy"


class TestErpnextIsolationLogic(FrappeTestCase):
    # ---------- _company_condition (permission_query_conditions) ----------
    def test_super_sees_all(self):
        with patch(f"{MOD}.is_data_super", return_value=True):
            self.assertEqual(multitenancy._company_condition("x@y.z", "GL Entry"), "")

    def test_no_company_denies_by_default(self):
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value=None
        ):
            self.assertEqual(multitenancy._company_condition("x@y.z", "GL Entry"), "1=0")

    def test_company_scoped_condition(self):
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value="Charity A"
        ):
            cond = multitenancy._company_condition("x@y.z", "Journal Entry")
        self.assertIn("`tabJournal Entry`.`company`", cond)
        self.assertIn("Charity A", cond)
        # لا حقن: القيمة مُهرَّبة بين علامتي اقتباس
        self.assertTrue("'Charity A'" in cond or '"Charity A"' in cond)

    def test_query_wrappers_use_right_doctype(self):
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value="C1"
        ):
            self.assertIn("`tabGL Entry`", multitenancy.gl_entry_query("u"))
            self.assertIn("`tabPayment Entry`", multitenancy.payment_entry_query("u"))
            self.assertIn("`tabSales Invoice`", multitenancy.sales_invoice_query("u"))
            self.assertIn("`tabAccount`", multitenancy.account_query("u"))

    # ---------- has_erpnext_permission (record-level) ----------
    def test_has_perm_super(self):
        with patch(f"{MOD}.is_data_super", return_value=True):
            self.assertTrue(multitenancy.has_erpnext_permission(_FakeDoc(company="X"), "read", "u"))

    def test_has_perm_no_company_denies(self):
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value=None
        ):
            self.assertFalse(multitenancy.has_erpnext_permission(_FakeDoc(company="X"), "read", "u"))

    def test_has_perm_same_company_allowed_other_denied(self):
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value="A"
        ):
            self.assertTrue(multitenancy.has_erpnext_permission(_FakeDoc(company="A"), "read", "u"))
            self.assertFalse(multitenancy.has_erpnext_permission(_FakeDoc(company="B"), "read", "u"))

    def test_has_perm_create_blocks_foreign_company(self):
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value="A"
        ):
            # إنشاء بشركة أخرى = مرفوض؛ إنشاء بلا/بنفس الشركة = مسموح (تُفرَض في set_company)
            self.assertFalse(multitenancy.has_erpnext_permission(_FakeDoc(company="B"), "create", "u"))
            self.assertTrue(multitenancy.has_erpnext_permission(_FakeDoc(company=None), "create", "u"))
            self.assertTrue(multitenancy.has_erpnext_permission(_FakeDoc(company="A"), "create", "u"))

    # ---------- set_company (before_insert, الطبقة 3) ----------
    def test_set_company_super_noop(self):
        doc = _FakeDoc(company="ClientChosen")
        with patch(f"{MOD}.is_data_super", return_value=True):
            multitenancy.set_company(doc)
        self.assertEqual(doc.company, "ClientChosen")  # المشغّل يحتفظ بخياره

    def test_set_company_forces_user_company(self):
        doc = _FakeDoc(company="Foreign")  # محاولة زرع في شركة أخرى
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value="Mine"
        ):
            multitenancy.set_company(doc)
        self.assertEqual(doc.company, "Mine")  # تُتجاهَل القيمة الواردة وتُفرَض شركة المستخدم

    def test_set_company_no_company_throws(self):
        doc = _FakeDoc()
        with patch(f"{MOD}.is_data_super", return_value=False), patch(
            f"{MOD}.get_user_company", return_value=None
        ):
            with self.assertRaises(frappe.PermissionError):
                multitenancy.set_company(doc)

    # ---------- اكتمال تسجيل الهوكات لكل جدول مالي ----------
    def test_every_financial_doctype_is_wired(self):
        for dt in multitenancy.ERPNEXT_FINANCIAL_DOCTYPES:
            self.assertIn(dt, hooks.permission_query_conditions, f"PQC مفقود لـ {dt}")
            self.assertIn(dt, hooks.has_permission, f"has_permission مفقود لـ {dt}")
            self.assertEqual(
                hooks.has_permission[dt],
                "stochops_nonprofit.multitenancy.has_erpnext_permission",
            )

    def test_pqc_wrappers_resolve(self):
        # كل دالة PQC مُشار إليها في hooks موجودة فعلاً في الوحدة
        for dt in multitenancy.ERPNEXT_FINANCIAL_DOCTYPES:
            path = hooks.permission_query_conditions[dt]
            attr = path.rsplit(".", 1)[1]
            self.assertTrue(callable(getattr(multitenancy, attr)), f"{attr} غير موجود")

    # ---------- السلوك على bench بلا erpnext (deny-by-default طبيعي) ----------
    def test_erpnext_disabled_on_dev_bench(self):
        # لا دكتايب Company ⇒ المحاسبة معطّلة، والجسر/التهيئة يُتخطّيان بأمان
        if not frappe.db.exists("DocType", "Company"):
            self.assertFalse(erpnext_bridge.erpnext_enabled())
            self.assertIsNone(multitenancy.get_user_company("Administrator"))
            self.assertIsNone(erpnext_bridge.provision_charity_company("any"))

    def test_assistance_bridge_skips_without_erpnext(self):
        # on_update لا يرمي ولا يفعل شيئاً إن لم تُفعّل المحاسبة
        doc = _FakeDoc()
        doc.status = "مصروف"
        if not frappe.db.exists("DocType", "Company"):
            # لا استثناء
            erpnext_bridge.assistance_on_update(doc)
