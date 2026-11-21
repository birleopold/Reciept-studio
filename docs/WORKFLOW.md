# Printing, storage and backups

## Print or save a PDF

Choose the same paper width in Receipt Studio and in your printer driver. Use 100% scale, disable browser headers and footers, and check the print preview before printing. For PDF, select **Save as PDF** in the browser and review the saved output. If your browser does not offer the thermal width for PDF, use A4. The thermal roll width and printable area can differ because of printer margins. Print a test receipt before using a new driver or printer.

Scan a printed QR code with a separate device before relying on it. The app encodes the supplied text or URL. It cannot verify its contents or issue a tax verification code.

## Manage saved receipts

Issue receipt assigns a unique number and saves the original. Use **Reprint / Save PDF** to print it again or **Duplicate as draft** to create an editable copy with a new number on issue. Older snapshots are still editable. Search by receipt number or select **Load older receipts** to browse earlier snapshots. Results appear newest first. The active draft and saved business/printer profiles are stored in the current browser. Reloading restores the draft. Starting a new receipt or opening history replaces the draft after confirmation when there are edits. Use the same browser profile and localhost URL to keep access to autosaved drafts and profiles.

Under **Profiles and exports**, choose **Download database backup** to take a consistent SQLite copy while the app runs. This includes saved receipts and issued originals. Browser drafts and profiles are kept separately. You can also export a CSV register filtered by UTC save date. With no range, the export includes all saved receipts.

### Recover a backup

From the project folder, run:

```text
python app.py --recover "receipt-studio.sqlite3" "recovered.sqlite3"
python app.py --database "recovered.sqlite3" --port 8766
```

Use your virtual environment's Python if needed. The first command checks integrity and creates a new file only. It refuses to overwrite any existing file. Open http://127.0.0.1:8766 and verify the receipt register and a reprint. To keep using that database, start Receipt Studio with `--database "recovered.sqlite3"` on subsequent launches.

The database can include customer and delivery details. Store backups somewhere private.

Reference: [MDN printing guide](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Printing) and [Python SQLite documentation](https://docs.python.org/3/library/sqlite3.html).
