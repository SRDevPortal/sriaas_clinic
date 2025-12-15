# a/sriaas_clinic/api/batch.py
import frappe
from datetime import datetime

def generate_sequential_batch_id(batch_id, item_name):
    # Get the current year (e.g., 2025)
    current_year = datetime.now().year

    # Fetch the latest batch entry for the same batch_id and item
    last_record = frappe.db.sql("""
        SELECT name FROM `tabBatch`
        WHERE batch_id=%s AND item=%s ORDER BY creation DESC LIMIT 1
    """, (batch_id, item_name))

    # If last record exists, extract the last sequence number
    if last_record:
        last_series = int(last_record[0][0].split("-")[-1])  # Extract number from last ID (e.g., 'BAT-2025-001')
        new_series = last_series + 1
    else:
        # If no previous record exists, start from 1
        new_series = 1

    # Format the new ID as 'BAT-2025-0001'
    new_batch_id = f"{batch_id}-{current_year}-{new_series:04d}"

    return new_batch_id
