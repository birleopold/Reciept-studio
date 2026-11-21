# Printing, storage and backups

## Print or save a PDF

Choose the same paper width in Receipt Studio and in your printer driver. Use 100% scale, disable browser headers and footers, and check the print preview before printing. For PDF, select **Save as PDF** in the browser and review the saved output. If your browser does not offer the thermal width for PDF, use A4. The thermal roll width and printable area can differ because of printer margins. Print a test receipt before using a new driver or printer.

Scan a printed QR code with a separate device before relying on it. The app encodes the supplied text or URL. It cannot verify its contents or issue a tax verification code.

## Manage saved receipts

Each save creates a separate snapshot. The selector shows the newest 200 snapshots. Opening an existing receipt and saving again creates a new entry. Save before closing the tab if you want to preserve your edits.

To back up, stop Receipt Studio with Ctrl+C, then copy `receipts.sqlite3` from the project folder to your backup location. To restore, stop the app, keep a separate copy of the current database, and copy the backup into the project folder under the original name. Restart the app and open a saved receipt to verify it. The database can include customer and delivery details. Store backups somewhere private.

Reference: [MDN printing guide](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Printing) and [Python SQLite documentation](https://docs.python.org/3/library/sqlite3.html).
