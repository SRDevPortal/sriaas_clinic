# sriaas_clinic/api/address.py
import frappe

def _get_title(doctype: str, name: str) -> str:
    """Return the display title for a doc (falls back to name)."""
    meta = frappe.get_meta(doctype)
    title_field = getattr(meta, "title_field", None) or "name"
    if title_field == "name":
        return name
    return frappe.db.get_value(doctype, name, title_field) or name

def _append_customer_link_if_missing(d, customer: str, do_save: bool = False) -> bool:
    for l in (d.links or []):
        if l.link_doctype == "Customer" and l.link_name == customer:
            return False
    d.append("links", {
        "link_doctype": "Customer",
        "link_name": customer,
        "link_title": _get_title("Customer", customer),
    })
    if do_save:
        d.save(ignore_permissions=True)
    return True

def ensure_address_has_customer_link(doc, method=None):
    patients = [
        r.link_name for r in (doc.links or [])
        if getattr(r, "link_doctype", None) == "Patient" and getattr(r, "link_name", None)
    ]
    if not patients:
        return

    customers = {
        c for c in (frappe.db.get_value("Patient", p, "customer") for p in patients) if c
    }
    if not customers:
        return

    existing = {(r.link_doctype, r.link_name) for r in (doc.links or []) if r.link_doctype and r.link_name}
    for cust in customers:
        if ("Customer", cust) not in existing:
            doc.append("links", {
                "link_doctype": "Customer",
                "link_name": cust,
                "link_title": _get_title("Customer", cust),
            })

def mirror_links_to_customer(doc, method=None):
    customer = doc.get("customer")
    if not customer:
        return

    patient = doc.name

    addr_names = frappe.get_all(
        "Dynamic Link",
        filters={"parenttype": "Address", "link_doctype": "Patient", "link_name": patient},
        pluck="parent",
    )
    for addr in set(addr_names):
        _append_customer_link_if_missing(frappe.get_doc("Address", addr), customer, do_save=True)

    contact_names = frappe.get_all(
        "Dynamic Link",
        filters={"parenttype": "Contact", "link_doctype": "Patient", "link_name": patient},
        pluck="parent",
    )
    for c in set(contact_names):
        _append_customer_link_if_missing(frappe.get_doc("Contact", c), customer, do_save=True)

def validate_state(doc, method=None):
    """Require an Indian state; accept either the link field or the legacy text.
    If only text is provided (e.g. Patient Quick Entry), auto-map it to SR State.
    """
    country = (doc.country or "").strip().lower()

    # If India and sr_state_link is empty but legacy text has a value,
    # try to resolve it to SR State by name.
    if country == "india" and not doc.get("sr_state_link") and (doc.state or "").strip():
        # Try exact name in SR State.sr_state_name
        match = frappe.db.get_value("SR State",
                                    {"sr_state_name": doc.state.strip()},
                                    "name")
        if not match:
            # also try by docname (in case name == state name)
            match = frappe.db.get_value("SR State", doc.state.strip(), "name")

        if match:
            doc.sr_state_link = match

    # If still missing for India, block save
    if country == "india" and not doc.get("sr_state_link"):
        frappe.throw("State/Province is required for addresses in India.")

    # Keep legacy text in sync (some core reports still read it)
    if doc.get("sr_state_link"):
        # Use the SR State's title/name so the text looks nice
        state_name = frappe.db.get_value("SR State", doc.sr_state_link, "sr_state_name") or doc.sr_state_link
        doc.state = state_name
