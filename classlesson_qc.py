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
