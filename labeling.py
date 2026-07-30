# labeling.py
import pandas as pd
import re

# 湖南地级市（含自治州）及用户特别指定的关键词
HUNAN_CITIES = [
    '长沙', '株洲', '湘潭', '衡阳', '邵阳', '岳阳',
    '常德', '张家界', '益阳', '郴州', '永州', '怀化',
    '娄底', '湘西'
]
COVER_KEYWORDS = HUNAN_CITIES + ['省域网络']   # 匹配任意一个即覆盖


def apply_classlesson_standard_department(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据 classlesson 字段生成“标化部门”，并放在第一列。

    字段映射：
      - 标准部门名称：对应 classinfo 的“标准部门”
      - 科目名称：对应 classinfo 的“科目(原)”
      - 教学区名称：对应 classinfo 的“校区名称”
    """
    result = df.copy()

    for col in ['标准部门名称', '科目名称', '教学区名称']:
        result[col] = result[col].astype('string').str.strip()

    department = result['标准部门名称']
    subject = result['科目名称']
    teaching_area = result['教学区名称']
    result['标化部门'] = ''

    result.loc[department == '高中班级部', '标化部门'] = '高中班级部'
    result.loc[department == '国外考试部', '标化部门'] = '国外考试部'

    suyang_department = department == '素养智学部'
    result.loc[suyang_department, '标化部门'] = '小学学习机'

    suyang_subjects = {'博文妙笔', '脑力与思维', '书法', '双语故事表演'}
    suzhi_subjects = {'编程', '机器人', '科创', '围棋'}
    result.loc[
        suyang_department & subject.isin(suyang_subjects),
        '标化部门',
    ] = '素养'
    result.loc[
        suyang_department & subject.isin(suzhi_subjects),
        '标化部门',
    ] = '素质'

    result.loc[department == '智慧学习部', '标化部门'] = '中学学习机'

    pattern = '|'.join(COVER_KEYWORDS)
    innovation_area = teaching_area.str.contains(
        pattern,
        case=False,
        na=False,
        regex=True,
    )
    result.loc[innovation_area, '标化部门'] = '创新'

    columns = ['标化部门'] + [
        col for col in result.columns if col != '标化部门'
    ]
    return result[columns]


def apply_standard_department(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据规则为 DataFrame 添加“标化部门”列，并确保其位于第二列。

    规则：
    1. 标准部门 = 高中班级部 → 标化部门 = '高中班级部'
    2. 标准部门 = 国外考试部 → '国外考试部'
    3. 标准部门 = 素养智学部：
       - 科目(原)in {博文妙笔, 脑力与思维, 书法, 双语故事表演} → '素养'
       - 科目(原)in {编程, 机器人, 科创, 围棋} → '素质'
       - 其他科目 → '小学学习机'
    4. 标准部门 = 智慧学习部 → '中学学习机'
    5. 若校区名称包含 湖南地级市名 或 '省域网络'，则覆盖上一步结果为 '创新'

    Parameters
    ----------
    df : pd.DataFrame
        必须包含列：'标准部门', '科目(原)', '校区名称'，且应已有'数据分类'列

    Returns
    -------
    pd.DataFrame
        添加了 '标化部门' 列，且列顺序为：数据分类 -> 标化部门 -> 其余列
    """
    # 复制避免修改原数据
    result = df.copy()

    # 确保字符串列去除首尾空格（若存在）
    str_cols = ['标准部门', '科目(原)', '校区名称']
    for col in str_cols:
        if col in result.columns:
            result[col] = result[col].astype(str).str.strip()

    # ---------- 第一轮：按部门与科目打标签 ----------
    result['标化部门'] = ''   # 初始化（暂时放在最后一列）

    # 1) 高中班级部
    mask_high = result['标准部门'] == '高中班级部'
    result.loc[mask_high, '标化部门'] = '高中班级部'

    # 2) 国外考试部
    mask_foreign = result['标准部门'] == '国外考试部'
    result.loc[mask_foreign, '标化部门'] = '国外考试部'

    # 3) 素养智学部
    mask_suyang_dept = result['标准部门'] == '素养智学部'
    # 先默认给 '小学学习机'
    result.loc[mask_suyang_dept, '标化部门'] = '小学学习机'

    # 定义科目集合
    suyang_subjects = {'博文妙笔', '脑力与思维', '书法', '双语故事表演'}
    suzhi_subjects = {'编程', '机器人', '科创', '围棋'}

    # 素养
    mask_suyang_sub = mask_suyang_dept & result['科目(原)'].isin(suyang_subjects)
    result.loc[mask_suyang_sub, '标化部门'] = '素养'

    # 素质
    mask_suzhi_sub = mask_suyang_dept & result['科目(原)'].isin(suzhi_subjects)
    result.loc[mask_suzhi_sub, '标化部门'] = '素质'

    # 4) 智慧学习部
    mask_smart = result['标准部门'] == '智慧学习部'
    result.loc[mask_smart, '标化部门'] = '中学学习机'

    # ---------- 第二轮：根据校区名称覆盖为“创新” ----------
    pattern = '|'.join(COVER_KEYWORDS)
    mask_cover = result['校区名称'].str.contains(pattern, case=False, na=False, regex=True)
    result.loc[mask_cover, '标化部门'] = '创新'

    # ---------- 调整列顺序：确保“数据分类”第一，“标化部门”第二 ----------
    # 如果“数据分类”不存在，则不做调整（但按流程一定存在）
    if '数据分类' in result.columns:
        # 取出第一列、第二列、其余列
        desired_order = ['数据分类', '标化部门'] + [
            col for col in result.columns if col not in ['数据分类', '标化部门']
        ]
        result = result[desired_order]
    else:
        # 若没有“数据分类”，则将标化部门移到最前面（备用）
        cols = ['标化部门'] + [c for c in result.columns if c != '标化部门']
        result = result[cols]

    return result
