import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from erpnext_thailand.constants import (
    ERP_CUSTOM_FIELDS, ERP_PROPERTY_SETTERS,
    HRMS_CUSTOM_FIELDS, BILLING_CUSTOM_FIELDS,
    DEPOSIT_CUSTOM_FIELDS,
)


def execute():
    create_custom_fields(ERP_CUSTOM_FIELDS, ignore_validate=True)
    create_custom_fields(BILLING_CUSTOM_FIELDS, ignore_validate=True)
    create_custom_fields(DEPOSIT_CUSTOM_FIELDS, ignore_validate=True)
    if "hrms" in frappe.get_installed_apps():
        create_custom_fields(HRMS_CUSTOM_FIELDS, ignore_validate=True)
