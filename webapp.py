import cgi
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import traceback
from urllib.parse import quote, urlparse
from uuid import uuid4

from qc_service import (
    BUSINESS_CLASS,
    BUSINESS_PREMIUM,
    classinfo_required_for_selection,
    detect_schedule_type,
    run_qc_job,
    validate_business_selection,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'web' / 'static'
JOBS_DIR = BASE_DIR / 'runtime' / 'jobs'
QC_RULES_FILE = BASE_DIR / '产品说明书' / '长沙学校数据质检规则-2026.9.xlsx'
MAX_UPLOAD_BYTES = 80 * 1024 * 1024


class QCRequestHandler(SimpleHTTPRequestHandler):
    server_version = 'AcademicQC/1.0'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        # 质检规则和前端参数会持续调整，避免浏览器混用新页面与旧脚本。
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            self._send_json({'status': 'ok', 'time': datetime.now().isoformat()})
            return
        if path == '/api/files/qc-rules':
            self._download_qc_rules()
            return
        if path.startswith('/api/jobs/') and path.endswith('/download'):
            self._download_job(path)
            return
        if path == '/':
            self.path = '/index.html'
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != '/api/qc':
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get('Content-Length', '0'))
        if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
            self._send_json(
                {'error': '上传内容为空或超过 80 MB 限制。'},
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return

        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._send_json({'error': '请使用文件上传表单。'}, HTTPStatus.BAD_REQUEST)
            return

        job_id = uuid4().hex
        job_dir = JOBS_DIR / job_id
        input_dir = job_dir / 'input'
        input_dir.mkdir(parents=True, exist_ok=True)

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': content_type,
                    'CONTENT_LENGTH': str(content_length),
                },
                keep_blank_values=True,
            )
            schedule_item = form['schedule'] if 'schedule' in form else None
            if schedule_item is None or not schedule_item.filename:
                raise ValueError('请上传配课表 classlesson 或 pclv。')

            schedule_path = self._save_upload(
                schedule_item,
                input_dir / 'schedule.xlsx',
            )
            business_type = (form.getfirst('business_type') or '').strip()
            if business_type not in {BUSINESS_CLASS, BUSINESS_PREMIUM}:
                raise ValueError('请选择负责的业务类型。')
            qc_month = form.getfirst('qc_month')
            if not qc_month:
                raise ValueError('请选择质检月份。')
            standard_department = (
                form.getfirst('standard_department')
                or form.getfirst('schedule_department')
                or ''
            ).strip()
            if not standard_department:
                raise ValueError('请选择质检部门。')
            validate_business_selection(
                business_type,
                detect_schedule_type(schedule_path),
                standard_department,
            )
            classinfo_required = classinfo_required_for_selection(business_type)
            if classinfo_required:
                classinfo_path, classinfo_mode = self._prepare_classinfo(
                    form,
                    input_dir,
                )
            else:
                classinfo_path, classinfo_mode = None, 'not_required'
            output_path = job_dir / '教务质检结果.xlsx'
            result = run_qc_job(
                classinfo_path,
                schedule_path,
                output_path,
                qc_month=qc_month,
                business_type=business_type,
                standard_department=standard_department,
            )
            result.update({
                'job_id': job_id,
                'classinfo_mode': classinfo_mode,
                'download_url': f'/api/jobs/{job_id}/download',
                'created_at': datetime.now().isoformat(timespec='seconds'),
            })
            (job_dir / 'result.json').write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            self._send_json(result)
        except ValueError as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            self._send_json({'error': str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            traceback.print_exc()
            shutil.rmtree(job_dir, ignore_errors=True)
            self._send_json(
                {'error': '质检运行失败，请确认文件格式和字段是否正确。'},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def log_message(self, format_string, *args):
        print(f"[{self.log_date_time_string()}] {format_string % args}")

    def _save_upload(self, item, destination, allowed_extensions=None):
        allowed_extensions = allowed_extensions or {'.xlsx', '.xls'}
        suffix = Path(item.filename).suffix.lower()
        if suffix not in allowed_extensions:
            allowed_text = '、'.join(sorted(allowed_extensions))
            raise ValueError(f'文件格式不正确，仅支持 {allowed_text}。')
        destination = destination.with_suffix(suffix)
        with destination.open('wb') as target:
            shutil.copyfileobj(item.file, target)
        return destination

    def _prepare_classinfo(self, form, input_dir):
        from qc_service import combine_classinfo_files

        separate_fields = [
            ('classinfo_opening', '本月&次月开课.csv'),
            ('classinfo_setup', '本月设班.csv'),
            ('classinfo_closing', '本月结课.csv'),
        ]
        separate_items = [
            form[field] if field in form else None
            for field, _ in separate_fields
        ]
        has_any_separate = any(
            item is not None and item.filename
            for item in separate_items
        )
        if has_any_separate:
            if not all(
                item is not None and item.filename
                for item in separate_items
            ):
                raise ValueError('请完整上传三份班级信息表。')
            saved_paths = [
                self._save_upload(
                    item,
                    input_dir / filename,
                    allowed_extensions={'.csv', '.xlsx', '.xls'},
                )
                for item, (_, filename) in zip(separate_items, separate_fields)
            ]
            combined_path = input_dir / 'classinfo-自动合并.xlsx'
            combine_classinfo_files(saved_paths, combined_path)
            return combined_path, 'three_files'

        classinfo_item = form['classinfo'] if 'classinfo' in form else None
        if classinfo_item is None or not classinfo_item.filename:
            raise ValueError('请上传三份班级信息表。')
        return (
            self._save_upload(classinfo_item, input_dir / 'classinfo.xlsx'),
            'combined_file',
        )

    def _download_job(self, path):
        parts = path.strip('/').split('/')
        if len(parts) != 4 or parts[:2] != ['api', 'jobs']:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        job_id = parts[2]
        if not job_id.isalnum():
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        output_path = JOBS_DIR / job_id / '教务质检结果.xlsx'
        if not output_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, '结果文件不存在或已过期')
            return

        download_name = '教务质检结果.xlsx'
        result_path = JOBS_DIR / job_id / 'result.json'
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding='utf-8'))
            department = result.get('selected_department')
            if department and department != '全部部门':
                download_name = f'教务质检结果-{department}.xlsx'

        payload = output_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            'Content-Type',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.send_header(
            'Content-Disposition',
            f"attachment; filename*=UTF-8''{quote(download_name)}",
        )
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _download_qc_rules(self):
        if not QC_RULES_FILE.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, '质检规则文件不存在')
            return

        payload = QC_RULES_FILE.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            'Content-Type',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.send_header(
            'Content-Disposition',
            f"attachment; filename*=UTF-8''{quote(QC_RULES_FILE.name)}",
        )
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host=None, port=None):
    host = host or os.environ.get('QC_HOST', '127.0.0.1')
    port = int(port or os.environ.get('QC_PORT', '8000'))
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), QCRequestHandler)
    print(f'教务 Excel 质检工具已启动：http://{host}:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    run()
