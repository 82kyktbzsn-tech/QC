import json
from pathlib import Path
import re
import tempfile
import unittest

from flask import Flask, session

from app.personalized.routes import AuthAdapter, register_routes
from app.personalized.store import FileJobStore


class FakeUser:
    def __init__(self, user_id=7, admin=False, permitted=True):
        self.id = user_id
        self.is_admin = admin
        self.is_active = True
        self.permitted = permitted

    def has_permission(self, permission):
        return self.permitted and permission == '/personalized/academic-data-qc'


class PersonalizedAdapterTests(unittest.TestCase):
    def make_app(self, user=None):
        app = Flask(__name__)
        app.secret_key = 'test-secret'
        users = {} if user is None else {user.id: user}
        auth = AuthAdapter(
            get_user=lambda user_id: users.get(user_id),
            is_active=lambda candidate: candidate.is_active,
            is_admin=lambda candidate: candidate.is_admin,
            has_permission=lambda candidate, permission: candidate.has_permission(permission),
            login_endpoint='login',
        )
        app.add_url_rule('/login', 'login', lambda: 'login')
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FileJobStore(Path(temp_dir))
            register_routes(app, auth=auth, job_store=store)
        return app

    def test_api_returns_json_when_not_logged_in(self):
        app = self.make_app(FakeUser())
        client = app.test_client()

        response = client.get('/personalized/academic-data-qc/api/data')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {'error': '请先登录'})

    def test_api_returns_json_when_user_has_no_permission(self):
        user = FakeUser(permitted=False)
        app = self.make_app(user)
        client = app.test_client()
        with client.session_transaction() as current_session:
            current_session['user_id'] = user.id

        response = client.get('/personalized/academic-data-qc/api/data')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {'error': '您没有使用该工具的权限'})

    def test_authorized_user_can_read_empty_authoritative_data(self):
        user = FakeUser()
        app = self.make_app(user)
        client = app.test_client()
        with client.session_transaction() as current_session:
            current_session['user_id'] = user.id

        response = client.get('/personalized/academic-data-qc/api/data')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'ok': True, 'data': []})

    def test_file_store_round_trips_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FileJobStore(Path(temp_dir))
            job = store.create_job({
                'business_type': 'premium',
                'business_label': '高端业务',
                'qc_month': '2026-09',
                'selected_department': '高中一对一部',
                'schedule_type': 'pclv',
                'classinfo_mode': 'not_required',
                'created_by': 7,
            })
            result_path = store.job_directory(job.id) / 'result.xlsx'
            result_path.write_bytes(b'test')
            completed = store.complete_job(job.id, {'schedule_rows': 1}, result_path)
            loaded = store.get_job(job.id)

            self.assertEqual(loaded.status, 'completed')
            self.assertEqual(loaded.result, {'schedule_rows': 1})
            self.assertEqual(loaded.created_by, 7)
            self.assertEqual(json.loads(
                (store.job_directory(job.id) / 'metadata.json').read_text(encoding='utf-8'),
            )['status'], 'completed')

    def test_template_and_script_selectors_are_consistent(self):
        template = Path('app/personalized/templates/academic_data_qc.html').read_text(
            encoding='utf-8',
        )
        script = Path('app/personalized/static/js/academic_data_qc.js').read_text(
            encoding='utf-8',
        )
        template_ids = set(re.findall(r'\bid="([^"]+)"', template))
        script_ids = set(re.findall(r"#[A-Za-z0-9_-]+", script))
        self.assertTrue(script_ids)
        self.assertTrue(script_ids.issubset({f'#{item}' for item in template_ids}))


if __name__ == '__main__':
    unittest.main()
