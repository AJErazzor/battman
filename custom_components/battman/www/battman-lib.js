// Battman shared card library: window.BattmanLib
// Served by the Battman integration at /battmanfiles/battman-lib.js (caching off, so
// no ?v= needed). Used by the Overrides card (timer maths, the cheapest-price calculators, presets), the
// Battman dialog (modal) and the cards' popups. Fixes are marked "Battman:" below.

window.BattmanLib=(function(){
var L = {};
L.VERSION = 1;
L.pad = function (n) { return ("0" + n).slice(-2); };
L.clk = function (d) { return L.pad(d.getHours()) + ":" + L.pad(d.getMinutes()); };
L.hm = function (sec) {
  var m = Math.round(sec / 60), h = Math.floor(m / 60);
  m = m % 60;
  return (h > 0 ? h + "h " : "") + m + "m";
};
L.hrs = function (sec) { return (Math.round(sec / 360) / 10) + "h"; };
L.hass = function () { return document.querySelector("home-assistant").hass; };
L.clkIcon = function () {
  return "<svg viewBox=\"0 0 24 24\" style=\"width:10px;height:10px;fill:var(--battman-text-dim);flex:none\"><path d=\"M13 3h-2v2h2V3zm7.03 4.39 1.42-1.42a9 9 0 0 0-1.42-1.42l-1.42 1.42A9 9 0 1 0 21 13a8.94 8.94 0 0 0-.97-5.61zM12 20a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm1-11h-2v6h2V9z\"/></svg>";
};
L.nextAt = function (v) {
  var p = String(v).split(":"), n = new Date(), t = new Date(n);
  t.setHours(parseInt(p[0], 10), parseInt(p[1], 10), 0, 0);
  var roll = false;
  if (t - n < 60000) { t.setDate(t.getDate() + 1); roll = true; }
  return { sec: Math.round((t - n) / 1000), roll: roll };
};
L.sunAt = function (H, k) {
  var s = H.states["sun.sun"];
  if (!s || !s.attributes || !s.attributes[k]) return null;
  var t = new Date(s.attributes[k]), n = new Date();
  if (t - n < 60000) return null;
  return { sec: Math.round((t - n) / 1000), at: L.clk(t) };
};
L.presetSec = function (p) {
  if (p.timer_at) return L.nextAt(p.timer_at).sec;
  return parseFloat(p.timer) || 0;
};
L.presetLabel = function (p, clkSvg) {
  if (p.timer_at) return "<span style=\"display:inline-flex;align-items:center;gap:2px;font-size:9px;font-weight:800;color:var(--battman-blue)\">\u2192" + p.timer_at + "</span>";
  if (p.timer > 0) return "<span style=\"display:inline-flex;align-items:center;gap:2px;font-size:9px;font-weight:700;color:var(--battman-text-dim)\">" + (clkSvg === undefined ? L.clkIcon() : clkSvg) + L.hrs(p.timer) + "</span>";
  return "";
};
L.preview = function (durH, untilStr, idleTxt) {
  var C = "var(--battman-blue)";
  var d = parseFloat(durH) || 0;
  if (d > 0) {
    var e = new Date(Date.now() + d * 3600000);
    return "<span style=\"color:" + C + "\">" + L.hm(d * 3600) + "</span> \u2192 until <span style=\"color:" + C + "\">" + L.clk(e) + "</span>";
  }
  if (untilStr) {
    var r = L.nextAt(untilStr);
    return "<span style=\"color:" + C + "\">until " + untilStr + "</span>"
         + (r.roll ? " <span style=\"color:var(--battman-amber)\">tomorrow</span>" : "")
         + " \u2192 <span style=\"color:" + C + "\">" + L.hm(r.sec) + "</span>";
  }
  return idleTxt || "";
};
L.timerSec = function (dEl, uEl) {
  var d = parseFloat(dEl.value) || 0;
  if (d > 0) return d * 3600;
  if (uEl.value) return L.nextAt(uEl.value).sec;
  return 0;
};
L.lockSvg = function (color, px) {
  return "<svg viewBox=\"0 0 24 24\" style=\"width:" + px + "px;height:" + px + "px;fill:" + color + ";flex:none\"><path d=\"M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z\"/></svg>";
};
L.runUntilList = function (H) {
  var out = [];
  var sr = L.sunAt(H, "next_rising"), ss = L.sunAt(H, "next_setting");
  if (sr) out.push(["Sunrise " + sr.at, sr.sec, sr.at]);
  if (ss) out.push(["Sunset " + ss.at, ss.sec, ss.at]);
  out.push(["Midnight", L.nextAt("00:00").sec, "00:00"]);
  out.push(["06:00", L.nextAt("06:00").sec, "06:00"]);
  return out;
};
L.hoursAtOrUnder = function (future, cents) {
  var h = 0;
  for (var i = 0; i < future.length; i++) { if (future[i].cents <= cents + 1e-6) h += future[i].durH; }
  return h;
};
L.futureIntervals = function (o) {
  var pf = o.price_field || "advanced_price_predicted";
  var nowMs = o.now_ms || Date.now();
  var dlMs = o.deadline_ms || 0;
  var future = [];
  for (var i = 0; i < o.forecasts.length; i++) {
    var f = o.forecasts[i];
    var start = Date.parse(f.start_time);
    if (isNaN(start) || start < nowMs) continue;
    if (dlMs && start >= dlMs) continue;
    var dollars = f[pf];
    if (dollars === undefined || dollars === null) dollars = f.per_kwh;
    if (dollars === undefined || dollars === null) continue;
    var durH = (f.duration || 5) / 60;
    future.push({ cents: dollars * 100, durH: durH });
  }
  future.sort(function (a, b) { return a.cents - b.cents; });
  return future;
};
L.cheapestFill = function (o) {
  var kwhPerPct = o.capacity_kwh / 100;
  var gapPct = Math.max(0, o.target_soc - o.cur_soc);
  var needKwh = gapPct * kwhPerPct;
  if (needKwh <= 0) return { ok: false, reason: "target_met", gapPct: gapPct };
  var dlMs = o.deadline_ms || 0;
  var future = L.futureIntervals(o);
  if (!future.length) return { ok: false, reason: dlMs ? "no_window" : "no_forecast" };
  var filled = 0, threshold = 0, used = 0;
  for (var j = 0; j < future.length; j++) {
    if (filled >= needKwh) break;
    filled += o.charge_kw * future[j].durH;
    threshold = future[j].cents;
    used++;
  }
  var step = o.round_step_cents || 1;
  var threshCents = Math.ceil((Math.round(threshold * 1e6) / 1e6) / step) * step;
  return {
    ok: true, threshold_cents: threshCents, threshold_raw: threshold,
    intervals_used: used, kwh_filled: filled, need_kwh: needKwh,
    fully_reachable: filled >= needKwh, gap_pct: gapPct, kwh_per_pct: kwhPerPct,
    hours_at_or_under: L.hoursAtOrUnder(future, threshCents)
  };
};
L.cheapestSustained = function (o) {
  var needMin = o.min_minutes || 30;
  var needIv = o.min_intervals || 1;
  var dlMs = o.deadline_ms || 0;
  var future = L.futureIntervals(o);
  if (!future.length) return { ok: false, reason: dlMs ? "no_window" : "no_forecast" };
  var mins = 0, threshold = 0, used = 0;
  for (var j = 0; j < future.length; j++) {
    if (mins >= needMin && used >= needIv) break;
    mins += future[j].durH * 60;
    threshold = future[j].cents;
    used++;
  }
  var step = o.round_step_cents || 1;
  var threshCents = Math.ceil((Math.round(threshold * 1e6) / 1e6) / step) * step;
  return {
    ok: true, threshold_cents: threshCents, threshold_raw: threshold,
    intervals_used: used, minutes_at_or_under: mins, need_minutes: needMin,
    need_intervals: needIv, enough: (mins >= needMin && used >= needIv),
    hours_at_or_under: L.hoursAtOrUnder(future, threshCents)
  };
};
return L;
})();


// ---------------------------------------------------------------------------------------------
// Battman: mode colours. The one place every Battman piece gets the battery modes' colours from
// (the Log page's timeline, the Live Activity bar via sensor.battman_theme_mode_colours).
// The five everyday modes are fixed: the Power view's Battery mode buttons. The three party
// modes (rainbow on those buttons) get the theme's other palette colours that are furthest from
// everything else, worked out per theme, so in every theme all eight are clearly different
// (no colour lines in the themes: their 12 palette colours are enough).
window.BattmanLib.MODE_HUE = {
  'Self Consume':     'blue',
  'Charge':           'yellow',
  'Discharge':        'green',
  'Float':            'orange',
  'Drain':            'red',
};
window.BattmanLib.PARTY_MODES = ['Charge Solar Off', 'Float Solar Off', 'Solar Soak'];
window.BattmanLib.MODES = Object.keys(window.BattmanLib.MODE_HUE).concat(window.BattmanLib.PARTY_MODES);
// every theme's palette (battman-<hue>)
window.BattmanLib.PALETTE = ['red', 'darkred', 'orange', 'amber', 'yellow', 'green', 'teal', 'sky',
                             'blue', 'purple', 'darkpurple', 'pink'];

// '#rrggbb' -> CIELAB, for "how different do these two colours look"
window.BattmanLib.hexLab = function (hex) {
  var h = String(hex).replace('#', '');
  var c = [0, 2, 4].map(function (i) {
    var u = parseInt(h.substr(i, 2), 16) / 255;
    return u > 0.04045 ? Math.pow((u + 0.055) / 1.055, 2.4) : u / 12.92;
  });
  var f = function (t) { return t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116; };
  var x = f((c[0] * 0.4124 + c[1] * 0.3576 + c[2] * 0.1805) / 0.95047);
  var y = f(c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722);
  var z = f((c[0] * 0.0193 + c[1] * 0.1192 + c[2] * 0.9505) / 1.08883);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
};

// {hue: '#rrggbb'} for the theme's palette -> {mode: hue} for all eight modes. Tries every
// choice of party-mode colours and keeps the one whose two closest colours are furthest apart
// (then the biggest total spread; then palette order), so the same theme always gives the same
// answer. Throws if a palette colour it needs is missing (no made-up colours).
window.BattmanLib.modeHues = function (hexByHue) {
  var L = window.BattmanLib, fixed = L.MODE_HUE, lab = {};
  L.PALETTE.forEach(function (h) {
    if (!/^#[0-9a-fA-F]{6}$/.test(String(hexByHue[h] || ''))) throw new Error('battman-' + h + ' is missing from the theme');
    lab[h] = L.hexLab(hexByHue[h]);
  });
  var used = Object.keys(fixed).map(function (m) { return fixed[m]; });
  var free = L.PALETTE.filter(function (h) { return used.indexOf(h) < 0; });
  var dist = function (a, b) { var A = lab[a], B = lab[b]; return Math.hypot(A[0] - B[0], A[1] - B[1], A[2] - B[2]); };
  var best = null;
  free.forEach(function (a) { free.forEach(function (b) { free.forEach(function (c) {
    if (a === b || b === c || a === c) return;
    var hues = used.concat([a, b, c]), min = Infinity, sum = 0;
    for (var i = 0; i < hues.length; i++) for (var j = i + 1; j < hues.length; j++) {
      var d = dist(hues[i], hues[j]); sum += d; if (d < min) min = d;
    }
    if (!best || min > best.min + 1e-9 || (Math.abs(min - best.min) <= 1e-9 && sum > best.sum + 1e-9)) best = { min: min, sum: sum, pick: [a, b, c] };
  }); }); });
  var out = {};
  Object.keys(fixed).forEach(function (m) { out[m] = fixed[m]; });
  L.PARTY_MODES.forEach(function (m, i) { out[m] = best.pick[i]; });
  return out;
};

// Any CSS colour (as getComputedStyle gives it) -> '#rrggbb', or '' if it isn't one.
window.BattmanLib.cssHex = function (value) {
  var v = String(value || '').trim(), m;
  if ((m = v.match(/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/))) {
    var h = m[1];
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    return '#' + h.slice(0, 6).toLowerCase();
  }
  if (v && typeof document !== 'undefined' && document.createElement) {   // named colours etc.: let the browser say
    var el = document.createElement('span');
    el.style.color = v;
    if (el.style.color && document.body) {
      document.body.appendChild(el);
      v = getComputedStyle(el).color;
      el.remove();
    }
  }
  if ((m = v.match(/^rgba?\(([^)]+)\)$/))) {
    var rgb = m[1].replace(/\//g, ',').split(',').slice(0, 3).map(function (p) { return Math.round(parseFloat(p)); });
    if (rgb.length === 3 && rgb.every(function (n) { return isFinite(n) && n >= 0 && n <= 255; }))
      return '#' + rgb.map(function (n) { return ('0' + n.toString(16)).slice(-2); }).join('');
  }
  return '';
};

// ---------------------------------------------------------------------------------------------
// Battman: Correct totals (the Billing card's popup). Sets a period's buy and sell totals with
// the totals event's SetTotal action, which the totals sensors record themselves.
window.BattmanLib.TOTAL_PERIODS = [['day', 'Today'], ['yesterday', 'Yesterday'], ['month', 'This Month'], ['bill', 'Billing Period']];

// Every --battman-* colour the active Battman theme defines, read off an element in the view (a dialog on the page body is outside the themed view).
window.BattmanLib.themeStyle = function (el) {
  var hass = document.querySelector('home-assistant').hass;
  var themes = (hass.themes && hass.themes.themes) || {};
  var name = Object.keys(themes).filter(function (n) { return /^Battman /.test(n); })[0];
  if (!name) return '';
  var keys = Object.keys(themes[name]).filter(function (k) { return /^battman-/.test(k); });
  keys.push('primary-font-family', 'ha-card-border-radius');
  var cs = getComputedStyle(el), out = '';
  keys.forEach(function (k) { var v = cs.getPropertyValue('--' + k).trim(); if (v) out += '--' + k + ':' + v + ';'; });
  return out;
};

// Correct totals opens in a Battman popup on the device that was tapped (no browser_mod).
window.BattmanLib.correctTotals = function (btn, ids) {
  var L = window.BattmanLib;
  // The button fires this on pointerup and on click (on an iPhone the tap inside this card never becomes a
  // click), so a second call right after the first is the same tap.
  if (L._ctAt && Date.now() - L._ctAt < 700) return;
  L._ctAt = Date.now();
  L._totals = ids;
  try {
    var hass = document.querySelector('home-assistant').hass;
    var dlg = L.modal(btn, {
      width: 'min(94vw,420px)', close: true,
      css: L.POPUP_CSS + '.bm .ph{font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--battman-orange,#f90);padding:4px 60px 8px 0;margin-bottom:8px;border-bottom:1px solid var(--battman-orange-border,#a60)}',
      html: '<div class="pop"><div class="ph">Correct totals</div>' + L.totalsForm(hass.states) + '</div>',
    });
    if (!dlg) L.toast(btn, "Correct totals can't open in this browser.");
  } catch (e) {
    L.toast(btn, 'Correct totals: ' + ((e && e.message) || e));   // say why, instead of doing nothing
  }
};

window.BattmanLib.totalsForm = function (states) {
  var ids = window.BattmanLib._totals;
  var b = states[ids.buy], s = states[ids.sell];
  if (!b || !s) return '<div style="padding:12px;color:var(--battman-red)">Correct totals: ' + (!b ? ids.buy : ids.sell) + ' not found</div>';
  var f4 = function (v) { var n = parseFloat(v); return isFinite(n) ? n.toFixed(4) : ''; };
  var INP = 'width:110px;text-align:right;font:inherit;font-size:14px;font-weight:600;padding:5px 8px;background:var(--battman-surface-card);border:1px solid var(--battman-border-neutral);border-radius:6px;color:var(--battman-text-bright)';
  var BTN = 'flex:1;height:34px;border-radius:8px;font:inherit;font-weight:700;font-size:13px;cursor:pointer;background:transparent';
  var stop = 'onclick="event.stopPropagation()" onmousedown="event.stopPropagation()" ontouchstart="event.stopPropagation()"';
  var html = '<div style="padding:4px 0 8px;font-size:13px;color:var(--battman-text-muted);line-height:1.4;white-space:normal">Fix a period\'s running totals. Battman asks first.</div>';
  window.BattmanLib.TOTAL_PERIODS.forEach(function (p) {
    var row = function (side, label) {
      return '<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0">'
        + '<span style="font-size:13px;color:var(--battman-text-muted)">' + label + ' $</span>'
        + '<input type="number" step="0.0001" data-side="' + side + '" value="' + f4((side === 'buy' ? b : s).attributes[p[0]]) + '" ' + stop + ' style="' + INP + '"></div>';
    };
    html += '<div data-period="' + p[0] + '" style="margin:0 0 10px;padding:10px 12px;border-radius:10px;background:var(--battman-surface-popup);border:1px solid var(--battman-border-neutral)">'
      + '<div style="font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--battman-text-bright);margin-bottom:4px">' + p[1] + '</div>'
      + row('sell', 'Sell') + row('buy', 'Buy')
      + '<div style="display:flex;gap:8px;margin-top:8px">'
      + '<button onclick="event.stopPropagation();window.BattmanLib.applyTotal(this,\'' + p[0] + '\')" style="' + BTN + ';border:1px solid var(--battman-amber);color:var(--battman-amber)">Apply</button>'
      + '<button onclick="event.stopPropagation();window.BattmanLib.resetTotal(this,\'' + p[0] + '\')" style="' + BTN + ';border:1px solid var(--battman-border-neutral);color:var(--battman-text-muted)">Reset</button>'
      + '</div><div class="bm-status" style="min-height:16px;margin-top:6px;font-size:12px"></div></div>';
  });
  return html;
};

window.BattmanLib._totalInputs = function (btn) {
  var box = btn.closest('[data-period]');
  return { box: box, buy: box.querySelector('input[data-side="buy"]'), sell: box.querySelector('input[data-side="sell"]'),
           status: box.querySelector('.bm-status') };
};

window.BattmanLib.resetTotal = function (btn, period) {
  var ids = window.BattmanLib._totals, st = document.querySelector('home-assistant').hass.states;
  var el = window.BattmanLib._totalInputs(btn);
  el.buy.value = parseFloat(st[ids.buy].attributes[period]).toFixed(4);
  el.sell.value = parseFloat(st[ids.sell].attributes[period]).toFixed(4);
  el.status.textContent = '';
};

// What Apply sends (kept separate so it can be checked without a browser).
window.BattmanLib.setTotalEvent = function (period, buyText, sellText) {
  var buy = parseFloat(buyText), sell = parseFloat(sellText);
  if (String(buyText).trim() === '' || String(sellText).trim() === '' || !isFinite(buy) || !isFinite(sell)) return null;
  return { attribute: 'SetTotal', period: period, buy: Math.round(buy * 10000) / 10000, sell: Math.round(sell * 10000) / 10000 };
};

window.BattmanLib.applyTotal = function (btn, period) {
  var ids = window.BattmanLib._totals, hass = document.querySelector('home-assistant').hass;
  var el = window.BattmanLib._totalInputs(btn);
  var label = window.BattmanLib.TOTAL_PERIODS.filter(function (p) { return p[0] === period; })[0][1];
  var say = function (t, ok) { el.status.textContent = t; el.status.style.color = ok ? 'var(--battman-green)' : 'var(--battman-red)'; };
  var data = window.BattmanLib.setTotalEvent(period, el.buy.value, el.sell.value);
  if (!data) { say(label + ': enter a number for both Sell and Buy', false); return; }
  var oldB = parseFloat(hass.states[ids.buy].attributes[period]).toFixed(4), oldS = parseFloat(hass.states[ids.sell].attributes[period]).toFixed(4);
  if (!confirm('Set ' + label + ':\n\nSell  $' + oldS + ' → $' + data.sell.toFixed(4) + '\nBuy   $' + oldB + ' → $' + data.buy.toFixed(4) + '\n\nThis overwrites the running totals.')) return;
  say('Applying…', true);
  hass.callWS({ type: 'fire_event', event_type: ids.event, event_data: data }).then(function () {
    // check the sensors took it: no silent success
    var t0 = Date.now();
    (function check() {
      var st = document.querySelector('home-assistant').hass.states;
      var okB = Math.abs(parseFloat(st[ids.buy].attributes[period]) - data.buy) < 0.00005;
      var okS = Math.abs(parseFloat(st[ids.sell].attributes[period]) - data.sell) < 0.00005;
      if (okB && okS) return say('✓ ' + label + ' updated', true);
      if (Date.now() - t0 > 5000) return say(label + ': not changed. The totals ignored it', false);
      setTimeout(check, 300);
    })();
  }, function (e) { say('Error: ' + ((e && e.message) || e), false); });
};

// ---------------------------------------------------------------------------------------------
// Battman: a save you can trust. Sends the event, then waits for the sensor to show the change
// (Battman's sensors ignore values they won't accept), and
// says what happened in HA's own toast, which survives the card redrawing with the new value.
window.BattmanLib.NOT_SAVED = "Not saved: Battman didn't take it";
window.BattmanLib.toast = function (el, message) {
  (el || document.querySelector('home-assistant')).dispatchEvent(new CustomEvent('hass-notification', { detail: { message: message }, bubbles: true, composed: true }));
};
window.BattmanLib.fireChecked = function (el, eventType, data, check, okText) {
  // A button that answers pointerup AND click (an iPhone tap inside the Billing card never becomes a click) calls
  // this twice for one tap: the second call, right after the first, is the same tap.
  if (el && el._fcAt && Date.now() - el._fcAt < 700) return Promise.resolve(false);
  if (el) el._fcAt = Date.now();
  var hass = document.querySelector('home-assistant').hass;
  if (el && el.tagName === 'BUTTON') el.disabled = true;
  var done = function (ok, msg) {
    if (el && el.tagName === 'BUTTON') el.disabled = false;
    window.BattmanLib.toast(el, msg);
    return ok;
  };
  return hass.callWS({ type: 'fire_event', event_type: eventType, event_data: data }).then(function () {
    var t0 = Date.now();
    return new Promise(function (resolve) {
      (function poll() {
        var ok = false;
        try { ok = !!check(document.querySelector('home-assistant').hass.states); } catch (e) {}
        if (ok) return resolve(done(true, okText || '✓ Saved'));
        if (Date.now() - t0 > 5000) return resolve(done(false, window.BattmanLib.NOT_SAVED));
        setTimeout(poll, 250);
      })();
    });
  }, function (e) { return done(false, 'Not saved: ' + ((e && e.message) || e)); });
};

// ---------------------------------------------------------------------------------------------
// Battman: the dashboard theme's eight mode colours, for sensor.battman_theme_mode_colours (a template
// sensor in Battman's packages: the iPhone Live Activity bar reads it, and theme: battman cards
// read its theme name). Templates can't see HA's themes, so the browser works the colours out
// and saves them, with the theme's name, in the parameters sensor (dashboardThemeColours).
// Whenever a Battman page is open it keeps them in step with the picked theme (dashboardTheme):
// a theme picked or changed (Settings, Make Active), or one Battman updated.

// A theme colour as #rrggbb, following var(--other) inside the theme. Throws an Error saying why not.
window.BattmanLib.themeHex = function (theme, key, depth) {
  depth = depth || 0;
  if (depth > 5) throw new Error(key + ': var() chain too deep');
  if (!(key in theme)) throw new Error(key + ' not in theme');
  var raw = String(theme[key]).trim(), m;
  if ((m = raw.match(/^var\(\s*--([a-z0-9-]+)\s*(?:,.*)?\)$/))) return window.BattmanLib.themeHex(theme, m[1], depth + 1);
  if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(raw)) {
    var h = raw.slice(1);
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    return '#' + h.slice(0, 6);
  }
  if ((m = raw.match(/^rgba?\(([^)]+)\)$/))) {
    var rgb = m[1].replace(/\//g, ',').split(',').slice(0, 3).map(function (p) { return Math.round(parseFloat(p)); });
    if (rgb.length === 3 && rgb.every(function (v) { return isFinite(v) && v >= 0 && v <= 255; }))
      return '#' + rgb.map(function (v) { return ('0' + v.toString(16)).slice(-2); }).join('');
  }
  throw new Error(key + " is '" + raw + "', not a colour Battman can read");
};

// What's saved for a theme: {theme, modes: {mode: '#rrggbb'}, hues: {mode: hue}}, or {theme, problem}.
window.BattmanLib.themeModeColours = function (themes, name) {
  var theme = themes && themes[name];
  if (!theme) return { theme: name, problem: "Theme '" + name + "' isn't loaded in Home Assistant" };
  var hex = {}, bad = [];
  window.BattmanLib.PALETTE.forEach(function (hue) {
    try { hex[hue] = window.BattmanLib.themeHex(theme, 'battman-' + hue); } catch (e) { bad.push(e.message); }
  });
  if (bad.length) return { theme: name, problem: bad.join('; ') };
  var hues = window.BattmanLib.modeHues(hex), modes = {};
  window.BattmanLib.MODES.forEach(function (m) { modes[m] = hex[hues[m]]; });
  return { theme: name, modes: modes, hues: hues };
};

// Keep the saved colours in step: checked when a page opens and every 15 seconds after. Only
// for a user who may fire events.
(function keepThemeColours() {
  var PARAMS = 'sensor.battman_parameters', EVENT = 'battman_parameters_update', busy = false, sent = '';
  function check() {
    var ha = document.querySelector('home-assistant'), hass = ha && ha.hass;
    if (!hass || !hass.themes || busy) return;
    if (hass.user && !hass.user.is_admin) return;
    var p = hass.states[PARAMS], name = p && String(p.attributes.dashboardTheme || '').trim();
    if (!name) return;
    var want = window.BattmanLib.themeModeColours(hass.themes.themes, name), key = JSON.stringify(want);
    if (key === JSON.stringify(p.attributes.dashboardThemeColours || null) || key === sent) return;
    sent = key;
    busy = true;
    hass.callWS({ type: 'fire_event', event_type: EVENT, event_data: { action: 'SetAttribute', dashboardThemeColours: want } })
      .catch(function () { sent = ''; })
      .then(function () { busy = false; });
  }
  [setTimeout(check, 3000), setInterval(check, 15000)].forEach(function (id) {
    if (id && id.unref) id.unref();      // (only outside a browser, e.g. tests: don't keep node running)
  });
})();

// ---------------------------------------------------------------------------------------------
// Battman: mode buttons that ask first. Sell, Sell Solar, HOOOOVER, House Party and Buy ask in a
// Battman panel (no browser_mod), when the press goes against the price, and just switch otherwise. The buttons
// fire a "battman_mode" dom event (as browser_mod's popups do); the listener below decides. Nothing it can't
// judge (a missing price, a failure here) stops the press: the mode is set. Active and Curtail ask in the same panel.
window.BattmanLib.MODE_NAMES = { 'Charge': 'Buy', 'Discharge': 'Sell', 'Float': 'Sell Solar', 'Charge Solar Off': 'HOOOOVER', 'Float Solar Off': 'House Party' };
window.BattmanLib.centsText = function (c) { return (c < 0 ? '-' : '') + Math.abs(c).toFixed(1) + 'c'; };

// The question to ask before switching to `option`, or null to just switch. x: { option, buy, fit }
// (c/kWh, NaN when unknown), confirmPrice
// (the "warn when a mode goes against the price" setting), buyAbove (c/kWh; 0 or blank = never).
window.BattmanLib.modeWarning = function (x) {
  var T = window.BattmanLib.centsText, name = window.BattmanLib.MODE_NAMES[x.option];
  if (!name) return null;
  if (x.confirmPrice !== false) {
    if ((x.option === 'Discharge' || x.option === 'Float') && isFinite(x.fit) && x.fit < 0)
      return 'Feed-in is ' + T(x.fit) + ': you would pay to export. ' + name + ' anyway?';
    if ((x.option === 'Charge Solar Off' || x.option === 'Float Solar Off') && isFinite(x.buy) && x.buy >= 0)
      return 'Buy is ' + T(x.buy) + ': ' + name + ' is for negative prices. ' + name + ' anyway?';
  }
  if (x.option === 'Charge' && x.buyAbove > 0 && isFinite(x.buy) && x.buy > x.buyAbove)
    return 'Buy is ' + T(x.buy) + ', above your ' + T(x.buyAbove) + ' limit. ' + name + ' anyway?';
  return null;
};

window.BattmanLib.setMode = function (d, el) {
  var hass = document.querySelector('home-assistant').hass;
  var go = function () { hass.callService('input_select', 'select_option', { entity_id: d.mode, option: d.option }); };
  var warning = null;
  try {
    var st = hass.states, p = (st[d.parameters] || {}).attributes || {};
    var cents = function (id) { return st[id] ? parseFloat(st[id].state) * 100 : NaN; };
    warning = window.BattmanLib.modeWarning({
      option: d.option, buy: cents('sensor.amber_5min_current_general_price'), fit: cents('sensor.amber_5min_current_feed_in_price'),
      confirmPrice: p.confirmPriceMismatch, buyAbove: parseFloat(p.confirmBuyAbove),
    });
  } catch (e) { warning = null; }
  if (!warning) return go();
  window.BattmanLib.askMode(warning, d.option, go, el);
};

// Battman's own popups: a native <dialog> opened with showModal(), so it sits in the browser's top layer (above
// HA's header and bars) and Escape, focus and an inert page come with it. No browser_mod. The dialog lives on
// document.body, outside the themed view, so the Battman colours are read off the tapped element and set on it.
window.BattmanLib.MODAL_KEYS = ['surface-popup', 'surface-card', 'text-bright', 'text-muted', 'text-dim', 'orange', 'orange-wash',
  'orange-border', 'orange-border-strong', 'border-neutral', 'green', 'yellow', 'amber', 'blue', 'purple', 'darkred', 'red', 'font'];
window.BattmanLib.modalTheme = function (el) {
  var cs = getComputedStyle(el || document.body), out = '';
  try { out = window.BattmanLib.themeStyle(el || document.body) || ''; } catch (e) { out = ''; }   // every --battman-* the theme defines
  window.BattmanLib.MODAL_KEYS.forEach(function (k) {
    if (out.indexOf('--battman-' + k + ':') >= 0) return;
    var v = String(cs.getPropertyValue('--battman-' + k) || '').trim();
    if (v) out += '--battman-' + k + ':' + v + ';';
  });
  ['hooover', 'houseparty'].forEach(function (ns) {          // the theme's effect variables (the forecast's Hooover / House Party rows)
    ['chase-display', 'chase-gradient', 'chase-duration', 'ring-width', 'border', 'glow-name', 'glow-color', 'glow-duration'].forEach(function (k) {
      var v = String(cs.getPropertyValue('--fx-' + ns + '-' + k) || '').trim();
      if (v) out += '--fx-' + ns + '-' + k + ':' + v + ';';
    });
  });
  ['primary-font-family', 'primary-text-color'].forEach(function (k) {
    var v = String(cs.getPropertyValue('--' + k) || '').trim();
    if (v) out += '--' + k + ':' + v + ';';
  });
  if (out.indexOf('--primary-font-family:') >= 0 && out.indexOf('--battman-font:') < 0)
    out += '--battman-font:' + String(cs.getPropertyValue('--primary-font-family')).trim() + ';';
  return out;
};

// Open a popup. o: { width: css length, html: the content (trusted markup), css: extra rules (scoped to .bm),
// close: true adds a ✕ button, onClose: called after it closes }. Returns the dialog, or null where <dialog>
// can't do this (the caller then falls back). Cancel / ✕, a tap on the dim backdrop, and Escape all close it.
window.BattmanLib.modal = function (el, o) {
  var L = window.BattmanLib;
  if (L._modal) { try { L._modal.close(); } catch (e) { /* already closed */ } }
  var dlg = document.createElement('dialog');
  if (!dlg.showModal) return null;
  dlg.setAttribute('style', L.modalTheme(el) + '--bm-w:' + (o.width || 'min(92vw,360px)') + ';');
  dlg.className = 'bm';
  dlg.setAttribute('autofocus', '');   // showModal() focuses the dialog itself, not the first button (no stray ring)
  dlg.innerHTML =
    '<style>' +
    'dialog.bm{padding:0;border:0;background:transparent;max-width:var(--bm-w);width:92vw;overflow:visible;color:var(--battman-text-bright,#eee);font-family:var(--battman-font,inherit)}' +
    'dialog.bm[open]{display:flex;flex-direction:column;max-height:calc(100vh - 32px);max-height:calc(100dvh - env(safe-area-inset-top,0px) - env(safe-area-inset-bottom,0px) - 32px)}' +
    '.bm .bm-scroll{min-height:0;overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch}' +
    'dialog.bm:focus,.bm button:focus:not(:focus-visible){outline:none}' +
    'dialog.bm::backdrop{background:rgba(0,0,0,.55)}' +
    '.bm .x{position:absolute;top:10px;right:10px;z-index:2;width:44px;height:38px;padding:0;border-radius:10px;border:1px solid var(--battman-border-neutral-soft,#333);background:var(--battman-surface-card,#000);color:var(--battman-text-muted,#999);font-size:18px;line-height:1;cursor:pointer;-webkit-tap-highlight-color:transparent}' +
    '.bm .x:active{filter:brightness(1.5)}' +
    (o.css || '') + '</style>' + (o.close ? '<button class="x" type="button" aria-label="Close">✕</button>' : '') + '<div class="bm-scroll">' + o.html + '</div>';
  // The page's own overflow, remembered once while no dialog is open. (dialog.close() fires its close event on a
  // later tick, so a dialog opened over another must not take the first one's "hidden" for the original.)
  if (L._overflow0 === undefined) L._overflow0 = document.documentElement.style.overflow;
  if (o.close) dlg.querySelector('.x').addEventListener('click', function () { dlg.close(); });
  // the dialog's own box is just the content, so a tap on the dialog itself is a tap on the backdrop
  var openedAt = Date.now();   // (a click that is still on its way from the tap that opened this must not close it)
  dlg.addEventListener('click', function (e) { if (e.target === dlg && Date.now() - openedAt > 500) dlg.close(); });
  // Escape closes it, including the synthetic Escape the popups' own scripts send to close themselves
  var onKey = function (e) { if (e.key === 'Escape' && dlg.open) dlg.close(); };
  dlg.addEventListener('close', function () {
    document.removeEventListener('keydown', onKey);
    dlg.remove();
    if (L._modal === dlg) {            // (not when another dialog has already taken over)
      L._modal = null;
      document.documentElement.style.overflow = L._overflow0;
      L._overflow0 = undefined;
    }
    if (el && el.focus) { try { el.focus({ preventScroll: true }); } catch (e) { /* not focusable */ } }
    if (o.onClose) o.onClose();
  });
  document.addEventListener('keydown', onKey);
  document.body.appendChild(dlg);
  document.documentElement.style.overflow = 'hidden';
  L._modal = dlg;
  dlg.showModal();
  return dlg;
};

window.BattmanLib.askMode = function (message, option, go, el) {
  var name = window.BattmanLib.MODE_NAMES[option] || option;
  window.BattmanLib.askConfirm(name + '?', message, name + ' anyway', go, el);
};

// Any yes/no question, in the same panel: heading, message, Cancel, and a confirm button. Without <dialog>
// support the browser's own confirm box asks instead.
window.BattmanLib.askConfirm = function (title, message, okLabel, go, el) {
  var answer = false;
  var dlg = window.BattmanLib.modal(el, {
    width: 'min(92vw,360px)',
    css: '.bm .p{background:var(--battman-surface-popup,#111);padding:14px 16px;border-radius:8px;border:1px solid var(--battman-orange-border,#a60)}' +
      '.bm .h{font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:var(--battman-orange,#f90);padding-bottom:8px;margin-bottom:10px;border-bottom:1px solid var(--battman-orange-border,#a60)}' +
      '.bm .m{font-size:14px;line-height:1.5;margin-bottom:14px}' +
      '.bm .r{display:flex;gap:8px}' +
      '.bm .r button{flex:1;min-height:44px;border-radius:8px;font-family:inherit;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;-webkit-tap-highlight-color:transparent}' +
      '.bm .no{background:transparent;color:var(--battman-text-muted,#999);border:1px solid var(--battman-border-neutral,#444)}' +
      '.bm .yes{flex:1.4;background:var(--battman-orange-wash,#320);color:var(--battman-orange,#f90);border:1px solid var(--battman-orange-border-strong,#f90)}',
    html: '<div class="p"><div class="h"></div><div class="m"></div><div class="r"><button class="no" type="button">Cancel</button><button class="yes" type="button"></button></div></div>',
    onClose: function () { if (answer && go) go(); },
  });
  if (!dlg) { if (window.confirm(message) && go) go(); return; }
  dlg.querySelector('.h').textContent = title;
  dlg.querySelector('.m').textContent = message;
  dlg.querySelector('.yes').textContent = okLabel;
  dlg.querySelector('.yes').addEventListener('click', function () { answer = true; dlg.close(); });
  dlg.querySelector('.no').addEventListener('click', function () { dlg.close(); });
};

// Content popups, opened by a button's "battman_popup" dom event. d.kind says which.
window.BattmanLib.POPUPS = {};
window.BattmanLib.showPopup = function (d, el) {
  var fn = window.BattmanLib.POPUPS[d.kind];
  if (fn) fn(d, el);
};

// The scrolling panel every content popup is drawn in.
window.BattmanLib.POPUP_CSS = '.bm .pop{box-sizing:border-box;width:100%;padding:10px 12px;border-radius:8px;background:var(--battman-surface-popup);color:var(--primary-text-color);font-family:var(--primary-font-family,var(--battman-font,sans-serif))}';

// The "Next hours" forecast (State card's tap): the <battman-forecast-view> element (battman-forecast-view.js), which
// shows what Battman's real engine would do over the next hours. The strip above it is for the ✕.
window.BattmanLib.POPUPS.forecast = function (d, el) {
  window.BattmanLib.modal(el, {
    width: 'min(94vw,480px)', close: true,
    css: '.bm .fc{padding-top:56px;background:var(--battman-surface-card,#000);border-radius:8px}',
    html: '<div class="fc"><battman-forecast-view></battman-forecast-view></div>',
  });
};

// Engine log (Battery mode card's info button): the engine's last-run log, drawn by Battman's engine log
// renderer (battman-enginelog.js), the same one the Log page uses. d.log is the log sensor's entity id.
window.BattmanLib.POPUPS.enginelog = function (d, el) {
  var note = function (t, c) { return "<div style='padding:8px 10px;font-size:15px;font-weight:700;color:" + c + ";'>" + t + '</div>'; };
  var esc = function (t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); };
  var body, st = ((document.querySelector('home-assistant') || {}).hass || { states: {} }).states[d.log], R = window.battmanEngineLog;
  if (!R) body = note("Engine log: Battman's log renderer (battman-enginelog.js) isn't loaded. Refresh the page.", 'var(--battman-darkred)');
  else if (!st) body = note('Engine log: missing ' + esc(d.log), 'var(--battman-darkred)');
  else {
    var raw = String((st.attributes || {}).message == null ? '' : st.attributes.message);
    body = raw.trim() ? R.render(raw, { title: 'Engine log' }) : note(esc(d.log) + ' has no log message yet.', 'var(--battman-text-muted)');
  }
  window.BattmanLib.modal(el, { width: 'min(94vw,480px)', css: window.BattmanLib.POPUP_CSS, close: true, html: '<div class="pop">' + body + '</div>' });
};

// Active / Curtail: ask before flipping the switch.
window.BattmanLib.setToggle = function (d, el) {
  var hass = document.querySelector('home-assistant').hass;
  var st = hass.states[d.entity], isOn = st && st.state === 'on';
  var msg = isOn ? d.ask_off : d.ask_on;
  if (isOn && d.ask_off_negative && d.price && hass.states[d.price]) {      // turning off while feed-in is negative: say so
    var c = parseFloat(hass.states[d.price].state) * 100;
    if (isFinite(c) && c < 0) msg = d.ask_off_negative.replace('{price}', window.BattmanLib.centsText(c));
  }
  window.BattmanLib.askConfirm(d.name + '?', msg, isOn ? 'Turn off' : 'Turn on',
    function () { hass.callService('homeassistant', 'toggle', { entity_id: d.entity }); }, el);
};

if (typeof window.addEventListener === 'function' && !window.BattmanLib._modeListener) {
  window.BattmanLib._modeListener = true;
  window.addEventListener('ll-custom', function (ev) {
    var d = ev.detail && ev.detail.battman_mode;
    var el = ev.composedPath ? ev.composedPath()[0] : ev.target;
    if (d) window.BattmanLib.setMode(d, el);
    var pp = ev.detail && ev.detail.battman_popup;
    if (pp) window.BattmanLib.showPopup(pp, el);
    var t = ev.detail && ev.detail.battman_toggle;
    if (t) window.BattmanLib.setToggle(t, el);
  });
}
