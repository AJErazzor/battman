// Guards the Theme studio's import path: every function it calls must exist in the file.
// The old stand-alone page defined applyChromeVars(); the card kept the call but not the
// function, so Import / Paste / Load from box threw halfway and the editor stayed half updated.
// usage: node theme_studio_import_check.js <battman-theme-studio.js>
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");

// Drop comments, string and template literals (the CSS and markup live in those) but keep code.
function codeOnly(s) {
  let out = "", i = 0, prev = "";
  while (i < s.length) {
    const c = s[i], d = s[i + 1];
    if (c === "/" && d === "*") { const e = s.indexOf("*/", i + 2); i = e < 0 ? s.length : e + 2; continue; }
    if (c === "/" && d === "/") { const e = s.indexOf("\n", i); i = e < 0 ? s.length : e; continue; }
    if (c === '"' || c === "'" || c === "`") {
      const q = c; i++;
      while (i < s.length) {
        if (s[i] === "\\") { i += 2; continue; }
        if (s[i] === q) { i++; break; }
        i++;
      }
      out += "0"; prev = "0"; continue;
    }
    if (c === "/" && (prev === "" || "=(,:!&|?{;".includes(prev))) {   // regex literal
      i++;
      while (i < s.length) {
        if (s[i] === "\\") { i += 2; continue; }
        if (s[i] === "[") { while (i < s.length && s[i] !== "]") i++; i++; continue; }
        if (s[i] === "/") { i++; break; }
        i++;
      }
      out += "0"; prev = "0"; continue;
    }
    out += c;
    if (!/\s/.test(c)) prev = c;
    i++;
  }
  return out;
}
// class methods (`run(root) {`) are declarations, not calls
const code = codeOnly(src).replace(/^[ \t]*[A-Za-z_$][\w$]*\s*\([^)]*\)\s*\{/gm, "");

const defined = new Set();
for (const m of code.matchAll(/\bfunction\s+([A-Za-z_$][\w$]*)/g)) defined.add(m[1]);
for (const m of code.matchAll(/\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=/g)) defined.add(m[1]);
for (const m of code.matchAll(/\bclass\s+([A-Za-z_$][\w$]*)/g)) defined.add(m[1]);
for (const m of src.matchAll(/import\s*\{([^}]*)\}/g)) m[1].split(",").forEach((n) => defined.add(n.trim().split(/\s+as\s+/).pop()));
for (const m of code.matchAll(/\bfunction\s*[A-Za-z_$\w]*\s*\(([^)]*)\)/g))
  m[1].split(",").forEach((p) => { p = p.trim().replace(/=.*$/, ""); if (/^[A-Za-z_$][\w$]*$/.test(p)) defined.add(p); });

const keywords = new Set(["if", "for", "while", "switch", "catch", "return", "function", "typeof", "new", "delete",
  "void", "do", "else", "try", "finally", "throw", "case", "in", "of", "instanceof", "yield", "await"]);
const globals = new Set(["Object", "Array", "String", "Number", "Boolean", "Math", "JSON", "Date", "RegExp", "Error",
  "Map", "Set", "Promise", "Function", "IntersectionObserver", "MutationObserver", "ResizeObserver", "parseInt",
  "parseFloat", "isNaN", "isFinite", "encodeURIComponent", "decodeURIComponent", "setTimeout", "clearTimeout",
  "setInterval", "clearInterval", "requestAnimationFrame", "fetch", "confirm", "prompt", "alert", "console",
  "document", "window", "FileReader", "File", "Blob", "URL", "URLSearchParams", "structuredClone"]);

const missing = new Set();
for (const m of code.matchAll(/(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(/g)) {
  const n = m[1];
  if (!defined.has(n) && !keywords.has(n) && !globals.has(n)) missing.add(n);
}
console.log(JSON.stringify({ missing: [...missing].sort() }));
