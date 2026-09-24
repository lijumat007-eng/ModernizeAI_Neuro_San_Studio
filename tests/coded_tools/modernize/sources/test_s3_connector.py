# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tests for S3Connector against a moto-mocked bucket - a real boto3 client
talking to an in-memory fake AWS, replacing the old server.py flow that
faked the whole thing with log lines and never touched S3 at all.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

try:
    import boto3
    from moto import mock_aws

    _BOTO_AVAILABLE = True
except ImportError:
    _BOTO_AVAILABLE = False

from coded_tools.modernize.sources.s3 import S3Connector


@unittest.skipUnless(_BOTO_AVAILABLE, "boto3/moto not installed")
class TestS3Connector(unittest.TestCase):
    def setUp(self):
        self.mock = mock_aws()
        self.mock.start()
        self.client = boto3.client("s3", region_name="us-east-1")
        self.client.create_bucket(Bucket="legacy-bucket")
        self.client.put_object(Bucket="legacy-bucket", Key="app/Order.java", Body=b"class Order {}")
        self.client.put_object(Bucket="legacy-bucket", Key="app/readme.md", Body=b"# docs")
        self.client.put_object(Bucket="legacy-bucket", Key="app/logo.png", Body=b"\x89PNG")

    def tearDown(self):
        self.mock.stop()

    def _connector(self, prefix: str = "app/") -> S3Connector:
        return S3Connector("s3src", {"s3_uri": f"s3://legacy-bucket/{prefix}", "region": "us-east-1"})

    def test_fetches_text_objects_only(self):
        docs, _fp = self._connector().fetch()
        paths = {d.path for d in docs}
        self.assertIn("Order.java", paths)
        self.assertIn("readme.md", paths)
        self.assertNotIn("logo.png", paths)

    def test_content_is_read_correctly(self):
        docs, _fp = self._connector().fetch()
        order = next(d for d in docs if d.path == "Order.java")
        self.assertEqual(order.content, "class Order {}")

    def test_uri_is_a_real_https_link(self):
        docs, _fp = self._connector().fetch()
        order = next(d for d in docs if d.path == "Order.java")
        self.assertTrue(order.uri.startswith("https://"))
        self.assertIn("app/Order.java", order.uri)

    def test_test_connection_succeeds_for_real_bucket(self):
        result = self._connector().test_connection()
        self.assertTrue(result.ok)

    def test_test_connection_fails_for_missing_bucket(self):
        connector = S3Connector("s3src", {"s3_uri": "s3://does-not-exist/x/", "region": "us-east-1"})
        result = connector.test_connection()
        self.assertFalse(result.ok)

    def test_fingerprint_changes_when_object_content_changes(self):
        _docs1, fp1 = self._connector().fetch()
        self.client.put_object(Bucket="legacy-bucket", Key="app/Order.java", Body=b"class Order { int x; }")
        _docs2, fp2 = self._connector().fetch()
        self.assertNotEqual(fp1, fp2)


if __name__ == "__main__":
    unittest.main()
