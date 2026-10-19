"""تعريب المنصة — اللغة العربية فقط + توقيت السعودية (idempotent)."""
import frappe


def ensure_arabic():
    frappe.db.set_value("System Settings", "System Settings", "language", "ar")
    frappe.db.set_value("System Settings", "System Settings", "time_zone", "Asia/Riyadh")
    frappe.db.set_value("System Settings", "System Settings", "country", "Saudi Arabia")
    frappe.db.set_default("lang", "ar")
    frappe.db.set_default("time_zone", "Asia/Riyadh")
    frappe.db.commit()
    frappe.clear_cache()
    return {"language": "ar", "time_zone": "Asia/Riyadh", "country": "Saudi Arabia"}
