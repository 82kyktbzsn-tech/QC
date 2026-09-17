"""可替换的任务元数据存储边界。

当前实现使用文件系统保存小型任务索引和 Excel 产物，方便在本仓库内冒烟。
嵌入宿主时可将同一接口替换为 MySQL/Flask-SQLAlchemy 实现，不触碰质检规则。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Iterable, Optional, Protocol
from uuid import uuid4


@dataclass
class StoredJob:
    id: str
    business_type: str
    business_label: str
    qc_month: str
    selected_department: str
    schedule_type: str
    status: str
    classinfo_mode: str
    created_by: Optional[int]
    created_at: str
    completed_at: Optional[str] = None
    output_path: Optional[str] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None


class JobStore(Protocol):
    def create_job(self, metadata: dict) -> StoredJob: ...

    def complete_job(self, job_id: str, result: dict, output_path: Path) -> StoredJob: ...

    def fail_job(self, job_id: str, message: str) -> StoredJob: ...

    def list_jobs(self, user_id: Optional[int], is_admin: bool) -> Iterable[StoredJob]: ...

    def get_job(self, job_id: str) -> Optional[StoredJob]: ...

    def job_directory(self, job_id: str) -> Path: ...


class FileJobStore:
    """独立冒烟用的文件存储实现；宿主生产环境应替换为数据库实现。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_job(self, metadata: dict) -> StoredJob:
        job_id = uuid4().hex
        job_dir = self.job_directory(job_id)
        job_dir.mkdir(parents=True, exist_ok=False)
        now = _now()
        job = StoredJob(
            id=job_id,
            business_type=metadata['business_type'],
            business_label=metadata['business_label'],
            qc_month=metadata['qc_month'],
            selected_department=metadata['selected_department'],
            schedule_type=metadata.get('schedule_type', ''),
            status='running',
            classinfo_mode=metadata.get('classinfo_mode', ''),
            created_by=metadata.get('created_by'),
            created_at=now,
        )
        self._write(job)
        (job_dir / 'input').mkdir()
        return job

    def complete_job(self, job_id: str, result: dict, output_path: Path) -> StoredJob:
        job = self._read(job_id)
        job.status = 'completed'
        job.completed_at = _now()
        job.output_path = str(Path(output_path).resolve())
        job.result = result
        self._write(job)
        return job

    def fail_job(self, job_id: str, message: str) -> StoredJob:
        job = self._read(job_id)
        job.status = 'failed'
        job.completed_at = _now()
        job.error_message = message
        self._write(job)
        return job

    def list_jobs(self, user_id: Optional[int], is_admin: bool) -> Iterable[StoredJob]:
        jobs = []
        for metadata_path in self.root.glob('*/metadata.json'):
            try:
                job = self._read(metadata_path.parent.name)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            if is_admin or job.created_by == user_id:
                jobs.append(job)
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)

    def get_job(self, job_id: str) -> Optional[StoredJob]:
        try:
            return self._read(job_id)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None

    def job_directory(self, job_id: str) -> Path:
        if not job_id.isalnum() or len(job_id) != 32:
            raise ValueError('任务编号不合法。')
        return self.root / job_id

    def delete_job(self, job_id: str) -> None:
        shutil.rmtree(self.job_directory(job_id), ignore_errors=True)

    def _read(self, job_id: str) -> StoredJob:
        path = self.job_directory(job_id) / 'metadata.json'
        return StoredJob(**json.loads(path.read_text(encoding='utf-8')))

    def _write(self, job: StoredJob) -> None:
        path = self.job_directory(job.id) / 'metadata.json'
        path.write_text(
            json.dumps(asdict(job), ensure_ascii=False, indent=2),
            encoding='utf-8',
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
