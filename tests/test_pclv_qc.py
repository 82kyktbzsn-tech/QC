import unittest

import pandas as pd

from pclv_qc import (
    build_department_combination_review,
    check_abnormal_attendance,
    check_abnormal_schedule_time,
    check_schedule_audit_status,
)


class AbnormalScheduleTimeTests(unittest.TestCase):
    def test_parses_time_range_and_checks_six_to_twenty_two_boundaries(self):
        frame = pd.DataFrame({
            '课次时间': [
                '2026-08-01 06:00-22:00',
                '2026-08-01 05:59-20:00',
                '2026-08-01 08:00-22:01',
                '2026-08-01 05:30-23:00',
                '2026/08/01 8:00 ~ 10:00',
                '2026-08-01 08:00—10:00',
                None,
                '无法识别',
            ],
        })

        result = check_abnormal_schedule_time(frame)

        self.assertEqual(
            result['课次开始时间'].tolist(),
            ['06:00', '05:59', '08:00', '05:30', '08:00', '08:00', '', ''],
        )
        self.assertEqual(
            result['课次结束时间'].tolist(),
            ['22:00', '20:00', '22:01', '23:00', '10:00', '10:00', '', ''],
        )
        self.assertEqual(
            result['异常时间排课'].tolist(),
            [0, 1, 1, 1, 0, 0, 1, 1],
        )
        self.assertEqual(
            result['异常时间排课原因'].tolist(),
            [
                '',
                '开始时间早于06:00',
                '结束时间晚于22:00',
                '开始时间早于06:00；结束时间晚于22:00',
                '',
                '',
                '课次时间为空或格式错误',
                '课次时间为空或格式错误',
            ],
        )


class AbnormalAttendanceTests(unittest.TestCase):
    def test_marks_only_empty_and_not_checked_attendance_as_abnormal(self):
        frame = pd.DataFrame({
            '学员考勤': [None, '', '   ', '未打卡', ' 未打卡 ', '打卡', '已补录', '已点名'],
            '教师考勤': ['打卡', '未打卡', None, '', '已补录', '打卡(迟1分钟)', '已点名', '   '],
        })

        result = check_abnormal_attendance(frame)

        self.assertEqual(
            result['学员考勤异常'].tolist(),
            [1, 1, 1, 1, 1, 0, 0, 0],
        )
        self.assertEqual(
            result['教师考勤异常'].tolist(),
            [0, 1, 1, 1, 0, 0, 0, 1],
        )
        self.assertEqual(
            result['学员考勤异常原因'].tolist(),
            [
                '学员考勤为空',
                '学员考勤为空',
                '学员考勤为空',
                '学员考勤为“未打卡”',
                '学员考勤为“未打卡”',
                '',
                '',
                '',
            ],
        )
        self.assertEqual(
            result['教师考勤异常原因'].tolist(),
            [
                '',
                '教师考勤为“未打卡”',
                '教师考勤为空',
                '教师考勤为空',
                '',
                '',
                '',
                '教师考勤为空',
            ],
        )


class ScheduleAuditStatusTests(unittest.TestCase):
    def test_only_approved_status_is_valid(self):
        frame = pd.DataFrame({
            '审核状态': ['已审核', ' 已审核 ', '未审核', '审核中', '', '   ', None],
        })

        result = check_schedule_audit_status(frame)

        self.assertEqual(
            result['配课表审核时效异常'].tolist(),
            [0, 0, 1, 1, 1, 1, 1],
        )
        self.assertEqual(
            result['配课表审核时效异常原因'].tolist(),
            [
                '',
                '',
                '审核状态应为“已审核”',
                '审核状态应为“已审核”',
                '审核状态为空',
                '审核状态为空',
                '审核状态为空',
            ],
        )


class DepartmentCombinationReviewTests(unittest.TestCase):
    def test_builds_unique_high_end_department_combinations(self):
        frame = pd.DataFrame({
            '管理部门': ['长沙新东方学校高中部', ' 长沙新东方学校高中部 ', None, ''],
            '标准部门名称': ['高中一对一部', '高中一对一部', '素养智学部', '高中一对一部'],
        })

        result = build_department_combination_review(frame)

        self.assertEqual(
            result.to_dict('records'),
            [
                {
                    '序号': 1,
                    '管理部门': '长沙新东方学校高中部',
                    '标准部门名称': '高中一对一部',
                    '课次记录数': 2,
                    '核对结论': '待核对',
                    '备注': '',
                },
                {
                    '序号': 2,
                    '管理部门': '（空）',
                    '标准部门名称': '素养智学部',
                    '课次记录数': 1,
                    '核对结论': '待核对',
                    '备注': '',
                },
                {
                    '序号': 3,
                    '管理部门': '（空）',
                    '标准部门名称': '高中一对一部',
                    '课次记录数': 1,
                    '核对结论': '待核对',
                    '备注': '',
                },
            ],
        )


if __name__ == '__main__':
    unittest.main()
