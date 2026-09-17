# 数据模型

## 任务表

生产宿主建议使用：`personalized_academic_qc_jobs`。

| 字段 | 类型建议 | 约束 | 说明 |
|---|---|---|---|
| id | `VARCHAR(32)` | PK | UUID hex 任务号 |
| business_type | `VARCHAR(16)` | NOT NULL | `class` / `premium` |
| qc_month | `CHAR(7)` | NOT NULL | `YYYY-MM` |
| selected_department | `VARCHAR(128)` | NOT NULL | 标化部门筛选值 |
| schedule_type | `VARCHAR(16)` | NOT NULL | `classlesson` / `pclv` |
| status | `VARCHAR(16)` | NOT NULL | `running` / `completed` / `failed` |
| classinfo_mode | `VARCHAR(32)` | NOT NULL | `three_files` / `combined_file` / `not_required` |
| output_uri | `VARCHAR(512)` | NULL | 结果文件归档地址，不建议存二进制 |
| error_message | `TEXT` | NULL | 失败原因 |
| created_by | `BIGINT` | NULL | 关联 `users.id` |
| updated_by | `BIGINT` | NULL | 关联 `users.id` |
| created_at | `DATETIME` | NOT NULL | Asia/Shanghai 业务时间 |
| updated_at | `DATETIME` | NOT NULL | Asia/Shanghai 业务时间 |

## JSON 结果

`result_json` 可选存储 `qc_service.run_qc_job()` 返回的统计快照；它不是规则数据的权威来源。结果 Excel 或对象存储仍是下载权威产物。

## 状态流

```text
未创建
  -> running       创建任务元数据并保存上传文件
  -> completed     规则运行完成、结果归档、写入 output_uri
  -> failed        失败原因写入 error_message
```

失败时不能把任务伪装成成功，也不能用空结果覆盖已经成功的任务。
