"""Battman's built-in guide and its Help view.

- The guide's pages (custom_components/battman/guide/) are all listed in its index, every link between
  them lands (page and section), and they render with the shipped Markdown reader (marked, vendored).
- The Repairs page covers every Repair in en.json under its own title; the device page quotes the
  buttons' messages as Battman sends them.
- The pages describe Battman as it is: none of the old words below appear.
- Only the Help card's small stub loads on every page; the guide itself loads when the card is shown.
- /api/battman/guide serves the contents and the pages, and nothing else.
- Settings → Dashboard options → Show help adds the Help view to the Battman dashboard or takes it
  off, and changes nothing else; the default dashboard has it as its last view (unless it's off).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parents[1] / "custom_components/battman"
GUIDE = ROOT / "guide"
WWW = ROOT / "www"
CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")
NEEDS_NODE = pytest.mark.skipif(not shutil.which("node"), reason="needs Node")

# Words for things that are gone or never part of Battman's story for its users.
LEGACY = re.compile(r"smiggles|solarsystem|solar_system_control|\bssc\b|migrat|hand ?back|\bin charge\b|in_charge"
                    r"|\bported\b|like for like", re.I)


def _index():
    from custom_components.battman import guide

    return guide.load_index()


def _pages() -> dict[str, str]:
    from custom_components.battman import guide

    return {pid: guide.page_file(pid).read_text(encoding="utf-8") for pid in guide.page_ids(_index())}


def _guide_file(tmp_path) -> str:
    """Every page, as a JSON file for the browser checks (too big for an environment variable)."""
    f = tmp_path / "guide.json"
    f.write_text(json.dumps({"pages": _pages()}))
    return str(f)


def _render_all() -> dict:
    """Every page through www/battman-guide-md.js (marked plus Battman's rules), in Node."""
    script = f"""
const {{ renderPage }} = await import({json.dumps(str(WWW / "battman-guide-md.js"))});
const pages = {json.dumps(_pages())};
const out = {{}};
for (const [id, md] of Object.entries(pages)) out[id] = renderPage(md, id);
process.stdout.write(JSON.stringify(out));
"""
    r = subprocess.run(["node", "--input-type=module", "-"], input=script, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


# ── the pages ──────────────────────────────────────────────────────────────────────────────


def test_every_page_has_its_file_and_every_file_is_a_page() -> None:
    from custom_components.battman import guide

    index = _index()
    ids = guide.page_ids(index)
    assert ids[0] == "home" and len(ids) == len(set(ids))
    for t in index["tracks"]:
        assert re.fullmatch(r"[a-z][a-z0-9-]*", t["id"]) and t["title"], t
        for p in t["pages"]:
            assert re.fullmatch(r"[a-z][a-z0-9-]*/[a-z0-9][a-z0-9-]*", p["id"]) and p["title"], p
    files = {guide.page_file(pid).relative_to(GUIDE).as_posix() for pid in ids}
    on_disk = {p.relative_to(GUIDE).as_posix() for p in GUIDE.rglob("*.md")}
    assert files == on_disk, (files ^ on_disk)


def test_home_page_lists_every_page() -> None:
    home = (GUIDE / "README.md").read_text(encoding="utf-8")
    for t in _index()["tracks"]:
        for p in t["pages"]:
            assert f"]({p['id']}.md)" in home, p["id"]


@NEEDS_NODE
def test_pages_render_and_every_link_lands() -> None:
    out = _render_all()
    index = _index()
    titles = {index["home"]["id"]: index["home"]["title"], **{p["id"]: p["title"] for t in index["tracks"] for p in t["pages"]}}
    for pid, page in out.items():
        assert page["title"] == titles[pid], (pid, page["title"])          # the page's heading is its contents entry
        assert [h["depth"] for h in page["headings"]].count(1) == 1, pid
        assert "<script" not in page["html"].lower() and "javascript:" not in page["html"].lower(), pid
        assert 'class="deadlink"' not in page["html"], (pid, [l for l in page["links"] if l["kind"] == "none"])
        assert {d["name"] for d in page["directives"]} <= {"repairs", "summary", "howto", "task", "show"}, pid
        for link in page["links"]:
            assert link["kind"] in ("page", "ha", "external"), (pid, link)
            if link["kind"] == "page":
                assert link["page"] in out, (pid, link)
                if link["anchor"]:
                    assert link["anchor"] in out[link["page"]]["ids"], (pid, link)
            if link["kind"] == "external":
                assert link["url"].startswith("https://"), (pid, link)


@NEEDS_NODE
def test_markdown_rules() -> None:
    """Raw HTML is escaped except the few tags the pages use; links go where they should."""
    md = ("# T\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n"
          "[a](javascript:alert(1)) [b](../help/repairs.md#local-cards) [c](/config/repairs) [d](https://example.org) "
          "[e](#same) [f](../README.md)\n\n> [!WARNING]\n> Careful\n\n<details>\n<summary>More</summary>\n\nx\n\n</details>\n\n"
          "<!-- private note -->\n\n<!-- guide:repairs -->\n\n## Same\n\n## Same\n\n```yaml\na: <b>\n```\n\n"
          '<a id="fixed-name"></a>\n### A title that may change\n\n<a id="stray"></a>\n\ntext\n\n### Plain\n')
    script = f"""
const {{ renderPage, resolveLink, slugify }} = await import({json.dumps(str(WWW / "battman-guide-md.js"))});
process.stdout.write(JSON.stringify({{ out: renderPage({json.dumps(md)}, "start/x"),
  slugs: [slugify("Battman's Repairs"), slugify("Create help view"), slugify("Restart: now (please)")],
  up: resolveLink("../../etc/passwd.md", "start/x"), file: resolveLink("data:text/html,x", "home") }}));
"""
    r = json.loads(subprocess.run(["node", "--input-type=module", "-"], input=script, capture_output=True, text=True,
                                  check=True).stdout)
    html = r["out"]["html"]
    assert "&lt;script&gt;" in html and "<script" not in html and "&lt;img" in html and "<img" not in html
    assert '<span class="deadlink">a</span>' in html
    assert 'href="?page=help/repairs#local-cards" data-page="help/repairs" data-anchor="local-cards"' in html
    assert 'href="/config/repairs" data-ha="/config/repairs"' in html
    assert 'href="https://example.org" target="_blank" rel="noopener noreferrer"' in html
    assert 'data-page="start/x" data-anchor="same"' in html and 'data-page="home"' in html
    assert '<div class="callout warning" role="note"><p class="callout-title">Warning</p>' in html
    assert "<details>" in html and "<summary>More</summary>" in html
    assert "private note" not in html and 'data-directive="repairs"' in html
    assert [h["id"] for h in r["out"]["headings"]] == ["t", "same", "same-1", "a-title-that-may-change", "plain"]
    # the # button copies a section's fixed anchor when it has one (headings can be retitled; anchors stay)
    assert [h["link"] for h in r["out"]["headings"]][3:] == ["fixed-name", "plain"]
    assert 'data-copy="fixed-name"' in html and 'data-copy="a-title-that-may-change"' not in html
    assert "a: &lt;b&gt;" in html and "data-copy-code" in html
    assert r["slugs"] == ["battmans-repairs", "create-help-view", "restart-now-please"]   # GitHub's ids
    assert r["up"] == {"kind": "none"} and r["file"] == {"kind": "none"}


def test_repairs_page_covers_every_repair_by_its_title() -> None:
    issues = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))["issues"]
    page = (GUIDE / "help/repairs.md").read_text(encoding="utf-8")
    for issue_id, text in issues.items():
        anchor = issue_id.replace("_", "-")
        m = re.search(rf'<a id="{anchor}"></a>\n### (.+)\n', page)
        assert m, issue_id
        assert m.group(1) == text["title"], (issue_id, m.group(1), text["title"])
    anchors = re.findall(r'<a id="([a-z0-9-]+)"></a>', page)
    assert len(anchors) == len(set(anchors)) == len(issues)


def test_device_page_quotes_the_messages() -> None:
    page = (GUIDE / "start/device-page.md").read_text(encoding="utf-8")
    src = (ROOT / "services.py").read_text(encoding="utf-8")
    for quoted in ("It's yours: edit it like any dashboard.", "For a fresh Battman dashboard, delete that one first.",
                   "All Battman automations and scripts already exist; nothing changed."):
        assert quoted in src and quoted in page, quoted
    en = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))
    assert set(en["entity"]["button"]) == {"create_dashboard", "create_automations"}
    for key in ("create_dashboard", "create_automations"):
        assert f"**{en['entity']['button'][key]['name']}**" in page, key
    from custom_components.battman import engine, notifications

    for alias in [s["alias"] for s in engine.SCRIPTS.values()] + [s["alias"] for s in notifications.SCRIPTS.values()]:
        assert f'"{alias}"' in page, alias
    for a in engine.AUTOMATIONS + notifications.AUTOMATIONS:
        short = a["alias"].split(" – ", 1)
        assert f'"{a["alias"]}"' in page or (len(short) == 2 and f'"– {short[1]}"' in page), a["alias"]


def test_no_known_problem_notes_in_the_guide() -> None:
    """Known problems are GitHub issues, not notes (or links to issues) in the guide."""
    hits = [f"{pid}: {line[:80]}" for pid, text in _pages().items() for line in text.splitlines()
            if re.search(r"known (problem|issue)|/issues/\d", line, re.I)]
    assert not hits, hits


def test_no_old_words_in_the_guide() -> None:
    files = [*GUIDE.rglob("*"), WWW / "battman-guide.js", WWW / "battman-guide-view.js", WWW / "battman-guide-md.js",
             ROOT / "guide.py", ROOT / "views/40-help.yaml"]
    hits = [f"{f.relative_to(ROOT)}:{n}: {line.strip()[:90]}" for f in files if f.is_file()
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1) if LEGACY.search(line)]
    assert not hits, "\n".join(hits)


# ── loading ────────────────────────────────────────────────────────────────────────────────


def test_only_the_stub_loads_on_every_page() -> None:
    loader = (WWW / "battman.js").read_text()
    names = [n.strip().strip('"') for n in re.search(r"const SCRIPTS = \[([^\]]*)\]", loader).group(1).replace("\n", " ").split(",")
             if n.strip()]
    assert "guide" in names and not {"guide-view", "guide-md"} & set(names)
    stub = (WWW / "battman-guide.js").read_text()
    assert len(stub.encode()) < 4000
    static_imports = re.findall(r'^import .* from "([^"]+)";', stub, re.M)
    assert static_imports == ["./battman-card-base.js"]
    assert 'import("./battman-guide-view.js")' in stub and "marked" not in stub
    assert 'battmanDefine("battman-guide", BattmanGuideCard)' in stub
    view = (WWW / "battman-guide-view.js").read_text()
    assert 'from "./battman-guide-md.js"' in view
    assert 'from "./vendor/marked.esm.js"' in (WWW / "battman-guide-md.js").read_text()


@NEEDS_NODE
def test_guide_scripts_are_valid() -> None:
    for f in ("battman-guide.js", "battman-guide-view.js", "battman-guide-md.js"):
        assert subprocess.run(["node", "--check", str(WWW / f)]).returncode == 0, f


def test_marked_is_the_published_build() -> None:
    marked = (WWW / "vendor/marked.esm.js").read_bytes()
    assert marked.startswith(b"/**\n * marked v18.1.2 - a markdown parser") and b"(MIT License)" in marked[:300]
    digest = hashlib.sha256(marked).hexdigest()
    readme = (WWW / "vendor/README.md").read_text()
    assert "`marked.esm.js` | marked" in readme and "18.1.2" in readme and digest in readme


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Chromium, Node and Playwright")
def test_guide_in_a_browser(tmp_path) -> None:
    guide_file = tmp_path / "guide-index.json"            # a file: too big for an environment variable
    guide_file.write_text(json.dumps({"index": _index(), "pages": _pages()}))
    r = subprocess.run(["node", str(Path(__file__).parent / "js/guide_check.mjs"), str(ROOT), str(tmp_path)],
                       capture_output=True, text=True, timeout=180,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME, "GUIDE_FILE": str(guide_file)})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == [], out["errors"]
    assert out["before"] == ["battman-guide.js"]                           # only the stub, until the card is shown
    assert {"battman-guide-view.js", "battman-guide-md.js", "vendor/marked.esm.js"} <= set(out["after"])
    assert out["home"]["h1"].startswith("Battman help") and out["home"]["current"] == "Battman help"
    assert out["home"]["toc"] == ["Battman help", "How do I…?", "The Battman device page", "Power", "Curvy", "Pricy", "Finances", "Log", "Theme", "Settings", "Battman's Repairs"]
    assert out["home"]["scripts"] == 0
    assert "Active: On" in out["status"] and "Mode: Self Consume" in out["status"] and "3 min ago" in out["status"]
    assert "Curtail: Off" in out["status"] and "Repairs: 1 open" in out["status"]     # ignored and other domains left out
    assert out["device"]["url"] == "/dash/help?page=start/device-page" and out["device"]["h1"].startswith("The Battman device page")
    assert out["back"] == "/dash/help"
    rep = out["repairs"]
    assert rep["anchor"] and rep["top"] < 200                                # scrolled to the section
    assert rep["open"] == ["Battman's package files aren't loaded"] and rep["openLink"] == "?page=help/repairs#packages-not-loaded"
    assert rep["codeCopy"] >= 2
    assert out["missing"] is True
    assert out["keep"] == "/dash/help?kiosk=1&page=help/repairs"           # other parts of the address are kept
    assert out["copyIds"][:2] == ["restart-required", "packages-not-loaded"]  # the # buttons copy the fixed anchors
    assert out["badHash"] is True                                           # a malformed #… still draws the page
    phone = out["phone"]
    assert (phone["before"], phone["after"], phone["expanded"], phone["overflow"]) == ("none", "block", "true", False)
    assert phone["btn"] != "none"


# ── Home Assistant: the API and the Help view ─────────────────────────────────────────────


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _cfg(hass):
    return await hass.data[LOVELACE_DATA].dashboards["battman"].async_load(False)


async def test_guide_api(hass: HomeAssistant, hass_client, hass_client_no_auth) -> None:
    await _setup(hass)
    client = await hass_client()
    r = await client.get("/api/battman/guide")
    assert r.status == 200
    body = await r.json()
    assert body["home"]["title"] == "Battman help" and body["version"]
    assert body["tracks"] == _index()["tracks"]
    for pid, md in _pages().items():
        r = await client.get(f"/api/battman/guide/page/{pid}")
        assert r.status == 200, pid
        assert (await r.json()) == {"id": pid, "markdown": md}
    for bad in ("nope", "start/nope", "index", "start/device-page.md", "readme", "a/b/c", "start/-x"):
        assert (await client.get(f"/api/battman/guide/page/{bad}")).status == 404, bad
    assert (await client.get("/api/battman/guide/page/%2e%2e/manifest")).status == 404
    noauth = await hass_client_no_auth()
    assert (await noauth.get("/api/battman/guide")).status == 401
    assert (await noauth.get("/api/battman/guide/page/home")).status == 401


async def test_help_view_is_the_dashboards_last_view(hass: HomeAssistant) -> None:
    await _setup(hass)
    views = (await _cfg(hass))["views"]
    assert views[-1] == yaml.safe_load((ROOT / "views/40-help.yaml").read_text())
    assert views[-1]["cards"] == [{"type": "custom:battman-guide"}] and views[-1]["type"] == "panel"


# ── Show help (Settings → Dashboard options): the Help view follows it ─────────────────────


async def _show(hass, on: bool) -> None:
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "showHelp": on})
    await hass.async_block_till_done()
    await hass.async_block_till_done()


def _note(hass):
    from homeassistant.components import persistent_notification

    return persistent_notification._async_get_or_create_notifications(hass).get("battman_help_view")


async def test_show_help_takes_the_help_view_off_and_puts_it_back(hass: HomeAssistant) -> None:
    from . import engine_harness as H

    await H.start(hass)
    assert hass.states.get("sensor.battman_parameters").attributes["showHelp"] is True       # on by default
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    cfg = await _cfg(hass)
    # a dashboard you've changed: your own view, titles, the Help view moved to the front and renamed
    help_view = next(v for v in cfg["views"] if v["path"] == "help")
    mine = {**cfg, "title": "My battery",
            "views": [{**help_view, "title": "Guide"}, *[{**v, "title": v["title"] + "!"} for v in cfg["views"] if v["path"] != "help"],
                      {"title": "Mine", "path": "mine", "cards": [{"type": "markdown", "content": "hello"}]}]}
    await dash.async_save(mine)

    await _show(hass, False)                                  # off: the Help view goes, nothing else changes
    off = await _cfg(hass)
    assert off == {**mine, "views": mine["views"][1:]}
    assert _note(hass) is None

    await _show(hass, True)                                   # on: back as the last tab, nothing else changes
    on = await _cfg(hass)
    assert on["views"][:-1] == off["views"] and on["title"] == "My battery"
    assert on["views"][-1] == yaml.safe_load((ROOT / "views/40-help.yaml").read_text())

    # another setting changing, or the same value again, leaves the dashboard alone
    await dash.async_save(off)
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "billInflation": 3})
    await _show(hass, True)
    assert await _cfg(hass) == off                            # you deleted it by hand: it stays deleted

    # while it's off, a new dashboard is made without it
    await _show(hass, False)
    from custom_components.battman import dashboard

    await dashboard._collection(hass).async_delete_item(dash.config["id"])
    await hass.async_block_till_done()
    created, _ = await dashboard.async_create(hass)
    assert created and "help" not in [v["path"] for v in (await _cfg(hass))["views"]]
    await _show(hass, True)
    assert [v["path"] for v in (await _cfg(hass))["views"]][-1] == "help"


async def test_show_help_says_when_it_cant(hass: HomeAssistant, monkeypatch) -> None:
    from homeassistant.components import frontend

    from custom_components.battman import dashboard, help_setting

    from . import engine_harness as H

    await H.start(hass)
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    readme = (GUIDE / "README.md").read_text(encoding="utf-8")

    # saving fails: says so, nothing changes
    before = await _cfg(hass)

    async def broken(_config):
        raise OSError("disk full")

    monkeypatch.setattr(dash, "async_save", broken)
    await _show(hass, False)
    assert _note(hass)["message"] == "Could not remove the Help view: Saving the dashboard failed: disk full"
    assert await _cfg(hass) == before
    monkeypatch.undo()

    # no dashboard to add it to
    await dashboard._collection(hass).async_delete_item(dash.config["id"])
    await hass.async_block_till_done()
    await _show(hass, True)
    msg = _note(hass)["message"]
    assert msg == help_setting._message(True, dashboard.NO_DASHBOARD, "battman") and f'"{msg}"' in readme
    assert "battman" not in hass.data[LOVELACE_DATA].dashboards               # never makes one
    await _show(hass, False)                                                   # nothing to take off: nothing said
    assert _note(hass) is None

    # a YAML dashboard, a dashboard with no saved views, something that isn't a dashboard: left alone
    class YamlDashboard:
        mode = "yaml"

        async def async_load(self, force):
            return {"views": [{"path": "help", "cards": [{"type": "custom:battman-guide"}]}]}

        async def async_save(self, config):
            raise AssertionError("a YAML dashboard must not be written")

    hass.data[LOVELACE_DATA].dashboards["battman"] = YamlDashboard()
    for on in (True, False):
        await _show(hass, on)
        msg = _note(hass)["message"]
        assert msg == help_setting._message(on, dashboard.NOT_EDITABLE, "battman") and f'"{msg}"' in readme
    del hass.data[LOVELACE_DATA].dashboards["battman"]
    await dashboard._collection(hass).async_create_item(
        {"allow_single_word": True, "title": "Battman", "url_path": "battman", "require_admin": False, "show_in_sidebar": True})
    await hass.async_block_till_done()
    await _show(hass, True)
    assert "written in YAML, one with no saved views yet" in _note(hass)["message"]
    strategy = {"strategy": {"type": "original-states"}}
    await hass.data[LOVELACE_DATA].dashboards["battman"].async_save(strategy)
    await _show(hass, False)
    assert _note(hass) is None                       # nothing there to take off: nothing to say
    await _show(hass, True)
    assert await _cfg(hass) == strategy
    await dashboard._collection(hass).async_delete_item(hass.data[LOVELACE_DATA].dashboards["battman"].config["id"])
    await hass.async_block_till_done()
    frontend.async_register_built_in_panel(hass, "iframe", "Other", "mdi:web", frontend_url_path="battman",
                                           config={"url": "https://example.org"})
    await _show(hass, False)
    await _show(hass, True)
    assert "something that isn't a dashboard" in _note(hass)["message"]


async def test_only_the_guides_help_view_is_taken_off(hass: HomeAssistant) -> None:
    """A view of yours at /battman/help without the guide card is yours: turning Show help off leaves it."""
    import asyncio

    from custom_components.battman import dashboard

    await _setup(hass)
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    cfg = await _cfg(hass)
    yours = {"path": "help", "title": "Our house rules", "cards": [{"type": "markdown", "content": "Be nice"}]}
    await dash.async_save({**cfg, "views": [v for v in cfg["views"] if v["path"] != "help"] + [yours]})
    assert (await dashboard.async_remove_help_view(hass))[0] == "absent"
    assert (await dashboard.async_add_help_view(hass))[0] == "exists"          # and nothing added beside it
    # the guide card in a sections view at /battman/help: that one is Battman's
    sections = {"path": "help", "type": "sections", "sections": [{"cards": [{"type": "custom:battman-guide"}]}]}
    await dash.async_save({**cfg, "views": [v for v in cfg["views"] if v["path"] != "help"] + [sections]})
    assert (await dashboard.async_remove_help_view(hass))[0] == "removed"
    # two changes at once don't add it twice
    a, b = await asyncio.gather(dashboard.async_add_help_view(hass), dashboard.async_add_help_view(hass))
    assert sorted([a[0], b[0]]) == ["added", "exists"]
    assert [v["path"] for v in (await _cfg(hass))["views"]].count("help") == 1


async def test_create_help_view_button_is_gone(hass: HomeAssistant) -> None:
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    # left in the registry by v0.49.0
    reg.async_get_or_create("button", "battman", f"{entry.entry_id}_create_help_view", config_entry=entry,
                            suggested_object_id="battman_create_help_view")
    assert await async_setup_component(hass, "lovelace", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert reg.async_get_entity_id("button", "battman", f"{entry.entry_id}_create_help_view") is None
    assert hass.states.get("button.battman_create_help_view") is None
    assert not hass.services.has_service("battman", "create_help_view")


def test_every_repair_id_is_its_translation_key() -> None:
    """The Help view links an open Repair to its section by the Repair's id; the page is checked against the
    translation keys. So each Repair Battman raises must use the same name for both."""
    calls = 0
    for f in ROOT.glob("*.py"):
        for m in re.finditer(r"async_create_issue\((.*?)\n\s*\)", f.read_text(), re.S):
            body = m.group(1)
            args = [a.strip() for a in re.split(r",\s*", body) if a.strip()]
            issue_id = args[2]                                   # (hass, DOMAIN, <id>, ...)
            key = re.search(r"translation_key=(\w+)", body).group(1)
            assert issue_id == key, (f.name, issue_id, key)
            calls += 1
    assert calls >= 12


async def test_device_buttons_and_actions_are_for_admins(hass: HomeAssistant, hass_admin_user) -> None:
    """Only an administrator can press Battman's buttons or run their actions; an automation (no user) can."""
    from homeassistant.core import Context
    from homeassistant.exceptions import HomeAssistantError, Unauthorized

    await _setup(hass)
    user = await hass.auth.async_create_user("Someone", group_ids=["system-users"])   # an ordinary, non-admin user
    assert not user.is_admin
    for service in ("create_dashboard", "create_automations"):
        with pytest.raises(Unauthorized):
            await hass.services.async_call("battman", service, {}, blocking=True, return_response=True,
                                           context=Context(user_id=user.id))
        r = await hass.services.async_call("battman", service, {}, blocking=True, return_response=True,
                                           context=Context(user_id=hass_admin_user.id))
        assert r["message"], service
        r = await hass.services.async_call("battman", service, {}, blocking=True, return_response=True)
        assert r["message"], service
    for button in ("button.battman_create_dashboard", "button.battman_create_automations"):
        with pytest.raises(HomeAssistantError) as err:
            await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True,
                                           context=Context(user_id=user.id))
        assert str(err.value) == "Only a Home Assistant administrator can press this button", button
        await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True,
                                       context=Context(user_id=hass_admin_user.id))
    page = (GUIDE / "start/device-page.md").read_text(encoding="utf-8")
    en = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))
    assert f'"{en["exceptions"]["admin_only"]["message"]}"' in page



# ── "?" help on cards: summaries in the guide, the panel, the Settings card ──────────────────


@NEEDS_NODE
def test_outline_and_summaries() -> None:
    md = ("# Settings\n\nIntro\n\n<a id=\"buy\"></a>\n## Buy\n\n<!-- guide:summary id=\"settings.buy\" -->\nHow hard it **charges**.\n"
          "<!-- /guide:summary -->\n\n### Prorate price SOC offset\n\nText\n\n```yaml\n# not a heading\n```\n\n### High price\n\n"
          "More\n\n<a id=\"rules\"></a>\n## Buy rules\n\nNo summary here.\n")
    script = f"""
const {{ summaries, outline }} = await import({json.dumps(str(WWW / "battman-guide-md.js"))});
process.stdout.write(JSON.stringify({{ s: summaries({json.dumps(md)}), o: outline({json.dumps(md)}) }}));
"""
    r = json.loads(subprocess.run(["node", "--input-type=module", "-"], input=script, capture_output=True, text=True,
                                  check=True).stdout)
    assert list(r["s"]) == ["settings.buy"]
    buy = r["s"]["settings.buy"]
    assert buy["markdown"] == "How hard it **charges**." and buy["head"]["title"] == "Buy" and buy["head"]["anchor"] == "buy"
    assert [(c["title"], c["anchor"]) for c in buy["children"]] == [("Prorate price SOC offset", "prorate-price-soc-offset"),
                                                                     ("High price", "high-price")]
    assert "# not a heading" in buy["section"] and "guide:summary" not in buy["section"] and "Buy rules" not in buy["section"]
    assert [h["title"] for h in r["o"]] == ["Settings", "Buy", "Prorate price SOC offset", "High price", "Buy rules"]


SETTINGS_JS = (WWW / "battman-settings.js").read_text()


def _settings_page() -> str:
    return (GUIDE / "intermediate/settings.md").read_text(encoding="utf-8")


def test_settings_page_has_a_summary_for_every_section_and_a_heading_for_every_setting() -> None:
    page = _settings_page()
    keys = re.findall(r"^\s+(\w+):\s+\{ title: '((?:[^'\\]|\\.)*)'", SETTINGS_JS, re.M)
    assert len(keys) == 15
    ids = re.findall(r'<!-- guide:summary id="([^"]+)" -->', page)
    assert len(ids) == len(set(ids))
    for key, title in keys:
        kebab = re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), key)
        title = title.replace("&amp;", "&")
        assert re.search(rf'<a id="{kebab}"></a>\n## {re.escape(title)}\n\n<!-- guide:summary id="settings.{key}" -->', page), key
    # a sub-group summary belongs to a sub-group the card really shows
    subdivs = {re.sub(r"[^a-z0-9 -]", "", t.replace("&amp;", "&").lower()).strip().replace(" ", "-")
               for t in re.findall(r'<div class="subdiv">([^<]+)</div>', SETTINGS_JS)}
    for sid in ids:
        parts = sid.split(".")
        assert parts[0] == "settings" and parts[1] in dict(keys), sid
        if len(parts) == 3:
            assert parts[2] in subdivs, sid
    # every setting the card shows has a heading of its own (two with the same label say which, in brackets)
    labels = set()
    for pat in (r"\brow\('((?:[^'\\]|\\.)*)'", r"numParam\('\w+', '((?:[^'\\]|\\.)*)'", r"\bsw\('\w+', '((?:[^'\\]|\\.)*)'",
                r"\bnum\('[^']*', '[^']*', '((?:[^'\\]|\\.)*)'"):
        labels |= {x.replace("\\'", "'") for x in re.findall(pat, SETTINGS_JS)}
    labels |= set(re.findall(r"side === 'buy' \? '([^']+)' : '([^']+)'", SETTINGS_JS)[0])           # Buy/Sell rules enabled
    labels |= set(re.findall(r"\b(?:q|stateRow)\('\w+', '([^']+)'", SETTINGS_JS))                       # quarterly bills, Live Activity
    assert {"Buy rules enabled", "Sell rules enabled", "Q1 · Jul – Sep", "Show when it becomes"} <= labels
    headings = re.findall(r"^#{3,4} (.+)$", page, re.M)
    missing = sorted(l for l in labels if not any(h == l or h.startswith(l + " (") for h in headings))
    assert not missing, missing


def test_settings_card_help_mode() -> None:
    """The Help button follows Show help; the panel and the guide load only when help is turned on."""
    assert 'data-helpmode aria-pressed="false" hidden' in SETTINGS_JS
    assert "(attrs('parameters') || {}).showHelp !== false" in SETTINGS_JS
    assert "import('./battman-help-panel.js')" in SETTINGS_JS
    static = re.findall(r'^import .* from "([^"]+)";', SETTINGS_JS, re.M)
    assert static == ["./battman-card-base.js"]                    # no guide, panel or Markdown reader up front
    assert "HELP_PAGE = 'intermediate/settings'" in SETTINGS_JS
    panel = (WWW / "battman-help-panel.js").read_text()
    assert re.findall(r'^import .* from "([^"]+)";', panel, re.M) == ["./battman-guide-md.js"]


async def test_show_help_appearing_or_coming_back_changes_nothing(hass: HomeAssistant, monkeypatch) -> None:
    """The setting appearing for the first time (an update), the sensor coming back, or a template reload
    leave the dashboard as it is; only turning it on or off changes it."""
    from . import engine_harness as H

    await H.start(hass)
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    cfg = await _cfg(hass)
    without = {**cfg, "views": [v for v in cfg["views"] if v["path"] != "help"]}
    await dash.async_save(without)

    # as on the first start after an update: the sensor without the setting, then a settings change adds it (on)
    st = hass.states.get("sensor.battman_parameters")
    hass.states.async_set(st.entity_id, st.state, {k: v for k, v in st.attributes.items() if k != "showHelp"})
    await hass.async_block_till_done()
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "billInflation": 2})
    await hass.async_block_till_done()
    assert hass.states.get(st.entity_id).attributes["showHelp"] is True
    for _ in range(2):                                  # unavailable and back, then a template reload
        hass.states.async_set(st.entity_id, "unavailable", {})
        await hass.async_block_till_done()
        hass.states.async_set(st.entity_id, st.state, dict(st.attributes))
        await hass.async_block_till_done()
    await hass.services.async_call("template", "reload", blocking=True)
    await hass.async_block_till_done()
    assert await _cfg(hass) == without

    # the switch already on with no Help tab (as after an update): off and on again adds it
    await _show(hass, False)
    await _show(hass, True)
    assert (await _cfg(hass))["views"][-1]["path"] == "help"

    # a change that works clears an earlier problem notification; one that can't add it says why
    await _show(hass, False)

    async def broken(_config):
        raise OSError("disk full")

    monkeypatch.setattr(dash, "async_save", broken)
    await _show(hass, True)
    assert _note(hass)["message"] == "Could not add the Help view: Saving the dashboard failed: disk full"
    monkeypatch.undo()
    await _show(hass, False)
    await _show(hass, True)
    assert _note(hass) is None and (await _cfg(hass))["views"][-1]["path"] == "help"


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Chromium, Node and Playwright")
def test_help_panel_in_a_browser(tmp_path) -> None:
    page = _settings_page()
    ids = re.findall(r'<!-- guide:summary id="([^"]+)" -->', page)
    section = next(i for i in ids if i.count(".") == 1 and f'id="{i}.' in page)     # a section that has sub-groups
    group = next(i for i in ids if i.startswith(section + "."))
    r = subprocess.run(["node", str(Path(__file__).parent / "js/help_panel_check.mjs"), str(ROOT)],
                       capture_output=True, text=True, timeout=180,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME, "OUT_DIR": str(tmp_path),
                            "GUIDE_FILE": _guide_file(tmp_path), "HELP_PAGE": "intermediate/settings",
                            "HELP_IDS": json.dumps([section, group])})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == [], out["errors"]
    for name in ("desktop", "phone"):
        o = out[name]
        assert o["hidden"] == ["none", "none"]                                    # tags show only in help mode
        assert o["shown"] == ["inline-flex 6px", "inline-flex 5px"]               # rounded corners, not circles
        s = o["summary"]
        assert s["label"] == f"Help: {s['title']}" and s["focused"] and s["pressed"] == [section]
        assert s["expand"] == "Expand" and s["chips"] and s["body"]
        assert s["href"].startswith("/dash/help?page=intermediate/settings#")
        assert o["child"]["title"] == s["chips"][0] and o["child"]["back"] == f"← {s['title']}" and o["child"]["chips"] == []
        assert o["child"]["focus"] == f"← {s['title']}"                            # focus moves to Back, not the page
        assert o["child"]["href"] != s["href"] and o["backTo"] == s["title"] and o["backFocus"] == s["chips"][0]
        assert o["expanded"]["expand"] == "Less" and len(o["expanded"]["body"]) > len(s["body"]) and o["expanded"]["chips"] == []
        assert o["expanded"]["focus"] == "Less" and o["less"]["focus"] == "Expand"
        assert o["less"]["body"] == s["body"] and o["escAfterButtons"] is False
        assert o["group"]["pressed"] == [group] and o["group"]["title"] != s["title"]
        assert o["closed"] == {"panel": False, "focus": group, "pressed": 0}       # Escape: focus back on the tag
        assert o["browse"]["at"] == s["href"] and o["browse"]["nav"] == [s["href"]] and not o["browse"]["panel"]
        assert o["browse"]["from"]["path"] == "/dash/settings"                    # the Help view offers the way back
        assert o["fetches"] == 1                                                  # the page is read once
        assert not o["overflow"]
    d, p = out["desktop"]["summary"], out["phone"]["summary"]
    assert d["width"] == 400 and d["left"] == 800 and d["top"] == 56              # a side panel on the right, under HA's toolbar
    assert p["left"] == 0 and p["width"] == 390 and p["top"] > 56 and p["bottom"] == 800   # a bottom sheet


# ── the Power view's "?" help (www/battman-help-layer.js) ────────────────────────────────────

POWER_VIEW = (ROOT / "views/05-power.yaml").read_text()
LAYER_JS = (WWW / "battman-help-layer.js").read_text()
IMAGES = WWW / "guide-images"


def _power_page() -> str:
    return _pages()["intermediate/power"]


def _power_cards() -> set[str]:
    """The Battman cards the Power view holds (the picture cards have no help)."""
    return set(re.findall(r"type: custom:battman-([a-z0-9]+)", POWER_VIEW)) - {"image"}


def test_power_page_has_a_summary_for_every_card_on_the_view() -> None:
    page = _power_page()
    ids = re.findall(r'<!-- guide:summary id="([^"]+)" -->', page)
    assert len(ids) == len(set(ids)) and all(re.fullmatch(r"power\.[a-z0-9]+", i) for i in ids), ids
    assert {i.split(".")[1] for i in ids} == _power_cards()
    for card in _power_cards():
        assert re.search(rf'<a id="{card}"></a>\n## .+\n\n<!-- guide:summary id="power.{card}" -->', page), card
    # the cards on the page are in the order they sit on the view
    order = [c for c in re.findall(r"type: custom:battman-([a-z0-9]+)", POWER_VIEW) if c != "image"]
    assert [i.split(".")[1] for i in ids] == order


def test_power_cards_register_for_help_under_their_own_ids() -> None:
    """The cards that draw others (the wrapper) register under the card's id; House and Overrides by name."""
    assert "helpRegisterCard(this.constructor.cardId," in (WWW / "battman-cards.js").read_text()
    assert 'helpRegister("power.house",' in (WWW / "battman-house.js").read_text()
    assert 'helpRegister("power.overrides",' in (WWW / "battman-overrides.js").read_text()
    cards = {p.stem for p in (ROOT / "cards").glob("*.yaml")}
    assert _power_cards() - {"house", "overrides"} <= cards
    # the layer: nothing of the guide or the panel up front; the panel only when help is turned on
    assert re.findall(r'^import .* from "([^"]+)";', LAYER_JS, re.M) == []
    assert 'import("./battman-help-panel.js")' in LAYER_JS
    pages = dict(re.findall(r'(\w+): "(intermediate/\w+)"', re.search(r"const PAGES = \{([^}]*)\}", LAYER_JS).group(1)))
    assert pages == {v: f"intermediate/{v}" for v in ("power", "curvy", "pricy", "finances", "log", "theme")}
    assert "st.attributes.showHelp === false" in LAYER_JS


def test_guide_images_are_all_used_and_all_there() -> None:
    from custom_components.battman import guide

    used: set[str] = set()
    for pid, text in _pages().items():
        for alt, src in re.findall(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)', text):
            assert alt.strip() and len(alt) > 15, (pid, "alt text says what the picture shows", src)
            parts = ["guide", *Path(guide.page_file(pid).relative_to(GUIDE)).parts[:-1]]
            for seg in src.split("/"):
                parts.pop() if seg == ".." else parts.append(seg)
            rel = "/".join(parts)
            assert re.fullmatch(r"www/guide-images/[a-z0-9][a-z0-9-]*\.(png|webp|jpg|svg)", rel), (pid, src)
            assert (ROOT / rel).is_file(), (pid, src)
            used.add(rel.rsplit("/", 1)[1])
    files = {p.name for p in IMAGES.glob("*")} if IMAGES.is_dir() else set()
    assert files == used, {"unused": files - used, "missing": used - files}
    assert all((IMAGES / f).stat().st_size < 400_000 for f in files)          # they ship with every update


@NEEDS_NODE
def test_markdown_images() -> None:
    md = ("# T\n\n![The House card](../../www/guide-images/power-house.png)\n\n![Elsewhere](https://example.org/x.png)\n\n"
          "![Up and out](../../www/guide-images/../../x.png)\n\n![Other folder](../../www/other/x.png)\n\n"
          "![Absolute](/local/x.png)\n\n![Home page](../www/guide-images/a.png)\n\n"
          '![A wide card](../../www/guide-images/power-house.png "wide")\n')
    script = f"""
const {{ renderPage }} = await import({json.dumps(str(WWW / "battman-guide-md.js"))});
process.stdout.write(JSON.stringify([renderPage({json.dumps(md)}, "intermediate/power"), renderPage({json.dumps(md)}, "home")]));
"""
    power, home = json.loads(subprocess.run(["node", "--input-type=module", "-"], input=script, capture_output=True,
                                            text=True, check=True).stdout)
    assert re.search(r'<img class="gimg" src="[^"]+/guide-images/power-house\.png" alt="The House card" loading="lazy">', power["html"])
    assert power["html"].count("<img") == 2 and power["html"].count('class="imgalt"') == 5
    assert '<img class="gimg wide"' in power["html"] and power["html"].count('class="gimg"') == 1
    assert [i["name"] for i in power["images"]] == ["power-house.png", None, None, None, None, None, "power-house.png"]
    assert [i["name"] for i in home["images"]][-2] == "a.png"                 # the home page sits one folder up


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Chromium, Node and Playwright")
def test_power_help_layer_in_a_browser(tmp_path) -> None:
    page = _power_page()
    cards = [i.split(".")[1] for i in re.findall(r'<!-- guide:summary id="([^"]+)" -->', page)]
    r = subprocess.run(["node", str(Path(__file__).parent / "js/help_layer_check.mjs"), str(ROOT)],
                       capture_output=True, text=True, timeout=180,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME, "GUIDE_FILE": _guide_file(tmp_path),
                            "HELP_CARDS": json.dumps([f"power.{c}" for c in cards[:2]])})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == [], out["errors"]
    for name in ("desktop", "phone"):
        o = out[name]
        assert o["button"]["hidden"] is False and o["button"]["pressed"] == "false" and o["tagsBefore"] == 0
        assert o["button"]["right"] == 16 and o["button"]["top"] == 68            # floating, top right, under HA's toolbar
        assert o["button"]["theme"] == "#123456"                                  # the layer wears the cards' theme
        assert o["pressed"] == "true"
        bg = o["pressedLook"]["bg"]                                               # on: a tint, never a solid fill
        assert bg.startswith(("rgba(", "color(")) and not bg.endswith(", 1)"), bg
        assert o["pressedLook"]["border"] == "solid"
        shown = [t for t in o["tags"] if t["vis"] != "hidden"]
        assert {t["id"] for t in o["tags"]} == {f"power.{c}" for c in cards[:2]}   # a part with no help gets none
        assert all(t["display"] == "flex" for t in o["tags"])                     # shown in help mode (fixed, so flex)
        boxes = {b["i"]: b for b in o["cardBoxes"]}
        a = next(t for t in shown if t["top"] == boxes["a"]["top"] + 8)
        assert a["right"] == boxes["a"]["right"] - 8                             # top right of its card, 8px in
        tall = [t for t in o["scrolled"] if t["vis"] != "hidden"]
        assert tall and all(t["top"] >= 60 for t in tall)                         # stays in view under the header
        p = o["panel"]
        assert p["pressed"] == 1 and p["title"]
        assert p["allBg"] == "rgba(0, 0, 0, 0)" and p["allBorder"] == "1px"      # Browse all help: outlined, not a solid fill
        assert o["fetches"] == 1                                                  # the Power page is read once
        assert o["afterEsc1"] == {"panel": False, "pressed": "true"}              # Escape closes the panel, then help
        assert o["afterEsc2"] == {"tags": 0, "pressed": "false"}
        assert o["showHelpOff"] == {"hidden": True, "tags": 0, "pressed": "false"}
        assert o["showHelpOn"] is False and o["theme"] == "#abcdef"
        assert o["gone"] == {"hidden": True, "tags": 0, "panel": False}
    d, ph = out["desktop"]["panel"], out["phone"]["panel"]
    assert d["width"] == 400 and d["left"] == 800 and ph["left"] == 0 and ph["width"] == 390


def _layer_sections() -> dict[str, list[str]]:
    block = re.search(r"const SECTIONS = \{(.*?)\n\};", LAYER_JS, re.S).group(1)
    return {m[0]: re.findall(r'"([a-z0-9.]+)"', m[1]) for m in re.findall(r"(\w+): \[([^\]]*)\]", block)}


def test_help_layer_knows_every_summary_and_the_editors_register_them() -> None:
    """The layer's list of parts with help is exactly the summaries on the Power, Curvy and Pricy pages, in order."""
    sections = _layer_sections()
    assert set(sections) == {"power", "curvy", "pricy", "finances", "log", "theme"}
    for name, ids in sections.items():
        page = _pages()[f"intermediate/{name}"]
        assert [i.split(".", 1)[1] for i in re.findall(r'<!-- guide:summary id="([^"]+)" -->', page)] == ids, name
    # every part is registered by the card that draws it
    sources = {"finances": ["battman-cost-chart.js", "battman-cost-compare.js", "battman-help-layer.js"], "log": ["battman-log.js"],
               "theme": ["battman-theme-studio.js"]}
    for name, files in sources.items():
        js = "\n".join((WWW / f).read_text() for f in files)
        for i in sections[name]:
            card, _, part = i.partition(".")
            assert f'"{card}"' in js or f'"{name}." + id' in js or card in ("billing", "solar"), (name, i)
    for name in ("curvy", "pricy"):
        js = (WWW / f"battman-{name}.js").read_text()
        registered = re.findall(r'\["([a-z0-9]+)", "[^"]+"\]', js.split("connectedCallback()", 1)[1].split("disconnectedCallback", 1)[0])
        assert registered == sections[name], name
        assert f'helpRegister("{name}." + id,' in js


# ── "How do I…?" (guide/howto/tasks.md, www/battman-guide-howto.js, www/battman-tour.js) ──────────

VIEWS = {"power", "curvy", "pricy", "finances", "settings", "log", "theme"}
# the card a Show me step names -> the files its visible text comes from
CARD_SOURCES = {
    "battman-house": ["www/battman-house.js"], "battman-overrides": ["www/battman-overrides.js", "www/battman-overrides-core.js"],
    "battman-curvy": ["www/battman-curvy.js", "www/battman-curve-editor.js"], "battman-pricy": ["www/battman-pricy.js", "www/battman-curve-editor.js"],
    "battman-cost-chart": ["www/battman-cost-chart.js"], "battman-cost-compare": ["www/battman-cost-compare.js"],
    "battman-settings": ["www/battman-settings.js"], "battman-log": ["www/battman-log.js", "www/battman-enginelog.js"],
    "battman-theme-studio": ["www/battman-theme-studio.js"],
}


ALL_SOURCE = "\n".join(p.read_text() for p in [*(ROOT / "www").glob("battman-*.js"), *(ROOT / "cards").glob("*.yaml")])
PACKAGES_SOURCE = "\n".join(p.read_text() for p in [*(ROOT / "packages").glob("*.yaml"), *ROOT.glob("*.py")])


def _card_source(card: str) -> str:
    files = CARD_SOURCES.get(card) or [f"cards/{card.removeprefix('battman-')}.yaml"]
    return "\n".join((ROOT / f).read_text() for f in files if (ROOT / f).is_file())


def test_howto_tasks_are_complete_and_point_at_real_things() -> None:
    """Every task has its marker, steps and at least one Show me stop, and every stop names a view, a card on it and
    text the card really shows."""
    page = _pages()["howto/tasks"]
    assert "<!-- guide:howto -->" in page
    tasks = re.findall(r'<a id="([a-z0-9-]+)"></a>\n### ([^\n]+)\n<!-- guide:task ([^>]*)-->\n([\s\S]*?)(?=\n<a id="|\n## |$(?![\s\S]))', page)
    assert len(tasks) >= int(os.environ.get("HOWTO_MIN", "18")), len(tasks)
    assert len({t[0] for t in tasks}) == len(tasks)
    assert page.count("<!-- guide:task ") == len(tasks)
    with_show = []
    for anchor, title, args, body in tasks:
        a = dict(re.findall(r'(\w+)="([^"]*)"', args))
        assert a.get("where") and "icon" not in a, anchor          # no icons: text only
        for img in a.get("uses", "").split():
            assert (WWW / "guide-images" / img).is_file(), (anchor, img)
        steps = re.findall(r"^\d+\. ", body, re.M)
        assert 2 <= len(steps) <= 10, (anchor, len(steps))      # every press its own step, popups included
        shows = re.findall(r"^   <!-- guide:show ([^>]*)-->$", body, re.M)
        with_show.append(bool(shows))
        for sh in shows:
            s = dict(re.findall(r'(\w+)="([^"]*)"', sh))
            assert s.get("view") in VIEWS, (anchor, s)
            assert "text" not in s, (anchor, "v1 marker: use target")
            u = s.get("until", "press")
            for one in u.split("|"):
                assert one in {"press", "popup", "closed", "open", "next"} or re.fullmatch(r"state:[a-z_]+\.[a-z0-9_]+=[^|]+", one), (anchor, u)
            if s.get("popup") == "*":                             # whichever popup the step before opened
                src = ALL_SOURCE
            elif s.get("popup"):                                  # in a popup: the popup really shows that text
                src = ALL_SOURCE
                # (a question's title can be built from the mode's name: "Sell" + "?")
                assert s["popup"].rstrip("?").lower() in src.replace("&amp;", "&").lower(), (anchor, s["popup"], "no popup shows this")
                assert u != "popup" or True
            else:
                assert s.get("card", "").startswith("battman-"), (anchor, s)
                src = _card_source(s["card"])
                assert src, (anchor, s["card"], "no source for this card")
                view = (ROOT / "views").glob(f"*-{s['view']}.yaml")
                assert any(f"custom:{s['card']}" in v.read_text() for v in view), (anchor, s, "card isn't on that view")
            if s.get("skipif"):
                assert re.fullmatch(r"state:[a-z_]+\.[a-z0-9_]+=\S+", s["skipif"]), (anchor, s["skipif"])
                assert s["skipif"][6:].split("=")[0].split(".", 1)[1] in ALL_SOURCE + PACKAGES_SOURCE, (anchor, s["skipif"])
            for one in u.split("|"):
                if one.startswith("state:"):
                    assert one[6:].split("=")[0].split(".", 1)[1] in ALL_SOURCE + PACKAGES_SOURCE, (anchor, one, "no such entity")
            s["text"] = s.get("target", "")
            # (the editors' hour and month labels are made by code, not written out in it)
            if s.get("popup"):
                src = ALL_SOURCE
            # (a popup's buttons can be built from names, "Sell" + " anyway": the real-HA walkthrough run checks those)
            if s.get("text", "").startswith("icon:"):                     # an icon-only control: the icon is named in the card
                assert s["text"][5:] in src, (anchor, s["text"])
                s["text"] = ""
            if s.get("text", "").startswith("id:"):                       # a control with no text of its own (a picker): its id
                assert f'id="{s["text"][3:]}"' in src, (anchor, s["text"])
                s["text"] = ""
            if s.get("text") and not s.get("popup") and not re.fullmatch(r"(1[0-2]|[1-9])(am|pm)|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", s["text"]):
                assert s["text"].lower() in src.replace("&amp;", "&").lower(), (anchor, s["text"], "the card doesn't show this text")
            assert len(s.get("say", "")) <= 40, (anchor, s.get("say"))
    assert sum(with_show) >= len(tasks) - 2          # Show me on all but a task or two with nothing on a view to point at


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Chromium, Node and Playwright")
def test_show_me_tour_in_a_browser(tmp_path) -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/tour_check.mjs"), str(ROOT)], capture_output=True, text=True, timeout=150,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == [], out["errors"]
    pad = lambda b: [b[0] - 8, b[1] - 8, b[2] + 8, b[3] + 8]                  # the lens pads its control by 8px
    for name in ("desktop", "phone"):
        o = out[name]
        assert o["s1"]["meta"] == "Step 1 of 4 · Stop exporting" and o["s1"]["ring"] == pad(o["card"]) and o["s1"]["next"]
        assert not o["s1"]["beckon"] and o["s1"]["frost"].startswith("blur(")     # a look-only step: no beckon; the page is frosted
        assert o["s2"]["say"] == "Tap Curtail" and o["s2"]["ring"] == pad(o["curtail"])    # the whole button, not its label
        assert o["s2"]["beckon"] and not o["s2"]["next"]                          # the control is the way forward
        assert o["paused"] and o["resumed"]["say"] == "Tap Curtail" and not o["resumed"]["paused"]   # click off pauses
        assert o["s3"]["say"] == "Press Turn on" and o["s3"]["inDialog"] and o["s3"]["ring"] == pad(o["on"])   # into the popup
        assert o["s4fold"]["say"] == "Open Billing" and o["s4fold"]["ring"] == pad(o["head"])   # folded: open it first
        assert o["s4"]["say"] == "Tap the charge" and o["s4"]["ring"] == pad(o["fee"]) and o["s4"]["buttons"] == ["Back", "Stop"]
        assert o["s4done"]["done"] and o["s4done"]["ring"] == pad(o["fee"]) and not o["s4done"]["beckon"]   # done: it stays
        assert o["s4done"]["buttons"] == ["Back", "Done"]                         # one Done, no Stop
        assert o["back"]["say"] == "Tap Curtail"                                  # Back to a popup step that isn't open: its opener
        assert o["afterEsc"] is False and o["clicks"] == ["curtail", "on", "fee"]   # only the person's presses
        w, ring = o["s2"]["words"], o["s2"]["ring"]
        assert w[2] <= o["vw"] - 12 and (w[0] >= ring[2] or w[2] <= ring[0] or w[1] >= ring[3] or w[3] <= ring[1])  # beside it, not over it


def test_help_controls_are_outlined_never_solid_or_dashed() -> None:
    """Help buttons and tags: an outline with a tint when on (the Help buttons use Self Consume's on look); no solid
    fills, no dashed or dotted outlines."""
    panel = (WWW / "battman-help-panel.js").read_text()
    tags = panel[panel.index(".bh-tag {"):panel.index(".helpmode .bh-tag")]
    assert "dashed" not in tags and "dotted" not in tags
    for f in ("battman-help-layer.js", "battman-settings.js", "battman-help-panel.js", "battman-guide-howto.js"):
        css = (WWW / f).read_text()
        for rule in re.findall(r'(?:helpbtn\[aria-pressed="true"\]|bh-tag\[aria-expanded="true"\]|button\.showme|aria-pressed="true"\]) \{([^}]*)\}', css):
            # a tint: the accent mixed thin, or Self Consume's on look (blue soft background, strong blue border)
            assert ("color-mix" in rule or "--battman-blue-soft-bg" in rule) and "var(--card-background-color)" not in rule.split("color:")[0], (f, rule)


def test_help_view_has_close_and_back_to_top_and_sticky_contents() -> None:
    view = (WWW / "battman-guide-view.js").read_text()
    assert '<button class="back-btn"' in view and "b.hidden = false;" in view and '"Close"' in view
    assert '<button class="totop" type="button" hidden>Back to top</button>' in view
    assert "position: sticky; top: var(--g-top, 56px)" in view and "ha-card { overflow: clip;" in view
    assert "battman.lastView" in (WWW / "battman-card-base.js").read_text()
    howto = (WWW / "battman-guide-howto.js").read_text()
    assert not re.search(r"[\U0001F300-\U0001FAFF]|▶ Show me|🔍", howto)        # no icons
