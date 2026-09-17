# API 契约

权限键统一为 `/personalized/academic-data-qc`。

## 页面

```text
GET /personalized/academic-data-qc
```

- 未登录：跳转宿主登录页
- 无权限：HTML 403 错误页
- 成功：返回宿主 Jinja 页面

## 查询历史任务

```text
GET /personalized/academic-data-qc/api/data
```

成功：

```json
{"data": [{"job_id": "...", "status": "completed", "download_url": "..."}]}
```

错误：

```json
{"error": "请先登录"}
```

状态码：未登录 `401`，账号不可用或无权限 `403`。

## 创建质检任务

```text
POST /personalized/academic-data-qc/api/jobs
Content-Type: multipart/form-data
```

表单字段：

```text
business_type: class | premium
standard_department: 部门名称
qc_month: YYYY-MM
schedule: classlesson 或 pclv 的 xlsx/xls
classinfo_opening: 本月及次月开课 csv/xlsx/xls，班课必填
classinfo_setup: 本月设班 csv/xlsx/xls，班课必填
classinfo_closing: 本月结课 csv/xlsx/xls，班课必填
```

成功返回质检结果概览，并包含：

```json
{
  "ok": true,
  "job_id": "任务编号",
  "status": "completed",
  "business_type": "class",
  "schedule_type": "classlesson",
  "selected_department": "素养",
  "classinfo_rows": 0,
  "schedule_rows": 0,
  "classinfo_abnormal_rows": 0,
  "schedule_abnormal_rows": 0,
  "download_url": "/personalized/academic-data-qc/api/jobs/任务编号/download"
}
```

注意：`qc_service.run_qc_job()` 的既有返回字段原样保留，适配层只补充任务状态字段。

## 下载结果

```text
GET /personalized/academic-data-qc/api/jobs/<job_id>/download
```

只有任务创建者或管理员可以下载。结果不存在、未完成或已过期时返回 JSON 错误，不返回登录 HTML。

## 错误状态码

| 场景 | 状态码 | 返回 |
|---|---:|---|
| 未登录 | 401 | `{"error":"请先登录"}` |
| 无权限 | 403 | `{"error":"您没有使用该工具的权限"}` |
| 参数/文件错误 | 400 | `{"error":"人类可读原因"}` |
| 任务不存在 | 404 | `{"error":"任务不存在或已过期"}` |
| 运行失败 | 500 | `{"error":"质检运行失败..."}` |
