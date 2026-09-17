"""宿主侧持久化模型草稿。

质检原始文件与结果仍由既有运行时任务目录管理；这些表只保存可追踪的任务元数据，
避免把大文件或核心质检结果迁移到宿主数据库后改变既有行为。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class QCJobRecord:
    """宿主数据库中的任务索引，不替代现有 Excel 质检产物。"""

    id: str
    business_type: str
    qc_month: str
    selected_department: str
    schedule_type: str
    status: str
    classinfo_mode: str
    output_path: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
