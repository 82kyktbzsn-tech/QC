import pandas as pd


def check_abnormal_schedule_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    解析并检测高端配课表的课次时间是否超出正常排课范围。

    规则：
      - 从“课次时间”中解析开始时间和结束时间
      - 开始时间早于06:00，或结束时间晚于22:00：标注1
      - 课次时间为空或无法解析：标注1
      - 其他情况：标注0

    参数:
        df: 需包含列 '课次时间'

    返回:
        添加 '课次开始时间'、'课次结束时间'、'异常时间排课' 和
        '异常时间排课原因' 列的DataFrame
    """
    result = df.copy()
    schedule_time = result['课次时间'].astype('string').str.strip()
    extracted = schedule_time.str.extract(
        r'(?P<start>\d{1,2}:\d{2})\s*[-—–~至]\s*'
        r'(?P<end>\d{1,2}:\d{2})',
    )

    start_text = extracted['start'].astype('string')
    end_text = extracted['end'].astype('string')
    start_time = pd.to_datetime(start_text, format='%H:%M', errors='coerce')
    end_time = pd.to_datetime(end_text, format='%H:%M', errors='coerce')
    valid_time = start_time.notna() & end_time.notna()

    start_minutes = start_time.dt.hour * 60 + start_time.dt.minute
    end_minutes = end_time.dt.hour * 60 + end_time.dt.minute
    issues = pd.DataFrame(
        {
            '课次时间为空或格式错误': ~valid_time,
            '开始时间早于06:00': valid_time & start_minutes.lt(6 * 60),
            '结束时间晚于22:00': valid_time & end_minutes.gt(22 * 60),
        },
        index=result.index,
    )
    reason = issues.apply(
        lambda row: '；'.join(row.index[row].tolist()),
        axis=1,
    ).astype('string')

    result['课次开始时间'] = start_time.dt.strftime('%H:%M').fillna('')
    result['课次结束时间'] = end_time.dt.strftime('%H:%M').fillna('')
    result['异常时间排课'] = issues.any(axis=1).astype(int)
    result['异常时间排课原因'] = reason
    return result


def check_abnormal_attendance(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测高端配课表的学员考勤和教师考勤是否异常。

    规则：
      - 学员考勤为空或为“未打卡”：“学员考勤异常”标注1
      - 教师考勤为空或为“未打卡”：“教师考勤异常”标注1
      - 其他考勤状态标注0

    参数:
        df: 需包含列 '学员考勤', '教师考勤'

    返回:
        添加学员、教师考勤异常标记及对应异常原因列的DataFrame
    """
    result = df.copy()
    student_attendance = result['学员考勤'].astype('string').str.strip()
    teacher_attendance = result['教师考勤'].astype('string').str.strip()

    student_empty = student_attendance.isna() | student_attendance.eq('')
    teacher_empty = teacher_attendance.isna() | teacher_attendance.eq('')
    student_not_checked = student_attendance.eq('未打卡').fillna(False)
    teacher_not_checked = teacher_attendance.eq('未打卡').fillna(False)

    result['学员考勤异常'] = (student_empty | student_not_checked).astype(int)
    result['教师考勤异常'] = (teacher_empty | teacher_not_checked).astype(int)
    result['学员考勤异常原因'] = ''
    result.loc[student_empty, '学员考勤异常原因'] = '学员考勤为空'
    result.loc[student_not_checked, '学员考勤异常原因'] = '学员考勤为“未打卡”'
    result['教师考勤异常原因'] = ''
    result.loc[teacher_empty, '教师考勤异常原因'] = '教师考勤为空'
    result.loc[teacher_not_checked, '教师考勤异常原因'] = '教师考勤为“未打卡”'
    return result


def check_schedule_audit_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测高端配课表是否已完成审核。

    所有记录均纳入质检；审核状态只有等于“已审核”时正常，
    为空或其他状态时均标注异常。

    参数:
        df: 需包含列 '审核状态'

    返回:
        添加 '配课表审核时效异常' 和 '配课表审核时效异常原因' 列的DataFrame
    """
    result = df.copy()
    audit_status = result['审核状态'].astype('string').str.strip()
    empty_status = audit_status.isna() | audit_status.eq('')
    abnormal = audit_status.ne('已审核').fillna(True)

    reason = pd.Series('', index=result.index, dtype='string')
    reason.loc[empty_status] = '审核状态为空'
    reason.loc[abnormal & ~empty_status] = '审核状态应为“已审核”'

    result['配课表审核时效异常'] = abnormal.astype(int)
    result['配课表审核时效异常原因'] = reason
    return result


def build_department_combination_review(df: pd.DataFrame) -> pd.DataFrame:
    """
    汇总高端配课表中的“管理部门 × 标准部门名称”组合，供人工核对。

    本规则没有可自动判定的部门对应关系，因此只生成去重后的组合、对应
    课次记录数及人工核对栏，不将待核对组合计入异常统计。

    参数:
        df: 需包含列 '管理部门', '标准部门名称'

    返回:
        包含序号、部门组合、课次记录数、核对结论和备注的DataFrame
    """
    department_columns = ['管理部门', '标准部门名称']
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
