// battman-countdown.js
// <battman-countdown></battman-countdown>: counts down to the next 5-minute Amber
// interval boundary (m:ss), updating every second. It inherits colour and font
// from its parent, so wrap it in a styled <span> to control how it looks.
// Battman's amber-countdown, loaded on every HA page.

import { battmanDefine } from "./battman-card-base.js";
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
battmanDefine('battman-countdown', BattmanCountdown);
