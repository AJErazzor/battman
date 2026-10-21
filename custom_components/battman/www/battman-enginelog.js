// Battman engine log: reads one engine log message and draws it.
//
// One renderer for both places the log is shown, so they always look the same:
// the Engine log popup (Battery mode card's info button) and the Log page's list.
//
// It reads both formats:
// - Battman's: one section per line that starts with a heading (Run:, Mode:, Prices:, ...);
//   the indented lines under it are its details. In the log file the line breaks are
//   written as \n so a whole run stays on one line.
// - Smiggles' (lines copied in at migration, and Battman's first runs): sections start
//   with an emoji (🔄 Mode, 💰 Prices, ...); in the log file the line breaks were turned
//   into spaces, so the emoji are where sections start. The emoji aren't shown.
//
// window.battmanEngineLog.parse(message)  -> { time, from, to, sections: [{ key, head, value, lines }] }
// window.battmanEngineLog.render(message, { title }) -> HTML (colours as var(--battman-*))
// window.battmanEngineLog.fromFileLine(line) -> { stamp, message } for a "time|message" log file line
(function () {
  const C = {
    green: "var(--battman-green)", yellow: "var(--battman-yellow)", amber: "var(--battman-amber)",
    orange: "var(--battman-orange)", blue: "var(--battman-blue)", purple: "var(--battman-purple)",
    darkred: "var(--battman-darkred)", muted: "var(--battman-text-muted)", dim: "var(--battman-text-dim)",
    text: "var(--primary-text-color)",
  };
  // heading -> colour (Battman's headings; Smiggles' emoji map onto them)
  const HEADS = {
    "Run": C.muted, "Mode": C.purple, "Prices": C.yellow, "Min Sell": C.orange, "Battery": C.green,
    "SOC Limits": C.blue, "Solar": C.amber, "Actions": C.muted, "Sell Forecasts": C.green,
    "Buy Forecasts": C.amber, "Version": C.muted, "Debug": C.muted,
  };
  const EMOJI = {
    "🕐": "Run", "🔄": "Mode", "💰": "Prices", "🔒": "Min Sell", "🔋": "Battery", "📊": "SOC Limits",
    "☀️": "Solar", "☀": "Solar", "⚡": "Actions", "📈": "Sell Forecasts", "📉": "Buy Forecasts",
    "ℹ️": "Info", "ℹ": "Info",
  };
  const HEAD_RE = new RegExp("^(" + Object.keys(HEADS).join("|") + "):\\s?(.*)$");
  const EMOJI_LIST = Object.keys(EMOJI).sort((a, b) => b.length - a.length);
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const clr = (s) => esc(s)
    .replace(/\bTrue\b/g, `<b style='color:${C.green};'>True</b>`)
    .replace(/\bFalse\b/g, `<b style='color:${C.dim};'>False</b>`)
    .replace(/(\$\s*-?[\d.]+)/g, (m) => `<b style='color:${parseFloat(m.replace(/[^0-9.-]/g, "")) < 0 ? C.darkred : C.green};'>${m}</b>`);

  function fromFileLine(line) {
    const i = line.indexOf("|");
    if (i < 0) return { stamp: "", message: line };
    let msg = line.slice(i + 1);
    // Smiggles' shell commands mangled some $ amounts
    msg = msg.replace(/hBc/g, "$-").replace(/bash\./g, "$0.");
    return { stamp: line.slice(0, i), message: msg.replace(/\\n/g, "\n") };
  }

  // Smiggles' format: a section starts at a known emoji: at a line start, or anywhere when the
  // line breaks were flattened into spaces (the log file). Returns [{ em, text }].
  const EM_RE = new RegExp("(" + EMOJI_LIST.map((e) => e.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")");
  function emojiLines(message) {
    let msg = message;
    // spike markers: the 💰 after "Prices:" aren't sections
    msg = msg.replace(/(💰\s*Prices:[^\n]*?)((?:💰\s*)+)(?=\s|$)/u,
      (m, head, marks) => head + (marks.match(/💰/gu) || []).map(() => "(Spike)").join(" "));
    if (msg.includes("\n")) {
      return msg.split("\n").map((line) => {
        const tr = line.trim();
        const em = EMOJI_LIST.find((e) => tr.startsWith(e));
        return em ? { em, text: tr.slice(em.length).trim() } : { text: line };
      });
    }
    const parts = msg.split(EM_RE);
    const out = [];
    if (parts[0].trim()) out.push({ text: parts[0] });
    for (let i = 1; i < parts.length; i += 2) out.push({ em: parts[i], text: (parts[i + 1] || "").trim(), flat: true });
    return out;
  }
  const noEmoji = (t) => t.replace(/💰/gu, "(Spike)").replace(/\s*[\u{1F300}-\u{1FAFF}\u2600-\u27BF]\uFE0F?/gu, "").trim();

  function parse(message) {
    const msg = String(message || "");
    const sections = [];
    let cur = null;
    const add = (key, headText) => {
      const m = headText.match(/^([^:]*):\s?(.*)$/);
      const head = key || (m ? m[1].trim() : headText.trim());
      const value = key && m && key !== "Run" ? m[2].trim() : (key === "Run" ? headText.trim() : (m ? m[2].trim() : ""));
      cur = { key: HEADS[head] ? head : (key || head), head, value, lines: [] };
      sections.push(cur);
    };
    const detail = (raw) => {
      const tr = raw.trim();
      if (!tr) return;
      if (!cur) { cur = { key: "", head: "", value: "", lines: [] }; sections.push(cur); }
      cur.lines.push({ ind: Math.min((raw.match(/^(\s+)/) || ["", ""])[1].length, 8), t: noEmoji(tr) });
    };
    if (/[\u{1F300}-\u{1FAFF}ℹ☀-➿]/u.test(msg) && !HEAD_RE.test(msg.split("\n")[0].trim())) {
      for (const p of emojiLines(msg)) {
        if (p.em) {
          const name = EMOJI[p.em];
          if (name === "Run") { add("Run", p.text); continue; }
          if (name === "Info") {   // "ℹ️ Version: x" / "ℹ️ Debug ..."
            const m = p.text.match(/^(Version|Debug)\b:?\s*(.*)$/);
            if (m) { add(m[1], m[1] + ": " + (m[1] === "Version" ? m[2] : "")); if (m[1] === "Debug" && m[2]) detail(m[2]); continue; }
          }
          // a flattened section's details follow its heading on the same line: split at 2+ spaces
          const parts = p.flat ? p.text.split(/\s{2,}/) : [p.text];
          const headPart = parts.shift();
          const hm = headPart.match(/^([^:]*):\s?(.*)$/);
          cur = { key: name, head: name, value: noEmoji(hm ? hm[2].trim() : headPart), lines: [] };
          sections.push(cur);
          parts.forEach((x) => detail("  " + x));
        } else {
          p.text.split(/\n/).forEach(detail);
        }
      }
    } else {
      for (const line of msg.split("\n")) {
        const m = !/^\s/.test(line) && line.trim().match(HEAD_RE);
        if (m) {
          cur = { key: m[1], head: m[1], value: m[2].trim(), lines: [] };
          sections.push(cur);
        } else {
          detail(line);
        }
      }
    }
    const run = sections.find((s) => s.key === "Run");
    const mode = sections.find((s) => s.key === "Mode");
    let from = "", to = "";
    if (mode) {
      const mm = mode.value.match(/^(.*?)\s*→\s*(.*)$/);
      if (mm) { from = mm[1].trim(); to = mm[2].trim(); }
    }
    return { time: run ? run.value : "", from, to, sections: sections.filter((s) => s.key !== "Run") };
  }

  function render(message, opts) {
    const o = opts || {};
    const p = parse(message);
    if (!p.sections.length && !p.time) {
      return `<div style='padding:8px 10px;font-size:15px;font-weight:700;color:${C.muted};'>Empty log message</div>`;
    }
    const pill = `<div style='display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap;font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:7px 10px;border-radius:8px;background:color-mix(in srgb, ${C.blue} 16%, transparent);border:1px solid color-mix(in srgb, ${C.blue} 45%, transparent);'>`
      + `<span style='color:${C.blue};'>${esc(o.title || "Engine log")}</span>`
      + `<span style='font-weight:600;text-transform:none;letter-spacing:0;'>${p.time ? (o.timePrefix === undefined ? "Last run " : o.timePrefix) + esc(p.time) : ""}</span></div>`;
    return pill + p.sections.map((s) => {
      const col = HEADS[s.key] || C.text;
      return `<div style='display:flex;gap:10px;padding:9px 10px;margin-top:6px;border-radius:8px;background:color-mix(in srgb, ${col} 14%, transparent);border:1px solid color-mix(in srgb, ${col} 40%, transparent);'>`
        + `<div style='width:4px;border-radius:2px;background:${col};flex-shrink:0;'></div>`
        + `<div style='flex:1;min-width:0;'>`
        + (s.head ? `<div style='display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap;'>`
            + `<span style='font-size:17px;font-weight:800;color:${col};'>${esc(s.head)}</span>`
            + (s.value ? `<span style='font-size:16px;font-weight:700;color:var(--primary-text-color);'>${clr(s.value)}</span>` : "")
            + `</div>` : "")
        + s.lines.map((l) => `<div style='font-size:15px;color:var(--primary-text-color);opacity:.85;line-height:1.35;margin-top:2px;padding-left:${Math.max(0, l.ind - 2) * 4}px;'>${clr(l.t)}</div>`).join("")
        + `</div></div>`;
    }).join("");
  }

  window.battmanEngineLog = { parse, render, fromFileLine, HEADS };
})();
