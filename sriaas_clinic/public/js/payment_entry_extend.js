// public/js/payment_entry_extend.js
/* sync parent Payment Entry.mode_of_payment with sr_payment_modes child rows
   Behaviour:
   - If one unique child mode exists -> set parent to that mode
   - If >1 unique child modes -> try to set parent to Mode of Payment named "Multiple"
     (fallback: do nothing to avoid invalid Link values)
*/

frappe.ui.form.on('Payment Entry', {
    refresh(frm) {
        // only run on loaded docs (avoid extra calls when form empty)
        sync_parent_mode_from_children(frm);
    }
});

frappe.ui.form.on('Payment Mode Detail', {
    sr_mode_of_payment(frm, cdt, cdn) { sync_parent_mode_from_children(frm); },
    sr_amount(frm, cdt, cdn) { sync_parent_mode_from_children(frm); },
    add(frm) { sync_parent_mode_from_children(frm); },
    remove(frm) { sync_parent_mode_from_children(frm); }
});

function sync_parent_mode_from_children(frm) {
    const rows = frm.doc.sr_payment_modes || [];
    if (!rows.length) {
        // nothing in child -> do nothing
        return;
    }

    // collect unique non-empty modes
    const uniqueModes = [...new Set(rows.map(r => (r.sr_mode_of_payment || '').trim()).filter(Boolean))];

    // If no valid child modes, do nothing
    if (!uniqueModes.length) return;

    // Single mode => set parent to that mode (safe for Link)
    if (uniqueModes.length === 1) {
        const mode = uniqueModes[0];
        if (frm.doc.mode_of_payment !== mode) {
            frm.set_value('mode_of_payment', mode);
        }
        return;
    }

    // Multiple modes => try to set parent to Mode of Payment record named "Multiple"
    // (do a quick server call only when parent doesn't already equal "Multiple")
    const MULTIPLE_LABEL = 'Multiple';
    if (frm.doc.mode_of_payment === MULTIPLE_LABEL) {
        // already set, nothing more to do
        return;
    }

    // check if Mode of Payment "Multiple" exists
    frappe.call({
        method: 'frappe.client.exists',
        args: {
            doctype: 'Mode of Payment',
            name: MULTIPLE_LABEL
        },
        callback: function(r) {
            if (r.message) {
                // safe to set Link field to "Multiple"
                try {
                    frm.set_value('mode_of_payment', MULTIPLE_LABEL);
                } catch (e) {
                    // just log - avoid interrupting user
                    console.error('Failed to set mode_of_payment to Multiple', e);
                }
            } else {
                // No "Multiple" record — do nothing (avoid setting invalid Link)
                // Optionally you could set a combined string for display if parent is Data (not Link).
                // If you want an aggressive fallback, create "Multiple" automatically via API (not done here).
            }
        }
    });
}
