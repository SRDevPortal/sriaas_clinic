# sriaas_clinic/setup/item_package.py
import frappe
from .utils import create_cf_with_module

DT = "Item"

def apply():
    _setup_item_package_details_tab()

def _setup_item_package_details_tab():
    """
    Add a new tab "Package Details" with fields:
    - Package Length (cm) (Float)
    - Package Width (cm) (Float)
    - Package Height (cm) (Float)
    - Dead Weight (kg) (Float)
    - Volumetric Weight (kg) (Float, read-only)
    - Applied Weight (kg) (Float, read-only)
    1 cm = 0.01 m
    Volumetric Weight (kg) = (Length cm * Width cm * Height cm) / 5000
    Applied Weight (kg) = max(Dead Weight, Volumetric Weight)
    """
    create_cf_with_module({
        DT: [
            {"fieldname": "sr_pkg_tab","label": "Package Details","fieldtype": "Tab Break","insert_after": "total_projected_qty"},

            # section break to group package fields
            {"fieldname": "sr_pkg_section","label": "Package","fieldtype": "Section Break","insert_after": "sr_pkg_tab"},

            # Left column
            {"fieldname": "sr_pkg_length","label": "Package Length (cm)","fieldtype": "Float","precision": 2,"insert_after": "sr_pkg_section"},
            {"fieldname": "sr_pkg_width","label": "Package Width (cm)","fieldtype": "Float","precision": 2,"insert_after": "sr_pkg_length"},
            {"fieldname": "sr_pkg_height","label": "Package Height (cm)","fieldtype": "Float","precision": 2,"insert_after": "sr_pkg_width"},
            {"fieldname": "sr_pkg_dead_weight","label": "Dead Weight (kg)","fieldtype": "Float","precision": 3,"insert_after": "sr_pkg_height"},

            # Right column
            {"fieldname": "sr_pkg_cb","fieldtype": "Column Break","insert_after": "sr_pkg_dead_weight"},
            {"fieldname": "sr_pkg_vol_weight","label": "Volumetric Weight (kg)","fieldtype": "Float","precision": 3,"read_only": 1,"insert_after": "sr_pkg_cb"},
            {"fieldname": "sr_pkg_applied_weight","label": "Applied Weight (kg)","fieldtype": "Float","precision": 3,"read_only": 1,"insert_after": "sr_pkg_vol_weight"},
        ]
    })
