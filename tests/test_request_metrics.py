"""Classic histogram cumulative buckets, boundaries and bounded route labels."""
import unittest
from app.request_metrics import RequestDurations


class RequestMetricsTests(unittest.TestCase):
    def test_cumulative_buckets_count_sum_and_infinite_bucket(self):
        histogram = RequestDurations()
        for seconds in (0.1, 0.5, 0.75, 8.0):
            histogram.observe('/v1/orders', seconds)
        output = '\n'.join(histogram.render())
        self.assertIn('le="0.1"} 1', output)
        self.assertIn('le="0.5"} 2', output)
        self.assertIn('le="1"} 3', output)
        self.assertIn('le="5"} 3', output)
        self.assertIn('le="+Inf"} 4', output)
        self.assertIn('relaydesk_request_duration_seconds_count{route="/v1/orders"} 4', output)
        self.assertAlmostEqual(histogram.observations['/v1/orders']['sum'], 9.35)

    def test_unknown_paths_do_not_become_labels(self):
        histogram = RequestDurations()
        histogram.observe('/private/customer-key?token=secret', 0.2)
        output = '\n'.join(histogram.render())
        self.assertIn('route="unmatched"', output)
        self.assertNotIn('secret', output)
        self.assertNotIn('customer-key', output)

    def test_invalid_duration_is_not_recorded(self):
        histogram = RequestDurations()
        for value in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                histogram.observe('/health', value)
        self.assertEqual(histogram.observations, {})
