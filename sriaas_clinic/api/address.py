# sriaas_clinic/api/address.py
import frappe
from frappe import _
from india_compliance.gst_india.constants import STATE_NUMBERS


STATE_ALIASES = {
    "andaman nicobar": "Andaman and Nicobar Islands",
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "andaman & nicobar": "Andaman and Nicobar Islands",
    "ap": "Andhra Pradesh",
    "arunachal": "Arunachal Pradesh",
    "cg": "Chhattisgarh",
    "chattisgarh": "Chhattisgarh",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi ncr": "Delhi",
    "hp": "Himachal Pradesh",
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu kashmir": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "ka": "Karnataka",
    "mp": "Madhya Pradesh",
    "mh": "Maharashtra",
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "pb": "Punjab",
    "rj": "Rajasthan",
    "tn": "Tamil Nadu",
    "tamilnadu": "Tamil Nadu",
    "ts": "Telangana",
    "tg": "Telangana",
    "up": "Uttar Pradesh",
    "u.p": "Uttar Pradesh",
    "u.p.": "Uttar Pradesh",
    "uttaranchal": "Uttarakhand",
    "uk": "Uttarakhand",
    "uttrakhand": "Uttarakhand",
    "wb": "West Bengal",
}


def _state_key(value: str) -> str:
    return " ".join((value or "").replace(".", " ").replace("-", " ").split()).strip().lower()


VALID_STATE_BY_KEY = {_state_key(state): state for state in STATE_NUMBERS}


def normalize_indian_state(value: str | None) -> str | None:
    state = (value or "").strip()
    if not state:
        return None

    if state in STATE_NUMBERS:
        return state

    key = _state_key(state)
    return STATE_ALIASES.get(key) or VALID_STATE_BY_KEY.get(key)

def _get_title(doctype: str, name: str) -> str:
    meta = frappe.get_meta(doctype)
    title_field = (meta.title_field or "").strip() if getattr(meta, "title_field", None) else ""
    if not title_field or title_field == "name":
        return name
    return frappe.get_cached_value(doctype, name, title_field) or name

def _append_customer_link_if_missing(d, customer: str, do_save: bool = False) -> bool:
    # ensure customer exists
    if not customer or not frappe.db.exists("Customer", customer):
        frappe.logger("sriaas").warning(f"Skipping append: Customer not found: {customer}")
        return False

    for l in (d.links or []):
        if l.link_doctype == "Customer" and l.link_name == customer:
            return False

    d.append("links", {
        "link_doctype": "Customer",
        "link_name": customer,
        "link_title": _get_title("Customer", customer),
    })
    if do_save:
        try:
            d.save(ignore_permissions=True)
        except Exception:
            frappe.logger("sriaas").exception(f"Failed to save Address/Contact {d.doctype}:{d.name} after appending Customer link {customer}")
            return False
    return True

def ensure_address_has_customer_link(doc, method=None):
    patients = [r.link_name for r in (doc.links or [])
                if getattr(r, "link_doctype", None) == "Patient" and getattr(r, "link_name", None)]
    if not patients:
        return

    # single query for all matching patients
    custs = frappe.get_all("Patient",
                           filters={"name": ["in", patients]},
                           pluck="customer")
    customers = {c for c in custs if c}
    if not customers:
        return

    existing = {(r.link_doctype, r.link_name) for r in (doc.links or [])
                if r.link_doctype and r.link_name}
    for cust in customers:
        if ("Customer", cust) not in existing:
            doc.append("links", {
                "link_doctype": "Customer",
                "link_name": cust,
                "link_title": _get_title("Customer", cust),
            })

def mirror_links_to_customer(doc, method=None):
    customer = doc.get("customer")
    if not customer or not frappe.db.exists("Customer", customer):
        return

    patient = doc.name

    addr_names = frappe.get_all(
        "Dynamic Link",
        filters={"parenttype": "Address", "link_doctype": "Patient", "link_name": patient},
        pluck="parent",
    )
    for addr in set(addr_names):
        try:
            addr_doc = frappe.get_doc("Address", addr)
        except frappe.DoesNotExistError:
            frappe.logger("sriaas").warning(f"Address not found: {addr} while mirroring links for patient {patient}")
            continue
        _append_customer_link_if_missing(addr_doc, customer, do_save=True)

    contact_names = frappe.get_all(
        "Dynamic Link",
        filters={"parenttype": "Contact", "link_doctype": "Patient", "link_name": patient},
        pluck="parent",
    )
    for c in set(contact_names):
        try:
            contact_doc = frappe.get_doc("Contact", c)
        except frappe.DoesNotExistError:
            frappe.logger("sriaas").warning(f"Contact not found: {c} while mirroring links for patient {patient}")
            continue
        _append_customer_link_if_missing(contact_doc, customer, do_save=True)

def validate_state(doc, method=None):
    """Normalize Indian states before India Compliance validates Address."""
    country = (doc.country or "").strip().lower()

    if country != "india":
        return

    raw_state = (doc.state or "").strip()
    if not raw_state:
        frappe.throw(_("State/Province is required for addresses in India."))

    normalized_state = normalize_indian_state(raw_state)
    if not normalized_state:
        frappe.throw(
            _("Invalid State {0}. Please select a valid Indian state.").format(frappe.bold(raw_state)),
            title=_("Invalid State"),
        )

    doc.state = normalized_state
