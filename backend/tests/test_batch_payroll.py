"""
批量薪酬计算单元测试
"""
from pathlib import Path

import pandas as pd
import pytest

from app.modules.payroll.batch_calculator import (
    calculate_batch,
    export_batch_report,
    generate_template,
)


@pytest.fixture
def normal_excel(tmp_path):
    """构造一份正常的批量薪酬要素表"""
    data = [
        {"工号": "E001", "姓名": "张三", "基本工资": 15000, "绩效工资": 3000,
         "岗位津贴": 500, "加班费": 0, "其他补贴": 200,
         "公积金费率": 0.07, "专项附加扣除": 1500, "其他扣款": 0},
        {"工号": "E002", "姓名": "李四", "基本工资": 10000, "绩效工资": 2000,
         "岗位津贴": 300, "加班费": 500, "其他补贴": 0,
         "公积金费率": 0.07, "专项附加扣除": 1000, "其他扣款": 0},
        {"工号": "E003", "姓名": "王五", "基本工资": 8000, "绩效工资": 1000,
         "岗位津贴": 200, "加班费": 0, "其他补贴": 100,
         "公积金费率": 0.08, "专项附加扣除": 500, "其他扣款": 0},
    ]
    df = pd.DataFrame(data)
    file_path = tmp_path / "normal.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def dirty_excel(tmp_path):
    """构造一份含异常的表"""
    data = [
        # 正常
        {"工号": "E001", "姓名": "张三", "基本工资": 15000, "绩效工资": 3000},
        # 基本工资为 0（应失败）
        {"工号": "E002", "姓名": "李四", "基本工资": 0, "绩效工资": 2000},
        # 基本工资是文字（应失败）
        {"工号": "E003", "姓名": "王五", "基本工资": "abc", "绩效工资": 1000},
        # 基本工资为空（应失败）
        {"工号": "E004", "姓名": "赵六", "基本工资": None, "绩效工资": 500},
    ]
    df = pd.DataFrame(data)
    file_path = tmp_path / "dirty.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


def test_normal_batch(normal_excel):
    """正常批量计算"""
    rows, summary = calculate_batch(normal_excel)
    assert summary.total_rows == 3
    assert summary.success_rows == 3
    assert summary.failed_rows == 0
    assert summary.total_gross > 0
    assert summary.total_net > 0


def test_dirty_batch(dirty_excel):
    """含异常行的批量计算"""
    rows, summary = calculate_batch(dirty_excel)
    assert summary.total_rows == 4
    assert summary.success_rows == 1
    assert summary.failed_rows == 3
    # 第一行应成功
    assert rows[0].success
    # 后三行应失败
    assert not rows[1].success
    assert not rows[2].success
    assert not rows[3].success


def test_missing_required_column(tmp_path):
    """缺少"基本工资"列应抛异常"""
    df = pd.DataFrame([{"工号": "E001", "姓名": "张三"}])
    file_path = tmp_path / "no_base.xlsx"
    df.to_excel(file_path, index=False)

    with pytest.raises(ValueError, match="基本工资"):
        calculate_batch(file_path)


def test_field_aliases(tmp_path):
    """测试字段别名识别（基本工资 → 底薪）"""
    df = pd.DataFrame([
        {"员工编号": "E001", "姓名": "张三", "底薪": 10000, "绩效": 2000},
    ])
    file_path = tmp_path / "alias.xlsx"
    df.to_excel(file_path, index=False)

    rows, summary = calculate_batch(file_path)
    assert summary.success_rows == 1
    assert rows[0].employee_id == "E001"


def test_sum_aggregation(normal_excel):
    """总览数字应该是各行结果的累加"""
    rows, summary = calculate_batch(normal_excel)
    # 手动汇总应发
    expected_gross = sum(r.result.gross_salary for r in rows if r.success)
    assert summary.total_gross == expected_gross


def test_export_report(normal_excel, tmp_path):
    """导出 Excel 报告"""
    rows, summary = calculate_batch(normal_excel)
    output = tmp_path / "report.xlsx"
    export_batch_report(rows, summary, output)
    assert output.exists()

    # 验证三个 sheet
    xls = pd.ExcelFile(output)
    assert "总览" in xls.sheet_names
    assert "工资条明细" in xls.sheet_names
    assert "异常清单" in xls.sheet_names


def test_generate_template(tmp_path):
    """生成模板"""
    output = tmp_path / "template.xlsx"
    generate_template(output)
    assert output.exists()

    df = pd.read_excel(output)
    assert "工号" in df.columns
    assert "基本工资" in df.columns
    assert len(df) >= 1  # 至少有示例数据