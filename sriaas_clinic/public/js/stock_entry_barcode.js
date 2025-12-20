frappe.ui.form.on('Stock Entry', {
  scan_barcode(frm) {
    if (!frm.doc.scan_barcode) return;

    let code = frm.doc.scan_barcode.trim();
    let price_list = "Standard Selling";

    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Batch",
        filters: { sr_barcode: code },
        fields: ["name", "item"],
        limit_page_length: 1
      },
      callback(r) {
        if (!(r.message && r.message.length)) {
          frappe.msgprint("❌ No Batch found for barcode: " + code);
          frm.set_value("scan_barcode", "");
          return;
        }

        let batch = r.message[0];

        // fetch item details
        frappe.call({
          method: "frappe.client.get",
          args: {
            doctype: "Item",
            name: batch.item
          },
          callback(res) {
            let item = res.message;

            // fetch selling price from Item Price
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

                // 🔁 check if row already exists for same item + batch
                let existing = frm.doc.items.find(row =>
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
                  row.qty = 1;
                  row.basic_rate = rate;
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
