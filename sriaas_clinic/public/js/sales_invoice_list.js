// Admin-only cost summary in Sales Invoice list
frappe.listview_settings['Sales Invoice'] = {
  onload(listview) {
    const isAdmin =
      frappe.user.has_role('System Manager') || frappe.user.name === 'Administrator';

    if (!isAdmin) return;

    // Add extra fields so list rows carry needed values
    listview.page.fields_dict && listview.page.fields_dict.refresh && listview.page.fields_dict.refresh();
    listview.meta.additional_columns = (listview.meta.additional_columns || []).concat([
      'sr_cost_pct_overall', 'sr_total_cost'
    ]);

    // Decorate rows after render
    listview.on_row_render = (row, data) => {
      // Show a compact tag at right (like: CP% 20 • Cost ₹1,000)
      const pct = (data.sr_cost_pct_overall || 0);
      const cost = (data.sr_total_cost || 0);
      const badge = document.createElement('span');
      badge.className = 'badge badge-default';
      badge.style.marginLeft = '8px';
      badge.textContent = `CP% ${pct} • Cost ${format_currency(cost, data.currency || frappe.defaults.get_default("currency"))}`;
      // Append to subject/indicator container
      const subject = row.querySelector('.list-row-col .level-left .list-subject') ||
                      row.querySelector('.list-subject');
      if (subject) subject.appendChild(badge);
    };
  }
};
