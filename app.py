"""Local receipt studio. Run: python app.py"""
import argparse
import base64
import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import qrcode
import qrcode.image.svg

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'receipts.sqlite3'
DEFAULT = dict(headline='WE DELIVER', phone_label='Toll Free Number', phone1='0800 707070', phone2='0800 272727', business="CAFE JAVAS LTD - NAMIREMBE ROAD", address='Plot 18, Namirembe road, Kampala', tin='1000655193', title='Tax Invoice', customer='Cash Sale', date=date.today().isoformat(), number='KG178', invoice='CJABLCA20112628', verification='', fdn='', vat='Inclusive of VAT 18% where applicable', delivery_title='Delivery', recipient='Hope', area='Red Dot Distribution Ltd, CALL SIR APOLLO KAGWA RD, Red Dot Distribution Ltd, Uganda', delivery_phone='785376485', qr='', airtel='Airtel Money: *185*9# 1089441', momo='Momopay: *165*3# 115799', width='80', cash='638000', card='0', coupon='0', mobile='0', loyalty='0', gift='0', promo='0', items=[dict(name='AMAZING MUFFINS', qty='20', price='10000'), dict(name='COFFEE', qty='20', price='12000'), dict(name='DELIVERY CHARGES', qty='1', price='8000'), dict(name='SAMOSAS', qty='20', price='9500')])
PAYMENTS = [('cash', 'Cash'), ('card', 'Credit Card Amount'), ('coupon', 'Coupon Amount'), ('mobile', 'Mobile Money'), ('loyalty', 'Loyalty Amount'), ('gift', 'Giftcard Amount'), ('promo', 'Promo Amount')]

def money(value):
    try:
        n = Decimal(str(value))
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
    for key, _ in PAYMENTS:
        d[key] = str(money(d[key]))
    return d

def render(d):
    e = lambda key: escape(d[key])
    total = sum((money(i['qty']) * money(i['price'])).quantize(Decimal('.01')) for i in d['items'])
    rows = ''.join(f'<tr><td>{escape(i["name"])}</td><td>{money(i["qty"]):g}</td><td>{money(i["qty"]) * money(i["price"]):,.2f}</td></tr>' for i in d['items'])
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
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/default':
            return self.respond(json.dumps(DEFAULT))
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

    def do_POST(self):
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
        except (ValueError, TypeError, KeyError) as exc:
            self.respond(json.dumps({'error': str(exc)}), 400)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Receipt Studio: http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
