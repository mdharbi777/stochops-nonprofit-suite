frappe.query_reports["Initiatives Overview"] = {
    filters: [
        {
            fieldname: "status",
            label: __("الحالة"),
            fieldtype: "Select",
            options: ["", "Planned", "Active", "On Hold", "Completed", "Cancelled"],
        },
        {
            fieldname: "initiative_owner",
            label: __("المسؤول"),
            fieldtype: "Link",
            options: "User",
        },
    ],
    onload: function (report) {
        report.page.add_inner_message(
            __("أرقام الميزانية تشغيلية مُدخلة يدوياً — ليست بديلاً عن النظام المالي. النِّسب كمّية وليست قياس أثر.")
        );
    },
};
