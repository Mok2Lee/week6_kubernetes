import importlib.util
import os
import unittest
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()
