frappe.query_reports["Decisions by Committee"] = {
    filters: [
        {
            fieldname: "committee",
            label: __("اللجنة"),
            fieldtype: "Link",
            options: "Committee",
        },
        {
            fieldname: "decision_owner",
            label: __("المسؤول"),
            fieldtype: "Link",
            options: "User",
        },
        {
            fieldname: "status",
            label: __("الحالة"),
            fieldtype: "Select",
            options: ["", "Open", "In Progress", "Completed", "Cancelled"],
        },
    ],
};
