# Development and release checks

`app.py` serves the browser editor, validates receipt data, renders HTML and writes saved snapshots. `static/app.js` manages the editor, preview and printing. User-entered text is escaped before rendering.

The server multiplies unit price by quantity, rounds each line to two places using decimal half-even rounding, subtracts each rounded line discount, and applies the optional percentage tax after discounts. The payment summary displays a balance due or change based on the entered payments. Changing a price or quantity does not change the manually entered payment amounts.

The server binds to IPv4 loopback. Use it locally with `127.0.0.1` or `localhost`. The app has no user accounts or access controls for shared or hosted use.

## Verify changes

Run from the project folder after installing dependencies:

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

Before distributing a release, open, edit, save and reopen a receipt, check unsaved-edit prompts, preview both widths and test a long receipt with your printer or PDF driver. Record the operating system, browser, printer model and driver used. The automated suite exercises the local HTTP API and SQLite. Physical printer testing requires a printer.

Reference: [Python Decimal documentation](https://docs.python.org/3/library/decimal.html).
