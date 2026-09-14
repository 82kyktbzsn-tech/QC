import unittest

import pandas as pd

from classlesson_qc import (
    build_department_combination_review,
    check_course_field_completeness,
    check_first_lesson_start_month,
    check_learning_device_teaching_method,
    check_lesson_content_type,
    check_schedule_audit_status,
)


class ScheduleAuditStatusTests(unittest.TestCase):
    def test_only_approved_status_is_valid(self):
        frame = pd.DataFrame({
            '审核状态': ['已审核', ' 已审核 ', '未审核', '', None, '审核中'],
        })

        result = check_schedule_audit_status(frame)

        self.assertEqual(
            result['配课表审核时效异常'].tolist(),
            [0, 0, 1, 1, 1, 1],
        )


class DepartmentCombinationReviewTests(unittest.TestCase):
    def test_builds_unique_combinations_with_counts_and_review_columns(self):
        frame = pd.DataFrame({
            '管理部门名称': ['高中班级部', ' 高中班级部 ', '北美项目部', None],
            '标准部门名称': ['高中班级部', '高中班级部', '国外考试部', ''],
        })

        result = build_department_combination_review(frame)

        self.assertEqual(
            result.to_dict('records'),
            [
                {
                    '序号': 1,
                    '管理部门名称': '北美项目部',
                    '标准部门名称': '国外考试部',
                    '课次记录数': 1,
                    '核对结论': '待核对',
                    '备注': '',
                },
                {
                    '序号': 2,
                    '管理部门名称': '高中班级部',
                    '标准部门名称': '高中班级部',
                    '课次记录数': 2,
                    '核对结论': '待核对',
                    '备注': '',
                },
                {
                    '序号': 3,
                    '管理部门名称': '（空）',
                    '标准部门名称': '（空）',
                    '课次记录数': 1,
                    '核对结论': '待核对',
                    '备注': '',
                },
            ],
        )


class LessonContentTypeTests(unittest.TestCase):
    def test_checks_content_type_in_required_priority_order(self):
        frame = pd.DataFrame({
            '课程名称': [
                '英语辅导课',
                '口语带练模考',
                '雅思模考',
                '晚间自习',
                '数学答疑',
                '物理助教课',
                '阶段测评',
                '数学正课',
                '英语训练课',
                '雅思模考',
                '晚间自习',
            ],
            '授课内容类型': [
                None,
                '测评课',
                '正课',
                '辅导课',
                '正课',
                '正课',
                '正课',
                '正课',
                '辅导课',
                '测评课',
                '自习课',
            ],
        })

        result = check_lesson_content_type(frame)

        self.assertEqual(
            result['授课内容类型异常'].tolist(),
            [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
        )
        self.assertEqual(
            result['授课内容类型异常原因'].tolist(),
            [
                '授课内容类型为空',
                '课程名称含“训练/辅导/带练”，授课内容类型应为“辅导课”',
                '课程名称含“模考”，授课内容类型应为“测评课”',
                '课程名称含“自习”，授课内容类型应为“自习课”',
                '授课内容类型为“正课”，课程名称含其他授课内容类型关键词',
                '授课内容类型为“正课”，课程名称含其他授课内容类型关键词',
                '授课内容类型为“正课”，课程名称含其他授课内容类型关键词',
                '',
                '',
                '',
                '',
            ],
        )


class CourseFieldCompletenessTests(unittest.TestCase):
    def test_requires_all_fields_outside_exemptions(self):
        frame = pd.DataFrame({
            '分钟数': [60, 1, '1', 60, 60, 60, 60, 60, 60, 60],
            '产品体系': [
                '常规体系',
                '常规体系',
                '常规体系',
                ' 计费体系 ',
                '常规体系',
                '常规体系',
                '常规体系',
                '常规体系',
                '常规体系',
                '常规体系',
            ],
            '标准部门名称': [
                '高中班级部',
                '高中班级部',
                '高中班级部',
                '高中班级部',
                '国外考试部',
                '国外考试部',
                '国外考试部',
                '高中班级部',
                '高中班级部',
                '高中班级部',
            ],
            '课程名称': [
                '数学正课',
                '',
                '',
                '',
                '雅思自习课',
                '雅思模考',
                '雅思正课',
                '',
                '物理正课',
                '',
            ],
            '教室名称': [
                '101教室',
                '',
                '',
                '',
                '',
                '',
                '网络教室',
                '102教室',
                '   ',
                '',
            ],
            '教师': [
                '张老师',
                '',
                '',
                '',
                '',
                '',
                None,
                '李老师',
                '王老师',
                None,
            ],
        })

        result = check_course_field_completeness(frame)

        self.assertEqual(
            result['课程字段完整性异常'].tolist(),
            [0, 0, 0, 0, 0, 0, 1, 1, 1, 1],
        )
        self.assertEqual(
            result['课程字段完整性异常原因'].tolist(),
            [
                '',
                '',
                '',
                '',
                '',
                '',
                '教师为空',
                '课程名称为空',
                '教室名称为空',
                '课程名称、教室名称、教师为空',
            ],
        )


class LearningDeviceTeachingMethodTests(unittest.TestCase):
    def test_checks_product_mapping_content_type_and_network_classroom(self):
        frame = pd.DataFrame({
            '授课方式标识': [
                '普通课',
                '智慧学习机',
                ' 智慧学习机 ',
                '智慧学习机',
                '智慧学习机',
                '智慧学习机',
                '智慧学习机',
                '智慧学习机',
                '智慧学习机',
            ],
            '产品体系': [
                '未知体系',
                '常规体系',
                'A体系',
                'B体系',
                'A体系',
                '常规体系',
                '未知体系',
                'A体系',
                'B体系',
            ],
            '产品品类': [
                '',
                'XXJ',
                'A2',
                'B1',
                'B1',
                'A1',
                'XXJ',
                'a1',
                'B2',
            ],
            '授课内容类型': [
                '',
                '答疑课',
                '答疑课',
                '答疑课',
                '答疑课',
                '答疑课',
                '答疑课',
                '正课',
                None,
            ],
            '教室名称': [
                '',
                '网络教室',
                'A校区网络教室',
                '网络教室1',
                '网络教室',
                '网络教室',
                '网络教室',
                '普通教室',
                '',
            ],
        })

        result = check_learning_device_teaching_method(frame)

        self.assertEqual(
            result['学习机-授课方式标识异常'].tolist(),
            [0, 0, 0, 0, 1, 1, 1, 1, 1],
        )
        self.assertEqual(
            result['学习机-授课方式标识异常原因'].tolist(),
            [
                '',
                '',
                '',
                '',
                '产品体系与产品品类不匹配',
                '产品体系与产品品类不匹配',
                '产品体系与产品品类不匹配',
                '授课内容类型应为“答疑课”；教室名称应包含“网络”',
                '授课内容类型应为“答疑课”；教室名称应包含“网络”',
            ],
        )


class FirstLessonStartMonthTests(unittest.TestCase):
    def test_only_checks_first_lesson_and_compares_year_and_month(self):
        frame = pd.DataFrame({
            '课次': [2, 1, '1', 1, 1, 1, 1, 1],
            '日期': [
                '2026-09-01',
                '2026-08-31',
                '2026-08-01',
                '2026-09-01',
                '2027-08-01',
                None,
                '2026-08-01',
                '不是日期',
            ],
            '开课日期': [
                '2026-08-01',
                '2026-08-01',
                '2026-08-31',
                '2026-08-01',
                '2026-08-01',
                '2026-08-01',
                None,
                '无效日期',
            ],
        })

        result = check_first_lesson_start_month(frame)

        self.assertEqual(
            result['上课日期不早于开课日期当月'].tolist(),
            [0, 0, 0, 1, 1, 1, 1, 1],
        )
        self.assertEqual(
            result['上课日期不早于开课日期当月异常原因'].tolist(),
            [
                '',
                '',
                '',
                '日期与开课日期不在同年同月',
                '日期与开课日期不在同年同月',
                '日期为空或格式错误',
                '开课日期为空或格式错误',
                '日期为空或格式错误；开课日期为空或格式错误',
            ],
        )


if __name__ == '__main__':
    unittest.main()
