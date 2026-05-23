"""
组织架构树解析单元测试
"""
from pathlib import Path

import pandas as pd
import pytest

from app.modules.org.org_tree_parser import (
    _clean_path,
    _detect_path_gap,
    _extract_path,
    parse_org_tree,
)


@pytest.fixture
def sample_excel(tmp_path):
    """构造一份包含各种场景的测试数据"""
    data = [
        # 1. 正常的三级路径
        {"员工编号": "E001", "姓名": "张三",
         "岗位_一级组织": "集团总部", "岗位_二级组织": "财务中心", "岗位_三级组织": "会计部"},
        # 2. 同部门第二人
        {"员工编号": "E002", "姓名": "李四",
         "岗位_一级组织": "集团总部", "岗位_二级组织": "财务中心", "岗位_三级组织": "会计部"},
        # 3. 同二级下另一个三级部门
        {"员工编号": "E003", "姓名": "王五",
         "岗位_一级组织": "集团总部", "岗位_二级组织": "财务中心", "岗位_三级组织": "出纳部"},
        # 4. 路径断层：一级有、二级空、三级又有
        {"员工编号": "E004", "姓名": "赵六",
         "岗位_一级组织": "集团总部", "岗位_二级组织": "", "岗位_三级组织": "应收组"},
        # 5. 二级就停了
        {"员工编号": "E005", "姓名": "钱七",
         "岗位_一级组织": "集团总部", "岗位_二级组织": "技术中心", "岗位_三级组织": ""},
        # 6. 完全没填组织
        {"员工编号": "E006", "姓名": "孙八",
         "岗位_一级组织": "", "岗位_二级组织": "", "岗位_三级组织": ""},
        # 7. 另一个一级组织
        {"员工编号": "E007", "姓名": "周九",
         "岗位_一级组织": "分公司A", "岗位_二级组织": "综合部", "岗位_三级组织": ""},
    ]
    df = pd.DataFrame(data)
    file_path = tmp_path / "test_org.xlsx"
    df.to_excel(file_path, index=False)
    return file_path


def test_extract_path_normal():
    row = pd.Series({"col1": "A", "col2": "B", "col3": "C"})
    cols = [(1, "col1"), (2, "col2"), (3, "col3")]
    assert _extract_path(row, cols) == ["A", "B", "C"]


def test_extract_path_trailing_empty():
    """末尾连续空值应该被去掉"""
    row = pd.Series({"col1": "A", "col2": "B", "col3": ""})
    cols = [(1, "col1"), (2, "col2"), (3, "col3")]
    assert _extract_path(row, cols) == ["A", "B"]


def test_extract_path_middle_empty_preserved():
    """中间的空值要保留（用于断层检测）"""
    row = pd.Series({"col1": "A", "col2": "", "col3": "C"})
    cols = [(1, "col1"), (2, "col2"), (3, "col3")]
    assert _extract_path(row, cols) == ["A", "", "C"]


def test_detect_path_gap_normal():
    assert not _detect_path_gap(["A", "B", "C"])
    assert not _detect_path_gap(["A", "B"])
    assert not _detect_path_gap(["A"])


def test_detect_path_gap_with_gap():
    assert _detect_path_gap(["A", "", "C"])
    assert _detect_path_gap(["A", "B", "", "D"])


def test_detect_path_gap_no_gap_with_trailing():
    """末尾空不算断层"""
    assert not _detect_path_gap(["A", "B"])


def test_clean_path():
    assert _clean_path(["A", "", "C"]) == ["A", "C"]
    assert _clean_path(["A", "B"]) == ["A", "B"]
    assert _clean_path([]) == []


def test_parse_basic(sample_excel):
    """基本场景：能正确建树"""
    tree, issues, total = parse_org_tree(sample_excel)
    assert total == 7
    assert len(tree) == 2  # 两个一级组织：集团总部、分公司A


def test_parse_node_counts(sample_excel):
    """节点人数统计"""
    tree, _, _ = parse_org_tree(sample_excel)
    # 找到 "集团总部"
    group = next(n for n in tree if n.name == "集团总部")
    # 集团总部下应该有：财务中心、技术中心、应收组（断层产生的）
    # 总人数：张三 + 李四 + 王五 + 赵六 + 钱七 = 5
    assert group.total_count == 5


def test_parse_issues(sample_excel):
    """异常检测"""
    _, issues, _ = parse_org_tree(sample_excel)
    # 应该至少有 2 个异常：1 个 path_gap + 1 个 empty_root
    gap_issues = [i for i in issues if i.issue_type == "path_gap"]
    empty_issues = [i for i in issues if i.issue_type == "empty_root"]
    assert len(gap_issues) == 1
    assert len(empty_issues) == 1
    assert gap_issues[0].employee_id == "E004"
    assert empty_issues[0].employee_id == "E006"


def test_parse_tree_structure(sample_excel):
    """树结构正确性"""
    tree, _, _ = parse_org_tree(sample_excel)
    group = next(n for n in tree if n.name == "集团总部")
    # 找到财务中心
    finance = next(n for n in group.children if n.name == "财务中心")
    # 财务中心下应该有两个子部门：会计部、出纳部
    sub_names = {c.name for c in finance.children}
    assert sub_names == {"会计部", "出纳部"}
    # 会计部下有 2 人
    accounting = next(c for c in finance.children if c.name == "会计部")
    assert accounting.employee_count == 2