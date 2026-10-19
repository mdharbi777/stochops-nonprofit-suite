"""التحقق من سلامة التثبيت — يُشغّل بعد install-app/migrate على أي موقع.

bench --site <site> execute stochops_nonprofit.setup.verify_install.run
يعيد ملخّصاً بوجود الـ DocTypes والأدوار والتقارير ولوحة المؤشرات (للتسليم/الفحص).
"""
import frappe

EXPECTED_DOCTYPES = [
    "Charity",
    "Committee", "Meeting", "Decision", "Decision Follow-up",
    "Initiative", "Initiative Task",
    "Beneficiary", "Assistance Request",
    "Donor", "Donation", "Grant",
    "Expense Request", "Compliance Obligation",
    "Personnel", "Contract", "Procurement Request",
    "Nonprofit AI Settings", "AI Run Log",
    "Privacy Configuration", "Regulatory Rule", "Data Field Catalog",
    "Processing Activity Record", "Sensitive Access Log",
    "Consent Record", "Privacy Rights Request", "Privacy Impact Assessment",
    "Disclosure Request", "Report Template Registry",
    "Retention Schedule", "Legal Hold", "Security Incident", "Subprocessor Register",
]
EXPECTED_ROLES = [
    "Stochops Admin",
    "Nonprofit Admin", "Executive Viewer", "Committee Coordinator", "Program Coordinator",
]
EXPECTED_REPORTS = [
    "Overdue Decisions", "Decisions by Committee", "Initiatives Overview", "Executive Summary",
    "Compliance Obligations", "Beneficiary Categories",
]


def run():
    doctypes = frappe.get_all("DocType", filters={"module": "Stochops Nonprofit"}, pluck="name")
    reports = frappe.get_all("Report", filters={"module": "Stochops Nonprofit"}, pluck="name")
    notifications = frappe.get_all(
        "Notification", filters={"channel": "System Notification", "enabled": 1}, pluck="name"
    )
    result = {
        "doctypes_ok": all(d in doctypes for d in EXPECTED_DOCTYPES),
        "doctypes": sorted(doctypes),
        "roles_ok": all(frappe.db.exists("Role", r) for r in EXPECTED_ROLES),
        "reports_ok": all(r in reports for r in EXPECTED_REPORTS),
        "reports": sorted(reports),
        "dashboard_page_ok": bool(frappe.db.exists("Page", "nonprofit-dashboard")),
        "notifications_ok": len(notifications) >= 6,
        "notifications_count": len(notifications),
        "user_charity_field_ok": frappe.db.has_column("User", "charity"),
    }
    result["all_ok"] = (
        result["doctypes_ok"]
        and result["roles_ok"]
        and result["reports_ok"]
        and result["dashboard_page_ok"]
        and result["notifications_ok"]
        and result["user_charity_field_ok"]
    )
    return result
