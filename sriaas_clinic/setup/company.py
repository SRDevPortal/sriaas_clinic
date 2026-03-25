# sriaas_clinic/setup/company.py
from .utils import create_cf_with_module

DT = "Company"


def apply():
    _make_company_fields()


def _make_company_fields():
    """Add custom fields to Company"""

    create_cf_with_module({
        DT: [

            # ------------------------------------------
            # 🔹 Basic Info
            # ------------------------------------------
            {
                "fieldname": "sr_company_cin_no",
                "label": "CIN No",
                "fieldtype": "Data",
                "insert_after": "pan",
            },

            # ------------------------------------------
            # 🔹 Branding Section
            # ------------------------------------------
            {
                "fieldname": "sr_branding_section",
                "label": "Branding Details",
                "fieldtype": "Section Break",
                "insert_after": "parent_company",
            },

            {
                "fieldname": "sr_company_logo",
                "label": "Company Logo URL",
                "fieldtype": "Data",
                "options": "URL",
                "insert_after": "sr_branding_section",
                "description": "Paste public image URL (S3/CDN)",
            },

            {
                "fieldname": "sr_company_signature",
                "label": "Company Signature URL",
                "fieldtype": "Data",
                "options": "URL",
                "insert_after": "sr_company_logo",
                "description": "Paste signature image URL",
            },

            {
                "fieldname": "sr_payment_barcode",
                "label": "Payment QR / Barcode URL",
                "fieldtype": "Data",
                "options": "URL",
                "insert_after": "sr_company_signature",
                "description": "Paste QR code image URL",
            },

            {
                "fieldname": "sr_upi_id",
                "label": "UPI ID",
                "fieldtype": "Data",
                "insert_after": "sr_payment_barcode",
                "description": "Example: sriaas@icici",
            },

            # ------------------------------------------
            # 🔹 OPD Section
            # ------------------------------------------
            {
                "fieldname": "sr_opd_section",
                "label": "OPD Details",
                "fieldtype": "Section Break",
                "insert_after": "sr_upi_id",
            },

            {
                "fieldname": "sr_opd_timings",
                "label": "OPD Timings",
                "fieldtype": "Small Text",
                "insert_after": "sr_opd_section",
                "description": "Example: Mon-Sat 10:00 AM - 6:00 PM",
            },

            {
                "fieldname": "sr_opd_notes",
                "label": "OPD Notes",
                "fieldtype": "Small Text",
                "insert_after": "sr_opd_timings",
                "description": "Optional notes like Sunday closed, emergency timing etc.",
            },

        ]
    })