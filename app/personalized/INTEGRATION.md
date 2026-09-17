# 宿主接入说明

## 需要修改的宿主文件

```text
[ ] 将 app/personalized/ 放入宿主 app/personalized/
[ ] 在 app/auth/permissions.py 增加权限键
[ ] 在 app/templates/shared/navbar.html 增加导航入口
[ ] 如需要，在 app/templates/dashboard.html 增加入口
[ ] 将 migrations/versions/add_personalized_academic_qc_jobs.py 挂入 Alembic
[ ] 执行数据库迁移
[ ] 注入宿主 User 查询、权限函数和 MySQL JobStore
[ ] 管理员冒烟
[ ] 授权用户冒烟
[ ] 无权限用户验证 403
[ ] 回归登录及既有页面
```

## 权限与导航

权限目录追加：

```python
{"id": "/personalized/academic-data-qc", "name": "教务数据质检", "group": "个性化"},
```

导航片段：

```jinja
{% if current_user.is_admin or current_user.has_permission('/personalized/academic-data-qc') %}
  <a href="{{ url_for('personalized.academic_data_qc_page') }}">教务数据质检</a>
{% endif %}
```

实际 endpoint 名称取决于宿主使用的是本包自建 Blueprint 还是现有 Blueprint；接线时以 `app.url_map` 为准，不要复制错误 endpoint。

## 蓝图挂载

宿主已有 `personalized_bp` 时：

```python
from app.personalized import AuthAdapter, register_routes

register_routes(
    app,
    blueprint=personalized_bp,
    auth=AuthAdapter(
        get_user=lambda user_id: User.query.get(user_id),
        is_active=lambda user: user.is_active,
        is_admin=lambda user: user.is_admin,
        has_permission=lambda user, permission: user.has_permission(permission),
    ),
    job_store=宿主的 MySQLJobStore,
)
```

没有已有 Blueprint 时：

```python
register_routes(app, auth=宿主鉴权适配器, job_store=宿主的 MySQLJobStore)
```

## 不修改的宿主文件

适配包不要求改动既有质检规则、旧 `webapp.py`、CLI 入口或现有数据文件。宿主只负责鉴权、权限目录、导航、迁移挂链及生产存储实现。

## 存储策略

- 任务元数据：宿主主库的 `personalized_academic_qc_jobs`
- 原始上传和 Excel 结果：宿主配置的文件归档目录或对象存储
- 本地 `FileJobStore`：仅用于开发和最小冒烟
- 数据库保存 `created_by` / `updated_by`，按宿主 `users.id` 关联
