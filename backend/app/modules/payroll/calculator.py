"""
薪酬计算核心模块
================
单人月度工资计算，含五险一金、个税、实发工资。

设计说明
--------
个税计算采用月度税率表的简化方式（非累计预扣法）。
对于单月试算场景，这种方式足够；批量算薪场景如需精确，
需扩展为累计预扣法（即按"年度累计应纳税所得额"逐月推算）。

参考依据：
- 个税：《个人所得税法》月度综合所得税率表
- 五险一金：各地费率略有差异，本模块取常见标准值，公积金费率可配置。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional


# ===== 常量配置 =====

# 个税起征点（月）
TAX_THRESHOLD = Decimal("5000")

# 个人社保固定费率
PENSION_RATE = Decimal("0.08")      # 养老 8%
MEDICAL_RATE = Decimal("0.02")      # 医疗 2%
UNEMPLOYMENT_RATE = Decimal("0.005") # 失业 0.5%

# 公积金默认费率（用户可在调用时覆盖，常见范围 5%-12%）
DEFAULT_HOUSING_FUND_RATE = Decimal("0.07")

# 月度个税速算表
# 每条：(下限, 上限, 税率, 速算扣除数)
TAX_BRACKETS = [
    (Decimal("0"),     Decimal("3000"),  Decimal("0.03"), Decimal("0")),
    (Decimal("3000"),  Decimal("12000"), Decimal("0.10"), Decimal("210")),
    (Decimal("12000"), Decimal("25000"), Decimal("0.20"), Decimal("1410")),
    (Decimal("25000"), Decimal("35000"), Decimal("0.25"), Decimal("2660")),
    (Decimal("35000"), Decimal("55000"), Decimal("0.30"), Decimal("4410")),
    (Decimal("55000"), Decimal("80000"), Decimal("0.35"), Decimal("7160")),
    (Decimal("80000"), None,             Decimal("0.45"), Decimal("15160")),
]


# ===== 数据结构 =====

@dataclass
class PayrollInput:
    """工资计算输入"""
    # 收入项（应发工资构成）
    base_salary: Decimal = Decimal("0")        # 基本工资
    performance: Decimal = Decimal("0")        # 绩效工资
    position_allowance: Decimal = Decimal("0") # 岗位津贴
    overtime_pay: Decimal = Decimal("0")       # 加班费
    other_allowance: Decimal = Decimal("0")    # 其他补贴

    # 五险一金计算基数（一般等于应发，但有上下限保护，这里简化为用户传入）
    social_insurance_base: Optional[Decimal] = None  # 不传则用应发工资

    # 公积金费率（默认 7%，可配置 5%-12%）
    housing_fund_rate: Decimal = field(default_factory=lambda: DEFAULT_HOUSING_FUND_RATE)

    # 专项附加扣除（月度合计：子女教育、房贷利息、租金、赡养老人等）
    special_deduction: Decimal = Decimal("0")

    # 其他扣款（如借支、罚款等）
    other_deduction: Decimal = Decimal("0")


@dataclass
class PayrollResult:
    """工资计算结果"""
    # 收入侧
    gross_salary: Decimal           # 应发工资合计
    income_breakdown: dict          # 应发明细

    # 扣除侧
    pension: Decimal                # 养老保险
    medical: Decimal                # 医疗保险
    unemployment: Decimal           # 失业保险
    housing_fund: Decimal           # 住房公积金
    social_insurance_total: Decimal # 五险一金合计

    taxable_income: Decimal         # 应纳税所得额
    tax_rate: Decimal               # 适用税率
    quick_deduction: Decimal        # 速算扣除数
    income_tax: Decimal             # 个人所得税

    other_deduction: Decimal        # 其他扣款

    # 实发
    net_salary: Decimal             # 实发工资
    deduction_total: Decimal        # 扣除合计

    # 计算说明（用于前端展示推导过程）
    notes: List[str] = field(default_factory=list)


# ===== 工具函数 =====

def _round2(value: Decimal) -> Decimal:
    """保留两位小数，四舍五入"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_decimal(value) -> Decimal:
    """把各种数字类型统一转 Decimal"""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# ===== 核心计算函数 =====

def calculate_income_tax(taxable_income: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """
    根据应纳税所得额计算个税

    Args:
        taxable_income: 应纳税所得额（已扣除五险一金、起征点、专项附加）

    Returns:
        (税额, 适用税率, 速算扣除数)
    """
    if taxable_income <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")

    for low, high, rate, quick in TAX_BRACKETS:
        if high is None or taxable_income <= high:
            tax = taxable_income * rate - quick
            return _round2(max(tax, Decimal("0"))), rate, quick

    # 兜底（理论上走不到，最高档已经覆盖了无上限）
    return Decimal("0"), Decimal("0"), Decimal("0")


def calculate_payroll(input_data: PayrollInput) -> PayrollResult:
    """
    完整的工资计算

    流程：
    1. 应发 = 各项收入相加
    2. 五险一金 = 基数 × 个人费率（养老 8% + 医疗 2% + 失业 0.5% + 公积金 X%）
    3. 应纳税所得额 = 应发 − 五险一金 − 5000 − 专项附加扣除
    4. 个税 = 查税率表计算
    5. 实发 = 应发 − 五险一金 − 个税 − 其他扣款
    """
    # 把所有输入转 Decimal
    base = _to_decimal(input_data.base_salary)
    perf = _to_decimal(input_data.performance)
    pos = _to_decimal(input_data.position_allowance)
    ot = _to_decimal(input_data.overtime_pay)
    other = _to_decimal(input_data.other_allowance)
    special = _to_decimal(input_data.special_deduction)
    other_ded = _to_decimal(input_data.other_deduction)
    hf_rate = _to_decimal(input_data.housing_fund_rate)

    # 1. 应发工资
    gross = base + perf + pos + ot + other
    income_breakdown = {
        "基本工资": _round2(base),
        "绩效工资": _round2(perf),
        "岗位津贴": _round2(pos),
        "加班费": _round2(ot),
        "其他补贴": _round2(other),
    }

    # 2. 社保基数
    si_base = (
        _to_decimal(input_data.social_insurance_base)
        if input_data.social_insurance_base is not None
        else gross
    )

    # 3. 五险一金（个人部分）
    pension = _round2(si_base * PENSION_RATE)
    medical = _round2(si_base * MEDICAL_RATE)
    unemployment = _round2(si_base * UNEMPLOYMENT_RATE)
    housing_fund = _round2(si_base * hf_rate)
    si_total = pension + medical + unemployment + housing_fund

    # 4. 应纳税所得额
    taxable = gross - si_total - TAX_THRESHOLD - special
    taxable = max(taxable, Decimal("0"))

    # 5. 个税
    tax, tax_rate, quick = calculate_income_tax(taxable)

    # 6. 实发
    deduction_total = si_total + tax + other_ded
    net = _round2(gross - deduction_total)

    # 7. 推导过程说明
    notes = [
        f"应发合计：基本工资 {base} + 绩效 {perf} + 岗位津贴 {pos} + 加班费 {ot} + 其他补贴 {other} = {_round2(gross)}",
        f"五险一金（个人）：基数 {_round2(si_base)} × (养老8% + 医疗2% + 失业0.5% + 公积金{hf_rate*100:.1f}%) = {si_total}",
        f"应纳税所得额：应发 {_round2(gross)} − 五险一金 {si_total} − 起征点 5000 − 专项附加 {special} = {_round2(taxable)}",
    ]
    if taxable > 0:
        notes.append(f"个税：应纳税所得额 {_round2(taxable)} × {tax_rate*100:.0f}% − 速算扣除 {quick} = {tax}")
    else:
        notes.append("应纳税所得额 ≤ 0，无需缴纳个税")
    notes.append(f"实发工资：应发 {_round2(gross)} − 五险一金 {si_total} − 个税 {tax} − 其他扣款 {other_ded} = {net}")

    return PayrollResult(
        gross_salary=_round2(gross),
        income_breakdown=income_breakdown,
        pension=pension,
        medical=medical,
        unemployment=unemployment,
        housing_fund=housing_fund,
        social_insurance_total=si_total,
        taxable_income=_round2(taxable),
        tax_rate=tax_rate,
        quick_deduction=quick,
        income_tax=tax,
        other_deduction=_round2(other_ded),
        net_salary=net,
        deduction_total=_round2(deduction_total),
        notes=notes,
    )