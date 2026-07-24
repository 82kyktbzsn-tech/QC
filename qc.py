# quality_checks.py
import pandas as pd

def check_renewal_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据产品体系、续班类型、年级(原) 检测续班类型是否异常。
    规则：
      - 出口年级（含“高三/初三/六年级/中考/高考”等关键词）：续班类型必须为 '不可续'，否则异常
      - 常规体系产品：续班类型必须为 '可续' 或 '连季续'，否则异常
      - 专项体系产品：续班类型必须为 '不可续'，否则异常
      - 计费体系产品：续班类型无限制（可为空），不判异常
      - 其他产品体系：视为异常（保守处理）

    参数:
        df: 需包含列 '产品体系', '续班类型', '年级(原)'

    返回:
        添加 '续班类型异常' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    # 预处理字符串列：去除首尾空格
    for col in ['产品体系', '续班类型', '年级(原)']:
        if col in result.columns:
            result[col] = result[col].astype(str).str.strip()

    # 初始化异常列，默认0（正常）
    result['续班类型异常'] = 0

    # ---------- 修改点（开始） ----------
    # 定义出口年级关键词列表（可自定义）
    exit_grades = ['高三', '初三', '六年级', '中考', '高考']
    regular_systems = ['常规体系','A体系','B体系']
    # 构建正则表达式，实现“包含任一关键词”的模糊匹配（忽略大小写）
    pattern = '|'.join(exit_grades)
    mask_exit = result['年级(原)'].str.contains(pattern, case=False, na=False, regex=True)
    # ---------- 修改点（结束） ----------

    # 1. 出口年级：若年级(原) 包含关键词，且 续班类型 != '不可续' → 异常
    mask_exit_abnormal = mask_exit & (result['续班类型'] != '不可续')
    result.loc[mask_exit_abnormal, '续班类型异常'] = 1

    # 2. 非出口年级，按产品体系判断
    not_exit = ~mask_exit

    # 2.1 常规体系：续班类型 in ['可续','连季续'] 为正常，否则异常
    mask_regular = (result['产品体系'].isin(regular_systems)) & not_exit
    regular_ok = result['续班类型'].isin(['可续', '连季续'])
    result.loc[mask_regular & ~regular_ok, '续班类型异常'] = 1

    # 2.2 专项体系：续班类型 == '不可续' 为正常，否则异常
    mask_special = (result['产品体系'] == '专项体系') & not_exit
    special_ok = result['续班类型'] == '不可续'
    result.loc[mask_special & ~special_ok, '续班类型异常'] = 1

    # 2.3 计费体系：不判异常（不做任何操作）

    # 2.4 其他未定义的产品体系：视为异常（保守），但排除已处理过的
    defined_systems = ['常规体系', 'A体系','B体系', '专项体系', '计费体系']
    mask_other = (~result['产品体系'].isin(defined_systems)) & not_exit
    result.loc[mask_other, '续班类型异常'] = 1

    return result