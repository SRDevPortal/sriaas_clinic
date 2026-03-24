# sriaas_clinic/api/integrations/shipkia_sales_invoice.py
from __future__ import annotations
import json
from typing import Dict, Any

import requests
import frappe
from frappe.utils import cstr, flt

# =========================================================
# Helpers: Settings
# =========================================================
def _settings():
    """Shipkia Settings (Single Doctype)"""
    return frappe.get_single("Shipkia Settings")


# =========================================================
# Headers: ERP → n8n Webhook
# =========================================================
def _webhook_headers(s) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}

    # --------------------------------------------------
    # n8n authentication
    # --------------------------------------------------
    webhook_token = s.get_password("webhook_header_token", raise_exception=False) or ""
    if webhook_token:
        headers[cstr(s.webhook_header_key or "x-api-key")] = webhook_token

    # --------------------------------------------------
    # Shipkia authentication (pass-through)
    # --------------------------------------------------    
    shipkia_token = s.get_password("shipkia_order_token", raise_exception=False) or ""
    if shipkia_token:
        headers["shipkia-auth-token"] = f"token {shipkia_token}"

    return headers


# =========================================================
# Headers: ERP → Shipkia API (Direct / Future)
# =========================================================
def _shipkia_headers(s) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}

    shipkia_token = s.get_password("shipkia_order_token", raise_exception=False) or ""
    if shipkia_token:
        headers["shipkia-auth-token"] = f"token {shipkia_token}"

    return headers


# =========================================================
# POST to Shipkia
# =========================================================
def _post_shipkia(payload: Dict[str, Any]):
    s = _settings()
    return requests.post(
        s.webhook_url,
        headers=_webhook_headers(s),   # ✅ ERP → n8n
        json=payload,
        timeout=60,
    )


# =========================================================
# Patient ID Helper
# =========================================================
def _get_patient_id(si) -> str:
    """
    Safely fetch sr_patient_id from Patient linked to Sales Invoice
    """
    patient_name = cstr(getattr(si, "patient", "")).strip()
    if not patient_name:
        return ""

    try:
        return cstr(frappe.db.get_value("Patient", patient_name, "sr_patient_id") or "")
    except Exception:
        return ""


# =========================================================
# Phone Normalizer Helper
# =========================================================
def _safe_phone(phone: str) -> str:
    """
    Normalize Indian mobile number:
    - Trim spaces
    - Remove internal spaces & hyphens
    - Remove leading 0
    - Ensure +91-XXXXXXXXXX format
    """
    phone = cstr(phone or "").strip()
    phone = phone.replace(" ", "").replace("-", "")

    # Remove leading 0
    if phone.startswith("0"):
        phone = phone[1:]

    # Remove country code if present
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]

    # Final validation (10 digit)
    if len(phone) == 10 and phone.isdigit():
        return f"+91-{phone}"

    # Fallback (Shipkia-safe dummy)
    # return "+91-9999999999"


# =========================================================
# Address Helpers
# =========================================================
def _get_shipping_address(si):
    if si.shipping_address_name:
        return frappe.get_doc("Address", si.shipping_address_name)

    if si.customer_address:
        return frappe.get_doc("Address", si.customer_address)

    frappe.throw("No Shipping Address found")


def _get_billing_address(si):
    if si.customer_address:
        return frappe.get_doc("Address", si.customer_address)

    if si.shipping_address_name:
        return frappe.get_doc("Address", si.shipping_address_name)

    frappe.throw("No Billing Address found")


# =========================================================
# Package Calculation Helper
# =========================================================
def _calculate_package(items):
    """
    Calculates dead & volumetric weight
    volumetric = (L * B * H) / 5000

    If item-level dimensions are missing:
    - Apply safe defaults
    - Do NOT block order creation
    """
    max_l = max_b = max_h = 0.0
    dead_weight = 0.0

    items_with_missing_dimensions = set()

    for row in items:
        if not row.item_code:
            continue

        try:
            item = frappe.get_cached_doc("Item", row.item_code)
        except Exception:
            continue

        l = flt(getattr(item, "sr_pkg_length", 0))
        b = flt(getattr(item, "sr_pkg_width", 0))
        h = flt(getattr(item, "sr_pkg_height", 0))
        w = flt(getattr(item, "sr_pkg_applied_weight", 0))

        # Detect missing dimensions at item level
        if l <= 0 or b <= 0 or h <= 0:
            items_with_missing_dimensions.add(row.item_code)

        max_l = max(max_l, l)
        max_b = max(max_b, b)
        max_h = max(max_h, h)
        dead_weight += w * flt(row.qty)
    
    # --------------------------------------------------
    # APPLY SAFE DEFAULTS (ONLY IF REQUIRED)
    # --------------------------------------------------
    if max_l <= 0:
        max_l = 1
    if max_b <= 0:
        max_b = 1
    if max_h <= 0:
        max_h = 1
    if dead_weight <= 0:
        dead_weight = 0.1

    volumetric = (max_l * max_b * max_h) / 5000
    if volumetric <= 0:
        volumetric = 0.1

    return {
        "length": round(max_l, 2),
        "breadth": round(max_b, 2),
        "height": round(max_h, 2),
        "dead_weight": round(dead_weight, 2),
        "volumetric_weight": round(volumetric, 2),
        "items_with_missing_dimensions": list(items_with_missing_dimensions),
    }


# =========================================================
# Payment Helpers
# =========================================================
def _payment_method(si) -> str:
    """
    Decide payment method based on outstanding amount
    """
    outstanding = flt(getattr(si, "outstanding_amount", 0))

    if outstanding <= 0:
        return "prepaid"

    return "cod"


# =========================================================
# Prepaid Amount Helper
# =========================================================
def _get_prepaid_amount(si) -> float:
    prepaid = flt(si.grand_total) - flt(si.outstanding_amount)
    return round(prepaid, 2) if prepaid > 0 else 0.0


# =========================================================
# Discount Helper
# =========================================================
def _get_total_discount(si) -> float:
    """
    Return ONLY actual discount applied on Sales Invoice.
    Do NOT treat tax difference as discount.
    """
    discount = flt(getattr(si, "discount_amount", 0))
    return round(discount, 2) if discount > 0 else 0.0


# =========================================================
# Tax Helper
# =========================================================
def _get_tax_rate(si) -> float:
    """
    Extract GST rate from Sales Invoice Taxes table
    Works for IGST / CGST / SGST
    """
    for tax in si.taxes or []:
        if flt(tax.rate) > 0:
            return flt(tax.rate)

    return 0.0


# =========================================================
# Shipkia Tag Helper
# =========================================================
def _build_shipkia_tag(si) -> str:
    parts = ["ERP"]

    if si.name:
        parts.append(f"SI:{si.name}")

    patient_id = _get_patient_id(si)
    if patient_id:
        parts.append(f"PAT:{patient_id}")

    return " | ".join(parts)


# =========================================================
# Payload Builder
# =========================================================
def _build_payload_from_so(si) -> Dict[str, Any]:
    s = _settings()

    shipping = _get_shipping_address(si)
    billing = _get_billing_address(si)

    billing_same_as_delivery = shipping.name == billing.name

    package = _calculate_package(si.items)

    if package["items_with_missing_dimensions"]:
        frappe.log_error(
            title="Shipkia Package Default Used",
            message=(
                "Default package dimensions were used while creating Shipkia order.\n\n"
                f"Items: {package['items_with_missing_dimensions']}"
            )
        )

    # if package["items_with_missing_dimensions"]:
    #     frappe.throw(
    #         "Cannot send order to Shipkia because package dimensions are missing.\n\n"
    #         "Please update Length / Width / Height for the following items:\n"
    #         f"{', '.join(package['items_with_missing_dimensions'])}"
    #     )

    products = []

    for row in si.items:
        if not row.item_code:
            continue

        products.append({
            "product_name": cstr(row.item_name),
            "unit_price": round(flt(row.rate), 2),
            "quantity": flt(row.qty),
            "hsn_code": cstr(getattr(row, "gst_hsn_code", "")),
            "product_discount": 0,
            "tax_rate": _get_tax_rate(si),
            "tax_preference": "Inclusive",
        })
 
    delivery_address = ", ".join(filter(None, [
        cstr(shipping.address_line1),
        cstr(shipping.address_line2),
    ]))

    billing_address = ", ".join(filter(None, [
        cstr(billing.address_line1),
        cstr(billing.address_line2),
    ]))

    payload = {
        # Meta
        "pickup_address": cstr(s.pickup_address),
        "order_channel": cstr(s.order_channel or "erpsriaas"),

        # Delivery
        "delivery_full_name": cstr(si.customer_name),
        "delivery_phone_number": _safe_phone(si.contact_mobile),
        "delivery_address": delivery_address,
        "delivery_city": cstr(shipping.city),
        "delivery_state": cstr(shipping.state),
        "delivery_pincode": cstr(shipping.pincode),

        # Billing logic
        "billing_same_as_delivery": billing_same_as_delivery,
    }

    # Only send billing block if DIFFERENT
    if not billing_same_as_delivery:
        payload.update({
            "billing_full_name": cstr(si.customer_name),
            "billing_phone_number": _safe_phone(si.contact_mobile),
            "billing_address": billing_address,
            "billing_city": cstr(billing.city),
            "billing_state": cstr(billing.state),
            "billing_pincode": cstr(billing.pincode),
        })
    
    payload.update({
        # Payment
        "payment_method": _payment_method(si),

        # Package
        "length": package["length"],
        "breadth": package["breadth"],
        "height": package["height"],
        "dead_weight": package["dead_weight"],
        # "volumetric_weight": package["volumetric_weight"],

        # Items
        "product_details": products,

        # Amounts
        "shipping_charges": 0,
        "transaction_charges": 0,
        "gift_wrap": 0,
        "total_discount": _get_total_discount(si),
        "prepaid_amount": _get_prepaid_amount(si),

        "notes": "",
        "tag": _build_shipkia_tag(si),
    })

    return payload


# ========================================================
# Public API: Manual Send Sales Invoice to Shipkia
# ========================================================
@frappe.whitelist()
def send_sales_invoice_to_shipkia(invoice_name: str):
    """
    MANUAL send to Shipkia via n8n webhook
    """

    si = frappe.get_doc("Sales Invoice", invoice_name)

    # --------------------------------------------------
    # Basic validations
    # --------------------------------------------------
    if si.docstatus != 1:
        frappe.throw("Sales Invoice must be submitted before sending to Shipkia.")

    s = _settings()
    if not s.enable_sync:
        frappe.throw("Shipkia sync is disabled in settings. Please enable it and try again.")

    payload = _build_payload_from_so(si)

    # --------------------------------------------------
    # Network / webhook call
    # --------------------------------------------------
    try:
        resp = _post_shipkia(payload)
    except Exception as e:
        frappe.log_error(
            title="Shipkia Network Error",
            message=(
                f"Sales Invoice: {si.name}\n"
                f"Error: {e}\n\n"
                f"Payload:\n{json.dumps(payload, indent=2)}"
            ),
        )
        frappe.throw(
            "Unable to reach the automation service (n8n). "
            "Please ensure the workflow is active and the webhook URL is accessible."
        )
    
    # --------------------------------------------------
    # n8n disabled / webhook not active
    # --------------------------------------------------
    if resp.status_code in (404, 410):
        frappe.log_error(
            title="Shipkia Webhook Disabled",
            message=(
                f"Sales Invoice: {si.name}\n"
                f"Status: {resp.status_code}\n"
                f"Response:\n{resp.text}"
            ),
        )
        frappe.throw(
            "Order sync failed because the automation service (n8n) is currently disabled. "
            "Please enable the workflow and try again."
        )

    # --------------------------------------------------
    # API-level rejection (validation / auth / data issue)
    # --------------------------------------------------
    if resp.status_code not in (200, 201, 202):
        frappe.log_error(
            title="Shipkia API Error",
            message=(
                f"Sales Invoice: {si.name}\n"
                f"Status: {resp.status_code}\n"
                f"Response:\n{resp.text}"
            ),
        )
        frappe.throw(
            "Unable to create order in Shipkia. "
            "The request was rejected due to validation or authorization issues. "
            "Please verify invoice data and Shipkia settings, then try again."
        )
    
    # --------------------------------------------------
    # Mark as sent (ONLY after success)
    # --------------------------------------------------
    if frappe.db.has_column("Sales Invoice", "sent_to_shipkia"):
        frappe.db.set_value(
            "Sales Invoice",
            si.name,
            "sent_to_shipkia",
            1,
            update_modified=False,
        )

    # --------------------------------------------------
    # Success response
    # --------------------------------------------------
    return {
        "success": True,
        "message": "Sales Invoice sent to Shipkia successfully.",
    }
