# 教务数据质检嵌入包

这是现有教务 Excel 质检逻辑的 Flask Blueprint 适配层，不是新的独立站。

## 工具契约

```text
工具名：教务数据质检
tool-slug：academic-data-qc
页面：GET /personalized/academic-data-qc
权限键：/personalized/academic-data-qc
```

页面和 API 复用宿主登录态；服务端仍调用项目根目录的 `qc_service.py`，因此既有班级信息、classlesson 和 PCLV 规则不变。

## 嵌入结构

```text
app/personalized/
├── __init__.py       # 包导出
├── constants.py      # URL、权限和名称
├── models.py         # 宿主数据库模型草稿的数据结构
├── store.py          # 任务元数据存储边界及本地冒烟实现
├── service.py        # 上传输入适配到既有 qc_service
├── routes.py         # Flask Blueprint、鉴权和 API
├── templates/        # 宿主 Jinja 模板
└── static/           # 工具前缀化 CSS 和原生 JS
```

## 本地冒烟

```python
from flask import Flask
from app.personalized import register_routes

app = Flask(__name__)
app.secret_key = 'local-only'
app.config['QC_JOB_ROOT'] = 'runtime/personalized-jobs'
register_routes(app, auth=宿主鉴权适配器)
```

生产环境应传入宿主 MySQL 存储实现和 `AuthAdapter`，不要把本地 `FileJobStore` 当作多人共享数据库。

## 明确不做

- 不创建独立登录、用户表或权限系统
- 不修改现有 `qc.py`、`classlesson_qc.py`、`pclv_qc.py`、`data_loader.py`、`labeling.py` 和根目录 `qc_service.py`
- 不改变原有 `webapp.py` 独立运行方式
- 不用浏览器 `localStorage` 保存权威数据
- 不把大文件直接写入宿主数据库
