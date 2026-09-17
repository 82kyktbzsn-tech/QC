# 验收清单

## 自动检查

```powershell
python -m unittest discover -s tests -v
python -m unittest tests.test_personalized_adapter -v
```

## 宿主联调

- [ ] 已登录用户打开 `/personalized/academic-data-qc`
- [ ] 未登录用户被送到宿主登录页
- [ ] 无权限用户打开页面得到 HTML 403
- [ ] 无权限用户调用 API 得到 JSON 403
- [ ] 页面加载后调用 `GET /personalized/academic-data-qc/api/data`
- [ ] 班课提交 classlesson + 三份班级信息文件
- [ ] 高端提交 PCLV，页面不要求班级信息
- [ ] 错误业务与配课表组合被后端拒绝
- [ ] 质检成功后能下载结果 Excel
- [ ] 下载权限只允许任务创建者或管理员
- [ ] 写入后刷新页面，历史任务仍来自服务端
- [ ] 导入/创建后重新 GET 权威任务数据
- [ ] 数据库迁移可执行、失败可 rollback
- [ ] 既有独立入口 `python webapp.py` 仍可启动
- [ ] `qc.py`、`classlesson_qc.py`、`pclv_qc.py` 规则测试回归通过

## DOM 对账

页面稳定节点：

```text
#academic-data-qc
#qc-form
#business-type
#standard-department
#qc-month
#schedule
#classinfo-opening
#classinfo-setup
#classinfo-closing
#start-button
#error-message
#result-section
#result-title
#result-summary
#download-button
#history-message
#history-list
```

JS 只访问上述节点及 `.classinfo-file`，模板与脚本的选择器差集应为空。
