frappe.query_reports["Overdue Decisions"] = {
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
    ],
};
