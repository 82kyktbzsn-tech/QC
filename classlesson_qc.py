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
