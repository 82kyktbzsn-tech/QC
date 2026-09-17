"""Flask Blueprint 与宿主鉴权边界。

路由只负责 HTTP、鉴权和参数校验；质检编排委托给 service，原有规则继续由
项目根目录的 qc_service.py 执行。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from .constants import BLUEPRINT_NAME, TOOL_NAME, TOOL_PERMISSION, TOOL_SLUG
from .service import UploadedQCService
from .store import FileJobStore, JobStore


@dataclass(frozen=True)
class AuthAdapter:
    """把宿主 User 模型适配为工具需要的最小鉴权协议。"""

    get_user: Callable[[int], Any]
    is_active: Callable[[Any], bool] = lambda user: bool(user)
    is_admin: Callable[[Any], bool] = lambda user: bool(getattr(user, 'is_admin', False))
    has_permission: Callable[[Any, str], bool] = (
        lambda user, permission: bool(user.has_permission(permission))
    )
    login_endpoint: str = 'auth.login'

    def current_user(self) -> Optional[Any]:
        user_id = session.get('user_id')
        if not user_id:
            return None
        return self.get_user(user_id)

    def allowed(self, user: Any) -> bool:
        return self.is_admin(user) or self.has_permission(user, TOOL_PERMISSION)


def create_blueprint(
    *,
    blueprint: Optional[Blueprint] = None,
    job_root: Optional[Path] = None,
    job_store: Optional[JobStore] = None,
    auth: Optional[AuthAdapter] = None,
    qc_service: Optional[UploadedQCService] = None,
) -> Blueprint:
    """创建或填充可挂载到宿主的 Blueprint。"""
    blueprint = blueprint or Blueprint(
        BLUEPRINT_NAME,
        __name__,
        template_folder='templates',
        static_folder='static',
        static_url_path='/static',
    )
    if job_store is None:
        job_root = job_root or Path(__file__).resolve().parents[2] / 'runtime' / 'personalized-jobs'
        job_store = FileJobStore(job_root)
    store = job_store
    service = qc_service or UploadedQCService(store)
    auth_adapter = auth or AuthAdapter(get_user=lambda user_id: None)

    def require_page_user(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = auth_adapter.current_user()
            if user is None:
                return redirect(url_for(auth_adapter.login_endpoint))
            if not auth_adapter.is_active(user):
                abort(403, description='账号不可用')
            if not auth_adapter.allowed(user):
                abort(403, description='您没有使用该工具的权限')
            return view(user, *args, **kwargs)

        return wrapped

    def require_api_user(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': '请先登录'}), 401
            user = auth_adapter.current_user()
            if user is None:
                return jsonify({'error': '账号不可用'}), 403
            if not auth_adapter.is_active(user):
                return jsonify({'error': '账号不可用'}), 403
            if not auth_adapter.allowed(user):
                return jsonify({'error': '您没有使用该工具的权限'}), 403
            return view(user, *args, **kwargs)

        return wrapped

    @blueprint.get(f'/{TOOL_SLUG}')
    @require_page_user
    def academic_data_qc_page(_user):
        return render_template(
            'academic_data_qc.html',
            tool_name=TOOL_NAME,
            tool_permission=TOOL_PERMISSION,
        )

    @blueprint.get(f'/{TOOL_SLUG}/api/data')
    @require_api_user
    def academic_data_qc_data(_user):
        user_id = session.get('user_id')
        jobs = store.list_jobs(user_id=user_id, is_admin=auth_adapter.is_admin(_user))
        return jsonify({'ok': True, 'data': [service.serialize_job(job) for job in jobs]})

    @blueprint.post(f'/{TOOL_SLUG}/api/jobs')
    @require_api_user
    def create_academic_data_qc_job(user):
        try:
            result = service.run(request.files, request.form, user_id=session.get('user_id'))
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except Exception:
            current_app.logger.exception('academic data qc failed')
            return jsonify({'error': '质检运行失败，请确认文件格式和字段是否正确。'}), 500
        return jsonify(result)

    @blueprint.get(f'/{TOOL_SLUG}/api/jobs/<job_id>/download')
    @require_api_user
    def download(user, job_id):
        job = store.get_job(job_id)
        if job is None:
            return jsonify({'error': '任务不存在或已过期'}), 404
        if not auth_adapter.is_admin(user) and job.created_by != session.get('user_id'):
            return jsonify({'error': '无权访问该任务'}), 403
        if job.status != 'completed' or not job.output_path:
            return jsonify({'error': '质检结果尚未生成'}), 404
        output_path = Path(job.output_path)
        if not output_path.is_file():
            return jsonify({'error': '结果文件不存在或已过期'}), 404
        return send_file(
            output_path,
            as_attachment=True,
            download_name=service.download_name(job),
        )

    return blueprint


def register_routes(
    app,
    *,
    blueprint: Optional[Blueprint] = None,
    url_prefix: str = '/personalized',
    job_root: Optional[Path] = None,
    job_store: Optional[JobStore] = None,
    auth: Optional[AuthAdapter] = None,
    qc_service: Optional[UploadedQCService] = None,
) -> Blueprint:
    """宿主只需调用一次；已有 personalized Blueprint 时传入它。"""
    registered_blueprint = create_blueprint(
        blueprint=blueprint,
        job_root=job_root,
        job_store=job_store,
        auth=auth,
        qc_service=qc_service,
    )
    if blueprint is None:
        app.register_blueprint(registered_blueprint, url_prefix=url_prefix)
    return registered_blueprint
