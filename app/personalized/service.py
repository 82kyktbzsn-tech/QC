"""上传任务到既有质检编排层的适配服务。"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional

from qc_service import (
    BUSINESS_CLASS,
    BUSINESS_PREMIUM,
    classinfo_required_for_selection,
    combine_classinfo_files,
    detect_schedule_type,
    run_qc_job,
    validate_business_selection,
)

from .constants import TOOL_SLUG
from .store import JobStore, StoredJob


class UploadedQCService:
    """只负责请求输入、任务文件和旧质检服务之间的数据流。"""

    SCHEDULE_FIELD = 'schedule'
    CLASSINFO_FIELDS = (
        ('classinfo_opening', '本月&次月开课'),
        ('classinfo_setup', '本月设班'),
        ('classinfo_closing', '本月结课'),
    )
    ALLOWED_SCHEDULE_EXTENSIONS = {'.xlsx', '.xls'}
    ALLOWED_CLASSINFO_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

    def __init__(self, store: JobStore, max_upload_bytes: int = 80 * 1024 * 1024):
        self.store = store
        self.max_upload_bytes = max_upload_bytes

    def run(self, files: Mapping, form: Mapping, user_id: Optional[int]) -> dict:
        business_type = self._required(form, 'business_type')
        qc_month = self._required(form, 'qc_month')
        department = self._required(form, 'standard_department')
        if business_type not in {BUSINESS_CLASS, BUSINESS_PREMIUM}:
            raise ValueError('请选择负责的业务类型。')

        schedule_item = files.get(self.SCHEDULE_FIELD)
        if schedule_item is None or not schedule_item.filename:
            raise ValueError('请上传配课表 classlesson 或 pclv。')

        job = self.store.create_job({
            'business_type': business_type,
            'business_label': '班课业务' if business_type == BUSINESS_CLASS else '高端业务',
            'qc_month': qc_month,
            'selected_department': department,
            'schedule_type': 'pending',
            'classinfo_mode': 'pending',
            'created_by': user_id,
        })
        input_dir = self.store.job_directory(job.id) / 'input'
        try:
            schedule_path = self._save_upload(
                schedule_item,
                input_dir / 'schedule',
                self.ALLOWED_SCHEDULE_EXTENSIONS,
            )
            schedule_type = detect_schedule_type(schedule_path)
            validate_business_selection(business_type, schedule_type, department)

            classinfo_path = None
            classinfo_mode = 'not_required'
            if classinfo_required_for_selection(business_type):
                classinfo_path, classinfo_mode = self._prepare_classinfo(files, input_dir)

            output_path = self.store.job_directory(job.id) / '教务质检结果.xlsx'
            result = run_qc_job(
                classinfo_path,
                schedule_path,
                output_path,
                qc_month=qc_month,
                business_type=business_type,
                standard_department=department,
            )
            result.update({
                'job_id': job.id,
                'classinfo_mode': classinfo_mode,
                'status': 'completed',
                'ok': True,
                'download_url': (
                    f'/personalized/{TOOL_SLUG}/api/jobs/{job.id}/download'
                ),
            })
            completed = self.store.complete_job(job.id, result, output_path)
            return self.serialize_job(completed)
        except Exception as exc:
            self.store.fail_job(job.id, str(exc))
            raise

    def serialize_job(self, job: StoredJob) -> dict:
        result = dict(job.result or {})
        result.update({
            'job_id': job.id,
            'status': job.status,
            'business_type': job.business_type,
            'business_label': job.business_label,
            'qc_month': job.qc_month,
            'selected_department': job.selected_department,
            'schedule_type': result.get('schedule_type', job.schedule_type),
            'created_at': job.created_at,
            'completed_at': job.completed_at,
            'download_url': (
                f'/personalized/{TOOL_SLUG}/api/jobs/{job.id}/download'
                if job.status == 'completed'
                else None
            ),
        })
        if job.error_message:
            result['error'] = job.error_message
        return result

    @staticmethod
    def download_name(job: StoredJob) -> str:
        department = job.selected_department
        if department and department != '全部部门':
            return f'教务质检结果-{department}.xlsx'
        return '教务质检结果.xlsx'

    def _prepare_classinfo(self, files: Mapping, input_dir: Path):
        items = [files.get(field) for field, _ in self.CLASSINFO_FIELDS]
        if all(item is not None and item.filename for item in items):
            paths = [
                self._save_upload(
                    item,
                    input_dir / filename,
                    self.ALLOWED_CLASSINFO_EXTENSIONS,
                )
                for item, (_, filename) in zip(items, self.CLASSINFO_FIELDS)
            ]
            combined_path = input_dir / 'classinfo-自动合并.xlsx'
            combine_classinfo_files(paths, combined_path)
            return combined_path, 'three_files'

        classinfo_item = files.get('classinfo')
        if classinfo_item is not None and classinfo_item.filename:
            return (
                self._save_upload(
                    classinfo_item,
                    input_dir / 'classinfo',
                    self.ALLOWED_CLASSINFO_EXTENSIONS,
                ),
                'combined_file',
            )
        raise ValueError('请完整上传三份班级信息表。')

    def _save_upload(self, item, destination: Path, allowed_extensions: set[str]) -> Path:
        suffix = Path(item.filename).suffix.lower()
        if suffix not in allowed_extensions:
            allowed_text = '、'.join(sorted(allowed_extensions))
            raise ValueError(f'文件格式不正确，仅支持 {allowed_text}。')
        destination = destination.with_suffix(suffix)
        total = 0
        with destination.open('wb') as target:
            while True:
                chunk = item.stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > self.max_upload_bytes:
                    raise ValueError('上传内容为空或超过 80 MB 限制。')
                target.write(chunk)
        if total == 0:
            raise ValueError('上传内容为空。')
        return destination

    @staticmethod
    def _required(form: Mapping, name: str) -> str:
        value = str(form.get(name, '')).strip()
        if not value:
            labels = {
                'business_type': '业务类型',
                'qc_month': '质检月份',
                'standard_department': '质检部门',
            }
            raise ValueError(f'请选择{labels[name]}。')
        return value
