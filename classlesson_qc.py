import pandas as pd


def check_abnormal_schedule_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测课次起止时间是否超出正常排课范围。

    规则：
      - 起始时间早于06:00，或结束时间晚于22:00：标注1
      - 其他情况：标注0

    参数:
        df: 需包含列 '起始时间', '结束时间'

    返回:
        添加 '异常时间排课' 列（int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    start_time = pd.to_timedelta(
        result['起始时间'].astype('string'),
        errors='coerce',
    )
    end_time = pd.to_timedelta(
        result['结束时间'].astype('string'),
        errors='coerce',
    )

    starts_before_six = start_time < pd.Timedelta(hours=6)
    ends_after_twenty_two = end_time > pd.Timedelta(hours=22)
    result['异常时间排课'] = (
        starts_before_six | ends_after_twenty_two
    ).astype(int)

    return result


def check_abnormal_attendance(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测班级刷卡课次的教师、学员考勤是否异常。

    规则：
      - “使用一卡通”为“班级刷卡”或“班级打卡”时纳入质检
      - 教师打卡状态为“未打卡”或为空时，“教师考勤异常”标注1
      - 学员打卡状态为“未打卡”或为空时，“学员考勤异常”标注1
      - 国外考试部的自习、模课、模考课次不要求教师打卡
      - 分钟数为1的课次不要求教师和学员打卡
      - 不在质检范围或教师、学员考勤均符合要求时，标注0

    参数:
        df: 需包含列 '教师打卡状态', '学员打卡状态', '分钟数',
            '标准部门名称', '授课内容类型', '科目名称', '课程名称',
            '使用一卡通'

    返回:
        添加 '教师考勤异常'、'学员考勤异常' 列
        （int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    card_usage = result['使用一卡通'].astype('string').str.strip()
    teacher_status = result['教师打卡状态'].astype('string').str.strip()
    student_status = result['学员打卡状态'].astype('string').str.strip()
    department = result['标准部门名称'].astype('string').str.strip()
    content_type = result['授课内容类型'].astype('string').str.strip()
    subject = result['科目名称'].astype('string').str.strip()
    course_name = result['课程名称'].astype('string').str.strip()
    minutes = pd.to_numeric(result['分钟数'], errors='coerce')

    in_scope = card_usage.isin(['班级刷卡', '班级打卡'])
    teacher_not_checked = (
        teacher_status.isna()
        | teacher_status.eq('')
        | teacher_status.eq('未打卡')
    )
    student_not_checked = (
        student_status.isna()
        | student_status.eq('')
        | student_status.eq('未打卡')
    )

    foreign_special_lesson = (
        department.eq('国外考试部').fillna(False)
        & (
            content_type.str.contains('自习', na=False)
            | subject.str.contains('自习|模课|模考', na=False, regex=True)
            | course_name.str.contains('自习|模课|模考', na=False, regex=True)
        )
    )
    one_minute_lesson = minutes.eq(1)

    teacher_attendance_abnormal = (
        in_scope
        & teacher_not_checked
        & ~foreign_special_lesson
        & ~one_minute_lesson
    )
    student_attendance_abnormal = (
        in_scope & student_not_checked & ~one_minute_lesson
    )
    result['教师考勤异常'] = teacher_attendance_abnormal.astype(int)
    result['学员考勤异常'] = student_attendance_abnormal.astype(int)

    return result


def check_zero_student_class(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测当前人数是否为0。

    规则：
      - 当前人数（占名额） == 0：标注1
      - 其他情况：标注0

    参数:
        df: 需包含列 '当前人数（占名额）'

    返回:
        添加 '0人班处理' 列（int，1表示需要处理，0表示正常）的DataFrame
    """
    result = df.copy()
    current_students = pd.to_numeric(
        result['当前人数（占名额）'],
        errors='coerce',
    )
    result['0人班处理'] = current_students.eq(0).astype(int)

    return result


def check_schedule_audit_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测配课表是否及时完成审核。

    规则：
      - 审核状态为“已审核”：标注0
      - 审核状态为其他值、为空：标注1

    参数:
        df: 需包含列 '审核状态'

    返回:
        添加 '配课表审核时效异常' 列
        （int，1表示异常，0表示正常）的DataFrame
    """
    result = df.copy()
    audit_status = result['审核状态'].astype('string').str.strip()
    result['配课表审核时效异常'] = (
        audit_status.ne('已审核').fillna(True)
    ).astype(int)

    return result


def check_lesson_content_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测课程名称与授课内容类型是否匹配。

    按以下顺序判定，每条记录只保留优先级最高的异常原因：
      1. 授课内容类型不可为空
      2. 课程名称含“训练/辅导/带练”时，必须为“辅导课”
      3. 课程名称含“模考”时，必须为“测评课”
      4. 课程名称含“自习”时，必须为“自习课”
      5. 授课内容类型为“正课”时，课程名称不可包含其他授课内容
         类型关键词

    参数:
        df: 需包含列 '课程名称', '授课内容类型'

    返回:
        添加 '授课内容类型异常'（int，1表示异常，0表示正常）和
        '授课内容类型异常原因' 列的DataFrame
    """
    result = df.copy()
    course_name = result['课程名称'].astype('string').str.strip()
    content_type = result['授课内容类型'].astype('string').str.strip()

    empty_content_type = content_type.isna() | content_type.eq('')
    tutoring_course = course_name.str.contains(
        '训练|辅导|带练',
        na=False,
        regex=True,
    )
    mock_exam_course = course_name.str.contains('模考', na=False)
    self_study_course = course_name.str.contains('自习', na=False)
    other_content_keyword = course_name.str.contains(
        '自习|训练|辅导|带练|模考|答疑|助教|测评',
        na=False,
        regex=True,
    )

    reason = pd.Series('', index=result.index, dtype='string')
    reason.loc[empty_content_type] = '授课内容类型为空'

    pending = reason.eq('')
    reason.loc[
        pending & tutoring_course & content_type.ne('辅导课').fillna(False)
    ] = '课程名称含“训练/辅导/带练”，授课内容类型应为“辅导课”'

    pending = reason.eq('')
    reason.loc[
        pending & mock_exam_course & content_type.ne('测评课').fillna(False)
    ] = '课程名称含“模考”，授课内容类型应为“测评课”'

    pending = reason.eq('')
    reason.loc[
        pending & self_study_course & content_type.ne('自习课').fillna(False)
    ] = '课程名称含“自习”，授课内容类型应为“自习课”'

    pending = reason.eq('')
    reason.loc[
        pending & content_type.eq('正课').fillna(False) & other_content_keyword
    ] = '授课内容类型为“正课”，课程名称含其他授课内容类型关键词'

    result['授课内容类型异常'] = reason.ne('').astype(int)
    result['授课内容类型异常原因'] = reason
    return result


def check_course_field_completeness(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测班级配课表的课程名称、教室名称和教师是否填写完整。

    以下课次不纳入质检：
      - 分钟数为1
      - 产品体系为“计费体系”
      - 标准部门名称为“国外考试部”，且课程名称含“自习”或“模考”

    其余课次的课程名称、教室名称、教师均不可为空。

    参数:
        df: 需包含列 '分钟数', '产品体系', '标准部门名称',
            '课程名称', '教室名称', '教师'

    返回:
        添加 '课程字段完整性异常'（int，1表示异常，0表示正常）和
        '课程字段完整性异常原因' 列的DataFrame
    """
    result = df.copy()
    minutes = pd.to_numeric(result['分钟数'], errors='coerce')
    product_system = result['产品体系'].astype('string').str.strip()
    department = result['标准部门名称'].astype('string').str.strip()
    course_name = result['课程名称'].astype('string').str.strip()

    exempt = (
        minutes.eq(1)
        | product_system.eq('计费体系').fillna(False)
        | (
            department.eq('国外考试部').fillna(False)
            & course_name.str.contains('自习|模考', na=False, regex=True)
        )
    )

    required_fields = ['课程名称', '教室名称', '教师']
    blank_fields = pd.DataFrame(
        {
            field: (
                result[field].astype('string').str.strip().isna()
                | result[field].astype('string').str.strip().eq('')
            )
            for field in required_fields
        },
        index=result.index,
    )
    missing_reason = blank_fields.apply(
        lambda row: (
            '、'.join(row.index[row].tolist()) + '为空'
            if row.any()
            else ''
        ),
        axis=1,
    ).astype('string')

    abnormal = ~exempt & blank_fields.any(axis=1)
    result['课程字段完整性异常'] = abnormal.astype(int)
    result['课程字段完整性异常原因'] = missing_reason.where(abnormal, '')
    return result


def check_learning_device_teaching_method(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测智慧学习机课次的产品、授课内容类型和教室设置。

    仅“授课方式标识”为“智慧学习机”的课次纳入质检，要求：
      - 常规体系对应产品品类“XXJ”
      - A体系对应名称含“A”的产品品类
      - B体系对应名称含“B”的产品品类
      - 授课内容类型为“答疑课”
      - 教室名称含“网络”

    参数:
        df: 需包含列 '授课方式标识', '产品体系', '产品品类',
            '授课内容类型', '教室名称'

    返回:
        添加 '学习机-授课方式标识异常'（int，1表示异常，0表示正常）和
        '学习机-授课方式标识异常原因' 列的DataFrame
    """
    result = df.copy()
    teaching_method = result['授课方式标识'].astype('string').str.strip()
    product_system = result['产品体系'].astype('string').str.strip()
    product_category = result['产品品类'].astype('string').str.strip()
    content_type = result['授课内容类型'].astype('string').str.strip()
    classroom = result['教室名称'].astype('string').str.strip()

    in_scope = teaching_method.eq('智慧学习机').fillna(False)
    product_matches = (
        (product_system.eq('常规体系') & product_category.eq('XXJ'))
        | (
            product_system.eq('A体系')
            & product_category.str.contains('A', case=False, na=False)
        )
        | (
            product_system.eq('B体系')
            & product_category.str.contains('B', case=False, na=False)
        )
    ).fillna(False)

    issues = pd.DataFrame(
        {
            '产品体系与产品品类不匹配': in_scope & ~product_matches,
            '授课内容类型应为“答疑课”': (
                in_scope & content_type.ne('答疑课').fillna(True)
            ),
            '教室名称应包含“网络”': (
                in_scope & ~classroom.str.contains('网络', na=False)
            ),
        },
        index=result.index,
    )
    reason = issues.apply(
        lambda row: '；'.join(row.index[row].tolist()),
        axis=1,
    ).astype('string')

    result['学习机-授课方式标识异常'] = issues.any(axis=1).astype(int)
    result['学习机-授课方式标识异常原因'] = reason
    return result


def check_first_lesson_start_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测第一次课的上课日期与开课日期是否处于同年同月。

    仅课次为1的记录纳入质检；日期或开课日期为空、格式无法识别，
    或两者不在同年同月时标注异常。

    参数:
        df: 需包含列 '课次', '日期', '开课日期'

    返回:
        添加 '上课日期不早于开课日期当月'（int，1表示异常，0表示正常）和
        '上课日期不早于开课日期当月异常原因' 列的DataFrame
    """
    result = df.copy()
    lesson_number = pd.to_numeric(result['课次'], errors='coerce')
    lesson_date = pd.to_datetime(result['日期'], errors='coerce')
    opening_date = pd.to_datetime(result['开课日期'], errors='coerce')

    in_scope = lesson_number.eq(1)
    valid_dates = lesson_date.notna() & opening_date.notna()
    same_month = (
        lesson_date.dt.year.eq(opening_date.dt.year)
        & lesson_date.dt.month.eq(opening_date.dt.month)
    )
    issues = pd.DataFrame(
        {
            '日期为空或格式错误': in_scope & lesson_date.isna(),
            '开课日期为空或格式错误': in_scope & opening_date.isna(),
            '日期与开课日期不在同年同月': (
                in_scope & valid_dates & ~same_month
            ),
        },
        index=result.index,
    )
    reason = issues.apply(
        lambda row: '；'.join(row.index[row].tolist()),
        axis=1,
    ).astype('string')

    result['上课日期不早于开课日期当月'] = issues.any(axis=1).astype(int)
    result['上课日期不早于开课日期当月异常原因'] = reason
    return result


def build_department_combination_review(df: pd.DataFrame) -> pd.DataFrame:
    """
    汇总班级配课表中的“管理部门名称 × 标准部门名称”组合，供人工核对。

    本规则没有可自动判定的部门对应关系，因此只生成去重后的组合、对应
    课次记录数及人工核对栏，不将待核对组合计入异常统计。

    参数:
        df: 需包含列 '管理部门名称', '标准部门名称'

    返回:
        包含序号、部门组合、课次记录数、核对结论和备注的DataFrame
    """
    department_columns = ['管理部门名称', '标准部门名称']
    working = df[department_columns].copy()
    for column in department_columns:
        values = working[column].astype('string').str.strip().fillna('')
        working[column] = values.replace('', '（空）')

    review = (
        working.groupby(department_columns, dropna=False)
        .size()
        .reset_index(name='课次记录数')
        .sort_values(department_columns, kind='stable')
        .reset_index(drop=True)
    )
    review.insert(0, '序号', range(1, len(review) + 1))
    review['核对结论'] = '待核对'
    review['备注'] = ''
    return review
