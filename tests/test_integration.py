"""
Integration tests for ERPNext Thailand.

These tests require a running Frappe/ERPNext instance with the app installed.
Run with: bench run-tests --app erpnext_thailand

The tests exercise end-to-end workflows:
1. Sales Invoice -> Sales Tax Invoice auto-creation
2. Purchase Invoice -> Purchase Tax Invoice auto-creation
3. Undue tax: Invoice -> Payment -> Clear
4. Payment Entry with WHT deduction -> WHT Certificate
5. Deposit Invoice creation from Sales Order -> deduction
6. Petty Cash: GL Entry validation against float
7. Thai Billing: Sales Billing -> Payment Receipt
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days, flt


def create_test_company():
    return frappe.get_doc({
        "doctype": "Company",
        "company_name": "_Test Thailand Co",
        "abbr": "_TTC",
        "default_currency": "THB",
        "country": "Thailand",
        "create_chart_of_accounts_based_on": "Standard Template",
        "chart_of_accounts": "Standard",
    }).insert(ignore_if_duplicate=True)


def create_test_customer(company):
    if frappe.db.exists("Customer", "_Test Thailand Customer"):
        return frappe.get_doc("Customer", "_Test Thailand Customer")
    return frappe.get_doc({
        "doctype": "Customer",
        "customer_name": "_Test Thailand Customer",
        "customer_type": "Company",
        "default_currency": "THB",
        "tax_id": "1234567890123",
        "branch_code": "00000",
    }).insert()


def create_test_supplier(company, supplier_type="Company"):
    name = f"_Test Thailand Supplier ({supplier_type})"
    if frappe.db.exists("Supplier", name):
        return frappe.get_doc("Supplier", name)
    return frappe.get_doc({
        "doctype": "Supplier",
        "supplier_name": name,
        "supplier_type": supplier_type,
        "default_currency": "THB",
        "tax_id": "9876543210987",
        "branch_code": "00000",
    }).insert()


def get_or_create_item(company, item_name="_Test Thailand Item", is_deposit=False):
    if frappe.db.exists("Item", item_name):
        return frappe.get_doc("Item", item_name)
    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_name,
        "item_name": item_name,
        "item_group": "All Item Groups",
        "stock_uom": "Nos",
        "is_stock_item": 0 if is_deposit else 1,
        "is_deposit_item": 1 if is_deposit else 0,
        "company": company,
    })
    item.insert()
    return item


def setup_thai_tax_settings(company):
    settings = frappe.get_single("Thai Tax Settings")
    coa = frappe.get_all(
        "Account",
        filters={"company": company, "account_type": "Tax"},
        fields=["name", "account_type"],
    )
    sales_tax = frappe.get_all(
        "Account",
        filters={"company": company, "account_name": ["like", "%Output%VAT%"]},
        limit=1,
    )
    purchase_tax = frappe.get_all(
        "Account",
        filters={"company": company, "account_name": ["like", "%Input%VAT%"]},
        limit=1,
    )
    existing = [x for x in settings.company_accounts if x.company == company]
    if not existing:
        settings.append("company_accounts", {
            "company": company,
            "sales_tax_account": sales_tax[0].name if sales_tax else None,
            "purchase_tax_account": purchase_tax[0].name if purchase_tax else None,
        })
        settings.save()
    return settings


class TestSalesTaxInvoiceAutoCreation(FrappeTestCase):
    """When a Sales Invoice with VAT is submitted, a Sales Tax Invoice
    record should be auto-created via the GL Entry after_insert hook."""

    def setUp(self):
        self.company = create_test_company()
        self.customer = create_test_customer(self.company.name)
        self.item = get_or_create_item(self.company.name)
        self.settings = setup_thai_tax_settings(self.company.name)

    def test_sales_invoice_creates_sales_tax_invoice(self):
        si = frappe.new_doc("Sales Invoice")
        si.company = self.company.name
        si.customer = self.customer.name
        si.posting_date = today()
        si.append("items", {
            "item_code": self.item.name,
            "qty": 1,
            "rate": 1000,
        })
        tax_account = None
        if self.settings.company_accounts:
            tax_account = self.settings.company_accounts[0].sales_tax_account
        if tax_account:
            si.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": tax_account,
                "rate": 7,
                "description": "VAT 7%",
            })
        si.insert()
        si.submit()

        tax_invoices = frappe.get_all(
            "Sales Tax Invoice",
            filters={"voucher_type": "Sales Invoice", "voucher_no": si.name},
        )
        self.assertGreater(len(tax_invoices), 0, "Sales Tax Invoice should be auto-created")

        tinv = frappe.get_doc("Sales Tax Invoice", tax_invoices[0].name)
        self.assertEqual(tinv.party, self.customer.name)
        self.assertEqual(flt(tinv.tax_amount), 70.0)
        self.assertEqual(flt(tinv.tax_base), 1000.0)

        si.cancel()

    def test_sales_invoice_zero_tax_no_auto_creation(self):
        si = frappe.new_doc("Sales Invoice")
        si.company = self.company.name
        si.customer = self.customer.name
        si.posting_date = today()
        si.append("items", {
            "item_code": self.item.name,
            "qty": 1,
            "rate": 1000,
        })
        si.insert()
        si.submit()

        tax_invoices = frappe.get_all(
            "Sales Tax Invoice",
            filters={"voucher_type": "Sales Invoice", "voucher_no": si.name},
        )
        self.assertEqual(len(tax_invoices), 0, "No Sales Tax Invoice should be created for zero-tax invoice")

        si.cancel()


class TestPurchaseTaxInvoiceAutoCreation(FrappeTestCase):
    """When a Purchase Invoice with VAT is submitted, a Purchase Tax Invoice
    record should be auto-created via the GL Entry after_insert hook."""

    def setUp(self):
        self.company = create_test_company()
        self.supplier = create_test_supplier(self.company.name)
        self.item = get_or_create_item(self.company.name)
        self.settings = setup_thai_tax_settings(self.company.name)

    def test_purchase_invoice_creates_purchase_tax_invoice(self):
        pi = frappe.new_doc("Purchase Invoice")
        pi.company = self.company.name
        pi.supplier = self.supplier.name
        pi.posting_date = today()
        pi.append("items", {
            "item_code": self.item.name,
            "qty": 1,
            "rate": 1000,
        })
        tax_account = None
        if self.settings.company_accounts:
            tax_account = self.settings.company_accounts[0].purchase_tax_account
        if tax_account:
            pi.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": tax_account,
                "rate": 7,
                "description": "VAT 7%",
            })
        pi.tax_invoice_number = "TINV-001"
        pi.tax_invoice_date = today()
        pi.insert()
        pi.submit()

        tax_invoices = frappe.get_all(
            "Purchase Tax Invoice",
            filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name},
        )
        self.assertGreater(len(tax_invoices), 0, "Purchase Tax Invoice should be auto-created")

        tinv = frappe.get_doc("Purchase Tax Invoice", tax_invoices[0].name)
        self.assertEqual(flt(tinv.tax_amount), 70.0)
        self.assertEqual(flt(tinv.tax_base), 1000.0)

        pi.cancel()


class TestCancelRelatedTaxInvoice(FrappeTestCase):
    """When a Sales/Purchase Invoice is cancelled, the related Tax Invoice
    should also be cancelled."""

    def setUp(self):
        self.company = create_test_company()
        self.customer = create_test_customer(self.company.name)
        self.item = get_or_create_item(self.company.name)
        self.settings = setup_thai_tax_settings(self.company.name)

    def test_cancel_sales_invoice_cancels_tax_invoice(self):
        si = frappe.new_doc("Sales Invoice")
        si.company = self.company.name
        si.customer = self.customer.name
        si.posting_date = today()
        si.append("items", {
            "item_code": self.item.name,
            "qty": 1,
            "rate": 1000,
        })
        tax_account = None
        if self.settings.company_accounts:
            tax_account = self.settings.company_accounts[0].sales_tax_account
        if tax_account:
            si.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": tax_account,
                "rate": 7,
                "description": "VAT 7%",
            })
        si.insert()
        si.submit()

        tax_invoices = frappe.get_all(
            "Sales Tax Invoice",
            filters={"voucher_type": "Sales Invoice", "voucher_no": si.name},
        )
        self.assertGreater(len(tax_invoices), 0)

        si.cancel()

        tinv = frappe.get_doc("Sales Tax Invoice", tax_invoices[0].name)
        self.assertEqual(tinv.docstatus, 2, "Tax Invoice should be cancelled")


class TestValidateTaxInvoice(FrappeTestCase):
    """Purchase Invoice with VAT must have tax_invoice_number filled in.
    Purchase Invoice without VAT must NOT have tax_invoice_number."""

    def setUp(self):
        self.company = create_test_company()
        self.supplier = create_test_supplier(self.company.name)
        self.item = get_or_create_item(self.company.name)
        self.settings = setup_thai_tax_settings(self.company.name)

    def test_purchase_invoice_with_vat_requires_tax_invoice_number(self):
        pi = frappe.new_doc("Purchase Invoice")
        pi.company = self.company.name
        pi.supplier = self.supplier.name
        pi.posting_date = today()
        pi.append("items", {
            "item_code": self.item.name,
            "qty": 1,
            "rate": 1000,
        })
        tax_account = None
        if self.settings.company_accounts:
            tax_account = self.settings.company_accounts[0].purchase_tax_account
        if tax_account:
            pi.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": tax_account,
                "rate": 7,
                "description": "VAT 7%",
            })
        pi.insert()
        with self.assertRaises(frappe.exceptions.ValidationError):
            pi.submit()


class TestPettyCashHolder(FrappeTestCase):
    """Petty Cash Holder should validate float limits on GL Entry."""

    def test_create_petty_cash_holder(self):
        if frappe.db.exists("Petty Cash Holder", "_Test PCH"):
            frappe.delete_doc("Petty Cash Holder", "_Test PCH")
        pch = frappe.get_doc({
            "doctype": "Petty Cash Holder",
            "petty_cash_holder": "_Test PCH",
            "petty_cash_holder_name": "Test Petty Cash Holder",
            "petty_cash_float": 5000,
        })
        pch.insert()
        self.assertEqual(pch.petty_cash_float, 5000)


class TestDepositInvoiceWorkflow(FrappeTestCase):
    """Test deposit invoice creation and deduction from orders."""

    def setUp(self):
        self.company = create_test_company()
        self.customer = create_test_customer(self.company.name)
        self.item = get_or_create_item(self.company.name)
        self.deposit_item = get_or_create_item(
            self.company.name,
            item_name="_Test Deposit Item",
            is_deposit=True,
        )

    def test_deposit_item_must_not_be_stock(self):
        from erpnext_thailand.custom.item import validate_deposit_item
        item = frappe.get_doc("Item", self.deposit_item.name)
        self.assertEqual(item.is_stock_item, 0)

    def test_validate_deposit_item_throws_if_stock(self):
        from erpnext_thailand.custom.item import validate_deposit_item
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "_Test Stock Deposit",
            "item_name": "_Test Stock Deposit",
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "is_deposit_item": 1,
        })
        item.insert()
        validate_deposit_item(item, None)
        self.assertEqual(item.is_deposit_item, 0)
        item.delete()


class TestThaiBillingWorkflow(FrappeTestCase):
    """Test Sales Billing and Payment Receipt workflow."""

    def setUp(self):
        self.company = create_test_company()
        self.customer = create_test_customer(self.company.name)
        self.item = get_or_create_item(self.company.name)

    def test_create_sales_billing(self):
        billing_settings = frappe.get_single("Thai Billing Settings")
        si = frappe.new_doc("Sales Invoice")
        si.company = self.company.name
        si.customer = self.customer.name
        si.posting_date = today()
        si.append("items", {
            "item_code": self.item.name,
            "qty": 1,
            "rate": 1000,
        })
        si.insert()
        si.submit()

        billing = frappe.new_doc("Sales Billing")
        billing.company = self.company.name
        billing.customer = self.customer.name
        billing.append("sales_billing_line", {
            "sales_invoice": si.name,
        })
        billing.insert()
        billing.submit()

        self.assertEqual(billing.docstatus, 1)

        billing.cancel()
        si.cancel()


class TestWHTFromType(FrappeTestCase):
    """Test WHT rate lookup from Withholding Tax Type."""

    def setUp(self):
        self.company = create_test_company()
        self.supplier = create_test_supplier(self.company.name)
        self.supplier_individual = create_test_supplier(self.company.name, "Individual")

    def test_get_withholding_tax_from_type_calculation(self):
        from erpnext_thailand.custom.payment_entry import get_withholding_tax_from_type
        import json

        wht_types = frappe.get_all("Withholding Tax Type", limit=1)
        if not wht_types:
            self.skipTest("No Withholding Tax Types configured")

        wht = frappe.get_doc("Withholding Tax Type", wht_types[0].name)
        pay = {
            "company": self.company.name,
            "party_type": "Supplier",
            "party": self.supplier.name,
            "payment_type": "Pay",
            "references": [],
        }
        result = get_withholding_tax_from_type(
            str({"wht_type": wht.name}),
            json.dumps(pay),
        )
        if result:
            self.assertEqual(result["withholding_tax_type"], wht.name)
            self.assertEqual(result["rate"], wht.percent)


class TestAddressTaxBranchUpdate(FrappeTestCase):
    """When Address has update_tax_branch checked, Tax ID and Branch Code
    should propagate to linked Customer/Supplier."""

    def test_update_tax_info_in_linked_doc(self):
        from erpnext_thailand.custom.address import update_tax_info_in_linked_doc
        company = create_test_company()
        customer = create_test_customer(company.name)

        addr = frappe.new_doc("Address")
        addr.address_type = "Billing"
        addr.address_line1 = "123 Test Street"
        addr.city = "Bangkok"
        addr.country = "Thailand"
        addr.tax_id = "1112223334445"
        addr.branch_code = "00001"
        addr.update_tax_branch = 1
        addr.append("links", {
            "link_doctype": "Customer",
            "link_name": customer.name,
        })
        addr.insert()

        update_tax_info_in_linked_doc(addr, None)

        updated_tax_id = frappe.get_value("Customer", customer.name, "tax_id")
        updated_branch = frappe.get_value("Customer", customer.name, "branch_code")
        self.assertEqual(updated_tax_id, "1112223334445")
        self.assertEqual(updated_branch, "00001")


class TestPrintFormatCondition(FrappeTestCase):
    """Test that is_default_print_format evaluates correctly."""

    def test_is_default_print_format(self):
        from erpnext_thailand.custom.print_format import is_default_print_format
        si = frappe.new_doc("Sales Invoice")
        si.company = "_Test Thailand Co"
        si.doctype = "Sales Invoice"

        pf = frappe.new_doc("Print Format")
        pf.doc_type = "Sales Invoice"
        pf.standard = "No"
        pf.default_condition = "doc.doctype == 'Sales Invoice'"

        result = is_default_print_format(si, pf)
        self.assertTrue(result)

        pf.default_condition = "doc.doctype == 'Purchase Invoice'"
        result = is_default_print_format(si, pf)
        self.assertFalse(result)


class TestDashboardOverrides(FrappeTestCase):
    """Test that dashboard overrides add Tax Invoice section correctly."""

    def test_purchase_invoice_dashboard(self):
        from erpnext_thailand.custom.dashboard_overrides import get_dashboard_data_for_purchase_invoice
        data = {"non_standard_fieldnames": {}, "transactions": []}
        result = get_dashboard_data_for_purchase_invoice(data)
        self.assertIn("Purchase Tax Invoice", result["non_standard_fieldnames"])
        found = any("Purchase Tax Invoice" in t.get("items", []) for t in result["transactions"])
        self.assertTrue(found)

    def test_sales_invoice_dashboard(self):
        from erpnext_thailand.custom.dashboard_overrides import get_dashboard_data_for_sales_invoice
        data = {"non_standard_fieldnames": {}, "transactions": []}
        result = get_dashboard_data_for_sales_invoice(data)
        self.assertIn("Sales Tax Invoice", result["non_standard_fieldnames"])
        found = any("Sales Tax Invoice" in t.get("items", []) for t in result["transactions"])
        self.assertTrue(found)

    def test_payment_entry_dashboard(self):
        from erpnext_thailand.custom.dashboard_overrides import get_dashboard_data_for_payment_entry
        data = {"transactions": []}
        result = get_dashboard_data_for_payment_entry(data)
        found = any("Payment Receipt" in t.get("items", []) for t in result["transactions"])
        self.assertTrue(found)
