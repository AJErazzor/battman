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
| The Settings card (`www/battman-settings.js`): a section, a setting, its label, limits or default, or what it does | `guide/intermediate/settings.md` (the "?" on each section opens its summary block) |
| A label, button or message a task in `guide/howto/tasks.md` names (its steps, and the `guide:show` markers' `text`) | `guide/howto/tasks.md`: the steps, and each `guide:show` so Show me still finds it (the tests check the text is in the card) |
| A card on the Power view (`views/05-power.yaml`, `cards/*.yaml`, `www/battman-house.js`, `www/battman-overrides*.js`): what it shows, its labels, what a press does | `guide/intermediate/power.md` (the "?" on each card opens its summary block `power.<card>`), and retake the card's screenshot in `www/guide-images/` if its look changed |

Rules for the guide:

- Quote labels, button names and messages exactly as the code and `translations/en.json` have them.
- Describe Battman as it is now. No history, no "used to", no names of earlier systems.
- A page's address (`?page=<track>/<slug>`) and its section headings are what links point at. Don't rename
  them; if you have to, fix every link to them.
- Pictures are screenshots in `www/guide-images/`, linked relative to the page (`../../www/guide-images/power-house.png`),
  with alt text that says what they show. Every file there is used by a page. They're taken at twice the size they're
  shown; a picture of a wide card has the title "wide" (`![…](…/power-x.png "wide")`).
- Link between pages with relative `.md` links (`../help/repairs.md#local-cards`), as GitHub does.
- Describe what Battman does, not its bugs: a known problem is a GitHub issue, not a note in the guide.
- A "?" on a card opens a summary block on a guide page: `<!-- guide:summary id="settings.buy" -->` … `<!-- /guide:summary -->`,
  straight under the section's heading. Keep the ids; the card looks them up.
- `tests/test_guide.py` checks the contents, every link and section, that every Repair is covered under its
  own title, that the device page quotes the buttons' messages, that every Settings section has a summary and every
  setting a heading, and that no old words have crept in.

## Tests

```bash
BATTMAN_NO_SKIPS=1 BATTMAN_CHROME=<chromium> BATTMAN_NODE_PATH=<node_modules with playwright> \
  python -m pytest -q -n 8
```

Setup is described at the top of `requirements_test.txt`. GitHub runs the whole suite on every push and
pull request.

## Releases

A merge into `main` publishes a HACS release when a commit in it has a message starting with `major:`,
`minor:` or `patch:`, once the tests pass. The release workflow reads commit messages, not the pull request
title, so put the prefix on the commit message (for a squash merge, the commit title) as well as the PR title.
Anything else releases nothing.
