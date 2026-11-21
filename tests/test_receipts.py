import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db = patch.object(app, 'DB', Path(self.temp.name) / 'receipts.sqlite3')
        db.start()
        self.addCleanup(db.stop)
        self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, receipt=None, **headers):
        with_connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        try:
            body = None
            if receipt is not None:
                body = json.dumps(receipt)
                headers['Content-Type'] = 'application/json'
            with_connection.request(method, path, body, headers)
            response = with_connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            with_connection.close()

    def test_amounts_and_escaped_names_match_saved_snapshot(self):
        receipt = app.new_receipt()
        receipt['items'] = [{'name': '<Coffee>', 'qty': '1', 'price': '1.235'}] * 2
        status, result = self.request('POST', '/api/receipts', receipt)
        self.assertEqual(status, 200)
        self.assertEqual(result['html'].count('1.24</td>'), 2)
        self.assertIn('2.48</b>', result['html'])
        self.assertIn('&lt;Coffee&gt;', result['html'])
        status, saved = self.request('GET', f"/api/receipts/{result['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(saved, receipt)

    def test_oversized_qr_is_a_validation_error(self):
        receipt = app.new_receipt()
        receipt['items'][0]['name'] = 'Coffee'
        receipt['qr'] = 'é' * 1001
        status, _ = self.request('POST', '/api/receipts', receipt)
        self.assertEqual(status, 400)
        self.assertEqual(self.request('GET', '/api/receipts'), (200, []))

    def test_rejects_non_loopback_host_and_foreign_origin(self):
        self.assertEqual(self.request('GET', '/api/receipts', Host='example.test')[0], 403)
        self.assertEqual(self.request('POST', '/api/receipts', app.new_receipt(), Origin='https://example.test')[0], 403)

    def test_new_receipt_has_no_prefilled_business_identity(self):
        status, receipt = self.request('GET', '/api/default')
        self.assertEqual(status, 200)
        self.assertEqual(receipt['business'], '')
        self.assertEqual(receipt['tin'], '')

    def test_history_search_paginates_without_skips_or_duplicate_rows(self):
        with app.connect() as connection:
            connection.executemany(
                'INSERT INTO receipts(number, data) VALUES (?, ?)',
                [('R-%-A', '{}')] * 51 + [('R-other', '{}')],
            )
        status, first = self.request('GET', '/api/receipts/history?q=r-%25-a')
        self.assertEqual(status, 200)
        self.assertEqual([row['id'] for row in first['receipts']], list(range(51, 1, -1)))
        with app.connect() as connection:
            connection.execute(
                'INSERT INTO receipts(number, data) VALUES (?, ?)', ('R-%-A', '{}'),
            )
        status, second = self.request('GET', f"/api/receipts/history?q=r-%25-a&before={first['next_before']}")
        self.assertEqual(status, 200)
        self.assertEqual([row['id'] for row in second['receipts']], [1])
        self.assertIsNone(second['next_before'])
        self.assertEqual(self.request('GET', '/api/receipts/history?before=-1')[0], 400)
