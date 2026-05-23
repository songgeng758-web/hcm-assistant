"""
薪酬计算单元测试
"""
from decimal import Decimal

import pytest

from app.modules.payroll.calculator import (
    PayrollInput,
    calculate_income_tax,
    calculate_payroll,
)


def D(v):
    """快捷转 Decimal"""
    return Decimal(str(v))


class TestIncomeTax:
    """个税计算测试"""

    def test_zero_taxable(self):
        """应纳税所得额为 0 → 个税为 0"""
        tax, rate, quick = calculate_income_tax(D(0))
        assert tax == D(0)
        assert rate == D(0)

    def test_negative_taxable(self):
        """应纳税所得额为负 → 个税为 0"""
        tax, _, _ = calculate_income_tax(D(-1000))
        assert tax == D(0)

    def test_bracket_3_percent(self):
        """3% 档：应纳税所得额 2000 → 60"""
        tax, rate, quick = calculate_income_tax(D(2000))
        assert tax == D(60)
        assert rate == D("0.03")
        assert quick == D(0)

    def test_bracket_10_percent(self):
        """10% 档：应纳税所得额 5000 → 5000*10% − 210 = 290"""
        tax, rate, quick = calculate_income_tax(D(5000))
        assert tax == D(290)
        assert rate == D("0.10")
        assert quick == D(210)

    def test_bracket_20_percent(self):
        """20% 档：应纳税所得额 20000 → 20000*20% − 1410 = 2590"""
        tax, rate, _ = calculate_income_tax(D(20000))
        assert tax == D(2590)
        assert rate == D("0.20")

    def test_top_bracket(self):
        """最高档 45%：应纳税所得额 100000 → 100000*45% − 15160 = 29840"""
        tax, rate, _ = calculate_income_tax(D(100000))
        assert tax == D(29840)
        assert rate == D("0.45")


class TestPayrollCalculation:
    """完整工资计算测试"""

    def test_basic_salary_only(self):
        """只有基本工资，应发等于基本工资"""
        result = calculate_payroll(PayrollInput(base_salary=D(8000)))
        assert result.gross_salary == D(8000)

    def test_full_components(self):
        """各收入项相加"""
        result = calculate_payroll(PayrollInput(
            base_salary=D(8000),
            performance=D(2000),
            position_allowance=D(500),
            overtime_pay=D(300),
            other_allowance=D(200),
        ))
        assert result.gross_salary == D(11000)

    def test_social_insurance_calculation(self):
        """
        五险一金计算：
        基数 10000，养老 8%=800、医疗 2%=200、失业 0.5%=50、公积金 7%=700
        合计 1750
        """
        result = calculate_payroll(PayrollInput(base_salary=D(10000)))
        assert result.pension == D(800)
        assert result.medical == D(200)
        assert result.unemployment == D(50)
        assert result.housing_fund == D(700)
        assert result.social_insurance_total == D(1750)

    def test_custom_housing_fund_rate(self):
        """公积金费率可配置"""
        result = calculate_payroll(PayrollInput(
            base_salary=D(10000),
            housing_fund_rate=D("0.12"),  # 最高档 12%
        ))
        assert result.housing_fund == D(1200)

    def test_below_tax_threshold(self):
        """应纳税所得额 < 0，免税"""
        # 应发 6000，五险一金 1050，5000 起征点 → 应纳税 -50 → 免税
        result = calculate_payroll(PayrollInput(base_salary=D(6000)))
        assert result.income_tax == D(0)
        assert result.taxable_income == D(0)

    def test_typical_engineer_salary(self):
        """
        一个典型场景：月薪 15000 工程师
        - 应发：15000
        - 五险一金：15000 × 17.5% = 2625
        - 应纳税：15000 − 2625 − 5000 = 7375
        - 个税：7375 × 10% − 210 = 527.5
        - 实发：15000 − 2625 − 527.5 = 11847.5
        """
        result = calculate_payroll(PayrollInput(base_salary=D(15000)))
        assert result.gross_salary == D(15000)
        assert result.social_insurance_total == D("2625.00")
        assert result.taxable_income == D("7375.00")
        assert result.income_tax == D("527.50")
        assert result.net_salary == D("11847.50")

    def test_with_special_deduction(self):
        """
        含专项附加扣除：
        应发 15000，五险一金 2625，专项扣除 2000
        应纳税：15000 − 2625 − 5000 − 2000 = 5375
        个税：5375 × 10% − 210 = 327.5
        """
        result = calculate_payroll(PayrollInput(
            base_salary=D(15000),
            special_deduction=D(2000),
        ))
        assert result.taxable_income == D("5375.00")
        assert result.income_tax == D("327.50")

    def test_with_other_deduction(self):
        """其他扣款（如借支）会从实发中扣除"""
        result = calculate_payroll(PayrollInput(
            base_salary=D(10000),
            other_deduction=D(500),
        ))
        # 实发 = 应发 - 五险一金 - 个税 - 其他扣款
        expected_si = D(1750)
        expected_taxable = D(10000) - expected_si - D(5000)  # 3250
        expected_tax = expected_taxable * D("0.10") - D(210)  # 115
        expected_net = D(10000) - expected_si - expected_tax - D(500)
        assert result.net_salary == expected_net

    def test_notes_generated(self):
        """计算说明会被生成（用于前端展示推导过程）"""
        result = calculate_payroll(PayrollInput(base_salary=D(15000)))
        assert len(result.notes) >= 4
        assert any("应发合计" in n for n in result.notes)
        assert any("五险一金" in n for n in result.notes)
        assert any("个税" in n for n in result.notes)
        assert any("实发工资" in n for n in result.notes)