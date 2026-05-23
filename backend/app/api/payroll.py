"""
薪酬计算模块 · API 路由
"""
import uuid
from decimal import Decimal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.modules.payroll.batch_calculator import (
    calculate_batch,
    export_batch_report,
    generate_template,
)
from app.modules.payroll.calculator import PayrollInput, calculate_payroll
from app.schemas.payroll import PayrollCalcRequest, PayrollCalcResponse

router = APIRouter()


@router.get("/ping")
def ping():
    return {"module": "payroll", "status": "ok"}


@router.post("/calculate", response_model=PayrollCalcResponse)
def calculate(req: PayrollCalcRequest):
    """
    单人月度工资计算

    输入薪酬要素，计算应发、五险一金、个税、实发工资。

    **说明**：
    - 个税采用月度税率表（简化版），适合单月试算
    - 公积金费率范围 5%-12%，默认 7%
    - 五险一金基数留空则取应发工资
    - 专项附加扣除直接填月度合计金额
    """
    # 把 float 转 Decimal，进入精确计算
    input_data = PayrollInput(
        base_salary=Decimal(str(req.base_salary)),
        performance=Decimal(str(req.performance)),
        position_allowance=Decimal(str(req.position_allowance)),
        overtime_pay=Decimal(str(req.overtime_pay)),
        other_allowance=Decimal(str(req.other_allowance)),
        social_insurance_base=(
            Decimal(str(req.social_insurance_base))
            if req.social_insurance_base is not None
            else None
        ),
        housing_fund_rate=Decimal(str(req.housing_fund_rate)),
        special_deduction=Decimal(str(req.special_deduction)),
        other_deduction=Decimal(str(req.other_deduction)),
    )

    result = calculate_payroll(input_data)

    # Decimal 转 float 给前端，注释里说明为何这么做
    # 内部计算用 Decimal 保证精度，对外用 float 因为 JSON 没有 Decimal 类型
    return PayrollCalcResponse(
        gross_salary=float(result.gross_salary),
        income_breakdown={k: float(v) for k, v in result.income_breakdown.items()},
        pension=float(result.pension),
        medical=float(result.medical),
        unemployment=float(result.unemployment),
        housing_fund=float(result.housing_fund),
        social_insurance_total=float(result.social_insurance_total),
        taxable_income=float(result.taxable_income),
        tax_rate=float(result.tax_rate),
        quick_deduction=float(result.quick_deduction),
        income_tax=float(result.income_tax),
        other_deduction=float(result.other_deduction),
        deduction_total=float(result.deduction_total),
        net_salary=float(result.net_salary),
        notes=result.notes,
    )

# ============================================
# 批量算薪
# ============================================

@router.post("/batch/calculate")
async def batch_calculate(file: UploadFile = File(...)):
    """
    批量薪酬计算：上传 Excel，返回每人工资条 + 总览。

    Excel 字段（支持中英文别名）：
    - 必需：工号、姓名、基本工资
    - 可选：绩效工资、岗位津贴、加班费、其他补贴、社保基数、公积金费率、专项附加扣除、其他扣款
    """
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, detail="仅支持 .xlsx 或 .xls 格式")

    task_id = uuid.uuid4().hex[:8]
    upload_path = settings.UPLOAD_DIR / f"batch_{task_id}_{file.filename}"
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, detail="文件超出大小限制（最大 50MB）")
    upload_path.write_bytes(content)

    try:
        rows, summary = calculate_batch(upload_path)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=f"计算失败：{e}")

    # 导出结果 Excel
    report_path = settings.OUTPUT_DIR / f"batch_report_{task_id}.xlsx"
    export_batch_report(rows, summary, report_path)

    # 转成 JSON 友好的格式给前端
    return {
        "success": True,
        "summary": {
            "total_rows": summary.total_rows,
            "success_rows": summary.success_rows,
            "failed_rows": summary.failed_rows,
            "total_gross": float(summary.total_gross),
            "total_si": float(summary.total_si),
            "total_tax": float(summary.total_tax),
            "total_net": float(summary.total_net),
        },
        "rows": [
            {
                "row": r.row,
                "employee_id": r.employee_id,
                "name": r.name,
                "success": r.success,
                "error": r.error,
                "gross_salary": float(r.result.gross_salary) if r.success else None,
                "social_insurance_total": float(r.result.social_insurance_total) if r.success else None,
                "income_tax": float(r.result.income_tax) if r.success else None,
                "net_salary": float(r.result.net_salary) if r.success else None,
            }
            for r in rows
        ],
        "report_file": f"/api/payroll/batch/reports/{task_id}",
    }


@router.get("/batch/reports/{task_id}")
def download_batch_report(task_id: str):
    """下载批量算薪结果 Excel"""
    report_path = settings.OUTPUT_DIR / f"batch_report_{task_id}.xlsx"
    if not report_path.exists():
        raise HTTPException(404, detail="报告不存在或已过期")
    return FileResponse(
        path=report_path,
        filename=f"payroll_batch_{task_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/batch/template")
def download_batch_template():
    """下载批量算薪 Excel 模板"""
    template_path = settings.TEMPLATE_DIR / "payroll_batch_template.xlsx"
    if not template_path.exists():
        # 第一次访问时生成
        generate_template(template_path)
    return FileResponse(
        path=template_path,
        filename="payroll_batch_template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )