# V0.4.2 Preview Fix

This overlay fixes Jinja dictionary key collisions in both import preview templates.

Replace these files in the V0.4.2 repository:

- `app/templates/import_preview.html`
- `app/templates/costs_import_preview.html`

The bug was caused by `data.items`, which Jinja resolved as Python's `dict.items` method. The templates now use explicit dictionary access such as `data["items"]`.

No database changes are required.
