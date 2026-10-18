frappe.pages["nonprofit-dashboard"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("لوحة الجمعية — المؤشرات"),
        single_column: true,
    });

    const from_field = page.add_field({
        fieldname: "from_date", label: __("من تاريخ"), fieldtype: "Date",
        default: frappe.datetime.month_start(),
    });
    const to_field = page.add_field({
        fieldname: "to_date", label: __("إلى تاريخ"), fieldtype: "Date",
        default: frappe.datetime.month_end(),
    });

    page.set_primary_action(__("تحديث"), () => render());

    const $body = $('<div style="padding:12px 0"></div>').appendTo(page.body);

    function card(title, value, sub) {
        return `<div style="flex:1 1 180px;min-width:180px;border:1px solid var(--border-color);
            border-radius:8px;padding:14px 16px;background:var(--card-bg,#fff)">
            <div style="font-size:12px;color:var(--text-muted)">${frappe.utils.escape_html(title)}</div>
            <div style="font-size:26px;font-weight:700;margin-top:4px">${value}</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">${sub || ""}</div>
        </div>`;
    }

    function render() {
        frappe.call({
            method: "stochops_nonprofit.dashboard_metrics.get_dashboard",
            args: { from_date: from_field.get_value(), to_date: to_field.get_value() },
            callback: (r) => {
                const d = r.message || {};
                const sar = (n) =>
                    Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                const cards = [
                    card(__("القرارات غير الملغاة"), d.decisions_non_cancelled, __("إجمالي حالي")),
                    card(__("مفتوحة وقيد العمل"), d.decisions_open_inprogress, "Open + In Progress"),
                    card(__("القرارات المتأخرة"), d.decisions_overdue, __("الاستحقاق < اليوم")),
                    card(__("مكتملة خلال الفترة"), d.decisions_completed_in_period, `${d.from_date} → ${d.to_date}`),
                    card(__("المبادرات النشطة"), d.initiatives_active, "Active"),
                    card(__("المهام المتأخرة"), d.tasks_overdue, __("الاستحقاق < اليوم")),
                    card(__("إجمالي الميزانيات المخططة"), sar(d.total_planned_budget),
                        __("لـ") + " " + (d.initiatives_counted_planned || 0) + " " + __("مبادرة لها قيمة")),
                    card(__("إجمالي الصرف المسجّل"), sar(d.total_actual_spend),
                        __("لـ") + " " + (d.initiatives_counted_actual || 0) + " " + __("مبادرة لها قيمة")),
                ];
                const note = `<div style="background:var(--bg-light-gray,#f8fafc);border-radius:8px;
                    padding:10px 14px;margin-bottom:14px;font-size:12px;color:var(--text-muted)">
                    ${__("أرقام الميزانية تشغيلية مُدخلة يدوياً — ليست بديلاً عن النظام المالي ولا دقة محاسبية. النِّسب كمّية وليست قياس أثر. الملغاة مستبعدة.")}
                    ${d.initiatives_without_budget
                        ? "<br>" + __("مبادرات بلا أرقام ميزانية:") + " " + d.initiatives_without_budget + " " + __("(لا تُحتسب صفراً).")
                        : ""}
                </div>`;
                $body.html(note + `<div style="display:flex;flex-wrap:wrap;gap:12px">${cards.join("")}</div>`);
            },
        });
    }

    render();
};
