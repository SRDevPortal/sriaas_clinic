# sriaas_clinic/setup/address.py
import frappe
from .utils import create_cf_with_module, upsert_property_setter

DT = "Address"

def apply():
    # Create the Link users will actually use
    create_cf_with_module({
        DT: [{
            "fieldname": "sr_state_link",
            "label": "State New",
            "fieldtype": "Link",
            "options": "SR State",
            "insert_after": "city",
            "allow_in_quick_entry": 1,
            "mandatory_depends_on": 'eval:doc.country=="India"',
        }]
    })

    # Keep legacy text field VISIBLE, but not required; clear any old conditions
    if frappe.get_meta(DT).get_field("state"):
        upsert_property_setter(DT, "state", "reqd", "0", "Check")
        upsert_property_setter(DT, "state", "hidden", "0", "Check")
        upsert_property_setter(DT, "state", "read_only", "1", "Check")
        upsert_property_setter(DT, "state", "mandatory_depends_on", "", "Data")
        upsert_property_setter(DT, "state", "depends_on", "", "Data")
        # (optional) make it obvious it's just mirrored text
        # upsert_property_setter(DT, "state", "label", "State (legacy text)", "Data")
