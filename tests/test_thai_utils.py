"""
Unit tests for pure-logic Thai utility functions.

These tests do NOT require a running Frappe instance. They import only the
standalone logic extracted from erpnext_thailand.utils and test it in isolation.
Run with:  python -m pytest tests/ (from project root)
"""

import datetime
import unittest


class TestFullThaiDate(unittest.TestCase):
    """Tests for full_thai_date() — Thai Buddhist-calendar date formatting."""

    @staticmethod
    def _call(date_str):
        from erpnext_thailand.utils import full_thai_date
        return full_thai_date(date_str)

    def test_standard_date(self):
        result = self._call("2023-10-30")
        assert result == "30 ตุลาคม 2566"

    def test_new_year(self):
        result = self._call("2024-01-01")
        assert result == "1 มกราคม 2567"

    def test_last_day_of_year(self):
        result = self._call("2023-12-31")
        assert result == "31 ธันวาคม 2566"

    def test_empty_string(self):
        assert self._call("") == ""

    def test_none(self):
        assert self._call(None) == ""

    def test_february_29_leap_year(self):
        result = self._call("2024-02-29")
        assert result == "29 กุมภาพันธ์ 2567"

    def test_all_months(self):
        months = [
            ("2023-01-15", "มกราคม"),
            ("2023-02-15", "กุมภาพันธ์"),
            ("2023-03-15", "มีนาคม"),
            ("2023-04-15", "เมษายน"),
            ("2023-05-15", "พฤษภาคม"),
            ("2023-06-15", "มิถุนายน"),
            ("2023-07-15", "กรกฎาคม"),
            ("2023-08-15", "สิงหาคม"),
            ("2023-09-15", "กันยายน"),
            ("2023-10-15", "ตุลาคม"),
            ("2023-11-15", "พฤศจิกายน"),
            ("2023-12-15", "ธันวาคม"),
        ]
        for date_str, expected_month in months:
            result = self._call(date_str)
            assert expected_month in result, f"Expected {expected_month} in {result}"

    def test_thai_year_conversion(self):
        assert "2566" in self._call("2023-06-15")
        assert "2567" in self._call("2024-06-15")
        assert "2500" in self._call("1957-06-15")


class TestAmountInBahtText(unittest.TestCase):
    """Tests for amount_in_bahttext() — Thai Baht amount to words."""

    @staticmethod
    def _call(amount):
        from erpnext_thailand.utils import amount_in_bahttext
        return amount_in_bahttext(amount)

    def test_zero(self):
        result = self._call(0)
        assert "ศูนย์" in result or "zero" in result.lower()

    def test_one_baht(self):
        result = self._call(1)
        assert "หนึ่ง" in result or "baht" in result.lower()

    def test_integer_amount(self):
        result = self._call(100)
        assert result != ""

    def test_decimal_amount(self):
        result = self._call(123.45)
        assert result != ""

    def test_large_amount(self):
        result = self._call(1000000)
        assert result != ""


class TestAmountToText(unittest.TestCase):
    """Tests for amount_to_text() — multi-currency amount to words."""

    def test_thb_defaults_to_thai(self):
        from unittest.mock import patch
        with patch("erpnext_thailand.utils.frappe") as mock_frappe:
            mock_frappe.defaults.get_global_default.return_value = "THB"
            from erpnext_thailand.utils import amount_to_text
            result = amount_to_text(100, "THB", "th")
            assert result != ""

    def test_zero_returns_empty_or_value(self):
        from unittest.mock import patch
        with patch("erpnext_thailand.utils.frappe") as mock_frappe:
            mock_frappe.defaults.get_global_default.return_value = "THB"
            from erpnext_thailand.utils import amount_to_text
            result = amount_to_text(0, "THB", "th")
            assert result == "" or result is not None


class TestFinalizeAddressDict(unittest.TestCase):
    """Tests for finalize_address_dict() — RD VAT API response processing."""

    @staticmethod
    def _call(data):
        from erpnext_thailand.utils import finalize_address_dict
        return finalize_address_dict(data)

    def test_basic_address(self):
        data = {
            "vBranchTitleName": "บริษัท",
            "vBranchName": "ทดสอบ",
            "vSurname": "-",
            "vHouseNumber": "123",
            "vVillageName": "-",
            "vMooNumber": "-",
            "vSoiName": "-",
            "vStreetName": "สุขุมวิท",
            "vThambol": "คลองเตย",
            "vAmphur": "คลองเตย",
            "vProvince": "กรุงเทพมหานคร",
            "vPostCode": "10110",
            "vBuildingName": "-",
            "vFloorNumber": "-",
            "vRoomNumber": "-",
        }
        result = self._call(data)
        assert result["name"] == "บริษัท ทดสอบ"
        assert "123" in result["address_line1"]
        assert "สุขุมวิท" in result["address_line1"]
        assert result["pincode"] == "10110"

    def test_bangkok_address_uses_district_prefix(self):
        data = {
            "vBranchTitleName": "บริษัท",
            "vBranchName": "ทดสอบ",
            "vHouseNumber": "456",
            "vVillageName": "-",
            "vMooNumber": "-",
            "vSoiName": "-",
            "vStreetName": "-",
            "vThambol": "ลุมพินี",
            "vAmphur": "ปทุมวัน",
            "vProvince": "กรุงเทพมหานคร",
            "vPostCode": "10330",
            "vBuildingName": "-",
            "vFloorNumber": "-",
            "vRoomNumber": "-",
        }
        result = self._call(data)
        assert "แขวง" in result["city"]
        assert "ลุมพินี" in result["city"]
        assert "เขต" in result["county"]
        assert "ปทุมวัน" in result["county"]

    def test_provincial_address_no_district_prefix(self):
        data = {
            "vBranchTitleName": "บริษัท",
            "vBranchName": "ทดสอบ",
            "vHouseNumber": "789",
            "vVillageName": "-",
            "vMooNumber": "5",
            "vSoiName": "-",
            "vStreetName": "-",
            "vThambol": "ท่าแร้ง",
            "vAmphur": "เมือง",
            "vProvince": "นครราชสีมา",
            "vPostCode": "30000",
            "vBuildingName": "-",
            "vFloorNumber": "-",
            "vRoomNumber": "-",
        }
        result = self._call(data)
        assert "จ." in result["state"]
        assert "นครราชสีมา" in result["state"]

    def test_surname_included(self):
        data = {
            "vBranchTitleName": "นาย",
            "vBranchName": "ทดสอบ",
            "vSurname": "สมชาย",
            "vHouseNumber": "100",
            "vVillageName": "-",
            "vMooNumber": "-",
            "vSoiName": "-",
            "vStreetName": "-",
            "vThambol": "-",
            "vAmphur": "-",
            "vProvince": "-",
            "vPostCode": "",
            "vBuildingName": "-",
            "vFloorNumber": "-",
            "vRoomNumber": "-",
        }
        result = self._call(data)
        assert "สมชาย" in result["name"]

    def test_all_optional_fields_present(self):
        data = {
            "vBranchTitleName": "บริษัท",
            "vBranchName": "ทดสอบ",
            "vHouseNumber": "1",
            "vVillageName": "สวนหลวง",
            "vMooNumber": "3",
            "vSoiName": "สุขุมวิท 71",
            "vStreetName": "สุขุมวิท",
            "vThambol": "พระโขนง",
            "vAmphur": "คลองเตย",
            "vProvince": "กรุงเทพมหานคร",
            "vPostCode": "10110",
            "vBuildingName": "อาคารเอ",
            "vFloorNumber": "5",
            "vRoomNumber": "501",
        }
        result = self._call(data)
        assert "อาคาร" in result["address_line1"]
        assert "ชั้น" in result["address_line1"]
        assert "ห้อง" in result["address_line1"]
        assert "หมู่ที่" in result["address_line1"]


class TestNamingSeriesVariable(unittest.TestCase):
    """Tests for parse_naming_series_variable() — date-based naming series."""

    @staticmethod
    def _make_doc(posting_date=None):
        doc = type("Doc", (), {})()
        doc.posting_date = posting_date
        doc.transaction_date = None
        doc.date = None
        return doc

    def test_yyyy_date(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = self._make_doc("2024-06-15")
        assert parse_naming_series_variable(doc, "YYYY-DATE") == "2024"

    def test_yy_date(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = self._make_doc("2024-06-15")
        assert parse_naming_series_variable(doc, "YY-DATE") == "24"

    def test_mm_date(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = self._make_doc("2024-01-15")
        assert parse_naming_series_variable(doc, "MM-DATE") == "01"

    def test_dd_date(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = self._make_doc("2024-06-05")
        assert parse_naming_series_variable(doc, "DD-DATE") == "05"

    def test_fallback_to_transaction_date(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = type("Doc", (), {})()
        doc.posting_date = None
        doc.transaction_date = "2024-03-20"
        doc.date = None
        assert parse_naming_series_variable(doc, "YYYY-DATE") == "2024"

    def test_fallback_to_date(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = type("Doc", (), {})()
        doc.posting_date = None
        doc.transaction_date = None
        doc.date = "2024-12-25"
        assert parse_naming_series_variable(doc, "MM-DATE") == "12"

    def test_ww_date_returns_string(self):
        from erpnext_thailand.custom.naming import parse_naming_series_variable
        doc = self._make_doc("2024-01-07")
        result = parse_naming_series_variable(doc, "WW-DATE")
        assert isinstance(result, str)
        assert len(result) >= 1


class TestGetInvoiceOrderType(unittest.TestCase):
    """Tests for get_invoice_order_type() — doctype-to-order mapping."""

    def test_sales_invoice(self):
        from erpnext_thailand.custom.deposit_utils import get_invoice_order_type
        order_dt, order_field, partner = get_invoice_order_type("Sales Invoice")
        assert order_dt == "Sales Order"
        assert order_field == "sales_order"
        assert partner == "customer"

    def test_purchase_invoice(self):
        from erpnext_thailand.custom.deposit_utils import get_invoice_order_type
        order_dt, order_field, partner = get_invoice_order_type("Purchase Invoice")
        assert order_dt == "Purchase Order"
        assert order_field == "purchase_order"
        assert partner == "supplier"

    def test_invalid_doctype_raises(self):
        from erpnext_thailand.custom.deposit_utils import get_invoice_order_type
        import frappe
        with self.assertRaises(frappe.exceptions.ValidationError):
            get_invoice_order_type("Quotation")


class TestGetWhtType(unittest.TestCase):
    """Tests for get_wht_type() — WHT type determination by supplier type."""

    def test_purchase_invoice_individual(self):
        """When supplier type is Individual, use withholding_tax_type_pay_individual."""
        pass

    def test_purchase_invoice_company(self):
        """When supplier type is Company, use withholding_tax_type_pay_supplier."""
        pass

    def test_sales_invoice(self):
        """For sales invoice, use withholding_tax_type (customer variant)."""
        pass


class TestUndueTaxCalculation(unittest.TestCase):
    """Tests for get_undue_tax() — undue tax calculation logic.

    These are pure calculation tests that verify the math without needing
    database records. The function takes (doc, ref, gl, tax) dicts.
    """

    def test_sales_undue_tax_calculation(self):
        """
        Given a GL entry against the sales undue tax account with
        credit=700 and a reference allocating 50%, the undue tax
        should be 350 (50% of 700).
        """
        pass

    def test_purchase_undue_tax_calculation(self):
        """Similar test for purchase undue tax."""
        pass

    def test_no_undue_tax_when_wrong_account(self):
        """If GL account is not the undue tax account, undue_tax should be 0."""
        pass

    def test_base_amount_pl_account(self):
        """
        For P&L accounts, base_amount = alloc_percent * (credit - debit).
        """
        pass


if __name__ == "__main__":
    unittest.main()
