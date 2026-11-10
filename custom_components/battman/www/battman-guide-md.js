// Battman's guide: one page of Markdown (custom_components/battman/guide/) to HTML for the Help view.
//
// The pages are plain GitHub Markdown, so GitHub shows the same files. Here they're drawn with marked
// (vendor/marked.esm.js) plus a few rules of Battman's own:
// - Links between pages are relative .md links (start/device-page.md#create-dashboard), as on GitHub.
//   They become Help view links (?page=start/device-page#create-dashboard). Links to Home Assistant
//   pages (/config/repairs) stay inside HA; https: links open in a new tab; any other link is shown as
//   plain text.
// - Raw HTML is escaped, except the few tags the pages use: <details>, <summary>, <br>, <kbd> and
//   anchors (<a id="name"></a>). An HTML comment <!-- guide:name key="value" --> marks a live part of
//   the page (the view fills it in); any other comment is dropped.
// - Headings get GitHub's ids (so the same #anchors work on GitHub) and a copy-link button. A heading with its
//   own anchor just before it (<a id="packages-not-loaded"></a>) copies that anchor, which never changes.
// - GitHub's callouts (> [!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION]) are drawn as callouts.
// - Code blocks get a Copy button. Images aren't drawn yet (their alt text is shown).
//
// No DOM here, so tests run it under Node.

import { Marked } from "./vendor/marked.esm.js";

export const esc = (v) => String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'", nbsp: " " };
const plain = (html) => html.replace(/<[^>]*>/g, "").replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (_, e) => ENTITIES[e]);

// GitHub's heading ids: lower case, punctuation dropped, each space a hyphen.
export function slugify(text) {
  return String(text).trim().toLowerCase().replace(/[^\p{L}\p{N}\s_-]/gu, "").replace(/\s/g, "-");
}

// The Markdown file a page id is kept in (relative to guide/): home is README.md.
export const pageFile = (page) => (page === "home" ? "README.md" : `${page}.md`);

// A page id from a guide file path (relative to guide/), or null when it isn't a page.
export function pageFromFile(file) {
  if (file === "README.md") return "home";
  const m = /^([a-z0-9][a-z0-9-]*)\/([a-z0-9][a-z0-9-]*)\.md$/.exec(file);
  return m ? `${m[1]}/${m[2]}` : null;
}

// What a link in a page points at.
//   {kind: "page", page, anchor}  another guide page (or this one), anchor may be ""
//   {kind: "ha", path}            a Home Assistant page (/config/repairs)
//   {kind: "external", url}       https: only
//   {kind: "none"}                anything else: shown as plain text
export function resolveLink(href, fromPage) {
  const h = String(href || "").trim();
  if (h.startsWith("#")) return { kind: "page", page: fromPage, anchor: h.slice(1) };
  if (/^https:\/\/[^\s"'<>]+$/i.test(h)) return { kind: "external", url: h };
  if (/^\/(?!\/)[A-Za-z0-9/_\-.?=&%#]*$/.test(h)) return { kind: "ha", path: h };
  if (/^[a-z]+:/i.test(h) || h.startsWith("//")) return { kind: "none" };
  const [path, anchor = ""] = h.split("#", 2);
  if (!path.endsWith(".md")) return { kind: "none" };
  const parts = pageFile(fromPage).split("/").slice(0, -1);
  for (const seg of path.split("/")) {
    if (seg === "..") { if (!parts.length) return { kind: "none" }; parts.pop(); }
    else if (seg !== "." && seg !== "") parts.push(seg);
  }
  const page = pageFromFile(parts.join("/"));
  return page ? { kind: "page", page, anchor } : { kind: "none" };
}

// A Help view address (relative to the view itself, so it works on whatever dashboard holds it).
export const pageHref = (page, anchor) => (page === "home" ? "?" : `?page=${page}`) + (anchor ? `#${anchor}` : "");

const ALLOWED = [
  [/^<details( open)?>$/i, (m) => `<details${m[1] ? " open" : ""}>`],
  [/^<\/details>$/i, () => "</details>"],
  [/^<summary>$/i, () => "<summary>"],
  [/^<\/summary>$/i, () => "</summary>"],
  [/^<br ?\/?>$/i, () => "<br>"],
  [/^<kbd>$/i, () => "<kbd>"],
  [/^<\/kbd>$/i, () => "</kbd>"],
  [/^<a id="([a-z0-9][a-z0-9-]*)">$/, (m) => `<span class="anchor" id="${m[1]}"></span>`],
  [/^<\/a>$/i, () => ""],
];

// <!-- guide:name key="value" ... --> -> {name, args}, or null for any other comment.
export function directive(comment) {
  const m = /^<!--\s*guide:([a-z][a-z-]*)((?:\s+[a-z][a-zA-Z-]*="[^"<>]*")*)\s*-->$/.exec(comment.trim());
  if (!m) return null;
  const args = {};
  for (const [, k, v] of m[2].matchAll(/([a-z][a-zA-Z-]*)="([^"<>]*)"/g)) args[k] = v;
  return { name: m[1], args };
}

// Raw HTML from a page: the allowed tags and guide: comments kept, everything else escaped.
function cleanHtml(raw, ids, onAnchor) {
  return String(raw).split(/(<!--[\s\S]*?-->|<\/?[a-zA-Z][^<>]*>)/).map((part) => {
    if (!part) return "";
    if (part.startsWith("<!--")) {
      const d = directive(part);
      return d ? `<div class="directive" data-directive="${esc(d.name)}" data-args="${esc(JSON.stringify(d.args))}"></div>` : "";
    }
    if (/^<\/?[a-zA-Z]/.test(part)) {
      for (const [re, out] of ALLOWED) {
        const m = re.exec(part);
        if (m) {
          if (m[1] && re.source.includes(" id=")) { ids.add(m[1]); onAnchor(m[1]); }
          return out(m);
        }
      }
    }
    return esc(part);
  }).join("");
}

const ALERTS = { NOTE: "Note", TIP: "Tip", IMPORTANT: "Important", WARNING: "Warning", CAUTION: "Caution" };

// One page: {html, title, headings: [{depth, text, id}], ids: [every anchor], links: [{href, ...resolved}],
// directives: [{name, args}]}.
export function renderPage(markdown, page) {
  const headings = [];
  const ids = new Set();
  const links = [];
  const directives = [];
  const counts = new Map();
  const unique = (base) => {
    const n = counts.get(base) || 0;
    counts.set(base, n + 1);
    return n ? `${base}-${n}` : base;
  };
  let anchor = null;           // a fixed anchor waiting for the heading straight after it
  const ANCHOR_ONLY = /^\s*<span class="anchor" id="[^"]+"><\/span>\s*$/;
  const marked = new Marked({ gfm: true, breaks: false });
  marked.use({
    renderer: {
      heading({ tokens, depth }) {
        const inner = this.parser.parseInline(tokens);
        const text = plain(inner);
        const id = unique(slugify(text));
        ids.add(id);
        const link = anchor || id;
        anchor = null;
        headings.push({ depth, text, id, link });
        const copy = depth >= 2
          ? `<button class="hlink" type="button" data-copy="${esc(link)}" aria-label="Copy a link to ${esc(text)}" title="Copy a link to this section">#</button>`
          : "";
        return `<h${depth} id="${esc(id)}">${inner}${copy}</h${depth}>\n`;
      },
      link({ href, title, tokens }) {
        const inner = this.parser.parseInline(tokens);
        const r = resolveLink(href, page);
        links.push({ href, ...r });
        const t = title ? ` title="${esc(title)}"` : "";
        if (r.kind === "page") {
          return `<a href="${esc(pageHref(r.page, r.anchor))}" data-page="${esc(r.page)}" data-anchor="${esc(r.anchor)}"${t}>${inner}</a>`;
        }
        if (r.kind === "ha") return `<a href="${esc(r.path)}" data-ha="${esc(r.path)}"${t}>${inner}</a>`;
        if (r.kind === "external") return `<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer"${t}>${inner}</a>`;
        return `<span class="deadlink">${inner}</span>`;
      },
      image({ text }) {
        return `<span class="imgalt">${esc(text)}</span>`;
      },
      paragraph({ tokens }) {
        const inner = this.parser.parseInline(tokens);
        if (!ANCHOR_ONLY.test(inner)) anchor = null;
        return `<p>${inner}</p>\n`;
      },
      html({ text }) {
        const out = cleanHtml(text, ids, (a) => { anchor = a; });
        for (const m of out.matchAll(/data-directive="([^"]*)" data-args="([^"]*)"/g)) {
          directives.push({ name: m[1], args: JSON.parse(plain(m[2])) });
        }
        return out;
      },
      code({ text, lang }) {
        const cls = lang && /^[a-z0-9-]+$/i.test(lang) ? ` class="language-${lang}"` : "";
        return `<div class="code"><button class="copy" type="button" data-copy-code aria-label="Copy this code">Copy</button>`
          + `<pre><code${cls}>${esc(text)}</code></pre></div>\n`;
      },
      blockquote({ tokens }) {
        let body = this.parser.parse(tokens);
        const m = /^<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*/.exec(body);
        if (!m) return `<blockquote>\n${body}</blockquote>\n`;
        body = ("<p>" + body.slice(m[0].length)).replace(/^<p><\/p>\n?/, "");
        const kind = m[1].toLowerCase();
        return `<div class="callout ${kind}" role="note"><p class="callout-title">${ALERTS[m[1]]}</p>\n${body}</div>\n`;
      },
      table(token) {
        // marked's own table, inside a box that scrolls sideways on a narrow screen
        const head = token.header.map((c) => `<th${c.align ? ` style="text-align:${c.align}"` : ""}>${this.parser.parseInline(c.tokens)}</th>`).join("");
        const rows = token.rows.map((row) => "<tr>" + row.map((c) =>
          `<td${c.align ? ` style="text-align:${c.align}"` : ""}>${this.parser.parseInline(c.tokens)}</td>`).join("") + "</tr>").join("\n");
        return `<div class="table"><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>\n`;
      },
    },
  });
  const html = marked.parse(String(markdown));
  const h1 = headings.find((h) => h.depth === 1);
  return { html, title: h1 ? h1.text : "", headings, ids: [...ids], links, directives };
}
