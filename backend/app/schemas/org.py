"""
组织人事模块 · 数据模型（Pydantic）
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """单条校验异常"""
    row: int = Field(..., description="Excel 中的行号（含表头，从 2 开始）")
    employee_id: Optional[str] = Field(None, description="工号（若能取到）")
    name: Optional[str] = Field(None, description="姓名（若能取到）")
    field: str = Field(..., description="出错字段名")
    level: str = Field(..., description="级别：error / warning")
    message: str = Field(..., description="异常说明")
    suggestion: Optional[str] = Field(None, description="修复建议")


class ValidationSummary(BaseModel):
    """校验总览"""
    total_rows: int = Field(..., description="数据总行数（不含表头）")
    valid_rows: int = Field(..., description="完全合法的行数")
    error_count: int = Field(..., description="错误级问题数")
    warning_count: int = Field(..., description="警告级问题数")
    duplicate_employee_ids: List[str] = Field(default_factory=list, description="重复的工号列表")


class EmployeeValidationResponse(BaseModel):
    """员工档案校验响应"""
    success: bool
    summary: ValidationSummary
    issues: List[ValidationIssue]
    report_file: Optional[str] = Field(None, description="校验报告下载路径")