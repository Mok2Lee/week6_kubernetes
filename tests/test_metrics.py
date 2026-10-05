import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('metrics_lab', Path(__file__).parents[1] / 'metrics/app.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.wall = 1000.0
        self.store = metrics.RollingRequests(clock=lambda: self.now, wall_clock=lambda: self.wall)

    def event(self, event_id, pod='api-1', path='/api/projects'):
        return {'id': event_id, 'pod': pod, 'path': path, 'latency_ms': 12.5}

    def test_window_aggregates_across_pods_and_exact_boundary_expires(self):
        self.store.record(self.event('a'))
        self.now = 101
        self.store.record(self.event('b', 'api-2', '/api/analyze'))
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['requests_last_minute'], 2)
        self.assertEqual(sum(p['requests_last_minute'] for p in snapshot['pods']), 2)
        self.assertEqual(sum(p['requests_last_minute'] for p in snapshot['endpoints']), 2)
        self.now = 160
        self.assertEqual(self.store.snapshot()['requests_last_minute'], 1)
        self.now = 161
        self.assertEqual(self.store.snapshot()['requests_last_minute'], 0)
        self.assertEqual(self.store.snapshot()['total_requests'], 2)

    def test_retry_is_deduplicated_and_old_completed_event_not_current_load(self):
        self.assertTrue(self.store.record(self.event('same')))
        self.assertFalse(self.store.record(self.event('same')))
        old = self.event('old')
        old['completed_at'] = '1970-01-01T00:15:00+00:00'  # 100 seconds before receipt.
        self.store.record(old)
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['requests_last_minute'], 1)
        self.assertEqual(snapshot['total_requests'], 2)

    def test_target_boundary_and_maximum(self):
        for i in range(251):
            self.store.record(self.event(str(i)))
            if i + 1 in {40, 50, 51, 100, 101, 120, 200, 201, 220, 250, 251}:
                expected = {40: 1, 50: 1, 51: 2, 100: 2, 101: 3, 120: 3, 200: 4, 201: 5, 220: 5, 250: 5, 251: 5}[i + 1]
                self.assertEqual(self.store.snapshot()['recommended_replicas'], expected)

    def test_rejects_health_or_malformed_events(self):
        for event in [{'id': 'x'}, self.event('x', path='/api/health'),
                      {**self.event('x'), 'latency_ms': float('nan')}]:
            with self.assertRaises(ValueError):
                self.store.record(event)

    def test_external_metric_has_real_quantity_and_discovery(self):
        self.store.record(self.event('a'))
        with patch.object(metrics, 'store', self.store):
            client = metrics.external.test_client()
            result = client.get('/apis/external.metrics.k8s.io/v1beta1/namespaces/default/api_requests_per_minute')
            self.assertEqual(result.json['items'][0]['value'], '1')
            self.assertEqual(result.json['items'][0]['windowSeconds'], 60)
            self.assertEqual(client.get('/apis/external.metrics.k8s.io/v1beta1').json['resources'][0]['verbs'], ['get'])
            self.assertEqual(client.get('/apis/external.metrics.k8s.io/v1beta1/namespaces/other/api_requests_per_minute').status_code, 404)

    def test_dashboard_uses_actual_deployment_pods_and_hpa(self):
        self.store.record(self.event('a', pod='api-1'))
        objects = (
            {'spec': {'replicas': 3}, 'status': {'replicas': 2, 'readyReplicas': 1}},
            {'items': [{'metadata': {'name': 'api-1', 'creationTimestamp': '2026-10-05T00:00:00Z'},
                        'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]}},
                       {'metadata': {'name': 'api-2'}, 'status': {'phase': 'Pending'}}]},
            {'status': {'currentReplicas': 2, 'desiredReplicas': 3,
                        'conditions': [{'type': 'ScalingActive', 'status': 'True'}]}})
        with patch.object(metrics, 'store', self.store), patch.object(metrics.reader, 'objects', return_value=objects):
            result = metrics.internal.test_client().get('/internal/dashboard')
        self.assertEqual(result.json['desired_replicas'], 3)
        self.assertEqual(result.json['current_replicas'], 2)
        self.assertEqual(result.json['ready_replicas'], 1)
        self.assertEqual(result.json['current_average_requests_per_minute'], 0.5)
        self.assertEqual(result.json['target_requests_per_minute'], 50)
        self.assertEqual(result.json['pods'][0]['requests_last_minute'], 1)
        self.assertTrue(result.json['pods'][0]['ready'])
        self.assertFalse(result.json['pods'][1]['ready'])
        self.assertEqual(result.json['autoscaler']['conditions'][0]['type'], 'ScalingActive')

    def test_dashboard_reads_changed_hpa_target_instead_of_default(self):
        for i in range(220):
            self.store.record(self.event(str(i)))
        hpa = {'spec': {'minReplicas': 1, 'maxReplicas': 5,
                        'metrics': [{'type': 'External', 'external': {
                            'metric': {'name': 'api_requests_per_minute'},
                            'target': {'type': 'AverageValue', 'averageValue': '75'}}}]},
               'status': {'currentReplicas': 5, 'desiredReplicas': 3}}
        objects = (
            {'spec': {'replicas': 5}, 'status': {'replicas': 5, 'readyReplicas': 5}},
            {'items': [{'metadata': {'name': 'api-' + str(i)},
                        'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]}}
                       for i in range(1, 6)]}, hpa)
        with patch.object(metrics, 'store', self.store), patch.object(metrics.reader, 'objects', return_value=objects):
            result = metrics.internal.test_client().get('/internal/dashboard')
        self.assertEqual(result.json['requests_last_minute'], 220)
        self.assertEqual(result.json['current_replicas'], 5)
        self.assertEqual(result.json['current_average_requests_per_minute'], 44)
        self.assertEqual(result.json['target_requests_per_minute'], 75)
        self.assertEqual(result.json['autoscaler']['target_requests_per_minute'], 75)
        self.assertEqual(result.json['recommended_replicas'], 3)
        self.assertEqual(result.json['autoscaler']['min_replicas'], 1)
        self.assertEqual(result.json['autoscaler']['max_replicas'], 5)

        # HPA의 범위를 바꾸어도 대시보드가 고정된 기본 범위를 표시하지 않습니다.
        hpa['spec'].update(minReplicas=2, maxReplicas=2)
        with patch.object(metrics, 'store', self.store), patch.object(metrics.reader, 'objects', return_value=objects):
            constrained = metrics.internal.test_client().get('/internal/dashboard').json
        self.assertEqual(constrained['recommended_replicas'], 2)
        self.assertEqual(constrained['autoscaler']['min_replicas'], 2)
        self.assertEqual(constrained['autoscaler']['max_replicas'], 2)


if __name__ == '__main__':
    unittest.main()
