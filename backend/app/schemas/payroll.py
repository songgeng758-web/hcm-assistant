"""
薪酬计算模块 · 数据模型
"""
from typing import Dict, List
from pydantic import BaseModel, Field


class PayrollCalcRequest(BaseModel):
    """工资计算请求"""
    # 应发组成
    base_salary: float = Field(0, ge=0, description="基本工资")
    performance: float = Field(0, ge=0, description="绩效工资")
    position_allowance: float = Field(0, ge=0, description="岗位津贴")
    overtime_pay: float = Field(0, ge=0, description="加班费")
    other_allowance: float = Field(0, ge=0, description="其他补贴")

    # 五险一金配置
    social_insurance_base: float | None = Field(
        None, ge=0,
        description="社保基数，留空则用应发工资作为基数"
    )
    housing_fund_rate: float = Field(
        0.07, ge=0.05, le=0.12,
        description="公积金费率，范围 5%-12%，默认 7%"
    )

    # 扣除
    special_deduction: float = Field(0, ge=0, description="专项附加扣除（月度合计）")
    other_deduction: float = Field(0, ge=0, description="其他扣款（如借支）")

    class Config:
        # 提供一个示例，让 Swagger 文档页直接可用
        json_schema_extra = {
            "example": {
                "base_salary": 15000,
                "performance": 3000,
                "position_allowance": 500,
                "overtime_pay": 0,
                "other_allowance": 200,
                "housing_fund_rate": 0.07,
                "special_deduction": 1500,
                "other_deduction": 0,
            }
        }


class PayrollCalcResponse(BaseModel):
    """工资计算响应"""
    # 应发
    gross_salary: float = Field(..., description="应发工资合计")
    income_breakdown: Dict[str, float] = Field(..., description="应发明细")

    # 五险一金
    pension: float = Field(..., description="养老保险")
    medical: float = Field(..., description="医疗保险")
    unemployment: float = Field(..., description="失业保险")
    housing_fund: float = Field(..., description="住房公积金")
    social_insurance_total: float = Field(..., description="五险一金合计")

    # 个税
    taxable_income: float = Field(..., description="应纳税所得额")
    tax_rate: float = Field(..., description="适用税率")
    quick_deduction: float = Field(..., description="速算扣除数")
    income_tax: float = Field(..., description="个人所得税")

    # 其他
    other_deduction: float = Field(..., description="其他扣款")
    deduction_total: float = Field(..., description="扣除合计")

    # 实发
    net_salary: float = Field(..., description="实发工资")

    # 推导过程
    notes: List[str] = Field(default_factory=list, description="计算说明")