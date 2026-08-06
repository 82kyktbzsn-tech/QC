# quality_checks.py
import pandas as pd

def check_renewal_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据标准部门、产品体系、续班类型、年级(原) 检测续班类型是否异常。
    规则：
      - 标准部门为'国外考试部'：不纳入质检，标注0
      - 出口年级（含“高三/初三/六年级/中考/高考”等关键词）：续班类型必须为 '不可续'，否则异常
      - 常规体系产品：续班类型必须为 '可续' 或 '连季续'，否则异常
      - 专项体系产品：续班类型必须为 '不可续'，否则异常
      - 计费体系产品：续班类型无限制（可为空），不判异常
      - 其他产品体系：视为异常（保守处理）

    参数:
        df: 需包含列 '标准部门', '产品体系', '续班类型', '年级(原)'

    返回:
        添加 '续班类型异常' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    # 预处理字符串列：去除首尾空格
    for col in ['标准部门', '产品体系', '续班类型', '年级(原)']:
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
    in_scope = result['标准部门'] != '国外考试部'
    is_exit_grade = result['年级(原)'].str.contains(
        pattern,
        case=False,
        na=False,
        regex=True,
    )
    mask_exit = in_scope & is_exit_grade
    # ---------- 修改点（结束） ----------

    # 1. 出口年级：若年级(原) 包含关键词，且 续班类型 != '不可续' → 异常
    mask_exit_abnormal = mask_exit & (result['续班类型'] != '不可续')
    result.loc[mask_exit_abnormal, '续班类型异常'] = 1

    # 2. 非出口年级，按产品体系判断
    not_exit = in_scope & ~is_exit_grade

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


def check_class_price(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“班级标价”是否规范。
    规则：
      - 班级标价 == 0：标注为1
      - 班级标价 != 0：标注为0

    参数:
        df: 需包含列 '班级标价'

    返回:
        添加 '班级标价规范' 列（int，1表示不规范，0表示正常）的DataFrame
    """
    result = df.copy()
    class_price = pd.to_numeric(result['班级标价'], errors='coerce')
    result['班级标价规范'] = (class_price == 0).astype(int)

    return result


def check_audit_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“班级审核状态”是否异常。
    规则：
      - 班级审核状态 != '已审核'：标注为1
      - 班级审核状态 == '已审核'：标注为0

    参数:
        df: 需包含列 '班级审核状态'

    返回:
        添加 '审核状态异常' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    audit_status = result['班级审核状态'].astype('string').str.strip()
    result['审核状态异常'] = audit_status.ne('已审核').fillna(True).astype(int)

    return result


def check_quarter_start_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“季度(外)”与“开课日期”是否匹配。
    校验范围：
      - 标准部门 != '国外考试部'

    规则：
      - 季度含'暑'：开课月份须为6-8月
      - 季度含'秋'：开课月份须为9-11月
      - 季度含'寒'：开课月份须为12月或1-2月
      - 季度含'春'：开课月份须为3-5月
      - 不符合以上规则：标注1，否则标注0

    参数:
        df: 需包含列 '标准部门', '开课日期', '季度(外)'

    返回:
        添加 '季度与开课日期不符' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    department = result['标准部门'].astype('string').str.strip()
    quarter = result['季度(外)'].astype('string').str.strip()
    start_month = pd.to_datetime(result['开课日期'], errors='coerce').dt.month

    in_scope = department.ne('国外考试部').fillna(True)
    quarter_matches_date = (
        (quarter.str.contains('暑', na=False) & start_month.between(6, 8))
        | (quarter.str.contains('秋', na=False) & start_month.between(9, 11))
        | (quarter.str.contains('寒', na=False) & start_month.isin([12, 1, 2]))
        | (quarter.str.contains('春', na=False) & start_month.between(3, 5))
    )
    result['季度与开课日期不符'] = (in_scope & ~quarter_matches_date).astype(int)

    return result


def check_class_format_and_delivery(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“上课形式”“授课方式”“授课渠道”的组合是否异常。

    规则：
      - 上课形式为'在线'：授课方式须为'在线直播'、'在线录播'或
        '在线直播,在线录播'，且授课渠道不可为空
      - 上课形式为'走读'：授课方式须为'常规面授'，且授课渠道须为空
      - 上课形式同时包含'在线'和'走读'：授课方式须包含'常规面授'，
        并包含'在线直播'或'在线录播'中的至少一个，且授课渠道不可为空
      - 不符合以上规则：标注1，否则标注0

    参数:
        df: 需包含列 '上课形式', '授课方式', '授课渠道'

    返回:
        添加 '上课形式&授课方式&授课渠道异常' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    class_format = (
        result['上课形式'].astype('string').str.strip().str.replace(r'\s+', '', regex=True)
    )
    delivery_method = (
        result['授课方式'].astype('string').str.strip().str.replace(r'\s+', '', regex=True)
    )
    delivery_channel = result['授课渠道'].astype('string').str.strip()
    channel_empty = delivery_channel.isna() | delivery_channel.eq('')

    is_online = class_format.eq('在线').fillna(False)
    online_methods = ['在线直播', '在线录播', '在线直播,在线录播','在线录播,在线直播']
    online_valid = (
        is_online
        & delivery_method.isin(online_methods)
        & ~channel_empty
    )

    is_commuter = class_format.eq('走读').fillna(False)
    commuter_valid = (
        is_commuter
        & delivery_method.eq('常规面授').fillna(False)
        & channel_empty
    )

    is_mixed = (
        class_format.str.contains('在线', na=False)
        & class_format.str.contains('走读', na=False)
    )
    mixed_method_valid = (
        delivery_method.str.contains('常规面授', na=False)
        & (
            delivery_method.str.contains('在线直播', na=False)
            | delivery_method.str.contains('在线录播', na=False)
        )
    )
    mixed_valid = is_mixed & mixed_method_valid & ~channel_empty

    valid_combination = online_valid | commuter_valid | mixed_valid
    result['上课形式&授课方式&授课渠道异常'] = (~valid_combination).astype(int)

    return result


def check_cancelled_class_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测取消班状态、班级名称和最大人数是否匹配。

    正常情况仅包括：
      - 班级状态为'取消班'，内外班级名称都包含'取消'，且最大人数为0
      - 班级状态不为'取消班'，内外班级名称都不包含'取消'
      - 除以上两种情况外：标注1，否则标注0

    参数:
        df: 需包含列 '班级名称（外）', '班级名称（内）', '班级状态', '最大人数'

    返回:
        添加 '取消班状态异常' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    class_status = result['班级状态'].astype('string').str.strip()
    external_name = result['班级名称（外）'].astype('string').str.strip()
    internal_name = result['班级名称（内）'].astype('string').str.strip()
    maximum_students = pd.to_numeric(result['最大人数'], errors='coerce')

    external_has_cancel = external_name.str.contains('取消', na=False)
    internal_has_cancel = internal_name.str.contains('取消', na=False)
    is_cancelled = class_status.eq('取消班').fillna(False)

    cancelled_valid = (
        is_cancelled
        & external_has_cancel
        & internal_has_cancel
        & maximum_students.eq(0)
    )
    active_valid = (
        ~is_cancelled
        & ~external_has_cancel
        & ~internal_has_cancel
    )
    result['取消班状态异常'] = (~(cancelled_valid | active_valid)).astype(int)

    return result


def check_class_setup_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测设班日期是否晚于开课日期。

    规则：
      - 开课日期 - 设班日期 >= 0：标注0
      - 开课日期 - 设班日期 < 0：标注1
      - 日期为空或无法解析：标注1

    参数:
        df: 需包含列 '开课日期', '设班日期'

    返回:
        添加 '设班时间晚于开课时间' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    start_date = pd.to_datetime(result['开课日期'], errors='coerce')
    setup_date = pd.to_datetime(result['设班日期'], errors='coerce')
    setup_date_valid = (start_date - setup_date).dt.days.ge(0).fillna(False)
    result['设班时间晚于开课时间'] = (~setup_date_valid).astype(int)

    return result


def check_actual_start_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测非取消班的实际开课日期与开课日期是否为同一年月。

    规则：
      - 班级状态不为'取消班'时，两列日期的年份和月份必须一致
      - 年月不一致或日期为空、无法解析：标注1
      - 取消班不纳入质检：标注0

    参数:
        df: 需包含列 '班级状态', '实际开课日期', '开课日期'

    返回:
        添加 '实际开课日期不早于开课日期当月' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    class_status = result['班级状态'].astype('string').str.strip()
    actual_start_date = pd.to_datetime(result['实际开课日期'], errors='coerce')
    planned_start_date = pd.to_datetime(result['开课日期'], errors='coerce')

    not_cancelled = class_status.ne('取消班').fillna(True)
    same_year_month = (
        actual_start_date.notna()
        & planned_start_date.notna()
        & actual_start_date.dt.year.eq(planned_start_date.dt.year)
        & actual_start_date.dt.month.eq(planned_start_date.dt.month)
    )
    result['实际开课日期不早于开课日期当月'] = (
        not_cancelled & ~same_year_month
    ).astype(int)

    return result


def check_external_class_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“上课时间(外)”是否填写。

    规则：
      - 班级时长 == 1：不要求填写，标注0
      - 其他记录的上课时间(外)为空：标注1，否则标注0

    参数:
        df: 需包含列 '上课时间(外)', '班级时长'

    返回:
        添加 '上课时间（外）未填写' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    class_duration = pd.to_numeric(result['班级时长'], errors='coerce')
    external_class_time = result['上课时间(外)'].astype('string').str.strip()
    external_class_time_empty = (
        external_class_time.isna() | external_class_time.eq('')
    )
    result['上课时间（外）未填写'] = (
        class_duration.ne(1) & external_class_time_empty
    ).astype(int)

    return result


def check_textbook_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测非计费体系的“教材发放形式”是否填写。

    规则：
      - 产品体系 != '计费体系'且教材发放形式为空：标注1
      - 其他情况：标注0

    参数:
        df: 需包含列 '教材发放形式', '产品体系'

    返回:
        添加 '教材发放形式填写错误' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    product_system = result['产品体系'].astype('string').str.strip()
    textbook_distribution = result['教材发放形式'].astype('string').str.strip()

    not_billing_system = product_system.ne('计费体系').fillna(True)
    distribution_empty = (
        textbook_distribution.isna() | textbook_distribution.eq('')
    )
    result['教材发放形式填写错误'] = (
        not_billing_system & distribution_empty
    ).astype(int)

    return result


def check_class_closure(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测班级是否需要封班。

    标签规则：
      - 产品体系 != '计费体系'，实际开课日期不晚于当月最后一天，
        实际结课日期不早于当月第一天，且当前人数(占名额)为0：
        标注'0人班未封班'
      - 产品体系 == '计费体系'，且班级课次数或班级时长任一不等于1：
        标注'计费体系课次时长异常'
      - 其他情况保持为空

    参数:
        df: 需包含列 '实际开课日期', '实际结课日期',
            '当前人数(占名额)', '班级课次数', '班级时长', '产品体系'

    返回:
        添加 '封班检查' 列的DataFrame
    """
    result = df.copy()
    product_system = result['产品体系'].astype('string').str.strip()
    actual_start_date = pd.to_datetime(result['实际开课日期'], errors='coerce')
    actual_end_date = pd.to_datetime(result['实际结课日期'], errors='coerce')
    current_students = pd.to_numeric(result['当前人数(占名额)'], errors='coerce')
    class_count = pd.to_numeric(result['班级课次数'], errors='coerce')
    class_duration = pd.to_numeric(result['班级时长'], errors='coerce')

    today = pd.Timestamp.today().normalize()
    month_start = today.replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(1)

    is_billing_system = product_system.eq('计费体系').fillna(False)
    non_billing_needs_closure = (
        ~is_billing_system
        & actual_start_date.le(month_end)
        & actual_end_date.ge(month_start)
        & current_students.eq(0)
    )
    billing_needs_closure = (
        is_billing_system
        & (class_count.ne(1) | class_duration.ne(1))
    )
    result['封班检查'] = pd.Series(pd.NA, index=result.index, dtype='string')
    result.loc[
        non_billing_needs_closure,
        '封班检查',
    ] = '0人班未封班'
    result.loc[
        billing_needs_closure,
        '封班检查',
    ] = '计费体系课次时长异常'

    return result


def check_minimum_payroll_department(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“最小发薪部门”是否为空。

    规则：
      - 最小发薪部门为空：标注1
      - 最小发薪部门不为空：标注0

    参数:
        df: 需包含列 '最小发薪部门'

    返回:
        添加 '最小发薪部门为空' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    payroll_department = result['最小发薪部门'].astype('string').str.strip()
    result['最小发薪部门为空'] = (
        payroll_department.isna() | payroll_department.eq('')
    ).astype(int)

    return result


def check_class_and_actual_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“班级时长”和“实际时长”是否异常。

    规则：
      - 任意一个时长为0、为空或无法解析为数字：标注1
      - 两个时长均为有效非零数值：标注0

    参数:
        df: 需包含列 '班级时长', '实际时长'

    返回:
        添加 '班级时长&实际时长异常' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    class_duration = pd.to_numeric(result['班级时长'], errors='coerce')
    actual_duration = pd.to_numeric(result['实际时长'], errors='coerce')
    duration_abnormal = (
        class_duration.isna()
        | class_duration.eq(0)
        | actual_duration.isna()
        | actual_duration.eq(0)
    )
    result['班级时长&实际时长异常'] = duration_abnormal.astype(int)

    return result


def check_class_location_and_room(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“上课地点(外)”和“上课教室”是否填写。

    不纳入质检的情况：
      - 班级状态 == '取消班'
      - 产品体系 == '计费体系'
      - 开课日期 > 当天

    规则：
      - 校验范围内，上课地点(外)或上课教室任意一个为空：标注1
      - 其他情况：标注0

    参数:
        df: 需包含列 '上课地点(外)', '上课教室', '班级状态',
            '产品体系', '开课日期'

    返回:
        添加 '未设置上课地点/上课教室' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    class_status = result['班级状态'].astype('string').str.strip()
    product_system = result['产品体系'].astype('string').str.strip()
    start_date = pd.to_datetime(result['开课日期'], errors='coerce')
    external_location = result['上课地点(外)'].astype('string').str.strip()
    classroom = result['上课教室'].astype('string').str.strip()

    today = pd.Timestamp.today().normalize()
    in_scope = (
        class_status.ne('取消班').fillna(True)
        & product_system.ne('计费体系').fillna(True)
        & ~start_date.gt(today)
    )
    location_empty = external_location.isna() | external_location.eq('')
    classroom_empty = classroom.isna() | classroom.eq('')
    result['未设置上课地点/上课教室'] = (
        in_scope & (location_empty | classroom_empty)
    ).astype(int)

    return result


def check_attendance_card_setting(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测考勤方式与班容、产品体系是否匹配。

    规则：
      - 产品体系为'计费体系'：考勤方式须为'不使用一卡通'
      - 非计费体系且班容为1人：考勤方式须为'VIP刷卡'
      - 非计费体系且班容为2人及以上：考勤方式须为'班级刷卡'
      - 其他情况：标注1

    参数:
        df: 需包含列 '考勤方式', '班容名称', '产品体系'

    返回:
        添加 '一卡通设置错误' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    attendance_method = result['考勤方式'].astype('string').str.strip()
    capacity_name = result['班容名称'].astype('string').str.strip()
    product_system = result['产品体系'].astype('string').str.strip()
    capacity = pd.to_numeric(
        capacity_name.str.extract(r'(\d+)', expand=False),
        errors='coerce',
    )

    is_billing_system = product_system.eq('计费体系').fillna(False)
    billing_valid = (
        is_billing_system
        & attendance_method.eq('不使用一卡通').fillna(False)
    )
    one_person_valid = (
        ~is_billing_system
        & capacity.eq(1)
        & attendance_method.eq('VIP刷卡').fillna(False)
    )
    class_card_capacity = capacity.ge(2)
    class_card_valid = (
        ~is_billing_system
        & class_card_capacity
        & attendance_method.eq('班级刷卡').fillna(False)
    )

    result['一卡通设置错误'] = (
        ~(billing_valid | one_person_valid | class_card_valid)
    ).astype(int)

    return result


def check_learning_device_online_settings(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“学习机线上”的班级设置是否规范。

    规则：
      - 上课形式须为'在线'
      - 授课方式须为'在线录播'
      - 授课渠道须为'智慧学习机'
      - 考勤方式须为'班级刷卡'
      - 上课教室非空时须包含'网络'，为空不判异常
      - 校区名称非空时须包含'网络'，为空不判异常
      - 常规体系：产品品类须为'XXJ'
      - 计费体系：产品品类须包含'JF'
      - 专项体系：产品品类须包含'ZT'或'YL'
      - A体系/B体系/C体系：产品品类须以对应的A/B/C字母开头
      - 任意一项不符合：标注1；全部符合：标注0
      - 其他管理项目不纳入质检，标注0

    参数:
        df: 需包含列 '管理项目', '产品体系', '产品品类', '上课形式',
            '授课方式', '授课渠道', '考勤方式', '上课教室', '校区名称'

    返回:
        添加 '学习机线上班级设置规范' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    management_project = result['管理项目'].astype('string').str.strip()
    product_system = result['产品体系'].astype('string').str.strip()
    product_category = result['产品品类'].astype('string').str.strip()
    class_format = result['上课形式'].astype('string').str.strip()
    delivery_method = result['授课方式'].astype('string').str.strip()
    delivery_channel = result['授课渠道'].astype('string').str.strip()
    attendance_method = result['考勤方式'].astype('string').str.strip()
    classroom = result['上课教室'].astype('string').str.strip()
    campus_name = result['校区名称'].astype('string').str.strip()
    empty_text_values = ['', 'nan', 'none', '<na>']
    classroom_empty = (
        classroom.isna() | classroom.str.lower().isin(empty_text_values)
    )
    campus_name_empty = (
        campus_name.isna() | campus_name.str.lower().isin(empty_text_values)
    )

    in_scope = management_project.eq('学习机线上').fillna(False)
    class_setting_valid = (
        class_format.eq('在线').fillna(False)
        & delivery_method.eq('在线录播').fillna(False)
        & delivery_channel.eq('智慧学习机').fillna(False)
        & attendance_method.eq('班级刷卡').fillna(False)
        & (classroom_empty | classroom.str.contains('网络', na=False))
        & (campus_name_empty | campus_name.str.contains('网络', na=False))
    )
    valid_product_setting = (
        (
            product_system.eq('常规体系').fillna(False)
            & product_category.eq('XXJ').fillna(False)
        )
        | (
            product_system.eq('计费体系').fillna(False)
            & product_category.str.contains('JF', na=False)
        )
        | (
            product_system.eq('专项体系').fillna(False)
            & product_category.str.contains('ZT|YL', na=False, regex=True)
        )
        | (
            product_system.eq('A体系').fillna(False)
            & product_category.str.startswith('A', na=False)
        )
        | (
            product_system.eq('B体系').fillna(False)
            & product_category.str.startswith('B', na=False)
        )
        | (
            product_system.eq('C体系').fillna(False)
            & product_category.str.startswith('C', na=False)
        )
    )
    result['学习机线上班级设置规范'] = (
        in_scope & ~(class_setting_valid & valid_product_setting)
    ).astype(int)

    return result


def check_minimum_and_opening_students(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测保底人数是否小于开班人数。

    规则：
      - 保底人数 <= 开班人数：标注0
      - 其他情况：标注1

    参数:
        df: 需包含列 '开班人数', '保底人数'

    返回:
        添加 '开班保底人数' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    opening_students = pd.to_numeric(result['开班人数'], errors='coerce')
    minimum_students = pd.to_numeric(result['保底人数'], errors='coerce')
    result['开班保底人数'] = (
        ~minimum_students.le(opening_students)
    ).astype(int)

    return result


def check_teacher_and_related_class(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测“主带课老师”和“关联班号”是否异常。
    校验范围：
      - 标准部门属于 ['智慧学习部', '素养智学部', '高中班级部']
      - 产品体系 != '计费体系'

    规则：
      - 主带课教师异常：开课日期小于等于当天、班级状态不为'取消班'、主带课老师为空时，标注1，否则标注0
      - 关联班号异常：标准部门在校验部门内、季度包含'上'或'下'、
        班级状态不为'取消班'且关联班号为空时，标注1，否则标注0
      - 不在校验范围内：两列均标注0

    参数:
        df: 需包含列 '标准部门', '主带课老师', '班级状态', '开课日期', '产品体系', '关联班号', '季度'

    返回:
        添加 '主带课教师异常'、'关联班号异常' 列的DataFrame
    """
    result = df.copy()

    check_departments = ['智慧学习部', '素养智学部', '高中班级部']
    for col in ['标准部门', '主带课老师', '班级状态', '产品体系', '关联班号', '季度']:
        if col in result.columns:
            result[col] = result[col].astype('string').str.strip()

    today = pd.Timestamp.today().normalize()
    start_date = pd.to_datetime(result['开课日期'], errors='coerce')
    in_scope = (
        result['标准部门'].isin(check_departments)
        & (result['产品体系'] != '计费体系')
    )
    not_cancelled = result['班级状态'] != '取消班'

    teacher_empty = result['主带课老师'].isna() | (result['主带课老师'] == '')
    teacher_abnormal = in_scope & (start_date <= today) & not_cancelled & teacher_empty
    result['主带课教师异常'] = teacher_abnormal.astype(int)

    related_class_empty = result['关联班号'].isna() | (result['关联班号'] == '')
    quarter_needs_related_class = result['季度'].str.contains('上|下', na=False, regex=True)
    related_class_abnormal = (
        result['标准部门'].isin(check_departments)
        & quarter_needs_related_class
        & not_cancelled
        & related_class_empty
    )
    result['关联班号异常'] = related_class_abnormal.astype(int)

    return result
