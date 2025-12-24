# sriaas_clinic/api/s3/client.py
import frappe
import boto3

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=frappe.conf.aws_access_key_id,
        aws_secret_access_key=frappe.conf.aws_secret_access_key,
        region_name=frappe.conf.aws_region,
    )

def get_bucket():
    return frappe.conf.aws_s3_bucket
