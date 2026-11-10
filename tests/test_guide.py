"""Battman's built-in guide and its Help view.

- The guide's pages (custom_components/battman/guide/) are all listed in its index, every link between
  them lands (page and section), and they render with the shipped Markdown reader (marked, vendored).
- The Repairs page covers every Repair in en.json under its own title; the device page quotes the
  buttons' messages as Battman sends them.
- The pages describe Battman as it is: none of the old words below appear.
- Only the Help card's small stub loads on every page; the guide itself loads when the card is shown.
- /api/battman/guide serves the contents and the pages, and nothing else.
- Create help view adds the Help view to the Battman dashboard only when it's missing, and changes
  nothing else; the default dashboard has it as its last view.
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
        assert {d["name"] for d in page["directives"]} <= {"repairs"}, pid
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
    from custom_components.battman import dashboard, services

    page = (GUIDE / "start/device-page.md").read_text(encoding="utf-8")
    for outcome in (dashboard.ADDED, dashboard.EXISTS, dashboard.NO_DASHBOARD, dashboard.NOT_EDITABLE):
        assert f'"{services._help_message(outcome, "battman")}"' in page, outcome
    src = (ROOT / "services.py").read_text(encoding="utf-8")
    for quoted in ("It's yours: edit it like any dashboard.", "For a fresh Battman dashboard, delete that one first.",
                   "All Battman automations and scripts already exist; nothing changed."):
        assert quoted in src and quoted in page, quoted
    en = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))
    for key in ("create_dashboard", "create_help_view", "create_automations"):
        assert f"**{en['entity']['button'][key]['name']}**" in page, key
    from custom_components.battman import engine, notifications

    for alias in [s["alias"] for s in engine.SCRIPTS.values()] + [s["alias"] for s in notifications.SCRIPTS.values()]:
        assert f'"{alias}"' in page, alias
    for a in engine.AUTOMATIONS + notifications.AUTOMATIONS:
        short = a["alias"].split(" – ", 1)
        assert f'"{a["alias"]}"' in page or (len(short) == 2 and f'"– {short[1]}"' in page), a["alias"]


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
    guide_json = json.dumps({"index": _index(), "pages": _pages()})
    r = subprocess.run(["node", str(Path(__file__).parent / "js/guide_check.mjs"), str(ROOT), str(tmp_path)],
                       capture_output=True, text=True, timeout=180,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME, "GUIDE_JSON": guide_json})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == [], out["errors"]
    assert out["before"] == ["battman-guide.js"]                           # only the stub, until the card is shown
    assert {"battman-guide-view.js", "battman-guide-md.js", "vendor/marked.esm.js"} <= set(out["after"])
    assert out["home"]["h1"].startswith("Battman help") and out["home"]["current"] == "Battman help"
    assert out["home"]["toc"] == ["Battman help", "The Battman device page", "Battman's Repairs"]
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


# ── Home Assistant: the API, the Help view and Create help view ─────────────────────────────


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _cfg(hass):
    return await hass.data[LOVELACE_DATA].dashboards["battman"].async_load(False)


async def _help(hass):
    return await hass.services.async_call("battman", "create_help_view", {}, blocking=True, return_response=True)


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
    r = await _help(hass)                                    # a new dashboard has it: nothing to add
    assert r["outcome"] == "exists" and r["added"] is False


async def test_create_help_view_adds_only_the_help_view(hass: HomeAssistant) -> None:
    await _setup(hass)
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    # a dashboard made before the Help view, that you've since changed
    cfg = await _cfg(hass)
    mine = {**cfg, "title": "My battery", "views": [{**v, "title": v["title"] + "!"} for v in cfg["views"] if v["path"] != "help"]}
    mine["views"].append({"title": "Mine", "path": "mine", "cards": [{"type": "markdown", "content": "hello"}]})
    await dash.async_save(mine)

    r = await _help(hass)
    assert r == {"added": True, "outcome": "added", "url_path": "battman",
                 "message": "Added the Help view to your Battman dashboard at /battman. It's the last tab; "
                            "nothing else on the dashboard changed."}
    after = await _cfg(hass)
    assert after["views"][:-1] == mine["views"] and after["title"] == "My battery"      # everything else as it was
    assert after["views"][-1]["path"] == "help" and after["views"][-1]["cards"] == [{"type": "custom:battman-guide"}]

    r = await _help(hass)                                    # again: already there, nothing changes
    assert r["outcome"] == "exists" and r["message"].startswith("Your Battman dashboard already has a Help view (/battman/help)")
    assert await _cfg(hass) == after

    # moved and renamed by you: still found by its path, so not added twice
    moved = {**after, "views": [{**after["views"][-1], "title": "Guide"}, *after["views"][:-1]]}
    await dash.async_save(moved)
    assert (await _help(hass))["outcome"] == "exists" and await _cfg(hass) == moved


async def test_create_help_view_never_makes_or_rewrites_a_dashboard(hass: HomeAssistant) -> None:
    from custom_components.battman import dashboard

    await _setup(hass)
    item_id = hass.data[LOVELACE_DATA].dashboards["battman"].config["id"]
    await dashboard._collection(hass).async_delete_item(item_id)
    await hass.async_block_till_done()
    r = await _help(hass)
    assert r["outcome"] == "no_dashboard" and "Press Create dashboard" in r["message"]
    assert "battman" not in hass.data[LOVELACE_DATA].dashboards

    # a dashboard with no saved views (HA draws it for you), or one drawn by a strategy: left alone
    await dashboard._collection(hass).async_create_item(
        {"allow_single_word": True, "title": "Battman", "url_path": "battman", "require_admin": False, "show_in_sidebar": True})
    await hass.async_block_till_done()
    assert (await _help(hass))["outcome"] == "not_editable"
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    strategy = {"strategy": {"type": "original-states"}}
    await dash.async_save(strategy)
    r = await _help(hass)
    assert r["outcome"] == "not_editable" and "type: custom:battman-guide" in r["message"]
    assert await _cfg(hass) == strategy


async def test_create_help_view_button(hass: HomeAssistant) -> None:
    await _setup(hass)
    state = hass.states.get("button.battman_create_help_view")
    assert state is not None and state.attributes["friendly_name"] == "Battman Create help view"
    await hass.services.async_call("button", "press", {"entity_id": state.entity_id}, blocking=True)
    await hass.async_block_till_done()
    from homeassistant.components import persistent_notification

    note = persistent_notification._async_get_or_create_notifications(hass)["battman_help_view"]
    assert note["title"] == "Battman help view" and "already has a Help view" in note["message"]


async def test_create_help_view_says_when_saving_fails(hass: HomeAssistant, monkeypatch) -> None:
    await _setup(hass)
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    cfg = await _cfg(hass)
    without = {**cfg, "views": [v for v in cfg["views"] if v["path"] != "help"]}
    await dash.async_save(without)

    async def broken(_config):
        raise OSError("disk full")

    monkeypatch.setattr(dash, "async_save", broken)
    r = await _help(hass)
    assert r["outcome"] == "error" and r["added"] is False
    assert r["message"] == "Could not add the Help view: Saving the dashboard failed: disk full"
    assert await _cfg(hass) == without


async def test_two_presses_at_once_add_one_help_view(hass: HomeAssistant) -> None:
    import asyncio

    await _setup(hass)
    dash = hass.data[LOVELACE_DATA].dashboards["battman"]
    cfg = await _cfg(hass)
    await dash.async_save({**cfg, "views": [v for v in cfg["views"] if v["path"] != "help"]})
    a, b = await asyncio.gather(_help(hass), _help(hass))
    assert sorted([a["outcome"], b["outcome"]]) == ["added", "exists"]
    assert [v["path"] for v in (await _cfg(hass))["views"]].count("help") == 1


async def test_create_help_view_leaves_yaml_dashboards_and_panels_alone(hass: HomeAssistant) -> None:
    from homeassistant.components import frontend
    from custom_components.battman import dashboard

    await _setup(hass)
    item_id = hass.data[LOVELACE_DATA].dashboards["battman"].config["id"]
    await dashboard._collection(hass).async_delete_item(item_id)
    await hass.async_block_till_done()

    class YamlDashboard:                           # what HA keeps for a dashboard written in YAML
        mode = "yaml"

        async def async_load(self, force):
            return {"views": [{"path": "home", "cards": []}]}

        async def async_save(self, config):
            raise AssertionError("a YAML dashboard must not be written")

    hass.data[LOVELACE_DATA].dashboards["battman"] = YamlDashboard()
    r = await _help(hass)
    assert r["outcome"] == "not_editable" and "written in YAML" in r["message"]
    del hass.data[LOVELACE_DATA].dashboards["battman"]

    # something at /battman that isn't a dashboard: not "press Create dashboard" (that wouldn't help either)
    frontend.async_register_built_in_panel(hass, "iframe", "Other", "mdi:web", frontend_url_path="battman",
                                           config={"url": "https://example.org"})
    r = await _help(hass)
    assert r["outcome"] == "not_editable" and "something that isn't a dashboard" in r["message"]


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
    for service in ("create_dashboard", "create_help_view", "create_automations"):
        with pytest.raises(Unauthorized):
            await hass.services.async_call("battman", service, {}, blocking=True, return_response=True,
                                           context=Context(user_id=user.id))
        r = await hass.services.async_call("battman", service, {}, blocking=True, return_response=True,
                                           context=Context(user_id=hass_admin_user.id))
        assert r["message"], service
        r = await hass.services.async_call("battman", service, {}, blocking=True, return_response=True)
        assert r["message"], service
    for button in ("button.battman_create_dashboard", "button.battman_create_help_view", "button.battman_create_automations"):
        with pytest.raises(HomeAssistantError) as err:
            await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True,
                                           context=Context(user_id=user.id))
        assert str(err.value) == "Only a Home Assistant administrator can press this button", button
        await hass.services.async_call("button", "press", {"entity_id": button}, blocking=True,
                                       context=Context(user_id=hass_admin_user.id))
    page = (GUIDE / "start/device-page.md").read_text(encoding="utf-8")
    en = json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8"))
    assert f'"{en["exceptions"]["admin_only"]["message"]}"' in page
