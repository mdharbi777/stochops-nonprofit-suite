frappe.query_reports["Executive Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("من تاريخ"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("إلى تاريخ"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
        },
    ],
    onload: function (report) {
        report.page.add_inner_message(
            __("أرقام الميزانية تشغيلية مُدخلة يدوياً — ليست بديلاً عن النظام المالي. الفترة تؤثّر فقط على «القرارات المكتملة خلال الفترة»؛ بقية المؤشرات حالية. الملغاة مستبعدة.")
        );
    },
};
