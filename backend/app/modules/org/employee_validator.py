"""
员工档案校验主逻辑
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

from app.schemas.org import ValidationIssue, ValidationSummary
from app.utils import id_card as id_card_util
from app.utils.validators import (
    clean_header,
    is_blank,
    is_id_card_type,
    is_valid_email,
    is_valid_phone,
)


# 标准字段名映射 - 覆盖浪潮 HCM 常见字段名变体
FIELD_ALIASES = {
    "employee_id": [
        "工号", "员工编号", "员工号", "employee_id", "工号/编号",
        "人员编号", "用工编号", "员工id",
    ],
    "name": [
        "姓名", "name", "员工姓名", "人员姓名",
    ],
    "id_card": [
        "身份证号", "身份证", "证件号码", "证件号", "id_card",
        "身份证号码", "身份证件号码",
    ],
    "id_card_type": [
        "证件类型", "id_card_type",
    ],
    "gender": [
        "性别", "gender",
    ],
    "phone": [
        "手机号", "电话", "联系电话", "phone", "mobile", "手机号码",
    ],
    "email": [
        "邮箱", "电子邮箱", "email", "e-mail", "电子邮件",
    ],
    "department": [
        "部门", "所属部门", "department",
    ],
    "position": [
        "岗位", "职位", "position", "岗位名称",
    ],
    "birth_date": [
        "出生日期", "组织认定出生日期", "birth_date",
    ],
    "hire_date": [
        "入职日期", "参加工作时间", "hire_date",
    ],
}


def _resolve_columns(df: pd.DataFrame) -> dict:
    """
    把 Excel 实际列名映射到标准字段名
    先把所有表头做 clean_header 清洗（去掉空格、不可见字符）
    """
    actual_cols = {}
    for c in df.columns:
        cleaned = clean_header(c)
        actual_cols[cleaned] = c  # cleaned -> 原始列名（保留原列名做 df 索引）

    resolved = {}
    for std_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in actual_cols:
                resolved[std_name] = actual_cols[alias]
                break
    return resolved


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """基础清洗：去空行、去空列、字符串字段去首尾空格"""
    df = df.dropna(how="all").copy()
    df = df.dropna(axis=1, how="all")
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    return df.reset_index(drop=True)


def inspect_columns(file_path: Path | str) -> dict:
    """
    诊断接口：分析 Excel 表头，告诉用户哪些字段被识别、哪些没识别
    实施顾问视角：先看清楚字段映射，再决定怎么校验
    """
    file_path = Path(file_path)
    df = pd.read_excel(file_path, dtype=str, nrows=0)  # 只读表头，性能友好
    cols = _resolve_columns(df)

    raw_columns = [clean_header(c) for c in df.columns]
    recognized = {std: actual for std, actual in cols.items()}
    unrecognized = [c for c in raw_columns if clean_header(c) not in [clean_header(v) for v in recognized.values()]]

    # 标识哪些"标准字段"完全没匹配到（重要字段缺失提示）
    important = ["employee_id", "name", "id_card"]
    missing_important = [k for k in important if k not in recognized]

    return {
        "total_columns": len(raw_columns),
        "all_columns": raw_columns,
        "recognized": recognized,
        "unrecognized_columns": unrecognized,
        "missing_important_fields": missing_important,
    }


def validate_employees(file_path: Path | str) -> Tuple[ValidationSummary, List[ValidationIssue], pd.DataFrame]:
    file_path = Path(file_path)
    df = pd.read_excel(file_path, dtype=str)
    df = _clean_dataframe(df)
    cols = _resolve_columns(df)

    issues: List[ValidationIssue] = []
    seen_employee_ids: dict = {}
    valid_row_flags = [True] * len(df)

    for idx, row in df.iterrows():
        excel_row = idx + 2

        emp_id = row.get(cols.get("employee_id", ""), None) if cols.get("employee_id") else None
        name = row.get(cols.get("name", ""), None) if cols.get("name") else None

        def add_issue(field: str, level: str, message: str, suggestion: str = None):
            issues.append(ValidationIssue(
                row=excel_row,
                employee_id=str(emp_id) if not is_blank(emp_id) else None,
                name=str(name) if not is_blank(name) else None,
                field=field,
                level=level,
                message=message,
                suggestion=suggestion,
            ))
            if level == "error":
                valid_row_flags[idx] = False

        # 必填校验
        if "employee_id" not in cols:
            if idx == 0:
                add_issue("工号", "error", "Excel 中缺少『工号/员工编号』列", "请补充工号列")
        elif is_blank(emp_id):
            add_issue("工号", "error", "工号为空", "请填写工号")

        if "name" not in cols:
            if idx == 0:
                add_issue("姓名", "error", "Excel 中缺少『姓名』列", "请补充姓名列")
        elif is_blank(name):
            add_issue("姓名", "error", "姓名为空", "请填写姓名")

        # 工号唯一性
        if "employee_id" in cols and not is_blank(emp_id):
            if emp_id in seen_employee_ids:
                add_issue(
                    "工号", "error",
                    f"工号重复（与第 {seen_employee_ids[emp_id]} 行相同）",
                    "请确认工号唯一性",
                )
            else:
                seen_employee_ids[emp_id] = excel_row

        # 证件类型联动 - 只有居民身份证才用身份证规则校验
        id_card_val = row.get(cols.get("id_card", ""), None) if cols.get("id_card") else None
        id_type_val = row.get(cols.get("id_card_type", ""), None) if cols.get("id_card_type") else None
        id_info = None

        if "id_card" in cols:
            if is_blank(id_card_val):
                add_issue("证件号", "error", "证件号为空", "请填写证件号")
            else:
                # 如果证件类型列存在且非身份证，跳过身份证强校验（只警告非空即可）
                if "id_card_type" in cols and not is_blank(id_type_val) and not is_id_card_type(id_type_val):
                    # 非身份证类型，只做基础非空校验
                    pass
                else:
                    # 没有证件类型列，或证件类型 = 居民身份证 -> 用身份证规则
                    id_info = id_card_util.parse(id_card_val)
                    if not id_info.is_valid:
                        add_issue("证件号", "error", f"身份证号不合法：{id_info.error}", "请核对身份证号")

        # 性别一致性（仅对合法身份证校验）
        if id_info and id_info.is_valid and "gender" in cols:
            gender_val = row.get(cols["gender"])
            if not is_blank(gender_val):
                gender_str = str(gender_val).strip()
                if gender_str not in ("男", "女"):
                    add_issue("性别", "warning", f"性别取值异常：'{gender_str}'", "性别应为『男』或『女』")
                elif gender_str != id_info.gender:
                    add_issue(
                        "性别", "error",
                        f"性别与身份证不符（表中：{gender_str}，身份证解析：{id_info.gender}）",
                        "请核对性别与身份证",
                    )

        # 手机号
        if "phone" in cols:
            phone_val = row.get(cols["phone"])
            if not is_blank(phone_val) and not is_valid_phone(phone_val):
                add_issue("手机号", "warning", f"手机号格式不正确：'{phone_val}'", "应为 11 位，以 1 开头")

        # 邮箱
        if "email" in cols:
            email_val = row.get(cols["email"])
            if not is_blank(email_val) and not is_valid_email(email_val):
                add_issue("邮箱", "warning", f"邮箱格式不正确：'{email_val}'", "应符合 name@domain.com 格式")

    # 工号重复列表
    id_counts = {}
    if "employee_id" in cols:
        col_name = cols["employee_id"]
        for v in df[col_name].dropna():
            v_str = str(v).strip()
            if v_str:
                id_counts[v_str] = id_counts.get(v_str, 0) + 1
    duplicate_ids = [k for k, v in id_counts.items() if v > 1]

    summary = ValidationSummary(
        total_rows=len(df),
        valid_rows=sum(valid_row_flags),
        error_count=sum(1 for i in issues if i.level == "error"),
        warning_count=sum(1 for i in issues if i.level == "warning"),
        duplicate_employee_ids=duplicate_ids,
    )

    return summary, issues, df


def export_report(issues: List[ValidationIssue], summary: ValidationSummary, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame([{
        "总行数": summary.total_rows,
        "合法行数": summary.valid_rows,
        "错误数": summary.error_count,
        "警告数": summary.warning_count,
        "重复工号": ", ".join(summary.duplicate_employee_ids) or "无",
    }])

    if issues:
        issues_df = pd.DataFrame([{
            "Excel行号": i.row,
            "工号": i.employee_id or "",
            "姓名": i.name or "",
            "字段": i.field,
            "级别": "错误" if i.level == "error" else "警告",
            "问题描述": i.message,
            "修复建议": i.suggestion or "",
        } for i in issues])
    else:
        issues_df = pd.DataFrame([{"提示": "所有数据校验通过，未发现异常"}])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="校验总览", index=False)
        issues_df.to_excel(writer, sheet_name="异常明细", index=False)

    return output_path