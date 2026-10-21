import frappe
from frappe.tests.utils import FrappeTestCase

from stochops_nonprofit.stochops_nonprofit.doctype.legal_document.legal_document import get_published
from stochops_nonprofit.stochops_nonprofit.doctype.charity.test_charity import (
    make_charity,
    make_charity_user,
)


def make_doc(slug, version, content="<p>نص قانوني</p>", language="ar"):
    return frappe.get_doc(
        {
            "doctype": "Legal Document",
            "title": "وثيقة " + slug,
            "slug": slug,
            "version": version,
            "language": language,
            "status": "Draft",
            "content": content,
        }
    ).insert(ignore_permissions=True)


def publish(doc):
    for st in ("In Review", "Approved", "Published"):
        doc.status = st
        doc.save(ignore_permissions=True)
    doc.reload()
    return doc


class TestLegalDocument(FrappeTestCase):
    def setUp(self):
        self.tok = frappe.generate_hash(length=6)
        self.slug = "terms-" + self.tok
        self.ca = make_charity(f"جمعية قانونية أ {self.tok}")
        self.cb = make_charity(f"جمعية قانونية ب {self.tok}")
        self.admin_a = make_charity_user(f"la_{self.tok}@t.local", self.ca, ["Nonprofit Admin"])
        self.admin_b = make_charity_user(f"lb_{self.tok}@t.local", self.cb, ["Nonprofit Admin"])

    def tearDown(self):
        frappe.set_user("Administrator")
        for n in frappe.get_all("Legal Acceptance", filters={"charity": ["in", [self.ca, self.cb]]}, pluck="name"):
            frappe.delete_doc("Legal Acceptance", n, force=1, ignore_permissions=True)
        for n in frappe.get_all("Legal Document", filters={"slug": ["like", f"%{self.tok}%"]}, pluck="name"):
            frappe.delete_doc("Legal Document", n, force=1, ignore_permissions=True)
        for e in (self.admin_a, self.admin_b):
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=1, ignore_permissions=True)
        for c in (self.ca, self.cb):
            if frappe.db.exists("Charity", c):
                frappe.delete_doc("Charity", c, force=1, ignore_permissions=True)
        frappe.db.commit()

    def test_illegal_transition_blocked(self):
        d = make_doc(self.slug, "1.0")
        d.status = "Published"  # Draft -> Published غير مسموح
        with self.assertRaises(frappe.PermissionError):
            d.save(ignore_permissions=True)

    def test_publish_flow_sets_hash_and_stamps(self):
        d = publish(make_doc(self.slug, "1.0"))
        self.assertEqual(d.status, "Published")
        self.assertTrue(d.content_hash)
        self.assertTrue(d.published_on)
        pub = get_published(self.slug)
        self.assertTrue(pub and pub["version"] == "1.0")

    def test_immutable_after_publish(self):
        d = publish(make_doc(self.slug, "1.0"))
        d.content = "<p>محتوى مغيّر</p>"
        with self.assertRaises(frappe.PermissionError):
            d.save(ignore_permissions=True)

    def test_new_version_supersedes_previous(self):
        v1 = publish(make_doc(self.slug, "1.0"))
        v2 = publish(make_doc(self.slug, "2.0"))
        v1.reload()
        self.assertEqual(v1.status, "Superseded")
        pub = get_published(self.slug)
        self.assertEqual(pub["version"], "2.0")

    def test_non_operator_cannot_drive(self):
        d = make_doc(self.slug, "1.0")
        frappe.set_user(self.admin_a)  # Nonprofit Admin: قراءة فقط على Legal Document
        try:
            d2 = frappe.get_doc("Legal Document", d.name)
            d2.status = "In Review"
            with self.assertRaises(frappe.PermissionError):
                d2.save()
        finally:
            frappe.set_user("Administrator")

    def test_acceptance_requires_published(self):
        d = make_doc(self.slug, "1.0")  # مسودة
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {"doctype": "Legal Acceptance", "charity": self.ca, "document": d.name,
                 "representative_name": "ممثل", "acceptance_text": "أوافق"}
            ).insert(ignore_permissions=True)

    def test_acceptance_binds_and_is_immutable(self):
        d = publish(make_doc(self.slug, "1.0"))
        acc = frappe.get_doc(
            {"doctype": "Legal Acceptance", "charity": self.ca, "document": d.name,
             "representative_name": "ممثل الجمعية", "representative_title": "مدير", "acceptance_text": "أوافق"}
        ).insert(ignore_permissions=True)
        acc.reload()
        self.assertEqual(acc.document_version, "1.0")
        self.assertEqual(acc.document_hash, d.content_hash)
        self.assertTrue(acc.accepted_on)
        acc.representative_name = "اسم مختلف"
        with self.assertRaises(frappe.PermissionError):
            acc.save(ignore_permissions=True)

    def test_acceptance_isolated_by_charity(self):
        d = publish(make_doc(self.slug, "1.0"))
        acc = frappe.get_doc(
            {"doctype": "Legal Acceptance", "charity": self.ca, "document": d.name,
             "representative_name": "ممثل", "acceptance_text": "أوافق"}
        ).insert(ignore_permissions=True)
        frappe.set_user(self.admin_b)
        try:
            vis = frappe.get_list("Legal Acceptance", pluck="name", limit_page_length=0)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(acc.name, vis)
