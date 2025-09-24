// sriaas_clinic/public/js/address_state_link.js

frappe.ui.form.on('Address', {
  setup(frm) {
    set_state_query(frm);
  },
  onload(frm) {
    arrange_fields(frm);
    set_state_query(frm);
    backfill_link_from_text(frm);
  },
  onload_post_render(frm) {
    arrange_fields(frm);
  },
  refresh(frm) {
    arrange_fields(frm);
  },
  country(frm) {
    set_state_query(frm);
    arrange_fields(frm);
  },
  sr_state_link(frm) {
    if (frm.doc.state !== frm.doc.sr_state_link) {
      frm.set_value('state', frm.doc.sr_state_link || '');
    }
  },
  validate(frm) {
    if ((frm.doc.country || '').toLowerCase() === 'india' && !frm.doc.sr_state_link) {
      frappe.throw(__('State/Province is required for addresses in India.'));
    }
    frm.set_value('state', frm.doc.sr_state_link || '');
  },
});

// ----------------------
// helper functions
// ----------------------

function arrange_fields(frm) {
  const link = frm.fields_dict.sr_state_link;
  const txt  = frm.fields_dict.state;
  if (!link || !txt) return;

  // Place Link above legacy field
  link.$wrapper.insertBefore(txt.$wrapper);

  const is_india = (frm.doc.country || '').toLowerCase() === 'india';
  link.df.hidden = 0;
  link.df.reqd   = is_india;
  link.refresh();

  txt.df.hidden   = 0;
  txt.df.read_only = 1;
  txt.refresh();
}

function set_state_query(frm) {
  frm.set_query('sr_state_link', () => {
    const filters = {};
    if (frm.doc.country) filters.sr_country = frm.doc.country;
    return { filters };
  });
}

function backfill_link_from_text(frm) {
  if (!frm.doc.sr_state_link && frm.doc.state) {
    frappe.db.get_value('SR State', { name: frm.doc.state }, 'name').then(r => {
      if (r && r.message && r.message.name) {
        frm.set_value('sr_state_link', r.message.name);
      }
    });
  }
}

// ----------------------
// PATCH Quick Entry dialog
// ----------------------

// This is the key part: run our arrange_fields logic when Quick Entry is created.
frappe.ui.form.on('Patient', {
  onload_post_render(frm) {
    // Attach handler for embedded Address Quick Entry dialogs
    frm.$wrapper.on('dialog:render', (e, dialog) => {
      if (dialog && dialog.fields_dict && dialog.fields_dict.sr_state_link) {
        const addressFrm = dialog.fields_dict;
        // Call our arrange logic after a short delay to let fields render
        setTimeout(() => {
          arrange_fields(dialog);
        }, 50);
      }
    });
  },
});
