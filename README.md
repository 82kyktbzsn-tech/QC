# 教务 Excel 质检工具

一个可独立运行的 Web 工具。用户先选择班课或高端业务，系统再呈现对应的文件入口，执行质检、展示部门统计并生成可下载的 Excel 结果。

## 本地运行

```bash
python3 -m pip install -r requirements.txt
python3 webapp.py
```

浏览器访问：`http://127.0.0.1:8000`

也可以继续运行原有命令：

```bash
python3 main.py
python3 classlesson_main.py
```

## 上传流程

1. 先选择负责的业务类型。
2. 班课业务：选择一次负责部门，同时用于筛选班级信息和配课表；上传一份 `classlesson` 班级配课表，以及“本月&次月开课”“本月设班”“本月结课”三份班级信息表。
3. 高端业务：选择一次负责部门，只上传 `pclv` 高端配课表，不检查班级信息；部门按 PCLV 的“标准部门名称”筛选。
4. 点击“开始质检”。页面仅展示所选部门的记录数、异常数和规则命中情况。
5. 下载仅包含所选部门明细的 `教务质检结果-部门.xlsx`。

业务类型、部门和配课表类型会在后端再次校验：班课业务只接受 `classlesson`，高端业务只接受 `pclv`，上传错误类型时会直接提示。

系统会读取三份 CSV，自动兼容 UTF-8、UTF-8 BOM 和 GB18030 编码，检查列结构一致性，然后自动合并为以下 Sheet：

- `本月&次月开课`
- `本月设班`
- `本月结课`

用户无需再手工合并或修改 Sheet 名。接口仍兼容原来通过 `classinfo` 字段上传单个已合并工作簿的方式。

下载结果包含：

- `质检参数`（记录业务类型、质检月份和标化部门）
- `部门汇总`
- `班级信息质检`（仅班课业务）
- `配课质检-classlesson` 或 `配课质检-pclv`
- `部门组合核对`，用于人工确认管理部门与标准部门的对应关系

班级信息和配课质检 Sheet 的首列为 `质检结果反馈`，会用 `+` 汇总该行命中的全部异常，并以黄色底、红色加粗字体突出显示。

`classinfo` 和 `classlesson` 执行班课质检规则；`pclv` 执行独立的高端配课规则，其“标化部门”直接取原表的“标准部门名称”，不再做二次映射。

## 配置

可通过环境变量修改监听地址和端口：

```bash
QC_HOST=0.0.0.0 QC_PORT=8080 python3 webapp.py
```

上传任务保存在 `runtime/jobs/<任务ID>/`，该目录已加入 `.gitignore`。生产环境可以使用定时任务清理过期任务目录。

## 服务器部署

项目没有额外 Web 框架依赖，可直接用 Python 启动。服务器需要：

- Python 3.9+
- `pandas`
- `openpyxl`
- 可写的 `runtime/` 目录

示例 systemd 启动命令：

```ini
ExecStart=/path/to/venv/bin/python /path/to/QC/webapp.py
Environment=QC_HOST=0.0.0.0
Environment=QC_PORT=8000
WorkingDirectory=/path/to/QC
```

公司网站接入时，可由 Nginx 将内部路径反向代理到该服务。建议在生产环境补充统一登录鉴权、HTTPS、上传文件病毒扫描、任务过期清理和访问日志归档。
