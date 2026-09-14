# main.py
from data_loader import merge_and_deduplicate_excel
from labeling import apply_standard_department
from qc import (
    check_audit_status,
    check_actual_start_month,
    check_attendance_card_setting,
    check_cancelled_class_status,
    check_class_and_actual_duration,
    check_class_closure,
    check_class_format_and_delivery,
    check_class_location_and_room,
    check_class_price,
    check_class_setup_date,
    check_class_type,
    check_external_class_time,
    check_learning_device_online_settings,
    check_management_project_class_name,
    check_minimum_and_opening_students,
    check_minimum_payroll_department,
    check_quarter_start_date,
    check_renewal_type,
    check_textbook_distribution,
    check_teacher_and_related_class,
)

def main():
    # 第一步：合并去重（生成“数据分类”列）
    df_clean = merge_and_deduplicate_excel(
        input_file="data/classinfo.xlsx",
        output_file="output/step1_result.xlsx"
    )

    # 第二步：打标化部门标签（标化部门放第二列）
    df_labeled = apply_standard_department(df_clean)

    # 第三步：续班类型异常检测（添加“续班类型异常”列）
    df_checked = check_renewal_type(df_labeled)

    # 第四步：班级标价规范检测（添加“班级标价规范”列）
    df_checked = check_class_price(df_checked)

    # 第五步：主带课教师、关联班号检测
    df_checked = check_teacher_and_related_class(df_checked)

    # 第六步：班级审核状态检测
    df_checked = check_audit_status(df_checked)

    # 第七步：季度与开课日期匹配检测
    df_checked = check_quarter_start_date(df_checked)

    # 第八步：上课形式、授课方式、授课渠道组合检测
    df_checked = check_class_format_and_delivery(df_checked)

    # 第九步：取消班状态、班级名称、最大人数检测
    df_checked = check_cancelled_class_status(df_checked)

    # 第十步：设班日期与开课日期先后顺序检测
    df_checked = check_class_setup_date(df_checked)

    # 第十一步：实际开课日期与开课日期年月一致性检测
    df_checked = check_actual_start_month(df_checked)

    # 第十二步：上课时间(外)填写检测
    df_checked = check_external_class_time(df_checked)

    # 第十三步：教材发放形式填写检测
    df_checked = check_textbook_distribution(df_checked)

    # 第十四步：封班条件检测
    df_checked = check_class_closure(df_checked)

    # 第十五步：最小发薪部门填写检测
    df_checked = check_minimum_payroll_department(df_checked)

    # 第十六步：班级时长、实际时长检测
    df_checked = check_class_and_actual_duration(df_checked)

    # 第十七步：上课地点、上课教室填写检测
    df_checked = check_class_location_and_room(df_checked)

    # 第十八步：一卡通考勤方式检测
    df_checked = check_attendance_card_setting(df_checked)

    # 第十九步：学习机线上班级设置检测
    df_checked = check_learning_device_online_settings(df_checked)

    # 第二十步：开班人数、保底人数检测
    df_checked = check_minimum_and_opening_students(df_checked)

    # 第二十一步：班级类型检测
    df_checked = check_class_type(df_checked)

    # 第二十二步：管理项目与班级名称匹配检测
    df_checked = check_management_project_class_name(df_checked)

    # 统计异常数量
    renewal_abnormal_count = df_checked['续班类型异常'].sum()
    class_price_abnormal_count = df_checked['班级标价规范'].sum()
    teacher_abnormal_count = df_checked['未设置主带课教师'].sum()
    related_class_abnormal_count = df_checked['关联班号异常'].sum()
    audit_status_abnormal_count = df_checked['审核状态异常'].sum()
    quarter_start_date_abnormal_count = df_checked['季度与开课日期不符'].sum()
    class_format_delivery_abnormal_count = (
        df_checked['上课形式&授课方式&授课渠道异常'].sum()
    )
    cancelled_class_status_abnormal_count = df_checked['取消班状态异常'].sum()
    class_setup_date_abnormal_count = df_checked['设班时间晚于开课时间'].sum()
    actual_start_month_abnormal_count = (
        df_checked['实际开课日期不早于开课日期当月'].sum()
    )
    external_class_time_abnormal_count = df_checked['上课时间（外）未填写'].sum()
    textbook_distribution_abnormal_count = (
        df_checked['教材发放形式填写错误'].sum()
    )
    zero_student_unclosed_count = (
        df_checked['封班检查'] == '0人班未封班'
    ).sum()
    billing_class_count_duration_abnormal_count = (
        df_checked['封班检查'] == '计费体系不为1次课1分钟（需确认）'
    ).sum()
    minimum_payroll_department_abnormal_count = (
        df_checked['最小发薪部门为空'].sum()
    )
    class_actual_duration_abnormal_count = (
        df_checked['班级时长&实际时长异常'].sum()
    )
    class_location_room_abnormal_count = (
        df_checked['未设置上课地点/上课教室'].sum()
    )
    attendance_card_setting_abnormal_count = df_checked['一卡通设置错误'].sum()
    learning_device_online_settings_abnormal_count = (
        df_checked['学习机线上班级设置规范'].sum()
    )
    minimum_opening_students_abnormal_count = df_checked['开班保底人数'].sum()
    class_type_abnormal_count = df_checked['班级类型错误'].sum()
    management_project_class_name_abnormal_count = (
        df_checked['疑似非本管理项目下班级'].sum()
    )
    print(f"续班类型异常行数：{renewal_abnormal_count} 行")
    print(f"班级标价规范异常行数：{class_price_abnormal_count} 行")
    print(f"未设置主带课教师行数：{teacher_abnormal_count} 行")
    print(f"关联班号异常行数：{related_class_abnormal_count} 行")
    print(f"审核状态异常行数：{audit_status_abnormal_count} 行")
    print(f"季度与开课日期不符行数：{quarter_start_date_abnormal_count} 行")
    print(
        "上课形式&授课方式&授课渠道异常行数："
        f"{class_format_delivery_abnormal_count} 行"
    )
    print(f"取消班状态异常行数：{cancelled_class_status_abnormal_count} 行")
    print(f"设班时间晚于开课时间行数：{class_setup_date_abnormal_count} 行")
    print(
        "实际开课日期不早于开课日期当月行数："
        f"{actual_start_month_abnormal_count} 行"
    )
    print(f"上课时间（外）未填写行数：{external_class_time_abnormal_count} 行")
    print(f"教材发放形式填写错误行数：{textbook_distribution_abnormal_count} 行")
    print(f"0人班未封班行数：{zero_student_unclosed_count} 行")
    print(
        "计费体系不为1次课1分钟（需确认）行数："
        f"{billing_class_count_duration_abnormal_count} 行"
    )
    print(
        "最小发薪部门为空行数："
        f"{minimum_payroll_department_abnormal_count} 行"
    )
    print(
        "班级时长&实际时长异常行数："
        f"{class_actual_duration_abnormal_count} 行"
    )
    print(
        "未设置上课地点/上课教室行数："
        f"{class_location_room_abnormal_count} 行"
    )
    print(f"一卡通设置错误行数：{attendance_card_setting_abnormal_count} 行")
    print(
        "学习机线上班级设置规范异常行数："
        f"{learning_device_online_settings_abnormal_count} 行"
    )
    print(f"开班保底人数异常行数：{minimum_opening_students_abnormal_count} 行")
    print(f"班级类型错误行数：{class_type_abnormal_count} 行")
    print(
        "疑似非本管理项目下班级行数："
        f"{management_project_class_name_abnormal_count} 行"
    )

    # 保存最终结果
    output_path = "output/final_result.xlsx"
    df_checked.to_excel(output_path, index=False)
    print(f"质检完成，结果已保存至 {output_path}")

if __name__ == "__main__":
    main()
