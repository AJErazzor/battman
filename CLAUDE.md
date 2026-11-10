# Working on Battman

Notes for anyone (person or AI) changing Battman's code.

## Keep the built-in guide in step

Battman's user guide is in `custom_components/battman/guide/`: Markdown, one file per page, listed in
`guide/index.yaml`. It ships with the integration and is shown on the dashboard's **Help** view
(`custom:battman-guide`), and GitHub shows the same files.

When a change alters what someone sees or does, update the guide in the same change:

| If you change | Update |
|---|---|
| The device buttons or actions (`button.py`, `services.py`, `services.yaml`, `dashboard.py`, the button and service text in `translations/en.json`) | `guide/start/device-page.md` |
| A Repair (anything under `issues` in `translations/en.json`, or the code that raises one) | `guide/help/repairs.md` |
| Which views a new dashboard has (`views/*.yaml`) | `guide/start/device-page.md` (the list of views) |
| The Show help setting or how the Help view is added and removed (`help_setting.py`, `dashboard.py`) | `guide/README.md` (Showing or hiding the guide) |

Rules for the guide:

- Quote labels, button names and messages exactly as the code and `translations/en.json` have them.
- Describe Battman as it is now. No history, no "used to", no names of earlier systems.
- A page's address (`?page=<track>/<slug>`) and its section headings are what links point at. Don't rename
  them; if you have to, fix every link to them.
- Link between pages with relative `.md` links (`../help/repairs.md#local-cards`), as GitHub does.
- Known problems are stated plainly where they matter, not hidden.
- `tests/test_guide.py` checks the contents, every link and section, that every Repair is covered under its
  own title, that the device page quotes the buttons' messages, and that no old words have crept in.

## Tests

```bash
BATTMAN_NO_SKIPS=1 BATTMAN_CHROME=<chromium> BATTMAN_NODE_PATH=<node_modules with playwright> \
  python -m pytest -q -n 8
```

Setup is described at the top of `requirements_test.txt`. GitHub runs the whole suite on every push and
pull request.

## Releases

A pull request whose title starts with `major:`, `minor:` or `patch:` publishes a HACS release when it's
merged into `main`, once the tests pass. Any other title releases nothing.
