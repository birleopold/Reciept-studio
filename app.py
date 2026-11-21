"""Local receipt studio. Run: python app.py"""
import argparse
import base64
import io
import json
import sqlite3
import webbrowser
from threading import Timer
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import qrcode
import qrcode.image.svg

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'receipts.sqlite3'
DEFAULT = dict(
    headline='', phone_label='', phone1='', phone2='', business='',
    address='', tin='', title='Receipt', customer='', date='', number='',
    invoice='', verification='', fdn='', vat='', delivery_title='', recipient='',
    area='', delivery_phone='', qr='', airtel='', momo='', width='80',
    cash='0', card='0', coupon='0', mobile='0', loyalty='0', gift='0', promo='0',
    items=[dict(name='', qty='1', price='0')],
)


def new_receipt():
    return {**DEFAULT, 'date': date.today().isoformat(), 'items': [DEFAULT['items'][0].copy()]}

PAYMENTS = [('cash', 'Cash'), ('card', 'Credit Card Amount'), ('coupon', 'Coupon Amount'), ('mobile', 'Mobile Money'), ('loyalty', 'Loyalty Amount'), ('gift', 'Giftcard Amount'), ('promo', 'Promo Amount')]

def money(value):
    try:
        value = str(value)
        if len(value) > 64:
            raise ValueError('Numeric inputs must be at most 64 characters.')
        n = Decimal(value)
        if not n.is_finite() or n < 0 or n > Decimal('1000000000000'):
            raise ValueError('Amounts must be between 0 and 1 trillion.')
        return n
    except InvalidOperation:
        raise ValueError('Enter a valid number for quantities and amounts.') from None

def normalize(raw):
    if not isinstance(raw, dict):
        raise ValueError('Receipt must be an object.')
    d = {k: str(raw.get(k, v))[:2000] for k, v in DEFAULT.items() if k != 'items'}
    if d['width'] not in ('58', '80'):
        raise ValueError('Choose 58 or 80 mm paper.')
    items = raw.get('items', [])
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError('Add between 1 and 100 items.')
    d['items'] = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get('name', '')).strip():
            raise ValueError('Each item needs a name.')
        qty, price = money(item.get('qty', '')), money(item.get('price', ''))
        if qty == 0:
            raise ValueError('Item quantities must be greater than zero.')
        d['items'].append(dict(name=str(item['name'])[:300], qty=str(qty), price=str(price)))
    if len(d['qr'].encode('utf-8')) > 2000:
        raise ValueError('QR content must be at most 2,000 UTF-8 bytes.')
    for key, _ in PAYMENTS:
        d[key] = str(money(d[key]))
    return d

def render(d):
    e = lambda key: escape(d[key])
    amounts = [
        (money(item['qty']) * money(item['price'])).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_EVEN
        )
        for item in d['items']
    ]
    total = sum(amounts)
    rows = ''.join(
        f'<tr><td>{escape(item["name"])}</td><td>{money(item["qty"]):g}</td><td>{amount:,.2f}</td></tr>'
        for item, amount in zip(d['items'], amounts)
    )
    payments = ''.join(f'<div class="payment"><span>{label}:</span><b>{money(d[key]):,.2f}</b></div>' for key, label in PAYMENTS)
    qr = ''
    if d['qr'].strip():
        buf = io.BytesIO()
        qrcode.make(d['qr'], image_factory=qrcode.image.svg.SvgPathImage).save(buf)
        qr = '<img class="qr" alt="Receipt QR code" src="data:image/svg+xml;base64,' + base64.b64encode(buf.getvalue()).decode() + '">'
    return f'''<article class="receipt" style="--paper:{e('width')}mm">
      <header class="delivery-banner"><strong>{e('headline')}</strong><div>{e('phone_label')}</div><b>{e('phone1')}</b><b>{e('phone2')}</b></header>
      <div class="business">{e('business')}</div><div class="address">{e('address')}</div><div class="tin">Tin No: {e('tin')}</div>
      <h2>{e('title')}</h2><div>Customer Tin/Name</div><div>* {e('customer')}</div>
      <div class="meta"><div>Date: <span>{e('date')}</span></div><div>Number: <span>{e('number')}</span></div><div>Invoice No: <span>{e('invoice')}</span></div></div>
      <p class="identifier"><b>Verif Code: {e('verification')}</b></p><p class="identifier"><b>FDN: {e('fdn')}</b></p>
      <table><thead><tr><th>Item Name</th><th>Qty</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>
      <div class="payment total"><span>Total Amount:</span><b>{total:,.2f}</b></div>{payments}
      <div class="vat">{e('vat')}</div><h3>{e('delivery_title')}</h3><p class="recipient">Name: {e('recipient')}</p>
      <p class="area">Area: {e('area')}</p><div class="delivery-phone">{e('delivery_phone')}</div>{qr}
      <footer><p>{e('airtel')}</p><p>{e('momo')}</p></footer></article>'''

@contextmanager
def connect():
    con = sqlite3.connect(DB)
    try:
        with con:
            con.execute('CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, number TEXT, data TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
            yield con
    finally:
        con.close()

class Handler(BaseHTTPRequestHandler):
    def respond(self, content, status=200, kind='application/json'):
        content = content.encode() if isinstance(content, str) else content
        self.send_response(status)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def local_request(self):
        host = self.headers.get('Host', '').lower()
        port = self.server.server_port
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if port == 80:
            allowed.update({'127.0.0.1', 'localhost'})
        if host not in allowed:
            self.respond(json.dumps({'error': 'Open Receipt Studio via its loopback address.'}), 403)
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        url = urlparse(self.path)
        path = url.path
        if path == '/api/default':
            return self.respond(json.dumps(new_receipt()))
        if path == '/api/receipts/history':
            return self.receipt_history(url.query)
        if path == '/api/receipts':
            with connect() as con:
                rows = con.execute('SELECT id, number, created FROM receipts ORDER BY id DESC LIMIT 200').fetchall()
            return self.respond(json.dumps([dict(id=r[0], number=r[1], created=r[2]) for r in rows]))
        if path.startswith('/api/receipts/'):
            try:
                rid = int(path.rsplit('/', 1)[1])
            except ValueError:
                return self.respond('{}', 404)
            with connect() as con:
                row = con.execute('SELECT data FROM receipts WHERE id=?', (rid,)).fetchone()
            return self.respond(row[0] if row else '{}', 200 if row else 404)
        files = {'/': ('index.html', 'text/html'), '/style.css': ('style.css', 'text/css'), '/app.js': ('app.js', 'text/javascript')}
        if path in files:
            name, kind = files[path]
            return self.respond((ROOT / 'static' / name).read_bytes(), kind=kind)
        self.respond('{}', 404)

    def receipt_history(self, query):
        try:
            params = parse_qs(query, max_num_fields=10)
            search = params.get('q', [''])[0].strip()
            before = int(params.get('before', ['0'])[0])
            if len(search) > 200 or not 0 <= before < 2**63:
                raise ValueError
        except ValueError:
            return self.respond(json.dumps({'error': 'Invalid receipt history filter.'}), 400)

        conditions = []
        values = []
        if search:
            conditions.append('instr(lower(number), lower(?)) > 0')
            values.append(search)
        if before:
            conditions.append('id < ?')
            values.append(before)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        with connect() as con:
            rows = con.execute(
                'SELECT id, number, created FROM receipts' + where + ' ORDER BY id DESC LIMIT 51',
                values,
            ).fetchall()
        return self.respond(json.dumps({
            'receipts': [dict(id=row[0], number=row[1], created=row[2]) for row in rows[:50]],
            'next_before': rows[49][0] if len(rows) > 50 else None,
        }))

    def do_POST(self):
        if not self.local_request():
            return
        origin = self.headers.get('Origin')
        if origin is not None and origin != 'http://' + self.headers['Host'].lower():
            return self.respond(json.dumps({'error': 'Use the Receipt Studio tab to submit changes.'}), 403)
        if self.path not in ('/api/preview', '/api/receipts'):
            return self.respond('{}', 404)
        # JSON-only requests prevent cross-origin HTML forms from writing receipts.
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.respond(json.dumps({'error': 'JSON required.'}), 415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 300000:
                raise ValueError('Receipt is too large or empty.')
            d = normalize(json.loads(self.rfile.read(size)))
            html = render(d)
            result = {'html': html}
            if self.path == '/api/receipts':
                with connect() as con:
                    cur = con.execute('INSERT INTO receipts(number, data) VALUES (?, ?)', (d['number'], json.dumps(d)))
                    result['id'] = cur.lastrowid
            self.respond(json.dumps(result))
        except qrcode.exceptions.DataOverflowError:
            self.respond(json.dumps({'error': 'QR content is too long to encode.'}), 400)
        except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
            self.respond(json.dumps({'error': str(exc)}), 400)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Receipt Studio: {url}', flush=True)
    if args.open_browser:
        opener = Timer(0, webbrowser.open, args=(url,))
        opener.daemon = True
        opener.start()
    with server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
