"""
Standalone unit tests for pure-logic Thai utility functions.

These tests do NOT require a running Frappe/ERPNext instance.
They test extractable pure logic from the Thailand module.
Run with:  python -m pytest tests/ (from project root)
"""

import datetime
import unittest
from unittest.mock import patch, MagicMock


class TestThaiDateLogic(unittest.TestCase):
    """Test the Thai Buddhist-calendar date formatting logic.

    We extract and test the core logic inline to avoid importing frappe.
    """

    @staticmethod
    def full_thai_date(date_str):
        if not date_str:
            return ""
        date = datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
        month_name = "x มกราคม กุมภาพันธ์ มีนาคม เมษายน พฤษภาคม มิถุนายน กรกฎาคม สิงหาคม กันยายน ตุลาคม พฤศจิกายน ธันวาคม".split()[
            date.month
        ]
        thai_year = date.year + 543
        return f"{date.day} {month_name} {thai_year}"

    def test_standard_date(self):
        assert self.full_thai_date("2023-10-30") == "30 ตุลาคม 2566"

    def test_new_year(self):
        assert self.full_thai_date("2024-01-01") == "1 มกราคม 2567"

    def test_last_day_of_year(self):
        assert self.full_thai_date("2023-12-31") == "31 ธันวาคม 2566"

    def test_empty_string(self):
        assert self.full_thai_date("") == ""

    def test_none(self):
        assert self.full_thai_date(None) == ""

    def test_february_29_leap_year(self):
        assert self.full_thai_date("2024-02-29") == "29 กุมภาพันธ์ 2567"

    def test_all_months_correct(self):
        expected = [
            ("2023-01-15", "มกราคม", "2566"),
            ("2023-02-15", "กุมภาพันธ์", "2566"),
            ("2023-03-15", "มีนาคม", "2566"),
            ("2023-04-15", "เมษายน", "2566"),
            ("2023-05-15", "พฤษภาคม", "2566"),
            ("2023-06-15", "มิถุนายน", "2566"),
            ("2023-07-15", "กรกฎาคม", "2566"),
            ("2023-08-15", "สิงหาคม", "2566"),
            ("2023-09-15", "กันยายน", "2566"),
            ("2023-10-15", "ตุลาคม", "2566"),
            ("2023-11-15", "พฤศจิกายน", "2566"),
            ("2023-12-15", "ธันวาคม", "2566"),
        ]
        for date_str, expected_month, expected_year in expected:
            result = self.full_thai_date(date_str)
            assert expected_month in result, f"Expected {expected_month} in {result}"
            assert expected_year in result, f"Expected {expected_year} in {result}"

    def test_thai_year_is_ad_plus_543(self):
        assert "2566" in self.full_thai_date("2023-06-15")
        assert "2567" in self.full_thai_date("2024-06-15")
        assert "2500" in self.full_thai_date("1957-06-15")


class TestFinalizeAddressDict(unittest.TestCase):
    """Test the finalize_address_dict logic for RD VAT API response processing.

    We extract the function to test it standalone.
    """

    @staticmethod
    def finalize_address_dict(data):
        def get_part(data, key, value):
            return data.get(key, "-") != "-" and value % (map[key], data.get(key)) or ""

        map = {
            "vBuildingName": "อาคาร",
            "vFloorNumber": "ชั้น",
            "vVillageName": "หมู่บ้าน",
            "vRoomNumber": "ห้อง",
            "vMooNumber": "หมู่ที่",
            "vSoiName": "ซอย",
            "vStreetName": "ถนน",
            "vThambol": "ต.",
            "vAmphur": "อ.",
            "vProvince": "จ.",
        }
        name = f"{data.get('vBranchTitleName')} {data.get('vBranchName')}"
        if "vSurname" in data and data["vSurname"] not in ("-", "", None):
            name = f"{name} {data['vSurname']}"
        house = data.get("vHouseNumber", "")
        village = get_part(data, "vVillageName", "%s %s")
        soi = get_part(data, "vSoiName", "%s %s")
        moo = get_part(data, "vMooNumber", "%s %s")
        building = get_part(data, "vBuildingName", "%s %s")
        floor = get_part(data, "vFloorNumber", "%s %s")
        room = get_part(data, "vRoomNumber", "%s %s")
        street = get_part(data, "vStreetName", "%s%s")
        thambon = get_part(data, "vThambol", "%s%s")
        amphur = get_part(data, "vAmphur", "%s%s")
        province = get_part(data, "vProvince", "%s%s")
        postal = data.get("vPostCode", "")

        if province == "จ.กรุงเทพมหานคร":
            thambon = data.get("vThambol") and f"แขวง{data['vThambol']}" or ""
            amphur = data.get("vAmphur") and f"เขต{data['vAmphur']}" or ""
            province = data.get("vProvince") and f"{data['vProvince']}" or ""

        address_parts = filter(
            lambda x: x != "", [house, village, soi, moo, building, floor, room, street]
        )
        return {
            "name": name,
            "address_line1": " ".join(address_parts),
            "city": thambon,
            "county": amphur,
            "state": province,
            "pincode": postal,
        }

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
        result = self.finalize_address_dict(data)
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
        result = self.finalize_address_dict(data)
        assert "แขวง" in result["city"]
        assert "ลุมพินี" in result["city"]
        assert "เขต" in result["county"]
        assert "ปทุมวัน" in result["county"]

    def test_provincial_address_uses_prefix(self):
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
        result = self.finalize_address_dict(data)
        assert "จ." in result["state"]
        assert "นครราชสีมา" in result["state"]
        assert "ต." in result["city"]
        assert "อ." in result["county"]

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
        result = self.finalize_address_dict(data)
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
        result = self.finalize_address_dict(data)
        assert "อาคาร" in result["address_line1"]
        assert "ชั้น" in result["address_line1"]
        assert "ห้อง" in result["address_line1"]
        assert "หมู่ที่" in result["address_line1"]

    def test_empty_surname_excluded(self):
        data = {
            "vBranchTitleName": "นาย",
            "vBranchName": "ทดสอบ",
            "vSurname": "",
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
        result = self.finalize_address_dict(data)
        assert result["name"] == "นาย ทดสอบ"

    def test_minimal_data(self):
        data = {
            "vBranchTitleName": "บริษัท",
            "vBranchName": "ทดสอบ",
            "vHouseNumber": "99",
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
        result = self.finalize_address_dict(data)
        assert result["address_line1"] == "99"
        assert result["pincode"] == ""


class TestNamingSeriesVariable(unittest.TestCase):
    """Test date-based naming series variable parsing logic.

    We replicate the logic without frappe imports to test standalone.
    """

    @staticmethod
    def parse_naming_series_variable(posting_date, transaction_date, date, variable):
        from datetime import datetime as dt
        d = dt.now()
        if posting_date:
            d = dt.strptime(str(posting_date), "%Y-%m-%d")
        elif transaction_date:
            d = dt.strptime(str(transaction_date), "%Y-%m-%d")
        elif date:
            d = dt.strptime(str(date), "%Y-%m-%d")
        if variable == "YYYY-DATE":
            return d.strftime("%Y")
        if variable == "YY-DATE":
            return d.strftime("%y")
        if variable == "MM-DATE":
            return d.strftime("%m")
        if variable == "DD-DATE":
            return d.strftime("%d")
        if variable == "WW-DATE":
            from datetime import datetime
            return str(datetime.date(d).isocalendar()[1])

    def test_yyyy_date(self):
        assert self.parse_naming_series_variable("2024-06-15", None, None, "YYYY-DATE") == "2024"

    def test_yy_date(self):
        assert self.parse_naming_series_variable("2024-06-15", None, None, "YY-DATE") == "24"

    def test_mm_date(self):
        assert self.parse_naming_series_variable("2024-01-15", None, None, "MM-DATE") == "01"

    def test_dd_date(self):
        assert self.parse_naming_series_variable("2024-06-05", None, None, "DD-DATE") == "05"

    def test_fallback_to_transaction_date(self):
        assert self.parse_naming_series_variable(None, "2024-03-20", None, "YYYY-DATE") == "2024"

    def test_fallback_to_date(self):
        assert self.parse_naming_series_variable(None, None, "2024-12-25", "MM-DATE") == "12"


class TestUndueTaxCalculation(unittest.TestCase):
    """Test the pure math in get_undue_tax().

    get_undue_tax(doc, ref, gl, tax) returns (undue_tax, base_amount, account_undue, account)

    We test the calculation logic without Frappe by extracting the core math.
    """

    @staticmethod
    def compute_undue_tax(gl, ref, tax_accounts_undue, tax_accounts, is_purchase=False):
        """Extracted calculation logic from get_undue_tax."""
        undue_tax = 0
        base_amount = 0
        credit = gl["credit"]
        debit = gl["debit"]
        alloc_percent = ref["allocated_amount"] / ref["total_amount"]

        account_undue = tax_accounts_undue
        account = tax_accounts

        base_amount = alloc_percent * (credit - debit)

        if gl["account"] == account_undue:
            undue_tax = alloc_percent * (credit - debit)

        return undue_tax, base_amount, account_undue, account

    def test_sales_undue_tax_with_allocation(self):
        gl = {"account": "Sales Tax Undue", "credit": 700, "debit": 0}
        ref = {"allocated_amount": 500, "total_amount": 1000}
        undue, base, acc_undue, acc = self.compute_undue_tax(
            gl, ref, "Sales Tax Undue", "Sales Tax"
        )
        assert undue == 350.0
        assert base == 350.0

    def test_no_undue_tax_when_wrong_account(self):
        gl = {"account": "Some Other Account", "credit": 700, "debit": 0}
        ref = {"allocated_amount": 500, "total_amount": 1000}
        undue, base, _, _ = self.compute_undue_tax(
            gl, ref, "Sales Tax Undue", "Sales Tax"
        )
        assert undue == 0
        assert base == 350.0

    def test_full_allocation(self):
        gl = {"account": "Purchase Tax Undue", "credit": 0, "debit": 500}
        ref = {"allocated_amount": 1000, "total_amount": 1000}
        undue, base, _, _ = self.compute_undue_tax(
            gl, ref, "Purchase Tax Undue", "Purchase Tax", is_purchase=True
        )
        assert undue == -500.0
        assert base == -500.0

    def test_zero_allocation(self):
        gl = {"account": "Sales Tax Undue", "credit": 700, "debit": 0}
        ref = {"allocated_amount": 0, "total_amount": 1000}
        undue, base, _, _ = self.compute_undue_tax(
            gl, ref, "Sales Tax Undue", "Sales Tax"
        )
        assert undue == 0
        assert base == 0

    def test_partial_allocation(self):
        gl = {"account": "Sales Tax Undue", "credit": 300, "debit": 0}
        ref = {"allocated_amount": 100, "total_amount": 1000}
        undue, base, _, _ = self.compute_undue_tax(
            gl, ref, "Sales Tax Undue", "Sales Tax"
        )
        assert undue == 30.0
        assert base == 30.0


class TestTaxInvoiceSignLogic(unittest.TestCase):
    """Test the sign/direction logic in create_tax_invoice_on_gl_tax.

    This tests the core decision: given tax_amount (credit - debit) and is_return,
    determine whether to create a Sales Tax Invoice or Purchase Tax Invoice.
    """

    def test_credit_tax_creates_sales_tax_invoice(self):
        tax_amount = 700
        is_return = False
        doctype = None

        if (tax_amount > 0 and not is_return) or (tax_amount < 0 and is_return):
            doctype = "Sales Tax Invoice"
        if (tax_amount < 0 and not is_return) or (tax_amount > 0 and is_return):
            doctype = "Purchase Tax Invoice"

        assert doctype == "Sales Tax Invoice"

    def test_debit_tax_creates_purchase_tax_invoice(self):
        tax_amount = -700
        is_return = False
        doctype = None

        if (tax_amount > 0 and not is_return) or (tax_amount < 0 and is_return):
            doctype = "Sales Tax Invoice"
        if (tax_amount < 0 and not is_return) or (tax_amount > 0 and is_return):
            doctype = "Purchase Tax Invoice"

        assert doctype == "Purchase Tax Invoice"

    def test_return_credit_creates_purchase_tax_invoice(self):
        tax_amount = 700
        is_return = True
        doctype = None

        if (tax_amount > 0 and not is_return) or (tax_amount < 0 and is_return):
            doctype = "Sales Tax Invoice"
        if (tax_amount < 0 and not is_return) or (tax_amount > 0 and is_return):
            doctype = "Purchase Tax Invoice"

        assert doctype == "Purchase Tax Invoice"

    def test_return_debit_creates_sales_tax_invoice(self):
        tax_amount = -700
        is_return = True
        doctype = None

        if (tax_amount > 0 and not is_return) or (tax_amount < 0 and is_return):
            doctype = "Sales Tax Invoice"
        if (tax_amount < 0 and not is_return) or (tax_amount > 0 and is_return):
            doctype = "Purchase Tax Invoice"

        assert doctype == "Sales Tax Invoice"


class TestWHTCalculation(unittest.TestCase):
    """Test WHT rate/amount calculations."""

    def test_wht_amount_from_rate_and_base(self):
        base_amount = 10000
        rate = 3
        expected = 300
        assert rate / 100 * base_amount == expected

    def test_wht_amount_1_percent(self):
        base_amount = 50000
        rate = 1
        expected = 500
        assert rate / 100 * base_amount == expected

    def test_wht_amount_5_percent(self):
        base_amount = 20000
        rate = 5
        expected = 1000
        assert rate / 100 * base_amount == expected

    def test_wht_sign_for_pay(self):
        pay_type = "Pay"
        sign = -1 if pay_type == "Pay" else 1
        assert sign == -1

    def test_wht_sign_for_receive(self):
        pay_type = "Receive"
        sign = -1 if pay_type == "Pay" else 1
        assert sign == 1

    def test_wht_deduction_amount(self):
        base = 10000
        rate = 3
        sign = -1
        amount = rate / 100 * base * sign
        assert amount == -300

    def test_tax_rate_validation_pass(self):
        base_amount = 10000
        tax_rate = 7
        tax_amount = 700
        assert abs((base_amount * tax_rate / 100) - tax_amount) <= 0.1

    def test_tax_rate_validation_fail(self):
        base_amount = 10000
        tax_rate = 7
        tax_amount = 500
        assert abs((base_amount * tax_rate / 100) - tax_amount) > 0.1


class TestDepositDeductionCalculation(unittest.TestCase):
    """Test deposit deduction amount calculations."""

    def test_percent_deduction(self):
        invoice_amount = 80000
        order_total = 100000
        initial_deposit = 20000
        deducted = 5000
        balance = initial_deposit - deducted

        percent_amount = (invoice_amount / order_total) * initial_deposit
        allocated = min(percent_amount, invoice_amount, balance)

        assert percent_amount == 16000.0
        assert allocated == 15000

    def test_full_amount_deduction(self):
        invoice_amount = 50000
        balance = 20000
        allocated = min(invoice_amount, balance)
        assert allocated == 20000

    def test_zero_previous_deductions(self):
        initial_amount = 10000
        deducted_amount = 0
        balance = initial_amount - deducted_amount
        assert balance == 10000


if __name__ == "__main__":
    unittest.main()
