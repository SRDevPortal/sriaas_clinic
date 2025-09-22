# sriaas_clinic/setup/ui.py
import frappe
from .utils import upsert_property_setter, collapse_section, set_label

def apply():
    _apply_address_ui_customizations()

def _apply_address_ui_customizations():
    upsert_property_setter("Address", "is_primary_address", "default", "1", "Text")
    upsert_property_setter("Address", "is_shipping_address", "default", "1", "Text")
