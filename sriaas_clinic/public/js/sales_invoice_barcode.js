// // old client script
// frappe.ui.form.on('Sales Invoice', {
//   scan_barcode(frm) {
//     if (!frm.doc.scan_barcode) return;
//     if (frm.doc.docstatus !== 0) return;

//     // 🚫 Warehouse must be selected
//     if (!frm.doc.set_warehouse) {
//       frappe.msgprint("⚠️ Please select Warehouse first");
//       frm.set_value("scan_barcode", "");
//       return;
//     }

//     const code = frm.doc.scan_barcode.trim();
//     const price_list = frm.doc.selling_price_list || "Standard Selling";

//     // 🔍 Find batch using barcode
//     frappe.call({
//       method: "frappe.client.get_list",
//       args: {
//         doctype: "Batch",
//         filters: { sr_barcode: code },
//         fields: ["name", "item"],
//         limit_page_length: 1
//       },
//       callback(r) {
//         if (!r.message || !r.message.length) {
//           frappe.msgprint(`❌ No Batch found for barcode: ${code}`);
//           frm.set_value("scan_barcode", "");
//           return;
//         }

//         const batch = r.message[0];

//         // 🔍 Fetch Item
//         frappe.call({
//           method: "frappe.client.get",
//           args: {
//             doctype: "Item",
//             name: batch.item
//           },
//           callback(itemRes) {
//             const item = itemRes.message;

//             // 🚫 Batch stock check (CORRECT API)
//             frappe.call({
//               method: "erpnext.stock.get_item_details.get_batch_qty",
//               args: {
//                 item_code: item.name,
//                 warehouse: frm.doc.set_warehouse,
//                 batch_no: batch.name
//               },
//               callback(stockRes) {
//                 const available_qty = stockRes.message || 0;

//                 if (available_qty < 1) {
//                   frappe.msgprint("❌ No stock available for this batch");
//                   frm.set_value("scan_barcode", "");
//                   return;
//                 }

//                 // 💰 Fetch selling price
//                 frappe.call({
//                   method: "frappe.client.get_list",
//                   args: {
//                     doctype: "Item Price",
//                     filters: {
//                       item_code: item.name,
//                       price_list: price_list
//                     },
//                     fields: ["price_list_rate"],
//                     order_by: "valid_from desc",
//                     limit_page_length: 1
//                   },
//                   callback(priceRes) {
//                     let rate = 0;
//                     if (priceRes.message && priceRes.message.length) {
//                       rate = priceRes.message[0].price_list_rate || 0;
//                     }

//                     // 🔁 Check existing row (same item + batch)
//                     let existing = frm.doc.items.find(row =>
//                       row.item_code === item.name &&
//                       row.batch_no === batch.name
//                     );

//                     if (existing) {
//                       existing.qty += 1;
//                     } else {
//                       let row = frm.add_child("items");
//                       row.item_code = item.name;
//                       row.item_name = item.item_name;
//                       row.batch_no = batch.name;
//                       row.qty = 1;
//                       row.rate = rate;
//                     }

//                     frm.refresh_field("items");
//                     frm.set_value("scan_barcode", "");
//                   }
//                 });
//               }
//             });
//           }
//         });
//       }
//     });
//   },

//   refresh(frm) {
//     // 🎯 Auto focus for fast scanning
//     if (frm.fields_dict.scan_barcode) {
//       frm.fields_dict.scan_barcode.$input?.focus();
//     }
//   }
// });


// latest client script
frappe.ui.form.on('Sales Invoice', {
  onload(frm) {
    apply_role_based_warehouse_rules(frm);
  },

  refresh(frm) {
    apply_role_based_warehouse_rules(frm);

    // 🎯 Auto focus for fast scanning
    if (frm.fields_dict.scan_barcode) {
      frm.fields_dict.scan_barcode.$input?.focus();
    }
  },

  set_warehouse(frm) {
    apply_role_based_warehouse_rules(frm);
  },

  // ==================================================
  // BARCODE SCAN (YOUR ORIGINAL LOGIC – UNTOUCHED)
  // ==================================================
  scan_barcode(frm) {
    if (!frm.doc.scan_barcode) return;
    if (frm.doc.docstatus !== 0) return;

    // 🚫 Warehouse must be selected
    if (!frm.doc.set_warehouse) {
      frappe.msgprint("⚠️ Please select Warehouse first");
      frm.set_value("scan_barcode", "");
      return;
    }

    const code = frm.doc.scan_barcode.trim();
    const price_list = frm.doc.selling_price_list || "Standard Selling";

    // 🔍 Find batch using barcode
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Batch",
        filters: { sr_barcode: code },
        fields: ["name", "item"],
        limit_page_length: 1
      },
      callback(r) {
        if (!r.message || !r.message.length) {
          frappe.msgprint(`❌ No Batch found for barcode: ${code}`);
          frm.set_value("scan_barcode", "");
          return;
        }

        const batch = r.message[0];

        // 🔍 Fetch Item
        frappe.call({
          method: "frappe.client.get",
          args: {
            doctype: "Item",
            name: batch.item
          },
          callback(itemRes) {
            const item = itemRes.message;

            // 🚫 Batch stock check
            frappe.call({
              method: "erpnext.stock.get_item_details.get_batch_qty",
              args: {
                item_code: item.name,
                warehouse: frm.doc.set_warehouse,
                batch_no: batch.name
              },
              callback(stockRes) {
                const available_qty = stockRes.message || 0;

                if (available_qty < 1) {
                  frappe.msgprint("❌ No stock available for this batch");
                  frm.set_value("scan_barcode", "");
                  return;
                }

                // 💰 Fetch selling price
                frappe.call({
                  method: "frappe.client.get_list",
                  args: {
                    doctype: "Item Price",
                    filters: {
                      item_code: item.name,
                      price_list: price_list
                    },
                    fields: ["price_list_rate"],
                    order_by: "valid_from desc",
                    limit_page_length: 1
                  },
                  callback(priceRes) {
                    let rate = 0;
                    if (priceRes.message && priceRes.message.length) {
                      rate = priceRes.message[0].price_list_rate || 0;
                    }

                    // 🔁 Existing row (same item + batch)
                    let existing = (frm.doc.items || []).find(row =>
                      row.item_code === item.name &&
                      row.batch_no === batch.name
                    );

                    if (existing) {
                      existing.qty += 1;
                    } else {
                      let row = frm.add_child("items");
                      row.item_code = item.name;
                      row.item_name = item.item_name;
                      row.batch_no = batch.name;
                      row.warehouse = frm.doc.set_warehouse;
                      row.qty = 1;
                      row.rate = rate;
                    }

                    frm.refresh_field("items");
                    frm.set_value("scan_barcode", "");
                  }
                });
              }
            });
          }
        });
      }
    });
  }
});

// ==================================================
// ROLE-BASED WAREHOUSE ENFORCEMENT (NEW)
// ==================================================

function apply_role_based_warehouse_rules(frm) {
  const roles = frappe.user_roles || [];

  // Admin / System Manager → free
  if (
    frappe.session.user === "Administrator" ||
    roles.includes("System Manager")
  ) {
    frm.set_df_property("set_warehouse", "read_only", 0);
    return;
  }

  if (roles.includes("OPD Biller")) {
    lock_warehouse(frm, "OPD Warehouse - SR");
    return;
  }

  if (roles.includes("Packaging Biller")) {
    lock_warehouse(frm, "Packaging Warehouse - SR");
    return;
  }
}

function lock_warehouse(frm, warehouse) {
  if (frm.doc.set_warehouse !== warehouse) {
    frm.set_value("set_warehouse", warehouse);
  }

  // 🔒 Lock warehouse field
  frm.set_df_property("set_warehouse", "read_only", 1);

  // 🔒 Force warehouse on item rows
  (frm.doc.items || []).forEach(row => {
    frappe.model.set_value(row.doctype, row.name, "warehouse", warehouse);
  });
}
