import frappe

# أدوار الوحدة الأولى (القرارات واللجان). Program Coordinator يُستخدم في الوحدة الثانية
# لكن يُنشأ الآن حتى تكون مصفوفة الأدوار كاملة.
MODULE_ROLES = [
    "Nonprofit Admin",
    "Executive Viewer",
    "Committee Coordinator",
    "Program Coordinator",
]


def ensure_roles():
    """Create the app roles if missing. Idempotent; safe to re-run (after_install + patch)."""
    created = []
    for role_name in MODULE_ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                }
            ).insert(ignore_permissions=True)
            created.append(role_name)
    frappe.db.commit()
    return {"created": created, "all": MODULE_ROLES}
