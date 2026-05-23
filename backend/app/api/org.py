"""
组织人事模块 · API 路由
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.modules.org.employee_validator import (
    export_report,
    inspect_columns,
    validate_employees,
)
from app.modules.org.org_tree_parser import parse_org_tree
from app.schemas.org import EmployeeValidationResponse
from app.schemas.org_tree import OrgTreeResponse

router = APIRouter()


@router.get("/ping")
def ping():
    return {"module": "org", "status": "ok"}


@router.post("/employees/validate", response_model=EmployeeValidationResponse)
async def validate_employees_api(file: UploadFile = File(...)):
    """
    上传员工档案 Excel，返回校验结果

    支持的列名（中英文别名都可以）：
    - 工号 / 员工编号 / employee_id
    - 姓名 / name
    - 身份证号 / 证件号 / id_card
    - 证件类型 / id_card_type
    - 性别 / gender
    - 手机号 / phone
    - 邮箱 / email
    - 部门 / department
    - 岗位 / position
    """
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, detail="仅支持 .xlsx 或 .xls 格式")

    task_id = uuid.uuid4().hex[:8]
    upload_path = settings.UPLOAD_DIR / f"{task_id}_{file.filename}"
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, detail="文件超出大小限制（最大 50MB）")
    upload_path.write_bytes(content)

    try:
        summary, issues, _ = validate_employees(upload_path)
    except Exception as e:
        raise HTTPException(500, detail=f"校验失败：{e}")

    report_path = settings.OUTPUT_DIR / f"report_{task_id}.xlsx"
    export_report(issues, summary, report_path)

    return EmployeeValidationResponse(
        success=True,
        summary=summary,
        issues=issues,
        report_file=f"/api/org/reports/{task_id}",
    )


@router.post("/employees/inspect")
async def inspect_employees_api(file: UploadFile = File(...)):
    """
    诊断 Excel 表头：识别字段映射，定位列名问题

    返回信息：
    - total_columns: 总列数
    - all_columns: 所有列名
    - recognized: 识别成功的字段映射（标准名 -> 实际列名）
    - unrecognized_columns: 未识别的列名
    - missing_important_fields: 缺失的重要字段（工号、姓名、身份证）
    """
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, detail="仅支持 .xlsx 或 .xls 格式")

    task_id = uuid.uuid4().hex[:8]
    upload_path = settings.UPLOAD_DIR / f"inspect_{task_id}_{file.filename}"
    content = await file.read()
    upload_path.write_bytes(content)

    try:
        result = inspect_columns(upload_path)
    except Exception as e:
        raise HTTPException(500, detail=f"诊断失败：{e}")

    return result


@router.get("/reports/{task_id}")
def download_report(task_id: str):
    """下载校验报告 Excel"""
    report_path = settings.OUTPUT_DIR / f"report_{task_id}.xlsx"
    if not report_path.exists():
        raise HTTPException(404, detail="报告不存在或已过期")
    return FileResponse(
        path=report_path,
        filename=f"validation_report_{task_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/templates/employee")
def download_employee_template():
    """下载员工档案标准模板"""
    template_path = settings.TEMPLATE_DIR / "employee_template.xlsx"
    if not template_path.exists():
        raise HTTPException(404, detail="模板文件不存在")
    return FileResponse(
        path=template_path,
        filename="employee_template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
@router.post("/structure/parse", response_model=OrgTreeResponse)
async def parse_org_structure(file: UploadFile = File(...)):
    """
    上传含组织层级列的 Excel，解析出组织架构树。

    自动识别的列名（中英文都支持）：
    - 岗位_一级组织 / 一级组织 / 一级部门
    - 岗位_二级组织 / 二级组织 / 二级部门
    - ...（最多到十级）

    返回信息：
    - tree: 树形结构 JSON
    - issues: 异常清单（路径断层、空组织等）
    - total_rows / total_nodes / max_depth: 统计信息
    """
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, detail="仅支持 .xlsx 或 .xls 格式")

    task_id = uuid.uuid4().hex[:8]
    upload_path = settings.UPLOAD_DIR / f"orgtree_{task_id}_{file.filename}"
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, detail="文件超出大小限制（最大 50MB）")
    upload_path.write_bytes(content)

    try:
        tree, issues, total_rows = parse_org_tree(upload_path)
    except Exception as e:
        raise HTTPException(500, detail=f"解析失败：{e}")

    # 统计树的深度和节点数
    def count_nodes(nodes):
        return sum(1 + count_nodes(n.children) for n in nodes)

    def max_depth(nodes):
        if not nodes:
            return 0
        return max(max_depth(n.children) + 1 for n in nodes)

    return OrgTreeResponse(
        success=True,
        total_rows=total_rows,
        total_nodes=count_nodes(tree),
        max_depth=max_depth(tree),
        issues=issues,
        tree=tree,
    )