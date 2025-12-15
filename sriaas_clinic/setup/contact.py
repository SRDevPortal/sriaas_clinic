# sriaas_clinic/setup/contact.py
from .utils import upsert_property_setter

def apply():
    _apply_contact_ui_customizations()

def _apply_contact_ui_customizations():
    upsert_property_setter("Address", "is_primary_address", "default", "1", "Text")
    upsert_property_setter("Address", "is_shipping_address", "default", "1", "Text")
