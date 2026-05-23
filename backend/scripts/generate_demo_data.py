"""
生成伪造的 HCM 演示数据
========================

为什么需要这个脚本：
- 项目截图、demo 演示需要"看起来真实"的数据
- 但不能使用任何真实客户数据
- 用 Faker 生成结构与浪潮 HCM 主集一致、内容完全虚构的测试数据

生成的文件：
- demo_employees.xlsx   人员主集（含组织 10 级、含身份证）
- demo_payroll.xlsx     批量算薪数据

运行方式（在 backend 目录下）：
    python -m scripts.generate_demo_data
"""
from __future__ import annotations

import random
import sys
import datetime
import pathlib

# 让脚本能直接跑（解决 import 路径）
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
from faker import Faker

from app.utils.id_card import calc_check_code


fake = Faker("zh_CN")
Faker.seed(42)   # 固定种子，保证多次生成数据稳定
random.seed(42)


# ============================================
# 工具函数
# ============================================

def gen_id_card(birth_date: datetime.date, gender: str) -> str:
    """生成合法的 18 位身份证号（虚构地区码 + 真实校验码）"""
    region = "320583"   # 江苏昆山，虚构示意，仅用于示例
    birth_str = birth_date.strftime("%Y%m%d")
    # 顺序码末位：男奇女偶
    seq_last = random.choice([1, 3, 5, 7, 9]) if gender == "男" else random.choice([0, 2, 4, 6, 8])
    seq = f"{random.randint(10, 99)}{seq_last}"
    prefix = region + birth_str + seq
    return prefix + calc_check_code(prefix)


def gen_birth_date(min_age: int = 22, max_age: int = 58) -> datetime.date:
    today = datetime.date.today()
    age = random.randint(min_age, max_age)
    birth = today - datetime.timedelta(days=age * 365 + random.randint(0, 364))
    return birth


# ============================================
# 组织架构（虚构的多级组织）
# ============================================

ORG_TREE = {
    "演示集团": {
        "技术中心": {
            "研发部": ["后端组", "前端组", "测试组", "运维组"],
            "数据部": ["数据工程", "数据分析", "算法组"],
            "产品部": ["产品设计", "用户研究"],
        },
        "财务中心": {
            "会计部": ["应收会计组", "应付会计组", "总账组"],
            "出纳部": ["现金组", "票据组"],
            "审计部": [],
        },
        "人力中心": {
            "招聘部": ["校园招聘组", "社会招聘组"],
            "薪酬绩效部": ["薪酬组", "绩效组"],
            "员工关系部": [],
        },
        "市场中心": {
            "品牌部": ["内容组", "设计组"],
            "销售部": ["华北区", "华东区", "华南区"],
        },
    },
    "演示分公司A": {
        "综合部": ["行政组", "后勤组"],
        "业务部": ["业务一组", "业务二组"],
    },
    "演示分公司B": {
        "综合部": ["行政组"],
    },
}


def get_org_paths() -> list[list[str]]:
    """从组织树展开成所有可能的路径"""
    paths = []
    for level1, level2_dict in ORG_TREE.items():
        for level2, level3_dict in level2_dict.items():
            if isinstance(level3_dict, dict):
                for level3, level4_list in level3_dict.items():
                    if level4_list:
                        for level4 in level4_list:
                            paths.append([level1, level2, level3, level4])
                    else:
                        paths.append([level1, level2, level3])
            elif isinstance(level3_dict, list):
                if level3_dict:
                    for level3 in level3_dict:
                        paths.append([level1, level2, level3])
                else:
                    paths.append([level1, level2])
    return paths


# ============================================
# 生成员工主集
# ============================================

POSITIONS = [
    "工程师", "高级工程师", "技术主管", "经理", "高级经理",
    "总监", "专员", "主管", "副总监", "助理",
]


def generate_employees(count: int = 200) -> pd.DataFrame:
    """生成员工主集数据"""
    paths = get_org_paths()
    rows = []

    for i in range(count):
        gender = random.choice(["男", "女"])
        name = fake.name_male() if gender == "男" else fake.name_female()
        birth = gen_birth_date()
        id_card = gen_id_card(birth, gender)

        path = random.choice(paths)
        # 补齐到 10 级（空字符串占位）
        org_levels = path + [""] * (10 - len(path))

        # 入职日期（随机过去 1-15 年内）
        hire_year_ago = random.randint(0, 15)
        hire_date = datetime.date.today() - datetime.timedelta(days=hire_year_ago * 365 + random.randint(0, 364))

        row = {
            "员工编号": f"E{i+1:04d}",
            "姓名": name,
            "证件类型": "居民身份证",
            "证件号": id_card,
            "性别": gender,
            "组织认定出生日期": birth.strftime("%Y-%m-%d"),
            "入职日期": hire_date.strftime("%Y-%m-%d"),
            "用工类型": random.choice(["正式员工", "劳务派遣", "实习生"]),
            "岗位状态": "在职",
        }

        # 10 级组织字段
        for level_idx in range(1, 11):
            level_names = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            row[f"岗位_{level_names[level_idx-1]}级组织"] = org_levels[level_idx - 1]

        rows.append(row)

    # 故意制造一些"脏数据"（让校验功能有东西可演示）
    if count >= 10:
        # 第 5 行：姓名为空
        rows[4]["姓名"] = ""
        # 第 8 行：身份证号错（最后一位故意改错）
        bad_id = rows[7]["证件号"]
        rows[7]["证件号"] = bad_id[:-1] + ("0" if bad_id[-1] != "0" else "1")
        # 第 12 行：性别与身份证不符（女改成男）
        if count > 11:
            rows[11]["性别"] = "男" if rows[11]["性别"] == "女" else "女"

    return pd.DataFrame(rows)


# ============================================
# 生成批量算薪数据
# ============================================

def generate_payroll(count: int = 50) -> pd.DataFrame:
    """生成批量算薪数据"""
    rows = []
    for i in range(count):
        gender = random.choice(["男", "女"])
        name = fake.name_male() if gender == "男" else fake.name_female()
        # 基本工资随机分布在 6k - 25k
        base = random.choice([6000, 8000, 10000, 12000, 15000, 18000, 22000, 25000])
        # 绩效占基本工资 0% - 40%
        perf = round(base * random.uniform(0, 0.4), -2)
        # 岗位津贴 0 - 1000
        position_allowance = random.choice([0, 200, 300, 500, 800, 1000])
        # 加班费 0 - 2000
        overtime = random.choice([0, 0, 0, 300, 500, 800, 1500])
        # 其他补贴
        other = random.choice([0, 100, 200])
        # 公积金费率 5%-12%
        hf_rate = random.choice([0.05, 0.06, 0.07, 0.08, 0.10, 0.12])
        # 专项扣除（房贷、子女教育等）
        special = random.choice([0, 500, 1000, 1500, 2000, 2500])

        rows.append({
            "工号": f"P{i+1:04d}",
            "姓名": name,
            "基本工资": base,
            "绩效工资": perf,
            "岗位津贴": position_allowance,
            "加班费": overtime,
            "其他补贴": other,
            "社保基数": "",
            "公积金费率": hf_rate,
            "专项附加扣除": special,
            "其他扣款": 0,
        })

    return pd.DataFrame(rows)


# ============================================
# 主程序
# ============================================

def main():
    output_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成员工主集
    print("正在生成员工主集...")
    employees_df = generate_employees(count=200)
    employees_file = output_dir / "demo_employees.xlsx"
    employees_df.to_excel(employees_file, index=False)
    print(f"✓ 员工主集已生成: {employees_file}（{len(employees_df)} 行）")

    # 生成批量算薪
    print("正在生成批量算薪数据...")
    payroll_df = generate_payroll(count=50)
    payroll_file = output_dir / "demo_payroll.xlsx"
    payroll_df.to_excel(payroll_file, index=False)
    print(f"✓ 批量算薪数据已生成: {payroll_file}（{len(payroll_df)} 行）")

    print("\n✅ 全部完成！可以用这些数据进行演示和截图。")
    print(f"   数据目录: {output_dir}")


if __name__ == "__main__":
    main()