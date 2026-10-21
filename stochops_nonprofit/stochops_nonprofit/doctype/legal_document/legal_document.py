import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# آلة حالات وثيقة قانونية. الحالة النهائية = مجموعة فارغة.
STATUS_FLOW = {
    "Draft": {"In Review", "Archived"},
    "In Review": {"Approved", "Draft", "Archived"},
    "Approved": {"Published", "Draft", "Archived"},
    "Published": {"Superseded", "Archived"},
    "Superseded": {"Archived"},
    "Archived": set(),
}
APPROVE_PUBLISH_STATES = {"Approved", "Published"}
APPROVER_ROLES = {"System Manager", "Stochops Admin"}
LOCKED_FIELDS = ("content", "version", "slug", "language", "document_category")


def _content_hash(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class LegalDocument(Document):
    """وثيقة قانونية للمشغّل بإصدارات وحالات. النسخة المنشورة ثابتة غير قابلة للتحرير؛
    أي تعديل يصبح إصداراً جديداً. يُعتمد/يُنشر بصلاحية مشغّل المنصّة فقط، ويُختم (من/متى)،
    وتُحسب بصمة SHA-256 للمحتوى (دليل سلامة لا توقيع رقمي). نشر إصدار جديد يُحيل السابق Superseded."""

    def validate(self):
        before = self.get_doc_before_save()
        self._guard_transition(before)
        self._guard_immutable_after_publish(before)
        if self.status in APPROVE_PUBLISH_STATES and (not before or before.status != self.status):
            self._require_operator()

    def _guard_transition(self, before):
        if self.is_new() or not self.has_value_changed("status"):
            return
        old = before.status if before else None
        if old is None:
            return
        if self.status not in STATUS_FLOW.get(old, set()) and self.status != old:
            frappe.throw(
                _("انتقال غير مسموح لحالة الوثيقة: من «{0}» إلى «{1}».").format(old, self.status),
                frappe.PermissionError,
            )

    def _guard_immutable_after_publish(self, before):
        """بعد النشر، لا يتغيّر المحتوى/الإصدار/المعرّف/اللغة — فقط الانتقال لحالة لاحقة."""
        if not before or before.status not in ("Published", "Superseded", "Archived"):
            return
        changed = [f for f in LOCKED_FIELDS if self.has_value_changed(f)]
        if changed:
            frappe.throw(
                _("النسخة المنشورة ثابتة؛ أنشئ إصداراً جديداً بدل تعديلها. الحقول المقفلة: {0}").format(
                    "، ".join(changed)
                ),
                frappe.PermissionError,
            )

    def _require_operator(self):
        if not (APPROVER_ROLES & set(frappe.get_roles(frappe.session.user))):
            frappe.throw(_("اعتماد/نشر الوثائق القانونية يتطلّب صلاحية مشغّل المنصّة."), frappe.PermissionError)

    def before_save(self):
        before = self.get_doc_before_save()
        becoming_published = self.status == "Published" and (not before or before.status != "Published")
        becoming_approved = self.status == "Approved" and (not before or before.status != "Approved")

        if becoming_approved:
            self.approved_by = frappe.session.user
            self.approved_on = now_datetime()
        if becoming_published:
            if not (self.content or "").strip():
                frappe.throw(_("لا يمكن نشر وثيقة بلا محتوى."))
            self.content_hash = _content_hash(self.content)
            self.publisher = frappe.session.user
            self.published_on = now_datetime()

    def on_update(self):
        # عند النشر: أحِل أي نسخة منشورة سابقة بنفس المعرّف واللغة إلى Superseded
        if self.status == "Published":
            others = frappe.get_all(
                "Legal Document",
                filters={
                    "slug": self.slug,
                    "language": self.language,
                    "status": "Published",
                    "name": ["!=", self.name],
                },
                pluck="name",
            )
            for name in others:
                frappe.db.set_value("Legal Document", name, {"status": "Superseded", "supersedes": None})
                frappe.db.set_value("Legal Document", self.name, "supersedes", name)


@frappe.whitelist(allow_guest=True)
def get_published(slug, language="ar"):
    """يعيد الوثيقة القانونية المنشورة لمسار معيّن (عام، للقراءة فقط)."""
    slug = (slug or "").strip()
    rows = frappe.get_all(
        "Legal Document",
        filters={"slug": slug, "language": language, "status": "Published"},
        fields=["name", "title", "version", "effective_date", "content", "content_hash", "published_on"],
        limit=1,
    )
    if not rows:
        return None
    doc = rows[0]
    operator = frappe.db.get_value(
        "Legal Entity Profile", "Legal Entity Profile", ["public_display_name", "legal_name"], as_dict=True
    ) or {}
    doc["operator"] = operator.get("public_display_name") or operator.get("legal_name") or "STOCHOPS"
    return doc


@frappe.whitelist(allow_guest=True)
def list_published(language="ar"):
    """قائمة الوثائق القانونية المنشورة (للمركز القانوني)."""
    return frappe.get_all(
        "Legal Document",
        filters={"language": language, "status": "Published"},
        fields=["title", "slug", "version", "effective_date"],
        order_by="document_category asc",
    )
