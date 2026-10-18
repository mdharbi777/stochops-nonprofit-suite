"""بيانات تجريبية وهمية للوحدة الأولى — قابلة لإعادة التشغيل بأمان وللحذف.

تشغيل:  bench --site <site> execute stochops_nonprofit.setup.seed_demo.run
حذف:    bench --site <site> execute stochops_nonprofit.setup.seed_demo.clear

ملاحظة: لا تحتوي أي بيانات مستفيدين أو هويات — أسماء لجان/قرارات عامة فقط موسومة بـ (عيّنة).
"""
import frappe
from frappe.utils import add_days, today

from stochops_nonprofit.setup.roles import ensure_roles

TAG = "(عيّنة)"

COMMITTEES = [
    {"committee_name": f"مجلس الإدارة {TAG}", "committee_type": "مجلس إدارة"},
    {"committee_name": f"لجنة البرامج {TAG}", "committee_type": "لجنة"},
]


def _get_or_create_committee(c):
    if frappe.db.exists("Committee", c["committee_name"]):
        return c["committee_name"]
    return frappe.get_doc(
        {"doctype": "Committee", "coordinator": "Administrator", **c}
    ).insert().name


def run():
    frappe.set_user("Administrator")
    ensure_roles()
    out = {"committees": [], "meetings": [], "decisions": []}

    committees = [_get_or_create_committee(c) for c in COMMITTEES]
    out["committees"] = committees

    meetings = []
    for i, cm in enumerate(committees):
        title = f"اجتماع دوري {i + 1} {TAG}"
        existing = frappe.db.get_value("Meeting", {"committee": cm, "title": title})
        if existing:
            meetings.append(existing)
            continue
        meetings.append(
            frappe.get_doc(
                {
                    "doctype": "Meeting",
                    "committee": cm,
                    "title": title,
                    "meeting_date": add_days(today(), -10),
                    "status": "Approved",
                }
            ).insert().name
        )
    out["meetings"] = meetings

    specs = [
        {"title": f"اعتماد خطة البرامج {TAG}", "meeting": meetings[0], "status": "Open", "due": add_days(today(), -5)},
        {"title": f"تحديث اللائحة الداخلية {TAG}", "meeting": meetings[0], "status": "In Progress", "due": add_days(today(), 7)},
        {"title": f"رفع التقرير السنوي {TAG}", "meeting": meetings[0], "status": "Completed", "due": add_days(today(), -20), "note": "تم الرفع للجهة المختصة"},
        {"title": f"مراجعة الميزانية الإدارية {TAG}", "meeting": meetings[1], "status": "Open", "due": add_days(today(), -1)},
        {"title": f"إلغاء فعالية مؤجلة {TAG}", "meeting": meetings[1], "status": "Cancelled", "due": add_days(today(), -3)},
    ]
    for s in specs:
        if frappe.db.exists("Decision", {"title": s["title"]}):
            continue
        d = frappe.get_doc(
            {
                "doctype": "Decision",
                "meeting": s["meeting"],
                "title": s["title"],
                "decision_owner": "Administrator",
                "due_date": s["due"],
            }
        )
        d.insert()
        if s["status"] != "Open":
            d.status = s["status"]
            if s.get("note"):
                d.completion_note = s["note"]
            d.save()
        out["decisions"].append(d.name)

    frappe.db.commit()
    return out


def clear():
    frappe.set_user("Administrator")
    deleted = {"decisions": 0, "meetings": 0, "committees": 0}
    for name in frappe.get_all("Decision", filters=[["title", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Decision", name, force=1)
        deleted["decisions"] += 1
    for name in frappe.get_all("Meeting", filters=[["title", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Meeting", name, force=1)
        deleted["meetings"] += 1
    for name in frappe.get_all("Committee", filters=[["committee_name", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Committee", name, force=1)
        deleted["committees"] += 1
    frappe.db.commit()
    return deleted
