# Receipt Studio

Receipt Studio is a local Python app for creating, saving and printing receipts on 58 mm or 80 mm paper. It opens in your browser and stores saved snapshots in SQLite on your computer.

## Quick start

Use Python 3.10 or newer. On Windows, double-click `start.bat`, or run these commands from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

On macOS or Linux, use `.venv/bin/python` in place of the Windows virtual environment executable. Visit http://127.0.0.1:8765. Keep the terminal open while working and press Ctrl+C to stop the app. Pass `--port 8001` to use another port.

## Make a receipt

1. Enter your own business details and add at least one named line item. Enter quantity and unit price for each item.
2. Enter any payment amounts separately. Receipt Studio does not collect payments or reconcile them against the total.
3. Optionally enter QR content and choose a paper width.
4. Select **Issue receipt** to assign a number and store the original, or **Print / Save PDF** to open the browser print dialog.

Use **Profiles and exports** to reuse business and printer settings, download a database backup, or export a receipt register.

The default receipt is blank apart from the current date and initial item controls. Verification codes and FDNs must come from your invoicing system. Receipt Studio has no tax-system integration.

- [Printing, storage and backups](docs/WORKFLOW.md)
- [Architecture, testing and release checks](docs/DEVELOPMENT.md)
