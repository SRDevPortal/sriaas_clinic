// sriaas_clinic/public/js/crm_lead_list.js

frappe.listview_settings['CRM Lead'] = {
  onload(listview) {

    console.log('✅ CRM Lead list loaded');

    const roles = frappe.user_roles || [];
    const can_manage =
      roles.includes("Team Leader") ||
      roles.includes("System Manager") ||
      frappe.session.user === "Administrator";

    if (!can_manage) return;

    // ------------------------------------------------------------
    // ASSIGN CRM LEAD
    // ------------------------------------------------------------
    listview.page.add_actions_menu_item(__('Assign Lead'), () => {
      const selected = listview.get_checked_items();
      if (!selected.length) {
        frappe.msgprint(__('Please select at least one CRM Lead'));
        return;
      }

      frappe.prompt(
        [{
          fieldname: 'new_owner',
          label: 'Assign To (Agent)',
          fieldtype: 'Link',
          options: 'User',
          reqd: 1
        }],
        (values) => {
          frappe.call({
            method: 'sriaas_clinic.api.crm_lead.controller.assign_crm_lead_owner',
            args: {
              leads: selected.map(d => d.name),
              new_owner: values.new_owner
            },
            freeze: true,
            callback() {
              frappe.msgprint(__('Lead assigned successfully'));
              listview.refresh();
            }
          });
        },
        __('Assign Lead'),
        __('Assign')
      );
    });

    // ------------------------------------------------------------
    // CLEAR ASSIGN CRM LEAD
    // ------------------------------------------------------------
    listview.page.add_actions_menu_item(__('Clear Assign Lead'), () => {
      const selected = listview.get_checked_items();
      if (!selected.length) {
        frappe.msgprint(__('Please select at least one CRM Lead'));
        return;
      }

      frappe.confirm(
        __('Are you sure you want to clear assignment for selected leads?'),
        () => {
          frappe.call({
            method: 'sriaas_clinic.api.crm_lead.controller.clear_crm_lead_owner',
            args: {
              leads: selected.map(d => d.name)
            },
            freeze: true,
            callback() {
              frappe.msgprint(__('Lead assignment cleared successfully'));
              listview.refresh();
            }
          });
        }
      );
    });
  }
};