import unittest

import pandas as pd

from labeling import (
    apply_classlesson_standard_department,
    apply_standard_department,
)


class StandardDepartmentFallbackTests(unittest.TestCase):
    def test_classinfo_uses_original_department_as_fallback(self):
        frame = pd.DataFrame({
            '数据分类': ['本月设班'] * 4,
            '标准部门': ['青少部', '高中一对一部', '素养智学部', None],
            '科目(原)': ['围棋', '英语', '编程', '英语'],
            '校区名称': ['', '', '', ''],
        })

        result = apply_standard_department(frame)

        self.assertEqual(
            result['标化部门'].tolist(),
            ['青少部', '高中一对一部', '素质', ''],
        )

    def test_classlesson_uses_fallback_but_keeps_innovation_override(self):
        frame = pd.DataFrame({
            '标准部门名称': ['青少部', '青少部', '素养智学部'],
            '科目名称': ['围棋', '围棋', '编程'],
            '教学区名称': ['', '长沙教学区', ''],
        })

        result = apply_classlesson_standard_department(frame)

        self.assertEqual(
            result['标化部门'].tolist(),
            ['青少部', '创新', '素质'],
        )


if __name__ == '__main__':
    unittest.main()
