"""
批量薪酬计算
============
输入：含员工薪酬要素的 Excel
输出：每人完整工资条（应发、扣除、个税、实发）+ 异常清单

算法
----
1. 读取 Excel，识别字段（支持中英文别名）
2. 逐行解析薪酬要素，调用 calculate_payroll
3. 解析失败的行进入异常清单（不阻断整体计算）
4. 输出结构化的批量结果
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from app.modules.payroll.calculator import PayrollInput, PayrollResult, calculate_payroll
from app.utils.validators import clean_header, is_blank


# 字段别名（复用员工档案校验的设计）
FIELD_ALIASES = {
    "employee_id": ["工号", "员工编号", "员工号", "employee_id"],
    "name": ["姓名", "name"],
    "base_salary": ["基本工资", "底薪", "base_salary"],
    "performance": ["绩效工资", "绩效", "performance"],
    "position_allowance": ["岗位津贴", "岗位补贴", "position_allowance"],
    "overtime_pay": ["加班费", "加班工资", "overtime_pay"],
    "other_allowance": ["其他补贴", "其他津贴", "other_allowance"],
    "social_insurance_base": ["社保基数", "缴费基数", "social_insurance_base"],
    "housing_fund_rate": ["公积金费率", "housing_fund_rate"],
    "special_deduction": ["专项附加扣除", "专项扣除", "special_deduction"],
    "other_deduction": ["其他扣款", "其他扣除", "other_deduction"],
}


@dataclass
class BatchPayrollRow:
    """单行批量计算结果"""
    row: int                       # Excel 行号
    employee_id: Optional[str]
    name: Optional[str]
    success: bool
    error: Optional[str] = None
    result: Optional[PayrollResult] = None


@dataclass
class BatchPayrollSummary:
    """批量计算总览"""
    total_rows: int
    success_rows: int
    failed_rows: int
    total_gross: Decimal          # 应发总额
    total_si: Decimal             # 五险一金总额
    total_tax: Decimal            # 个税总额
    total_net: Decimal            # 实发总额


def _resolve_columns(df: pd.DataFrame) -> dict:
    """字段别名解析"""
    actual_cols = {clean_header(c): c for c in df.columns}
    resolved = {}
    for std_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in actual_cols:
                resolved[std_name] = actual_cols[alias]
                break
    return resolved


def _parse_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
    """安全转 Decimal，失败返回默认值"""
    if is_blank(value):
        return default
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return default


def calculate_batch(file_path: Path | str) -> Tuple[List[BatchPayrollRow], BatchPayrollSummary]:
    """
    批量薪酬计算

    Returns:
        (rows, summary): 每行结果列表 + 总览统计
    """
    file_path = Path(file_path)
    df = pd.read_excel(file_path, dtype=str)
    df = df.dropna(how="all").reset_index(drop=True)

    cols = _resolve_columns(df)

    # 必须有基本工资列才能算（其他可以为空，默认 0）
    if "base_salary" not in cols:
        raise ValueError("Excel 中未找到『基本工资』列，请确认列名")

    rows: List[BatchPayrollRow] = []
    total_gross = Decimal("0")
    total_si = Decimal("0")
    total_tax = Decimal("0")
    total_net = Decimal("0")
    success_count = 0
    failed_count = 0

    for idx, row in df.iterrows():
        excel_row = idx + 2

        emp_id = row.get(cols.get("employee_id"), None) if cols.get("employee_id") else None
        name = row.get(cols.get("name"), None) if cols.get("name") else None
        emp_id_str = str(emp_id).strip() if not is_blank(emp_id) else None
        name_str = str(name).strip() if not is_blank(name) else None

        try:
            base = _parse_decimal(row.get(cols.get("base_salary")))
            if base <= 0:
                raise ValueError("基本工资必须 > 0")

            # 构造输入
            si_base_raw = row.get(cols.get("social_insurance_base")) if cols.get("social_insurance_base") else None
            hf_rate_raw = row.get(cols.get("housing_fund_rate")) if cols.get("housing_fund_rate") else None

            input_data = PayrollInput(
                base_salary=base,
                performance=_parse_decimal(row.get(cols.get("performance"))) if cols.get("performance") else Decimal("0"),
                position_allowance=_parse_decimal(row.get(cols.get("position_allowance"))) if cols.get("position_allowance") else Decimal("0"),
                overtime_pay=_parse_decimal(row.get(cols.get("overtime_pay"))) if cols.get("overtime_pay") else Decimal("0"),
                other_allowance=_parse_decimal(row.get(cols.get("other_allowance"))) if cols.get("other_allowance") else Decimal("0"),
                social_insurance_base=_parse_decimal(si_base_raw) if not is_blank(si_base_raw) else None,
                housing_fund_rate=_parse_decimal(hf_rate_raw, Decimal("0.07")) if not is_blank(hf_rate_raw) else Decimal("0.07"),
                special_deduction=_parse_decimal(row.get(cols.get("special_deduction"))) if cols.get("special_deduction") else Decimal("0"),
                other_deduction=_parse_decimal(row.get(cols.get("other_deduction"))) if cols.get("other_deduction") else Decimal("0"),
            )

            result = calculate_payroll(input_data)

            rows.append(BatchPayrollRow(
                row=excel_row,
                employee_id=emp_id_str,
                name=name_str,
                success=True,
                result=result,
            ))

            total_gross += result.gross_salary
            total_si += result.social_insurance_total
            total_tax += result.income_tax
            total_net += result.net_salary
            success_count += 1

        except Exception as e:
            rows.append(BatchPayrollRow(
                row=excel_row,
                employee_id=emp_id_str,
                name=name_str,
                success=False,
                error=str(e),
            ))
            failed_count += 1

    summary = BatchPayrollSummary(
        total_rows=len(df),
        success_rows=success_count,
        failed_rows=failed_count,
        total_gross=total_gross,
        total_si=total_si,
        total_tax=total_tax,
        total_net=total_net,
    )

    return rows, summary


def export_batch_report(
    rows: List[BatchPayrollRow],
    summary: BatchPayrollSummary,
    output_path: Path,
) -> Path:
    """导出批量算薪结果 Excel"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sheet 1: 总览
    summary_df = pd.DataFrame([{
        "总人数": summary.total_rows,
        "成功": summary.success_rows,
        "失败": summary.failed_rows,
        "应发总额": float(summary.total_gross),
        "五险一金总额": float(summary.total_si),
        "个税总额": float(summary.total_tax),
        "实发总额": float(summary.total_net),
    }])

    # Sheet 2: 工资条明细
    detail_rows = []
    for r in rows:
        if not r.success:
            continue
        res = r.result
        detail_rows.append({
            "Excel行号": r.row,
            "工号": r.employee_id or "",
            "姓名": r.name or "",
            "基本工资": float(res.income_breakdown.get("基本工资", 0)),
            "绩效工资": float(res.income_breakdown.get("绩效工资", 0)),
            "岗位津贴": float(res.income_breakdown.get("岗位津贴", 0)),
            "加班费": float(res.income_breakdown.get("加班费", 0)),
            "其他补贴": float(res.income_breakdown.get("其他补贴", 0)),
            "应发工资": float(res.gross_salary),
            "养老保险": float(res.pension),
            "医疗保险": float(res.medical),
            "失业保险": float(res.unemployment),
            "住房公积金": float(res.housing_fund),
            "五险一金合计": float(res.social_insurance_total),
            "应纳税所得额": float(res.taxable_income),
            "个人所得税": float(res.income_tax),
            "其他扣款": float(res.other_deduction),
            "实发工资": float(res.net_salary),
        })
    detail_df = pd.DataFrame(detail_rows) if detail_rows else pd.DataFrame([{"提示": "无成功计算的行"}])

    # Sheet 3: 异常清单
    failed_rows = [
        {"Excel行号": r.row, "工号": r.employee_id or "", "姓名": r.name or "", "错误原因": r.error}
        for r in rows if not r.success
    ]
    failed_df = pd.DataFrame(failed_rows) if failed_rows else pd.DataFrame([{"提示": "全部计算成功"}])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="总览", index=False)
        detail_df.to_excel(writer, sheet_name="工资条明细", index=False)
        failed_df.to_excel(writer, sheet_name="异常清单", index=False)

    return output_path


def generate_template(output_path: Path) -> Path:
    """生成批量算薪 Excel 模板"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    template_data = [
        {
            "工号": "E0001",
            "姓名": "张三",
            "基本工资": 15000,
            "绩效工资": 3000,
            "岗位津贴": 500,
            "加班费": 0,
            "其他补贴": 200,
            "社保基数": "",
            "公积金费率": 0.07,
            "专项附加扣除": 1500,
            "其他扣款": 0,
        },
        {
            "工号": "E0002",
            "姓名": "李四",
            "基本工资": 10000,
            "绩效工资": 2000,
            "岗位津贴": 300,
            "加班费": 500,
            "其他补贴": 0,
            "社保基数": "",
            "公积金费率": 0.07,
            "专项附加扣除": 1000,
            "其他扣款": 0,
        },
    ]
    df = pd.DataFrame(template_data)
    df.to_excel(output_path, index=False, sheet_name="薪酬要素")

    return output_path