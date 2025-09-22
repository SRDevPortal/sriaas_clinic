# sriaas_clinic/api/item_package_weight.py
import frappe

DIVISOR = 5000.0  # per your formula: (L*W*H)/5000 with L/W/H in cm

def _f(v):
    """Safe float cast (handles None / '1,234.5' in imports)."""
    try:
        if v is None:
            return 0.0
        if isinstance(v, str):
            v = v.replace(",", "").strip()
        return float(v or 0)
    except Exception:
        return 0.0

def calculate_pkg_weights(doc, method=None):
    """
    Fills:
      - sr_pkg_vol_weight  = (L * W * H) / 5000
      - sr_pkg_applied_weight = max(sr_pkg_dead_weight, sr_pkg_vol_weight)

    Runs on validate -> works for new, edit, and Data Import.
    Field units expected:
      - length/width/height in cm
      - weights in kg
    """
    L = _f(doc.get("sr_pkg_length"))
    W = _f(doc.get("sr_pkg_width"))
    H = _f(doc.get("sr_pkg_height"))
    dead = _f(doc.get("sr_pkg_dead_weight"))

    vol = 0.0
    if L and W and H:
        vol = (L * W * H) / DIVISOR

    applied = max(dead, vol)

    # round per your field precision (3 dp for weights)
    doc.sr_pkg_vol_weight = round(vol, 3)
    doc.sr_pkg_applied_weight = round(applied, 3)
