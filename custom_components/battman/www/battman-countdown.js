// battman-countdown.js
// <battman-countdown></battman-countdown>: counts down to the next 5-minute Amber
// interval boundary (m:ss), updating every second. It inherits colour and font
// from its parent, so wrap it in a styled <span> to control how it looks.
// Battman's copy of Smiggles' amber-countdown (same logic), loaded on every HA page.
class BattmanCountdown extends HTMLElement {
  connectedCallback() {
    this._update();
    this._interval = setInterval(() => this._update(), 1000);
  }
  disconnectedCallback() {
    clearInterval(this._interval);
  }
  _update() {
    const now = new Date();
    const secsInBlock = (now.getMinutes() % 5) * 60 + now.getSeconds();
    const totalSecs = 5 * 60 - secsInBlock;
    const m = Math.floor(totalSecs / 60);
    const s = totalSecs % 60;
    this.textContent = m + ':' + String(s).padStart(2, '0');
  }
}
// Register a custom element so HA finds it. HA's frontend may swap window.customElements for
// its own registry (a compatibility layer) while it starts; anything registered just before the
// swap is lost to HA. So register now, and again in HA's registry if the swap comes after us.
function battmanDefine(tag, cls) {
  const reg = window.customElements;
  if (!reg.get(tag)) reg.define(tag, cls);
  const t0 = Date.now();
  (function watch() {
    const now = window.customElements;
    if (now !== reg) {
      if (!now.get(tag)) {
        try { now.define(tag, cls); } catch (e) { console.error(`Battman: couldn't register ${tag}: ${e.message}`); }
      }
      return;
    }
    // HA's registry was already in place when we registered (it leaves this marker): nothing to wait for
    if (window.CustomElementRegistryPolyfill) return;
    if (Date.now() - t0 < 30000) setTimeout(watch, 20);
  })();
}


battmanDefine('battman-countdown', BattmanCountdown);
