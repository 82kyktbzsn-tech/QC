import tempfile
import unittest
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from qc_service import (
    ALL_DEPARTMENTS,
    BUSINESS_CLASS,
    BUSINESS_PREMIUM,
    CLASSINFO_SHEET_NAMES,
    PCLV_RULE_COLUMNS,
    PREMIUM_DEPARTMENT,
    _apply_pclv_standard_department,
    _format_output_workbook,
    add_qc_feedback,
    abnormal_mask,
    classinfo_required_for_selection,
    combine_classinfo_files,
    detect_schedule_type,
    filter_by_standard_department,
    list_available_departments,
    normalize_business_type,
    normalize_department_filter,
    validate_business_selection,
)


class QCServiceTests(unittest.TestCase):
    def test_filters_rows_by_selected_standard_department(self):
        frame = pd.DataFrame({
            '标化部门': ['素养', '素质', None, ''],
            '班级编码': ['A', 'B', 'C', 'D'],
        })

        filtered = filter_by_standard_department(frame, '素养')
        unclassified = filter_by_standard_department(frame, '未标化')
        unfiltered = filter_by_standard_department(frame, ALL_DEPARTMENTS)

        self.assertEqual(filtered['班级编码'].tolist(), ['A'])
        self.assertEqual(unclassified['班级编码'].tolist(), ['C', 'D'])
        self.assertEqual(len(unfiltered), 4)
        self.assertEqual(
            set(list_available_departments(frame)),
            {'素养', '素质', '未标化'},
        )
        self.assertEqual(normalize_department_filter('  素养  '), '素养')
        self.assertEqual(normalize_department_filter(None), ALL_DEPARTMENTS)

    def test_adds_all_row_abnormalities_to_first_column(self):
        frame = pd.DataFrame({
            '规则A': [1, 1, 0],
            '规则B': [0, 1, 0],
            '封班检查': [pd.NA, '0人班未封班', pd.NA],
            '原始字段': ['甲', '乙', '丙'],
        })

        result = add_qc_feedback(
            frame,
            ['规则A', '规则B', '封班检查'],
        )

        self.assertEqual(result.columns[0], '质检结果反馈')
        self.assertEqual(
            result['质检结果反馈'].tolist(),
            ['规则A', '规则A+规则B+0人班未封班', ''],
        )

    def test_formats_feedback_column_as_yellow_red_bold(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = '班级信息质检'
        sheet.append(['质检结果反馈', '班级编码'])
        sheet.append(['规则A+规则B', 'C001'])

        _format_output_workbook(workbook)

        for cell in [sheet['A1'], sheet['A2']]:
            self.assertEqual(cell.fill.fill_type, 'solid')
            self.assertEqual(cell.fill.fgColor.rgb, 'FFFFFF00')
            self.assertEqual(cell.font.color.rgb, 'FFFF0000')
            self.assertTrue(cell.font.bold)

    def test_pclv_uses_standard_department_name_without_mapping(self):
        frame = pd.DataFrame({
            '标准部门名称': ['高中一对一部', '青少部', '素养智学部'],
        })

        result = _apply_pclv_standard_department(frame)

        self.assertEqual(
            result['标化部门'].tolist(),
            ['高中一对一部', '青少部', '素养智学部'],
        )

    def test_business_type_and_schedule_constraints(self):
        self.assertEqual(
            normalize_business_type(None, 'classlesson'),
            BUSINESS_CLASS,
        )
        self.assertEqual(
            normalize_business_type(None, 'pclv'),
            BUSINESS_PREMIUM,
        )
        validate_business_selection(
            BUSINESS_PREMIUM,
            'pclv',
            PREMIUM_DEPARTMENT,
        )
        validate_business_selection(BUSINESS_PREMIUM, 'pclv', '国外考试部')
        validate_business_selection(BUSINESS_CLASS, 'classlesson', '素养')
        self.assertFalse(classinfo_required_for_selection(
            BUSINESS_PREMIUM,
            PREMIUM_DEPARTMENT,
        ))
        self.assertFalse(classinfo_required_for_selection(
            BUSINESS_PREMIUM,
            '国外考试部',
        ))
        self.assertTrue(classinfo_required_for_selection(
            BUSINESS_CLASS,
            '素养',
        ))

        with self.assertRaisesRegex(ValueError, '只能上传 PCLV'):
            validate_business_selection(
                BUSINESS_PREMIUM,
                'classlesson',
                PREMIUM_DEPARTMENT,
            )
        with self.assertRaisesRegex(ValueError, '只能上传班级配课表'):
            validate_business_selection(BUSINESS_CLASS, 'pclv', '素养')
        with self.assertRaisesRegex(ValueError, '请选择“高端业务”'):
            validate_business_selection(
                BUSINESS_CLASS,
                'classlesson',
                PREMIUM_DEPARTMENT,
            )

    def test_pclv_audit_rule_is_included_in_summary_rules(self):
        self.assertIn('配课表审核时效异常', PCLV_RULE_COLUMNS)

    def test_abnormal_mask_supports_numeric_and_text_rules(self):
        frame = pd.DataFrame({
            '规则A': [0, 1, 0],
            '封班检查': [pd.NA, pd.NA, '0人班未封班'],
        })
        mask = abnormal_mask(frame, ['规则A', '封班检查'])
        self.assertEqual(mask.tolist(), [False, True, True])

    def test_detects_schedule_types(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            classlesson = Path(temp_dir) / 'classlesson.xlsx'
            pclv = Path(temp_dir) / 'pclv.xlsx'
            pd.DataFrame(columns=[
                '班级编号', '课次', '日期', '教师打卡状态',
            ]).to_excel(classlesson, index=False)
            pd.DataFrame(columns=[
                '课时包编号', '课次序号', '学员姓名', '教师考勤',
            ]).to_excel(pclv, index=False)
            self.assertEqual(detect_schedule_type(classlesson), 'classlesson')
            self.assertEqual(detect_schedule_type(pclv), 'pclv')

    def test_combines_three_classinfo_csv_files_with_fixed_sheet_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_paths = []
            for index in range(3):
                source_path = Path(temp_dir) / f'source-{index}.csv'
                pd.DataFrame({
                    '标准部门': ['智慧学习部'],
                    '班级编码': [f'C{index}'],
                }).to_csv(source_path, index=False, encoding='utf-8-sig')
                source_paths.append(source_path)
            output_path = Path(temp_dir) / 'combined.xlsx'
            combine_classinfo_files(source_paths, output_path)

            with pd.ExcelFile(output_path) as workbook:
                self.assertEqual(workbook.sheet_names, CLASSINFO_SHEET_NAMES)
            self.assertEqual(
                [pd.read_excel(output_path, sheet_name=name).iloc[0]['班级编码']
                 for name in CLASSINFO_SHEET_NAMES],
                ['C0', 'C1', 'C2'],
            )


if __name__ == '__main__':
    unittest.main()
