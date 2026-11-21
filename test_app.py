import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

import app


class ReceiptTests(unittest.TestCase):
    def test_reference_total_and_section_order(self):
        html = app.render(app.normalize(copy.deepcopy(app.DEFAULT)))
        self.assertIn('638,000.00', html)
        labels = ['WE DELIVER', 'Tax Invoice', 'Verif Code:', 'FDN:', 'Item Name', 'Total Amount:', 'Credit Card Amount', 'Inclusive of VAT', 'Name: Hope', '785376485', 'Airtel Money', 'Momopay']
        positions = [html.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))

    def test_decimal_rounding_and_escaping(self):
        d = copy.deepcopy(app.DEFAULT)
        d['items'] = [dict(name='<script>alert(1)</script>', qty='3', price='0.10')]
        html = app.render(app.normalize(d))
        self.assertIn('0.30', html)
        self.assertNotIn('<script>', html)

    def test_reject_invalid_values(self):
        for value in ['NaN', 'Infinity', '-1', 'abc']:
            with self.assertRaises(ValueError):
                app.money(value)
        d = copy.deepcopy(app.DEFAULT)
        d['items'][0]['qty'] = '0'
        with self.assertRaises(ValueError):
            app.normalize(d)

    def test_qr_generated_only_when_requested(self):
        d = app.normalize(copy.deepcopy(app.DEFAULT))
        self.assertNotIn('data:image/svg+xml', app.render(d))
        d['qr'] = 'Receipt KG178'
        self.assertIn('data:image/svg+xml;base64,', app.render(d))

    def test_save_and_reopen_through_http(self):
        original_db = app.DB
        with tempfile.TemporaryDirectory() as temp:
            app.DB = Path(temp) / 'test.sqlite3'
            server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                req = Request(base + '/api/receipts', data=json.dumps(app.DEFAULT).encode(), headers={'Content-Type': 'application/json'})
                with urlopen(req) as response:
                    rid = json.load(response)['id']
                with urlopen(base + f'/api/receipts/{rid}') as response:
                    self.assertEqual(json.load(response), app.normalize(app.DEFAULT))
                with urlopen(base + '/') as response:
                    self.assertEqual(response.status, 200)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
                app.DB = original_db


if __name__ == '__main__':
    unittest.main()
