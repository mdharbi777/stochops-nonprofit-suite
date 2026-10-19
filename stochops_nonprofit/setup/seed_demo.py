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

    # --- المبادرات والمهام (الوحدة 2) — أعداد إجمالية فقط، بلا أي بيانات مستفيدين ---
    init_specs = [
        {"title": f"برنامج التأهيل {TAG}", "status": "Active", "start": add_days(today(), -30), "end": add_days(today(), 60),
         "objective": "تأهيل (عدد إجمالي)", "planned": 50000, "actual": 32000, "target": 200, "actual_count": 120, "unit": "مستفيد (عدد إجمالي فقط)"},
        {"title": f"مبادرة التوعية {TAG}", "status": "Completed", "start": add_days(today(), -90), "end": add_days(today(), -10),
         "objective": "حملات توعية", "planned": 15000, "actual": 16500, "note": "أُغلقت بنجاح", "target": 10, "actual_count": 10, "unit": "نشاط"},
        {"title": f"مشروع التطوير المؤسسي {TAG}", "status": "Planned", "start": today(), "end": add_days(today(), 120),
         "objective": "تطوير الإجراءات الداخلية"},
    ]
    initiatives = []
    for s in init_specs:
        existing = frappe.db.get_value("Initiative", {"title": s["title"]})
        if existing:
            initiatives.append(existing)
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Initiative", "title": s["title"], "initiative_owner": "Administrator",
                "objective": s["objective"], "start_date": s["start"], "end_date": s["end"],
                "planned_budget_sar": s.get("planned"), "actual_spend_sar": s.get("actual"),
                "target_count": s.get("target"), "actual_count": s.get("actual_count"), "target_unit": s.get("unit"),
            }
        )
        doc.insert()
        if s["status"] != "Planned":
            doc.status = s["status"]
            if s.get("note"):
                doc.closing_note = s["note"]
            doc.save()
        initiatives.append(doc.name)
    out["initiatives"] = initiatives

    task_specs = [
        {"initiative": initiatives[0], "title": f"إعداد الخطة {TAG}", "status": "Completed", "due": add_days(today(), -20), "note": "أُنجز"},
        {"initiative": initiatives[0], "title": f"تنفيذ الأنشطة {TAG}", "status": "In Progress", "due": add_days(today(), 15)},
        {"initiative": initiatives[0], "title": f"تقرير المتابعة {TAG}", "status": "Open", "due": add_days(today(), -2)},
        {"initiative": initiatives[1], "title": f"إغلاق الحملة {TAG}", "status": "Completed", "due": add_days(today(), -12), "note": "تم"},
    ]
    tasks = []
    for s in task_specs:
        if frappe.db.exists("Initiative Task", {"title": s["title"]}):
            continue
        d = frappe.get_doc(
            {"doctype": "Initiative Task", "initiative": s["initiative"], "title": s["title"], "assigned_to": "Administrator", "due_date": s["due"]}
        )
        d.insert()
        if s["status"] != "Open":
            d.status = s["status"]
            if s.get("note"):
                d.completion_note = s["note"]
            d.save()
        tasks.append(d.name)
    out["tasks"] = tasks

    # --- المستفيدون وطلبات المساعدة (الوحدة N2) — بيانات وهمية: أسماء عامة + أرقام هوية وهمية ---
    ben_specs = [
        {"beneficiary_name": f"أسرة أ {TAG}", "national_id": "1000000001", "gender": "أنثى", "social_category": "أرملة", "family_members_count": 5},
        {"beneficiary_name": f"أسرة ب {TAG}", "national_id": "1000000002", "gender": "ذكر", "social_category": "دخل محدود", "family_members_count": 3},
    ]
    beneficiaries = []
    for s in ben_specs:
        existing = frappe.db.get_value("Beneficiary", {"beneficiary_name": s["beneficiary_name"]})
        if existing:
            beneficiaries.append(existing)
            continue
        beneficiaries.append(frappe.get_doc({"doctype": "Beneficiary", **s}).insert().name)
    out["beneficiaries"] = beneficiaries

    req_specs = [
        {"beneficiary": beneficiaries[0], "request_type": "مالية", "amount": 1500, "priority": "عالية", "status": "معتمد", "note": "مستوفٍ للشروط (عيّنة)"},
        {"beneficiary": beneficiaries[1], "request_type": "عينية", "amount": 0, "priority": "عادية", "status": "مقدم"},
    ]
    requests = []
    for s in req_specs:
        if frappe.db.exists("Assistance Request", {"beneficiary": s["beneficiary"], "request_type": s["request_type"]}):
            continue
        d = frappe.get_doc(
            {
                "doctype": "Assistance Request", "beneficiary": s["beneficiary"], "request_type": s["request_type"],
                "amount": s["amount"], "priority": s["priority"], "description": f"طلب مساعدة {TAG}",
            }
        )
        d.insert()
        if s["status"] != "مقدم":
            d.status = s["status"]
            if s.get("note"):
                d.decision_note = s["note"]
            d.save()
        requests.append(d.name)
    out["requests"] = requests

    # --- المتبرعون والتبرعات والمنح (الوحدة N3) — تسجيل وهمي فقط، بلا بوابة دفع ---
    donor_specs = [
        {"donor_name": f"متبرّع فرد {TAG}", "donor_type": "فرد", "phone": "0500000001"},
        {"donor_name": f"جهة مانحة {TAG}", "donor_type": "جهة", "phone": "0500000002"},
    ]
    donors = []
    for s in donor_specs:
        existing = frappe.db.get_value("Donor", {"donor_name": s["donor_name"]})
        donors.append(existing or frappe.get_doc({"doctype": "Donor", **s}).insert().name)
    out["donors"] = donors

    don_specs = [
        {"donor": donors[0], "donation_type": "نقدي", "amount": 2000, "status": "مستلم", "reference": f"RCPT-001 {TAG}"},
        {"donor": donors[1], "donation_type": "تعهّد", "amount": 10000, "status": "تعهّد", "reference": f"PLDG-001 {TAG}"},
    ]
    donations = []
    for s in don_specs:
        if frappe.db.exists("Donation", {"reference": s["reference"]}):
            continue
        donations.append(
            frappe.get_doc({"doctype": "Donation", "donation_date": today(), "notes": TAG, **s}).insert().name
        )
    out["donations"] = donations

    grant_specs = [
        {"grant_title": f"منحة التشغيل {TAG}", "grantor_name": "مؤسسة مانحة (عيّنة)", "status": "معتمدة",
         "amount": 80000, "amount_received": 40000, "conditions": "تقارير ربع سنوية (عيّنة)",
         "start_date": add_days(today(), -30), "end_date": add_days(today(), 150)},
    ]
    grants = []
    for s in grant_specs:
        if frappe.db.exists("Grant", {"grant_title": s["grant_title"]}):
            continue
        grants.append(frappe.get_doc({"doctype": "Grant", **s}).insert().name)
    out["grants"] = grants

    # --- المصروفات (الوحدة N4) — أرقام إدارية محوكمة، حالات قبل البتّ (بلا دفع) ---
    exp_specs = [
        {"title": f"إيجار المقر {TAG}", "category": "إيجار", "amount": 12000, "status": "مقدّم"},
        {"title": f"مستلزمات برنامج {TAG}", "category": "برامج", "amount": 3500, "status": "قيد المراجعة"},
    ]
    expenses = []
    for s in exp_specs:
        if frappe.db.exists("Expense Request", {"title": s["title"]}):
            continue
        d = frappe.get_doc(
            {
                "doctype": "Expense Request", "request_date": today(), "title": s["title"],
                "category": s["category"], "amount": s["amount"], "status": s["status"],
            }
        )
        d.insert()
        expenses.append(d.name)
    out["expenses"] = expenses

    frappe.db.commit()
    return out


def clear():
    frappe.set_user("Administrator")
    deleted = {"expenses": 0, "grants": 0, "donations": 0, "donors": 0, "requests": 0, "beneficiaries": 0,
               "tasks": 0, "initiatives": 0, "decisions": 0, "meetings": 0, "committees": 0}
    for name in frappe.get_all("Expense Request", filters=[["title", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Expense Request", name, force=1)
        deleted["expenses"] += 1
    for name in frappe.get_all("Grant", filters=[["grant_title", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Grant", name, force=1)
        deleted["grants"] += 1
    for name in frappe.get_all("Donation", filters=[["notes", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Donation", name, force=1)
        deleted["donations"] += 1
    for name in frappe.get_all("Donor", filters=[["donor_name", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Donor", name, force=1)
        deleted["donors"] += 1
    for name in frappe.get_all("Assistance Request", filters=[["description", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Assistance Request", name, force=1)
        deleted["requests"] += 1
    for name in frappe.get_all("Beneficiary", filters=[["beneficiary_name", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Beneficiary", name, force=1)
        deleted["beneficiaries"] += 1
    for name in frappe.get_all("Initiative Task", filters=[["title", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Initiative Task", name, force=1)
        deleted["tasks"] += 1
    for name in frappe.get_all("Initiative", filters=[["title", "like", f"%{TAG}%"]], pluck="name"):
        frappe.delete_doc("Initiative", name, force=1)
        deleted["initiatives"] += 1
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
