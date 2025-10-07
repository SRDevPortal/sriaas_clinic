# sriaas_clinic/api/integrations/n8n_shiprocket.py
# Send Sales Invoice order details to n8n webhook when sr_si_delivery_type == "By Courier"
# Shows full product details in Shiprocket while collecting COD = sr_si_outstanding_amount.

from __future__ import annotations
import json
from typing import Dict, Any, Optional

import requests
import frappe
from frappe.utils import cstr, flt, getdate, now_datetime, add_months


# ====== DEFAULTS (override via "Shiprocket Settings" Single) ======
N8N_WEBHOOK_URL_DEFAULT = "https://n8n.butest.tech/webhook/shiprocket/createOrder"
N8N_SECRET_HEADER = "x-erp-secret"       # HTTP headers are case-insensitive
MIN_SHIPMENT_WEIGHT_KG = 0.1             # floor for shipment weight
# ================================================================


# -------------------------------
# Settings + helpers
# -------------------------------
def _settings():
    """Single doctype with fields: enable_sync, pickup_location, n8n_webhook_url, n8n_secret."""
    return frappe.get_single("Shiprocket Settings")


def _webhook_url(s) -> str:
    return (cstr(getattr(s, "n8n_webhook_url", "")) or N8N_WEBHOOK_URL_DEFAULT).strip()


def _n8n_headers(s) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    secret = ""
    try:
        if getattr(s, "get_password", None):
            secret = s.get_password("n8n_secret", raise_exception=False) or ""
    except Exception:
        secret = ""
    secret = (secret or cstr(getattr(s, "n8n_secret", ""))).strip()
    if secret:
        headers[N8N_SECRET_HEADER] = secret
    return headers


def _shiprocket_order_date(posting_date) -> str:
    """Return 'YYYY-MM-DD HH:mm', clamped to last 6 months and not future."""
    base_date = getdate(posting_date) if posting_date else getdate()
    today = getdate()
    six_months_ago = getdate(add_months(today, -6))
    if base_date < six_months_ago:
        base_date = today
    if base_date > today:
        base_date = today
    tnow = now_datetime().time()
    return f"{base_date.strftime('%Y-%m-%d')} {tnow.strftime('%H:%M')}"


# -------------------------------
# Packaging helpers
# -------------------------------
def _get_item_pkg(item_code: str) -> Dict[str, float]:
    """Read Item.sr_pkg_*; return KG and CM."""
    try:
        it = frappe.get_cached_doc("Item", item_code)
        return {
            "L": flt(getattr(it, "sr_pkg_length", 0)),
            "W": flt(getattr(it, "sr_pkg_width", 0)),
            "H": flt(getattr(it, "sr_pkg_height", 0)),
            "applied": flt(getattr(it, "sr_pkg_applied_weight", 0)),  # kg
        }
    except Exception:
        return {"L": 0.0, "W": 0.0, "H": 0.0, "applied": 0.0}


def _aggregate_parcel_from_rows(rows):
    """
    One-parcel rule:
      - dimensions: take max L/W/H across items that have values
      - weight: sum(applied_weight_kg * qty)
      - floor to MIN_SHIPMENT_WEIGHT_KG
    """
    max_L = max_W = max_H = 0.0
    total_kg = 0.0
    for r in (rows or []):
        if not getattr(r, "item_code", None):
            continue
        q = flt(getattr(r, "qty", 0))
        if q <= 0:
            continue
        pkg = _get_item_pkg(cstr(r.item_code))
        max_L = max(max_L, pkg["L"])
        max_W = max(max_W, pkg["W"])
        max_H = max(max_H, pkg["H"])
        total_kg += pkg["applied"] * q
    if total_kg < MIN_SHIPMENT_WEIGHT_KG:
        total_kg = MIN_SHIPMENT_WEIGHT_KG
    return {"length": max_L, "breadth": max_W, "height": max_H, "weight_kg": total_kg}


# -------------------------------
# Address utils
# -------------------------------
def _extract_addr(addrname: Optional[str]) -> Dict[str, Any]:
    if not addrname:
        return {}
    try:
        adr = frappe.get_doc("Address", addrname)
        return {
            "line1": cstr(getattr(adr, "address_line1", "")),
            "line2": cstr(getattr(adr, "address_line2", "")),
            "city": cstr(getattr(adr, "city", "")),
            "state": cstr(getattr(adr, "state", "")),
            "pincode": cstr(getattr(adr, "pincode", "")),
            "country": cstr(getattr(adr, "country", "")) or "India",
            "phone": cstr(getattr(adr, "phone", "")),
            "email": cstr(getattr(adr, "email_id", "")),
        }
    except Exception:
        return {}


def _safe_phone(phone: str) -> str:
    p = cstr(phone).strip()
    return p or "9999999999"


# -------------------------------
# Payment mapping
# -------------------------------
PAYMENT_TERM_TO_METHOD = {
    "UNPAID": "COD",
    "PARTIALLY PAID": "COD",
    "PAID IN FULL": "Prepaid",
}


def _payment_method_from_term(si) -> str | None:
    term = cstr(getattr(si, "sr_si_payment_term", "")).strip().upper()
    return PAYMENT_TERM_TO_METHOD.get(term)


def _fallback_is_cod(si) -> bool:
    hints = {
        cstr(getattr(si, "mode_of_payment", "")).upper(),
        cstr(getattr(si, "payment_method", "")).upper(),
        cstr(getattr(si, "payment_terms_template", "")).upper(),
    }
    return "COD" in hints or bool(getattr(si, "is_cod", 0) or getattr(si, "sr_cod", 0))


# -------------------------------
# Build payload (Shiprocket-style)
# -------------------------------
def _build_payload_from_si(si) -> Dict[str, Any]:
    s = _settings()

    # addresses / contacts
    bill = _extract_addr(getattr(si, "customer_address", None))
    ship = _extract_addr(getattr(si, "shipping_address_name", None)) or bill
    billing_customer_name = cstr(getattr(si, "customer_name", "") or getattr(si, "customer", ""))
    contact_email = cstr(getattr(si, "contact_email", "") or bill.get("email") or ship.get("email") or "")
    contact_phone = _safe_phone(getattr(si, "contact_mobile", "") or bill.get("phone") or ship.get("phone") or "")

    # parcel
    agg = _aggregate_parcel_from_rows(si.items)

    # ---------- build items exactly as on SI (for the clean SR table) ----------
    order_items = []
    items_sum = 0.0
    for row in (si.items or []):
        if not getattr(row, "item_code", None):
            continue
        qty = flt(getattr(row, "qty", 0))
        if qty <= 0:
            continue
        unit_price = flt(getattr(row, "rate", 0)) or flt(getattr(row, "net_rate", 0))
        line_total = unit_price * qty
        items_sum += line_total

        order_items.append({
            "name": cstr(row.item_name or row.item_code),
            "sku": cstr(row.item_code),
            "units": cstr(int(qty) if qty.is_integer() else qty),
            "selling_price": cstr(unit_price),   # visible unit price (no tax on SR)
            "discount": "0",                     # keep Discount column = 0
            "tax": "0",                          # do not apply GST on SR
            "hsn": cstr(getattr(row, "gst_hsn_code", "") or getattr(row, "hsn_code", "")),
        })

    # Desired COD (what courier collects) = outstanding
    desired_cod = flt(getattr(si, "sr_si_outstanding_amount", 0)) or flt(getattr(si, "outstanding_amount", 0))

    # INFO: Shiprocket "Order Total" = items_sum. Log if it differs from COD you want to collect.
    if abs(items_sum - desired_cod) > 1.0:
        frappe.log_error(
            title="Shiprocket UI total may differ from COD",
            message=(
                f"SI {si.name}: Items sum = {items_sum}, Outstanding (COD) = {desired_cod}.\n"
                "Shiprocket shows Order Total from items. To match UI with COD, keep outstanding = items sum."
            ),
        )

    # payment method mapping
    method_from_term = _payment_method_from_term(si)
    payment_method = method_from_term if method_from_term else ("COD" if _fallback_is_cod(si) else "Prepaid")

    payload = {
        "order_id": cstr(si.name),
        "order_date": _shiprocket_order_date(getattr(si, "posting_date", None)),
        "pickup_location": cstr(getattr(s, "pickup_location", "") or "default_pickup"),
        "comment": cstr(getattr(si, "remarks", "") or ""),

        # billing
        "billing_customer_name": billing_customer_name,
        "billing_last_name": "",
        "billing_address": bill.get("line1", ""),
        "billing_address_2": bill.get("line2", ""),
        "billing_city": bill.get("city", ""),
        "billing_pincode": bill.get("pincode", ""),
        "billing_state": bill.get("state", ""),
        "billing_country": bill.get("country", "") or "India",
        "billing_email": contact_email,
        "billing_phone": contact_phone,

        # shipping
        "shipping_is_billing": bool(ship == bill),
        "shipping_customer_name": billing_customer_name,
        "shipping_last_name": "",
        "shipping_address": ship.get("line1", ""),
        "shipping_address_2": ship.get("line2", ""),
        "shipping_city": ship.get("city", ""),
        "shipping_pincode": ship.get("pincode", ""),
        "shipping_country": ship.get("country", "") or "India",
        "shipping_state": ship.get("state", ""),
        "shipping_email": contact_email,
        "shipping_phone": contact_phone,

        # items (verbatim details)
        "order_items": order_items,

        # payment & totals
        "payment_method": payment_method,                          # "COD" | "Prepaid"
        "collectable_amount": cstr(desired_cod if payment_method == "COD" else 0.0),
        "sub_total": cstr(items_sum),                              # SR UI total = items_sum
        "order_total": cstr(items_sum),                            # informational
        "order_tax": "0",                                          # keep SR tax off

        # parcel (KG + CM)
        "length":  cstr(agg["length"]),
        "breadth": cstr(agg["breadth"]),
        "height":  cstr(agg["height"]),
        "weight":  cstr(agg["weight_kg"]),
    }
    return payload


# -------------------------------
# POST to n8n
# -------------------------------
def _post_n8n(url: str, body: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
    return requests.post(url, headers=headers, json=body, timeout=60)


# -------------------------------
# Public entrypoint (hook)
# -------------------------------
def send_to_n8n_on_submit(doc, method):
    """
    Hook: Sales Invoice -> on_submit
    Only when sr_si_delivery_type == "By Courier" and settings.enable_sync is true.
    """
    if cstr(getattr(doc, "sr_si_delivery_type", "")).strip() != "By Courier":
        return

    s = _settings()
    if not getattr(s, "enable_sync", 0):
        return

    # optional de-dupe
    if bool(getattr(doc, "sent_to_n8n", 0)):
        return

    payload = _build_payload_from_si(doc)
    body = {"source": "erpnext", "doctype": "Sales Invoice", "name": cstr(doc.name), "payload": payload}
    url = _webhook_url(s)
    headers = _n8n_headers(s)

    try:
        resp = _post_n8n(url, body, headers)
    except requests.RequestException as e:
        frappe.log_error(
            "n8n webhook network error",
            f"URL: {url}\nSI: {doc.name}\nError: {e}\nBody:\n{json.dumps(body, indent=2)}"
        )
        return

    if resp.status_code not in (200, 201, 202):
        frappe.log_error(
            f"n8n webhook error {resp.status_code}",
            f"URL: {url}\nSI: {doc.name}\nBody:\n{json.dumps(body, indent=2)}\n\nResponse:\n{resp.text}"
        )
        return

    # mark sent (if field exists)
    try:
        frappe.db.set_value(doc.doctype, doc.name, "sent_to_n8n", 1, update_modified=False)
    except Exception:
        pass

    frappe.logger().info(f"[n8n] Webhook accepted for SI {doc.name}: {resp.text[:250]}")
