import unittest

import pandas as pd

from qc import (
    check_class_closure,
    check_class_price,
    check_learning_device_online_settings,
    check_management_project_class_name,
    check_renewal_type,
    check_teacher_and_related_class,
)


class ClassPriceTests(unittest.TestCase):
    def test_marks_empty_and_zero_prices_as_abnormal(self):
        frame = pd.DataFrame({
            '班级标价': [None, '', '   ', 0, '0', 100, '100.50'],
        })

        result = check_class_price(frame)

        self.assertEqual(
            result['班级标价规范'].tolist(),
            [1, 1, 1, 1, 1, 0, 0],
        )


class ClassClosureTests(unittest.TestCase):
    def test_uses_selected_qc_month_for_zero_student_classes(self):
        frame = pd.DataFrame({
            '产品体系': ['常规体系', '常规体系', '常规体系', '计费体系'],
            '实际开课日期': ['2026-08-31', '2026-09-01', '2026-07-01', None],
            '实际结课日期': ['2026-08-01', '2026-09-30', '2026-07-31', None],
            '当前人数(占名额)': [0, 0, 0, 1],
            '班级课次数': [10, 10, 10, 2],
            '班级时长': [20, 20, 20, 1],
        })

        august_result = check_class_closure(frame, qc_month='2026-08')
        september_result = check_class_closure(frame, qc_month='2026-09')

        self.assertEqual(
            august_result['封班检查'].fillna('').tolist(),
            ['0人班未封班', '', '', '计费体系不为1次课1分钟（需确认）'],
        )
        self.assertEqual(
            september_result['封班检查'].fillna('').tolist(),
            ['', '0人班未封班', '', '计费体系不为1次课1分钟（需确认）'],
        )

    def test_rejects_invalid_qc_month(self):
        frame = pd.DataFrame({
            '产品体系': ['常规体系'],
            '实际开课日期': ['2026-08-01'],
            '实际结课日期': ['2026-08-31'],
            '当前人数(占名额)': [0],
            '班级课次数': [1],
            '班级时长': [1],
        })

        with self.assertRaisesRegex(ValueError, '质检月份格式不正确'):
            check_class_closure(frame, qc_month='2026-13')


class TeacherAndRelatedClassTests(unittest.TestCase):
    def test_teacher_check_uses_selected_month_end_and_new_column_name(self):
        frame = pd.DataFrame({
            '标准部门': ['智慧学习部'] * 4,
            '主带课老师': ['', '', '已设置教师', ''],
            '班级状态': ['正常班', '正常班', '正常班', '取消班'],
            '开课日期': [
                '2026-08-31',
                '2026-09-01',
                '2026-08-15',
                '2026-08-01',
            ],
            '产品体系': ['常规体系'] * 4,
            '关联班号': ['A001'] * 4,
            '季度': ['秋'] * 4,
        })

        august_result = check_teacher_and_related_class(
            frame,
            qc_month='2026-08',
        )
        september_result = check_teacher_and_related_class(
            frame,
            qc_month='2026-09',
        )

        self.assertNotIn('主带课教师异常', august_result.columns)
        self.assertEqual(
            august_result['未设置主带课教师'].tolist(),
            [1, 0, 0, 0],
        )
        self.assertEqual(
            september_result['未设置主带课教师'].tolist(),
            [1, 1, 0, 0],
        )


class ManagementProjectClassNameTests(unittest.TestCase):
    def test_excludes_foreign_examination_department_and_cancelled_class(self):
        frame = pd.DataFrame({
            '标准部门': ['国外考试部', '高中班级部', '高中班级部'],
            '班级状态': ['正常班', '正常班', '取消班'],
            '管理项目': ['高中班级', '高中班级', '高中班级'],
            '科目(外)': ['机器人', '机器人', '机器人'],
        })

        result = check_management_project_class_name(frame)

        self.assertEqual(
            result['疑似非本管理项目下班级'].tolist(),
            [0, 1, 0],
        )


class LearningDeviceOnlineSettingsTests(unittest.TestCase):
    def test_requires_network_campus_and_classroom_except_valid_cancelled_class(self):
        frame = pd.DataFrame({
            '管理项目': ['学习机线上'] * 4 + ['高中班级'],
            '产品体系': ['常规体系'] * 5,
            '产品品类': ['XXJ'] * 5,
            '上课形式': ['在线', '在线', '', '在线', ''],
            '授课方式': ['在线录播', '在线录播', '', '在线录播', ''],
            '授课渠道': ['智慧学习机', '智慧学习机', '', '智慧学习机', ''],
            '考勤方式': ['班级刷卡', '班级刷卡', '', '班级刷卡', ''],
            '上课教室': ['', '网络教室', '', '', ''],
            '校区名称': ['', '网络教学区', '', '', ''],
            '班级状态': ['正常班', '正常班', '取消班', '取消班', '正常班'],
            '班级名称（内）': ['学习机班', '学习机班', '取消学习机班', '取消学习机班', '普通班'],
            '班级名称（外）': ['学习机班', '学习机班', '学习机班取消', '学习机班', '普通班'],
        })

        result = check_learning_device_online_settings(frame)

        self.assertEqual(
            result['学习机线上班级设置规范'].tolist(),
            [1, 0, 0, 1, 0],
        )


class RenewalTypeTests(unittest.TestCase):
    def test_only_checks_classes_set_up_on_or_after_cutoff(self):
        frame = pd.DataFrame({
            '标准部门': ['高中班级部', '高中班级部'],
            '班级状态': ['正常班', '正常班'],
            '产品体系': ['常规体系', '常规体系'],
            '续班类型': ['不可续', '不可续'],
            '年级(原)': ['高一', '高一'],
            '季度': ['秋', '秋'],
            '设班日期': ['2026-07-31', '2026-08-01'],
        })

        result = check_renewal_type(frame)

        self.assertEqual(result['续班类型异常'].tolist(), [0, 1])

    def test_classifies_product_systems_by_keyword(self):
        frame = pd.DataFrame({
            '标准部门': ['高中班级部'] * 6,
            '班级状态': ['正常班'] * 6,
            '产品体系': [
                'C体系',
                '创新产品体系',
                '长沙专项体系',
                '专项课程体系',
                '月度计费体系',
                '计费专项体系',
            ],
            '续班类型': ['可续', '不可续', '不可续', '可续', '可续', '可续'],
            '年级(原)': ['高一'] * 6,
            '季度': ['秋'] * 6,
            '设班日期': ['2026-08-01'] * 6,
        })

        result = check_renewal_type(frame)

        self.assertEqual(result['续班类型异常'].tolist(), [0, 1, 0, 1, 0, 0])

    def test_keeps_existing_exclusions_and_exit_grade_rule(self):
        frame = pd.DataFrame({
            '标准部门': ['国外考试部', '高中班级部', '高中班级部', '高中班级部'],
            '班级状态': ['正常班', '取消班', '正常班', '正常班'],
            '产品体系': ['常规体系', '常规体系', '常规体系', '计费体系'],
            '续班类型': ['不可续', '不可续', '可续', ''],
            '年级(原)': ['高一', '高一', '高三', '高三'],
            '季度': ['秋', '秋', '春', '春'],
            '设班日期': ['2026-08-01'] * 4,
        })

        result = check_renewal_type(frame)

        self.assertEqual(result['续班类型异常'].tolist(), [0, 0, 1, 0])


if __name__ == '__main__':
    unittest.main()
