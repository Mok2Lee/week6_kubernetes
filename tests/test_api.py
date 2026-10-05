import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('lab', Path(__file__).parents[1] / 'api/app.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = lab.app.test_client()

    def test_health_identifies_version_and_pod(self):
        result = self.client.get('/api/health')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['version'], os.environ.get('APP_VERSION', 'v1'))
        self.assertTrue(result.json['pod'])

    def test_search_and_korean_query(self):
        result = self.client.get('/api/projects?category=web')
        self.assertEqual(result.json['count'], 2)
        result = self.client.get('/api/projects', query_string={'q': '캡스톤'})
        self.assertEqual(result.json['count'], 1)

    def test_length_boundaries_and_invalid_input(self):
        for n, expected in [(99, False), (100, True), (300, True), (301, False)]:
            result = self.client.post('/api/analyze', json={'text': '가' * n})
            self.assertEqual(result.json['within_range'], expected)
        for data in [{}, {'text': ''}, {'text': 123}, {'text': '가' * 5001}]:
            self.assertEqual(self.client.post('/api/analyze', json=data).status_code, 400)

    def test_successful_functional_requests_count_once_and_identify_pod(self):
        with patch.object(lab, 'record_event', return_value='recorded') as record:
            response = self.client.get('/api/projects?q=예약')
            self.assertEqual(response.headers['X-Pod-Name'], lab.POD_NAME)
            self.assertEqual(response.headers['X-Metrics-Status'], 'recorded')
            self.assertNotIn('metrics_status', response.json)
            self.client.post('/api/analyze', json={'text': '소개 문장'})
            self.client.post('/api/request', json={'source': 'week6_sender', 'sequence': 1})
            self.assertEqual(record.call_count, 3)
            paths = [call.args[0]['path'] for call in record.call_args_list]
            self.assertEqual(paths, ['/api/projects', '/api/analyze', '/api/request'])
            self.assertEqual(len({call.args[0]['id'] for call in record.call_args_list}), 3)
            for call in record.call_args_list:
                self.assertGreaterEqual(call.args[0]['latency_ms'], 0)

    def test_health_dashboard_invalid_requests_do_not_count(self):
        with patch.object(lab, 'record_event') as record:
            self.client.get('/api/health')
            self.client.get('/api/dashboard')
            self.client.post('/api/analyze', json={'text': ''})
            self.client.get('/missing')
            record.assert_not_called()

    def test_request_performs_search_and_returns_version(self):
        response = self.client.post('/api/request', json={'query': '예약'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['result']['count'], 1)
        self.assertEqual(len(response.json['result']['fingerprint']), 16)
        self.assertEqual(response.json['pod'], lab.POD_NAME)

    def test_collector_failure_queues_without_failing_actual_api(self):
        with patch.object(lab, 'METRICS_URL', 'http://metrics:8000'), patch.object(lab, 'send_record', side_effect=OSError('offline')):
            response = self.client.get('/api/projects')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['X-Metrics-Status'], 'queued')
            self.assertTrue(lab.PENDING_EVENTS)
            lab.PENDING_EVENTS.clear()


if __name__ == '__main__':
    unittest.main()
