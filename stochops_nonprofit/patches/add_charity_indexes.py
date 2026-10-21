"""P6 — تحصين الأداء: فهرسة حقل `charity` على كل أنواع المستأجرين.

كل استعلام مُعزول (permission_query_conditions) يفلتر على `charity`؛ بلا فهرس يصبح مسحاً كاملاً
للجدول عند النمو. هذا الترقيع يضيف فهرساً على `charity` (عكوس: يمكن إسقاطه)، ويعمل مرّة واحدة.
"""
import frappe

TENANT_DOCTYPES = [
    "Committee", "Meeting", "Decision", "Initiative", "Initiative Task",
    "Beneficiary", "Assistance Request", "Donor", "Donation", "Grant",
    "Expense Request", "Compliance Obligation", "Personnel", "Contract",
    "Procurement Request", "AI Run Log", "Processing Activity Record",
    "Sensitive Access Log", "Consent Record", "Privacy Rights Request",
    "Privacy Impact Assessment", "Disclosure Request", "Legal Hold", "Security Incident",
]


def execute():
    for dt in TENANT_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            if frappe.db.has_column(dt, "charity"):
                frappe.db.add_index(dt, ["charity"])
        except Exception:
            # موجود مسبقاً أو تعذّر — غير قاتل للترحيل
            frappe.db.rollback()
            frappe.log_error(title="charity index skipped", message=dt)
