"""
组织架构树 · 数据模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TreeNode(BaseModel):
    """树节点"""
    name: str = Field(..., description="部门名称")
    level: int = Field(..., description="层级，从 1 开始")
    employee_count: int = Field(0, description="直接挂在此节点的人数（不含子节点）")
    total_count: int = Field(0, description="本节点 + 所有子孙节点的总人数")
    children: List["TreeNode"] = Field(default_factory=list, description="子节点")


class TreeIssue(BaseModel):
    """组织架构异常"""
    row: int = Field(..., description="Excel 行号")
    employee_id: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    issue_type: str = Field(..., description="异常类型：path_gap / empty_root")
    message: str = Field(..., description="异常说明")
    path: List[str] = Field(default_factory=list, description="该行的原始路径")


class OrgTreeResponse(BaseModel):
    """组织架构解析响应"""
    success: bool
    total_rows: int = Field(..., description="数据行数")
    total_nodes: int = Field(..., description="树节点总数")
    max_depth: int = Field(..., description="树的最大深度")
    issues: List[TreeIssue] = Field(default_factory=list)
    tree: List[TreeNode] = Field(default_factory=list, description="根节点列表（可能有多个）")


# Pydantic 自引用模型需要这一行
TreeNode.model_rebuild()