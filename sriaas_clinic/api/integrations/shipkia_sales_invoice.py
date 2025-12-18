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


def _headers(s) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}

    token = ""
    try:
        token = s.get_password("api_token", raise_exception=False) or ""
    except Exception:
        token = ""

    if token:
        headers[cstr(s.header_key or "x-api-key")] = token

    return headers


# =========================================================
# Helpers: Utility
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
    return "+91-9999999999"


def _payment_method(si) -> str:
    """
    Decide payment method based on outstanding amount
    """
    outstanding = flt(getattr(si, "outstanding_amount", 0))

    if outstanding <= 0:
        return "Prepaid"

    return "Cash on delivery"


# =========================================================
# Helpers: Package Calculation
# =========================================================

def _calculate_package(items):
    """
    Calculates dead & volumetric weight
    volumetric = (L * B * H) / 5000
    """
    max_l = max_b = max_h = 0.0
    dead_weight = 0.0

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

        max_l = max(max_l, l)
        max_b = max(max_b, b)
        max_h = max(max_h, h)
        dead_weight += w * flt(row.qty)

    volumetric = (max_l * max_b * max_h) / 5000 if max_l and max_b and max_h else 0

    # Shipkia safety floor
    if dead_weight <= 0:
        dead_weight = 0.1

    if volumetric <= 0:
        volumetric = 0.1

    return {
        "length": round(max_l, 2),
        "breadth": round(max_b, 2),
        "height": round(max_h, 2),
        "dead_weight": round(dead_weight, 2),
        "volumetric_weight": round(volumetric, 2),
    }


# =========================================================
# Payload Builder
# =========================================================

def _get_shipping_address(si):
    """
    Safe shipping address resolution
    """
    if si.shipping_address_name:
        return frappe.get_doc("Address", si.shipping_address_name)

    if si.customer_address:
        return frappe.get_doc("Address", si.customer_address)

    frappe.throw("No Shipping or Customer Address found for Shipkia sync")


def _build_payload_from_so(si) -> Dict[str, Any]:
    s = _settings()
    shipping = _get_shipping_address(si)
    package = _calculate_package(si.items)

    products = []
    total_value = 0.0

    for row in si.items:
        if not row.item_code:
            continue

        qty = flt(row.qty)
        rate = flt(row.rate)
        line_total = qty * rate
        total_value += line_total

        products.append({
            "product_name": cstr(row.item_name),
            "unit_price": round(rate, 2),
            "hsn_code": cstr(getattr(row, "gst_hsn_code", "")),
            "tax_rate": flt(getattr(row, "gst_tax_rate", 0)),
            "quantity": qty,
            "product_discount": 0,
            "tax_preference": "Inclusive",
        })
    
    contact_mobile = _safe_phone(si.contact_mobile)

    delivery_address = ", ".join(
        filter(None, [
            cstr(shipping.address_line1),
            cstr(shipping.address_line2),
        ])
    )

    payment_method = _payment_method(si)

    cod_amount = round(flt(si.outstanding_amount), 2)

    payload = {
        # Order meta
        "pick_up_address": cstr(s.pickup_address),
        "order_status": "New",
        "stage": "New",
        "order_channel": cstr(s.order_channel or "erpsriaas"),

        # Customer details
        "delivery_full_name": cstr(si.customer_name),
        "delivery_phone_number": contact_mobile,
        "delivery_address": delivery_address,
        "delivery_city": cstr(shipping.city),
        "delivery_state": cstr(shipping.state),
        "delivery_pincode": cstr(shipping.pincode),

        # Payment method
        "payment_method": payment_method,

        # Package details
        "length": package["length"],
        "breadth": package["breadth"],
        "height": package["height"],
        "dead_weight": package["dead_weight"],
        "volumetric_weight": package["volumetric_weight"],

        # Items
        "product_details": products,

        # Order value
        "total_order_value": round(total_value, 2),
        "cod_amount": cod_amount if payment_method == "Cash on delivery" else 0.0,
    }

    return payload


# =========================================================
# POST to Shipkia
# =========================================================

def _post_shipkia(payload: Dict[str, Any]):
    s = _settings()
    return requests.post(
        s.webhook_url,
        headers=_headers(s),
        json=payload,
        timeout=60,
    )


# =========================================================
# Public Hook: Auto Send Sales Invoice to Shipkia on Submit
# =========================================================

# def send_sales_invoice_to_shipkia(doc, method):
#     """
#     Hook: Sales Invoice -> on_submit
#     """

#     # DEBUG (temporary, very important)
#     frappe.log_error(
#         title="Shipkia Hook Triggered",
#         message=f"Sales Invoice Submitted: {doc.name}"
#     )

#     s = _settings()

#     if not s.enable_sync:
#         return

#     if getattr(doc, "sent_to_shipkia", 0):
#         return

#     payload = _build_payload_from_so(doc)

#     try:
#         resp = _post_shipkia(payload)
#     except Exception as e:
#         frappe.log_error(
#             title="Shipkia Network Error",
#             message=f"SI: {doc.name}\nError: {e}\nPayload:\n{json.dumps(payload, indent=2)}",
#         )
#         return

#     if resp.status_code not in (200, 201, 202):
#         frappe.log_error(
#             title="Shipkia API Error",
#             message=(
#                 f"SI: {doc.name}\n"
#                 f"Status: {resp.status_code}\n"
#                 f"Response:\n{resp.text}"
#             ),
#         )
#         return

#     # Mark as sent
#     if frappe.db.has_column("Sales Invoice", "sent_to_shipkia"):
#         frappe.db.set_value(
#             doc.doctype,
#             doc.name,
#             "sent_to_shipkia",
#             1,
#             update_modified=False,
#         )

#     frappe.logger().info(f"[Shipkia] Sales Invoice sent successfully: {doc.name}")


# ========================================================
# Public API: Manual Send Sales Invoice to Shipkia
# ========================================================

@frappe.whitelist()
def send_sales_invoice_to_shipkia(invoice_name: str):
    """
    MANUAL send to Shipkia (no auto submit)
    """

    si = frappe.get_doc("Sales Invoice", invoice_name)

    if si.docstatus != 1:
        frappe.throw("Sales Invoice must be submitted")

    s = _settings()
    if not s.enable_sync:
        frappe.throw("Shipkia sync is disabled in settings")

    payload = _build_payload_from_so(si)

    try:
        resp = _post_shipkia(payload)
    except Exception as e:
        frappe.log_error(
            title="Shipkia Network Error",
            message=f"SI: {si.name}\nError: {e}\nPayload:\n{json.dumps(payload, indent=2)}",
        )
        frappe.throw("Failed to connect to Shipkia")

    if resp.status_code not in (200, 201, 202):
        frappe.log_error(
            title="Shipkia API Error",
            message=f"SI: {si.name}\nStatus: {resp.status_code}\nResponse:\n{resp.text}",
        )
        frappe.throw("Shipkia API rejected the request")

    # Mark as sent
    if frappe.db.has_column("Sales Invoice", "sent_to_shipkia"):
        frappe.db.set_value(
            "Sales Invoice",
            si.name,
            "sent_to_shipkia",
            1,
            update_modified=False,
        )

    return {
        "success": True,
        "message": "Sales Invoice sent to Shipkia successfully"
    }
