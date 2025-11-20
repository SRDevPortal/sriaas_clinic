import frappe

def get_si_values(name):
    return frappe.get_value(
        "Sales Invoice",
        name,
        ["outstanding_amount", "grand_total", "rounded_total", "docstatus", "status"],
        as_dict=True
    )
