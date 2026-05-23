"""
组织架构树解析
================
输入：含「一级组织 ~ 十级组织」列的员工 Excel
输出：树形结构 + 异常清单

算法
----
1. 扫描每一行，提取 10 级组织字段
2. 检测"路径断层"（非空 → 空 → 又非空）
3. 用 dict 作为树容器，递归建树
4. 计算每个节点的人数（直接 + 总数）
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd

from app.schemas.org_tree import TreeIssue, TreeNode
from app.utils.validators import clean_header, is_blank


# 一级到十级组织的列名候选
LEVEL_COLUMN_PATTERNS = [
    ["岗位_一级组织", "一级组织", "一级部门"],
    ["岗位_二级组织", "二级组织", "二级部门"],
    ["岗位_三级组织", "三级组织", "三级部门"],
    ["岗位_四级组织", "四级组织", "四级部门"],
    ["岗位_五级组织", "五级组织", "五级部门"],
    ["岗位_六级组织", "六级组织", "六级部门"],
    ["岗位_七级组织", "七级组织", "七级部门"],
    ["岗位_八级组织", "八级组织", "八级部门"],
    ["岗位_九级组织", "九级组织", "九级部门"],
    ["岗位_十级组织", "十级组织", "十级部门"],
]


def _resolve_level_columns(df: pd.DataFrame) -> List[Tuple[int, str]]:
    """
    识别 Excel 中的层级列，返回 [(层级, 实际列名), ...]
    例如：[(1, "岗位_一级组织"), (2, "岗位_二级组织"), ...]
    没识别到的层级不在返回结果中。
    """
    actual_cols = {clean_header(c): c for c in df.columns}
    resolved = []
    for level_idx, patterns in enumerate(LEVEL_COLUMN_PATTERNS, start=1):
        for p in patterns:
            if p in actual_cols:
                resolved.append((level_idx, actual_cols[p]))
                break
    return resolved


def _extract_path(row, level_columns: List[Tuple[int, str]]) -> List[str]:
    """
    从一行数据中提取组织路径（去掉末尾的空值）
    例如：["集团总部", "财务中心", "会计部", "", "", ...] → ["集团总部", "财务中心", "会计部"]
    """
    path = []
    for _, col_name in level_columns:
        val = row.get(col_name)
        if is_blank(val):
            path.append("")  # 先保留空值，便于断层检测
        else:
            path.append(str(val).strip())
    # 去掉末尾的连续空字符串
    while path and path[-1] == "":
        path.pop()
    return path


def _detect_path_gap(path: List[str]) -> bool:
    """
    检测路径断层：是否存在"非空 → 空 → 非空"的模式
    例如：["集团", "", "应收组"] → True（二级空了但三级又有）
    """
    seen_non_empty = False
    seen_empty_after_non_empty = False
    for v in path:
        if v == "":
            if seen_non_empty:
                seen_empty_after_non_empty = True
        else:
            if seen_empty_after_non_empty:
                return True
            seen_non_empty = True
    return False


def _clean_path(path: List[str]) -> List[str]:
    """
    清理路径：去除空值后的结果
    例如：["集团", "", "财务部", ""] → ["集团", "财务部"]
    """
    return [p for p in path if p != ""]


def _insert_to_tree(tree: dict, path: List[str]) -> dict:
    """
    把一条路径插入树（dict 嵌套结构），返回叶节点对应的 dict
    叶节点结构：{"_count": 0, "_level": int, "children": {子部门名: 子节点}}
    """
    current = tree
    for level, name in enumerate(path, start=1):
        if name not in current["children"]:
            current["children"][name] = {
                "_count": 0,
                "_level": level,
                "children": {},
            }
        current = current["children"][name]
    return current


def _dict_to_tree_nodes(d: dict, name: str = None, level: int = 0) -> TreeNode | None:
    """
    把内部 dict 结构转成 Pydantic 的 TreeNode 列表，同时计算 total_count
    """
    if name is None:
        return None
    direct = d.get("_count", 0)
    children_nodes = []
    total = direct
    for child_name, child_d in d["children"].items():
        child_node = _dict_to_tree_nodes(child_d, child_name, d.get("_level", level) + 1)
        if child_node:
            children_nodes.append(child_node)
            total += child_node.total_count
    return TreeNode(
        name=name,
        level=d["_level"],
        employee_count=direct,
        total_count=total,
        children=children_nodes,
    )


def _compute_depth(nodes: List[TreeNode]) -> int:
    """递归计算树的最大深度"""
    if not nodes:
        return 0
    return max(_compute_depth(n.children) + 1 for n in nodes)


def _count_nodes(nodes: List[TreeNode]) -> int:
    """递归统计节点总数"""
    return sum(1 + _count_nodes(n.children) for n in nodes)


def parse_org_tree(file_path: Path | str) -> Tuple[List[TreeNode], List[TreeIssue], int]:
    """
    解析组织架构树

    Returns:
        (tree_nodes, issues, total_rows)
    """
    file_path = Path(file_path)
    df = pd.read_excel(file_path, dtype=str)
    # 去掉完全空行
    df = df.dropna(how="all").reset_index(drop=True)

    level_columns = _resolve_level_columns(df)
    if not level_columns:
        return [], [], 0

    # 找出工号/姓名列，用于异常报告
    actual_cols = {clean_header(c): c for c in df.columns}
    emp_id_col = next(
        (actual_cols[p] for p in ["员工编号", "工号", "员工号"] if p in actual_cols),
        None,
    )
    name_col = next(
        (actual_cols[p] for p in ["姓名"] if p in actual_cols),
        None,
    )

    issues: List[TreeIssue] = []
    # 树的根容器
    root = {"_count": 0, "_level": 0, "children": {}}

    for idx, row in df.iterrows():
        excel_row = idx + 2
        raw_path = _extract_path(row, level_columns)

        emp_id = str(row.get(emp_id_col)).strip() if emp_id_col and not is_blank(row.get(emp_id_col)) else None
        name = str(row.get(name_col)).strip() if name_col and not is_blank(row.get(name_col)) else None

        # 异常 1：路径完全为空（一个组织都没填）
        if all(p == "" for p in raw_path) or not raw_path:
            issues.append(TreeIssue(
                row=excel_row,
                employee_id=emp_id,
                name=name,
                issue_type="empty_root",
                message="未填写任何组织信息",
                path=raw_path,
            ))
            continue

        # 异常 2：路径断层
        if _detect_path_gap(raw_path):
            issues.append(TreeIssue(
                row=excel_row,
                employee_id=emp_id,
                name=name,
                issue_type="path_gap",
                message=f"组织路径有断层：{' → '.join(p or '∅' for p in raw_path)}",
                path=raw_path,
            ))
            # 断层数据仍尝试入树（按清理后的路径）

        cleaned = _clean_path(raw_path)
        if cleaned:
            leaf = _insert_to_tree(root, cleaned)
            leaf["_count"] += 1

    # 转成 TreeNode 列表
    tree_nodes: List[TreeNode] = []
    for child_name, child_d in root["children"].items():
        node = _dict_to_tree_nodes(child_d, child_name)
        if node:
            tree_nodes.append(node)

    return tree_nodes, issues, len(df)