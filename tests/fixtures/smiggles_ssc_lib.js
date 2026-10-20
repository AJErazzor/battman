// The original Smiggles ssc-lib.js (v8), kept unchanged so tests can run the original
// overrides card next to Battman's. Never shipped; test data only.
// SSC dock shared library — window.SSCLIB
// Version: 8  (keep in sync with the resource URL ?v=N and SSCLIB.VERSION below)
// Hoisted verbatim from dashboard variables.ssc.lib_src (dedup, 2026-09-28).
// Loaded as a Lovelace module resource: /local/smiggles/ssc-lib.js
// Bump ?v=N in the resource URL on every edit to bust the browser cache.

window.SSCLIB=(function(){
var L = {};
L.VERSION = 8;   // bump together with the resource URL ?v=N on every edit
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
  return "<svg viewBox=\"0 0 24 24\" style=\"width:10px;height:10px;fill:var(--smiggles-text-dim);flex:none\"><path d=\"M13 3h-2v2h2V3zm7.03 4.39 1.42-1.42a9 9 0 0 0-1.42-1.42l-1.42 1.42A9 9 0 1 0 21 13a8.94 8.94 0 0 0-.97-5.61zM12 20a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm1-11h-2v6h2V9z\"/></svg>";
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
  if (p.timer_at) return "<span style=\"display:inline-flex;align-items:center;gap:2px;font-size:9px;font-weight:800;color:var(--smiggles-blue)\">\u2192" + p.timer_at + "</span>";
  if (p.timer > 0) return "<span style=\"display:inline-flex;align-items:center;gap:2px;font-size:9px;font-weight:700;color:var(--smiggles-text-dim)\">" + (clkSvg === undefined ? L.clkIcon() : clkSvg) + L.hrs(p.timer) + "</span>";
  return "";
};
L.preview = function (durH, untilStr, idleTxt) {
  var C = "var(--smiggles-blue)";
  var d = parseFloat(durH) || 0;
  if (d > 0) {
    var e = new Date(Date.now() + d * 3600000);
    return "<span style=\"color:" + C + "\">" + L.hm(d * 3600) + "</span> \u2192 until <span style=\"color:" + C + "\">" + L.clk(e) + "</span>";
  }
  if (untilStr) {
    var r = L.nextAt(untilStr);
    return "<span style=\"color:" + C + "\">until " + untilStr + "</span>"
         + (r.roll ? " <span style=\"color:var(--smiggles-amber)\">tomorrow</span>" : "")
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


/* ── Row + popup renderers (hoisted from the ssc_row template, 2026-10-01) ── */
window.SSCLIB.renderRow = function(variables, states, entity, ov_id){
  ov_id = ov_id || (variables && variables.ov_id);
var cfg = variables.ssc.overrides.filter(function(o){return o.id===ov_id;})[0];
  if (!cfg) return '';
  var S = variables.ssc;
  var a = entity.attributes;
  var soc   = parseFloat(a[cfg.attr_soc])   || 0;
  var price = parseFloat(a[cfg.attr_price]) || 0;
  var on    = soc > 0 || price > 0 || (cfg.allow_negative && price < 0);
  var c     = cfg.color;
  var bg     = on ? cfg.bg : 'linear-gradient(' + cfg.shade + ',' + cfg.shade + '), var(--smiggles-surface-card)';
  var border = on ? cfg.dim : cfg.shade_border;
  var cur  = parseFloat(states[S.soc_entity] && states[S.soc_entity].state) || 0;
  var isSpecial = cfg.special_at > 0 && soc === cfg.special_at;
  var locked = a[cfg.attr_reset] === false || a[cfg.attr_reset] === 'false';
  var plug = cfg.id === 'drain' && on && (a.drainBatteryPlughole === true || a.drainBatteryPlughole === 'true');
  var lockAmber = '<svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:var(--smiggles-amber);flex:none;display:block"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>';

  var pname = '';
  var pl = a.overridePresets || [];
  for (var i = 0; i < pl.length; i++) {
    var v = pl[i].values || {};
    if (Object.keys(v).length === 1 && v[cfg.id]
        && (parseFloat(v[cfg.id].soc)   || 0) === soc
        && (parseFloat(v[cfg.id].price) || 0) === price
        && ((v[cfg.id].allowReset === false) === locked)) { pname = pl[i].name; break; }
  }

  var rem  = cfg.direction === 'up' ? (soc - cur) : (cur - soc);
  var kwh  = Math.abs(rem) * S.kwh_per_pct;
  var live = on && soc > 0 && !isSpecial && rem > 0.5;
  var cost = (live && price > 0) ? (kwh * price / 100) : 0;

  var nameW  = (on && pname) ? pname.length * 7.5 : 0;
  var costFz = 24, costMw = 52, costInline = false;
  if (cost > 0) {
    if (nameW > 116)      { costInline = true; }
    else if (nameW > 96)  { costFz = 18; costMw = 44; }
    else if (nameW > 72)  { costFz = 20; costMw = 48; }
  }
  // Full-row squeeze with no preset name: wide SOC (100%) plus a multi-digit
  // PRICE leaves too little for the right-hand l2/l3 lines, so step COST down
  // even though no name triggered the ladder above. One extra digit in SOC or
  // PRICE each knock cost down a tier; both wide -> inline.
  if (cost > 0 && costFz === 24) {
    var wide = (soc >= 100 ? 1 : 0) + (price >= 10 ? 1 : 0);
    if (wide >= 2)      { costFz = 18; costMw = 44; }
    else if (wide >= 1) { costFz = 20; costMw = 48; }
  }

  var l1 = '', l2 = '', l3 = '';
  if (isSpecial) {
    if (pname && on) {
      l1 = '<span>' + pname.toUpperCase() + '</span>';
      l2 = '<span>' + cfg.special_desc + '</span>';
    } else {
      l1 = '<span>' + cfg.special_desc + '</span>';
    }
  }
  else if (pname && on) l1 = '<span>' + pname.toUpperCase() + '</span>';
  else if (!on)         l1 = '<span>TAP TO SET</span>';
  if (plug) l1 = '<span>PLUGHOLE</span>';   // Plughole wins the label slot on the Drain row

  if (on && soc > 0 && !isSpecial) {
    if (live) {
      l2 = cur.toFixed(0) + '% \u2192 ' + soc.toFixed(0) + '%';
      l3 = kwh.toFixed(1) + ' kWh';
    } else {
      l2 = 'target met';
    }
  }

  if (costInline && l3) {
    l3 += ' <span style="font-weight:800;opacity:1;letter-spacing:0.04em">\u00b7 $' + cost.toFixed(2) + '</span>';
  }

  var vOp = on ? '1' : '0.5', tOp = on ? '1' : '0.75', nOp = on ? '1' : '0.55';
  var fmt = function (v, u, d) { return v > 0 ? v.toFixed(d) + u : '\u2014'; };

  var vcol = function (label, val, mw, fz, op, pr) {
    var dash = (val === '\u2014');
    if (pr === undefined) pr = 8;
    return '<div style="display:flex;flex-direction:column;min-width:' + mw + 'px;flex:none;padding-right:' + pr + 'px">'
         +   '<span style="font-size:8px;font-weight:700;letter-spacing:0.1em;opacity:0.55;margin-bottom:3px">' + label + '</span>'
         +   '<span style="height:23px;display:flex;align-items:center;' + (dash ? 'justify-content:center;' : '') + 'font-size:' + fz + 'px;font-weight:900;line-height:1;white-space:nowrap;opacity:' + op + '">' + val + '</span>'
         + '</div>';
  };

  var moneyCol = (cost > 0 && !costInline)
    ? vcol(cfg.money_label, '$' + cost.toFixed(2), costMw, costFz, '1', 0)
    : '';

  var labelCol = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:64px;flex:none">'
               + (locked ? '<div style="line-height:0;margin-bottom:3px">' + lockAmber + '</div>' : '')
               + '<div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;line-height:1.15;text-align:center;opacity:' + tOp + '">' + cfg.row_label + '</div>'
               + '</div>';

  return '<div style="position:relative;height:60px;box-sizing:border-box;border-radius:8px;overflow:hidden;'
       +   'background:' + bg + ';border:' + (plug ? '1.5px solid ' + c : '1px solid ' + border) + ';color:' + c + ';cursor:pointer">'
       +  '<div style="display:flex;align-items:center;gap:8px;padding:0 12px 0 10px;height:100%">'
       +   labelCol
       +   vcol('SOC',   fmt(soc, '%', 0),        50, 24, vOp)
       +   vcol('PRICE', ((cfg.allow_negative && price < 0) ? (price.toFixed(1) + '\u00a2') : fmt(price, '\u00a2', 1)), 54, 24, vOp)
       +   moneyCol
       +   '<div style="margin-left:auto;flex:0 1 auto;text-align:right;line-height:1.25;white-space:nowrap;min-width:0">'
       +    (l1 ? '<div style="font-size:12px;font-weight:800;letter-spacing:0.04em;display:flex;align-items:center;gap:4px;justify-content:flex-end;opacity:' + nOp + '">' + l1 + '</div>' : '')
       +    (l2 ? '<div style="font-size:12px;font-weight:700;opacity:0.9">' + l2 + '</div>' : '')
       +    (l3 ? '<div style="font-size:12px;font-weight:700;opacity:0.9">' + l3 + '</div>' : '')
       +   '</div>'
       +  '</div></div>';
};
window.SSCLIB.buildPopup = function(variables, states, entity, ov_id){
  ov_id = ov_id || (variables && variables.ov_id);
var cfg = variables.ssc.overrides.filter(function(o){return o.id===ov_id;})[0];
  var S = variables.ssc;
  var C = cfg.color, D = cfg.dim, W = cfg.shade;
  var inner =
    'window.sscqRoot=root;try{(function(r){try{var found=null;function walk(root){if(found)return;var els=root.querySelectorAll("*");for(var i=0;i<els.length;i++){var el=els[i];if(!found){var v=getComputedStyle(el).getPropertyValue("--smiggles-purple");if(v&&v.trim()){found=el;return;}}if(el.shadowRoot){walk(el.shadowRoot);if(found)return;}}}walk(document);var s=found||document.body;var c=getComputedStyle(s);["--smiggles-red","--smiggles-red-wash","--smiggles-red-border","--smiggles-red-border-soft","--smiggles-red-border-light","--smiggles-red-border-strong","--smiggles-red-bg","--smiggles-red-soft-bg","--smiggles-darkred","--smiggles-darkred-wash","--smiggles-darkred-border","--smiggles-darkred-border-soft","--smiggles-darkred-border-light","--smiggles-darkred-border-strong","--smiggles-darkred-bg","--smiggles-darkred-soft-bg","--smiggles-darkred","--smiggles-darkred-wash","--smiggles-darkred-border","--smiggles-darkred-border-soft","--smiggles-darkred-border-light","--smiggles-darkred-border-strong","--smiggles-darkred-bg","--smiggles-darkred-soft-bg","--smiggles-orange","--smiggles-orange-wash","--smiggles-orange-border","--smiggles-orange-border-soft","--smiggles-orange-border-light","--smiggles-orange-border-strong","--smiggles-orange-bg","--smiggles-orange-soft-bg","--smiggles-amber","--smiggles-amber-wash","--smiggles-amber-border","--smiggles-amber-border-soft","--smiggles-amber-border-light","--smiggles-amber-border-strong","--smiggles-amber-bg","--smiggles-amber-soft-bg","--smiggles-yellow","--smiggles-yellow-wash","--smiggles-yellow-border","--smiggles-yellow-border-soft","--smiggles-yellow-border-light","--smiggles-yellow-border-strong","--smiggles-yellow-bg","--smiggles-yellow-soft-bg","--smiggles-green","--smiggles-green-wash","--smiggles-green-border","--smiggles-green-border-soft","--smiggles-green-border-light","--smiggles-green-border-strong","--smiggles-green-bg","--smiggles-green-soft-bg","--smiggles-blue","--smiggles-blue-wash","--smiggles-blue-border","--smiggles-blue-border-soft","--smiggles-blue-border-light","--smiggles-blue-border-strong","--smiggles-blue-bg","--smiggles-blue-soft-bg","--smiggles-purple","--smiggles-purple-wash","--smiggles-purple-border","--smiggles-purple-border-soft","--smiggles-purple-border-light","--smiggles-purple-border-strong","--smiggles-purple-bg","--smiggles-purple-soft-bg","--smiggles-darkpurple","--smiggles-darkpurple-wash","--smiggles-darkpurple-border","--smiggles-darkpurple-border-soft","--smiggles-darkpurple-border-light","--smiggles-darkpurple-border-strong","--smiggles-darkpurple-bg","--smiggles-darkpurple-soft-bg","--smiggles-teal","--smiggles-teal-wash","--smiggles-teal-border","--smiggles-teal-border-soft","--smiggles-teal-border-light","--smiggles-teal-border-strong","--smiggles-teal-bg","--smiggles-teal-soft-bg","--smiggles-text-bright","--smiggles-text-muted","--smiggles-text-dim","--smiggles-surface-card","--smiggles-surface-popup","--smiggles-border-neutral","--smiggles-border-neutral-soft"].forEach(function(v){var x=c.getPropertyValue(v);if(x)r.style.setProperty(v,x.trim());});}catch(e){}})(root);'
  + 'var H=document.querySelector("home-assistant").hass;'
  + 'if(!window.SSCLIB){if(!window.__ssclibLoad){window.__ssclibLoad=1;var _s=document.createElement("script");_s.src="/local/smiggles/ssc-lib.js?v=1";_s.onload=function(){window.__ssclibLoad=2;sscDraw(root);};document.head.appendChild(_s);}else{setTimeout(function(){sscDraw(root);},150);}return;}var L=window.SSCLIB;'
  + 'var P=(H.states["' + S.params_entity + '"]||{}).attributes||{};'
  + 'var AS="' + cfg.attr_soc + '",AP="' + cfg.attr_price + '",ID="' + cfg.id + '",AR="' + cfg.attr_reset + '";'
  + 'var TMR="' + S.timer_entity + '";'
  + 'var SOCE="' + S.soc_entity + '",FCE="' + S.forecast_entity + '",CKW="' + S.charge_kw_entity + '",CAP="' + S.capacity_entity + '";'
  + 'var PFIELD="' + S.price_field + '",RSTEP=' + (S.round_step_cents || 1) + ',SMIN=' + (S.safety_min_minutes || 30) + ',SIVL=' + (S.safety_min_intervals || 2) + ';'
  + 'var ISBUY=' + (cfg.id === 'any' ? 'true' : 'false') + ';'
  + 'var LKA=L.lockSvg("var(--smiggles-amber)",13);'
  + 'var Q=function(x){return sscqRoot.querySelector(x);};'
  + 'window.sscqUntilSec=0;'
  + 'window.sscqPv=function(){Q("#sscq-pv").innerHTML=L.preview(Q("#sscq-t").value,Q("#sscq-u").value,"no timer \u2014 stays until cleared");};'
  + 'window.sscqIn=function(w){window.sscqUntilSec=0;var d=Q("#sscq-t"),u=Q("#sscq-u");if(w===0&&d.value)u.value="";if(w===1&&u.value)d.value="";sscqPv();};'
  + 'window.sscqDur=function(h){window.sscqUntilSec=0;Q("#sscq-u").value="";Q("#sscq-t").value=h;sscqPv();};'
  + 'var UL=L.runUntilList(H);'
  + 'window.sscqUL=function(i){window.sscqUntilSec=UL[i][1];Q("#sscq-t").value="";Q("#sscq-u").value=UL[i][2];sscqPv();};'
  + 'window.sscqFire=function(d){d.action="SetAttribute";H.connection.sendMessage({type:"fire_event",event_type:"' + S.event_name + '",event_data:d});document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",keyCode:27,bubbles:true,cancelable:true}));};'
  + 'window.sscqSet=function(){var d={};d[AS]=parseFloat(Q("#sscq-s").value)||0;d[AP]=parseFloat(Q("#sscq-p").value)||0;'
  +   'var ts=window.sscqUntilSec>0?window.sscqUntilSec:L.timerSec(Q("#sscq-t"),Q("#sscq-u"));if(ts>0)H.callService("timer","start",{entity_id:TMR,duration:Math.round(ts)});'
  +   'var re=Q("#sscq-r");if(re)d[AR]=re.getAttribute("data-on")==="1"?false:true;var ph=Q("#sscq-ph");if(ph)d.drainBatteryPlughole=ph.getAttribute("data-on")==="1";sscqFire(d);};'
  + 'window.sscqClear=function(){var d={};d[AS]=0;d[AP]=0;d[AR]=true;if(ID==="drain")d.drainBatteryPlughole=false;sscqFire(d);};'
  + 'window.sscqPreset=function(pi){var pr=(P.overridePresets||[])[pi];if(!pr)return;var v=pr.values||{},d={};'
  +   'd[AS]=(v[ID]&&parseFloat(v[ID].soc))||0;d[AP]=(v[ID]&&parseFloat(v[ID].price))||0;'
  +   'd[AR]=(v[ID]&&v[ID].allowReset===false)?false:true;'
  +   'var ts=L.presetSec(pr);if(ts>0)H.callService("timer","start",{entity_id:TMR,duration:Math.round(ts)});sscqFire(d);};'
  + 'window.sscqRToggle=function(el){var on=el.getAttribute("data-on")==="1";on=!on;el.setAttribute("data-on",on?"1":"0");el.style.background=on?"var(--smiggles-amber-soft-bg)":"transparent";el.style.borderColor=on?"var(--smiggles-amber-border)":"var(--smiggles-border-neutral)";el.innerHTML=on?L.lockSvg("var(--smiggles-amber)",15)+"<span style=\\"font-size:11px;font-weight:800;color:var(--smiggles-amber)\\">ON</span>":"<span style=\\"font-size:11px;font-weight:800;color:var(--smiggles-text-muted)\\">OFF</span>";};'
  + 'function PHS(on){return "display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:8px;cursor:pointer;margin-bottom:10px;box-sizing:border-box;"+"background:transparent;border:1px solid var(--smiggles-border-neutral)";}'
  + 'function PHI(on){return "<div style=\\"flex:1;min-width:0\\"><div style=\\"font-size:12px;font-weight:900;letter-spacing:0.08em;text-transform:uppercase;color:"+(on?"var(--smiggles-red)":"var(--smiggles-text-bright)")+"\\">Plughole</div><div style=\\"font-size:10.5px;font-weight:600;line-height:1.35;color:var(--smiggles-text-muted)\\">Drain instead of House Party</div></div><div style=\\"width:44px;height:26px;border-radius:13px;flex:none;position:relative;background:"+(on?"var(--smiggles-red)":"var(--smiggles-border-neutral)")+"\\"><div style=\\"position:absolute;top:3px;left:"+(on?21:3)+"px;width:20px;height:20px;border-radius:50%;background:#fff\\"></div></div>";}'
  + 'window.sscqPhToggle=function(el){var on=el.getAttribute("data-on")!=="1";el.setAttribute("data-on",on?"1":"0");el.setAttribute("style",PHS(on));el.innerHTML=PHI(on);};'
  + 'function sscqNum(e){var s=H.states[e];return s?parseFloat(s.state):NaN;}'
  + 'window.sscqCostPv=function(){var el=Q("#sscq-costpv");if(!el)return;'
  +   'var tgt=parseFloat(Q("#sscq-s").value)||0,price=parseFloat(Q("#sscq-p").value)||0;'
  +   'var cap=sscqNum(CAP),cur=sscqNum(SOCE);'
  +   'if(isNaN(cap)||isNaN(cur)){el.innerHTML="\u2014";return;}'
  +   'var gap=tgt-cur;'
  +   'if(tgt<=0){el.innerHTML="set a target SOC to preview cost";return;}'
  +   'if(gap<=0.5){el.innerHTML="target already met at "+cur.toFixed(0)+"%";return;}'
  +   'var kwh=gap*(cap/100);'
  +   'if(price>0){var cost=kwh*price/100;el.innerHTML="<b style=\\"color:' + C + '\\">$"+cost.toFixed(2)+"</b> to reach "+tgt.toFixed(0)+"% <span style=\\"color:var(--smiggles-text-muted)\\">("+kwh.toFixed(1)+" kWh)</span>";}'
  +   'else{el.innerHTML=cur.toFixed(0)+"% \u2192 "+tgt.toFixed(0)+"% <span style=\\"color:var(--smiggles-text-muted)\\">("+kwh.toFixed(1)+" kWh, no price set)</span>";}'
  + '};'
  + 'window.sscqCalc=function(){var ex=Q("#sscq-cx");try{'
  +   'var tgt=parseFloat(Q("#sscq-s").value)||0;'
  +   'var fs=H.states[FCE];var fa=(fs&&fs.attributes)||{};var fc=fa.forecasts||fa.Forecasts||[];'
  +   'if(!fc.length){ex.innerHTML="<span style=\\"color:var(--smiggles-darkred)\\">No forecast on "+FCE+"</span>";return;}'
  +   'var ckw=sscqNum(CKW),cap=sscqNum(CAP),cur=sscqNum(SOCE);'
  +   'if(isNaN(ckw)||isNaN(cap)||isNaN(cur)){ex.innerHTML="<span style=\\"color:var(--smiggles-darkred)\\">Missing sensor (charge/capacity/SOC)</span>";return;}'
  +   'var dlSec=window.sscqUntilSec>0?window.sscqUntilSec:L.timerSec(Q("#sscq-t"),Q("#sscq-u"));'
  +   'var dlMs=(dlSec>0)?(Date.now()+dlSec*1000):0;'
  +   'var dlTxt="";if(dlMs){var de=new Date(dlMs);dlTxt=" by "+L.clk(de);}'
  +   'var r=(tgt>0)?L.cheapestFill({forecasts:fc,price_field:PFIELD,charge_kw:ckw,capacity_kwh:cap,cur_soc:cur,target_soc:tgt,round_step_cents:RSTEP,deadline_ms:dlMs||undefined}):{ok:false,reason:"target_met"};'
  +   'if(!r.ok&&r.reason==="target_met"){'
  +     'var sn=L.cheapestSustained({forecasts:fc,price_field:PFIELD,min_minutes:SMIN,min_intervals:SIVL,round_step_cents:RSTEP,deadline_ms:dlMs||undefined});'
  +     'if(!sn.ok){ex.innerHTML=sn.reason==="no_window"?"<span style=\\"color:var(--smiggles-amber)\\">No forecast intervals before"+dlTxt+"</span>":"<span style=\\"color:var(--smiggles-darkred)\\">No usable forecast</span>";return;}'
  +     'Q("#sscq-p").value=sn.threshold_cents.toFixed(1);'
  +     'var atTxt=(tgt>0)?("No fill needed at "+cur.toFixed(0)+"% \u2014 "):"";'
  +     'var smsg=atTxt+"armed <b style=\\"color:' + C + '\\">"+sn.threshold_cents.toFixed(1)+"\u00a2</b>"+(dlTxt?"<span style=\\"color:var(--smiggles-amber);font-weight:800\\">"+dlTxt+"</span>":"")+" \u2014 "+L.hm(sn.hours_at_or_under*3600)+" at/under";'
  +     'if(!sn.enough)smsg+=" <span style=\\"color:var(--smiggles-amber)\\">(only "+Math.round(sn.minutes_at_or_under)+" min available)</span>";'
  +     'ex.innerHTML=smsg;return;}'
  +   'if(!r.ok){ex.innerHTML=r.reason==="no_window"?"<span style=\\"color:var(--smiggles-amber)\\">No forecast intervals before"+dlTxt+"</span>":"<span style=\\"color:var(--smiggles-darkred)\\">No usable forecast</span>";return;}'
  +   'Q("#sscq-p").value=r.threshold_cents.toFixed(1);'
  +   'var msg="Buy under <b style=\\"color:' + C + '\\">"+r.threshold_cents.toFixed(1)+"\u00a2</b>"+(dlTxt?"<span style=\\"color:var(--smiggles-amber);font-weight:800\\">"+dlTxt+"</span>":"")+" \u2014 ~"+r.kwh_filled.toFixed(1)+" kWh, "+L.hm(r.hours_at_or_under*3600)+" at/under";'
  +   'if(!r.fully_reachable){var reach=cur+(r.kwh_filled/r.kwh_per_pct);msg+=" <span style=\\"color:var(--smiggles-amber)\\">(only reaches ~"+Math.min(100,reach).toFixed(0)+"%)</span>";}'
  +   'ex.innerHTML=msg;'
  + '}catch(ce){ex.innerHTML="<span style=\\"color:var(--smiggles-darkred)\\">Calc error: "+(ce&&ce.message?ce.message:ce)+"</span>";}};'
  + 'window.sscqSaveOpen=function(){var s=parseFloat(Q("#sscq-s").value)||0,p=parseFloat(Q("#sscq-p").value)||0;'
  +   'if(s<=0&&p<=0){Q("#sscq-sv").innerHTML="<span style=\\"color:var(--smiggles-amber);font-size:11px\\">Set a value first</span>";return;}'
  +   'Q("#sscq-body").style.display="none";Q("#sscq-save").style.display="block";var ni=Q("#sscq-nm");if(ni)ni.focus();};'
  + 'window.sscqSaveCancel=function(){Q("#sscq-save").style.display="none";Q("#sscq-body").style.display="block";};'
  + 'window.sscqSaveOk=function(){var ni=Q("#sscq-nm"),nm=ni?ni.value.trim():"";'
  +   'if(!nm){if(ni){ni.style.borderColor="var(--smiggles-darkred)";ni.focus();}return;}'
  +   'var s=parseFloat(Q("#sscq-s").value)||0,p=parseFloat(Q("#sscq-p").value)||0;'
  +   'var re=Q("#sscq-r");var lk=re&&re.getAttribute("data-on")==="1";'
  +   'var vals={};vals[ID]={soc:s,price:p,allowReset:lk?false:true};'
  +   'var th=parseFloat(Q("#sscq-t").value)||0,ta=Q("#sscq-u").value;'
  +   'var np={name:nm,timer:(!ta&&th>0)?Math.round(th*3600):0,values:vals};if(ta)np.timer_at=ta;'
  +   'var pl=(P.overridePresets||[]).concat([np]);'
  +   'H.connection.sendMessage({type:"fire_event",event_type:"' + S.event_name + '",event_data:{action:"SetAttribute",overridePresets:pl}});'
  +   'document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",keyCode:27,bubbles:true,cancelable:true}));};'
  + 'var CHS="height:26px;display:inline-flex;align-items:center;gap:5px;padding:0 9px;border-radius:5px;background:var(--smiggles-surface-card);cursor:pointer;margin:0 5px 5px 0";'
  + 'var CHL="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--smiggles-text-dim);margin-bottom:6px";'
  + 'var FL="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;display:block;margin-bottom:5px";'
  + 'var NUM="width:100%;box-sizing:border-box;height:37px;background:var(--smiggles-surface-card);border-radius:6px;color:var(--smiggles-text-bright);font-weight:800;text-align:center;padding:0 4px;font-family:var(--smiggles-font)";'
  + 'var chips="";'
  + '(P.overridePresets||[]).forEach(function(p,pi){var v=p.values||{};if(Object.keys(v).length!==1||!v[ID])return;'
  +   'var cv=[];if((+v[ID].soc||0)>0)cv.push((+v[ID].soc).toFixed(0)+"%");if((+v[ID].price||0)>0)cv.push((+v[ID].price).toFixed(1)+"\u00a2");'
  +   'chips+="<div onclick=\\"sscqPreset("+pi+")\\" style=\\""+CHS+";border:1px solid ' + D + '\\">"'
  +     '+"<span style=\\"font-size:11px;font-weight:800;color:' + C + '\\">"+p.name+"</span>"'
  +     '+"<span style=\\"font-size:10px;font-weight:700;color:var(--smiggles-text-dim)\\">"+cv.join("\u00b7")+"</span>"'
  +     '+(v[ID].allowReset===false?LKA:"")+L.presetLabel(p)+"</div>";'
  + '});'
  + 'var dchips="";[["15m",0.25],["30m",0.5],["1h",1],["2h",2]].forEach(function(e){dchips+="<span onclick=\\"sscqDur("+e[1]+")\\" style=\\""+CHS+";border:1px solid var(--smiggles-blue-border);font-size:11px;font-weight:800;color:var(--smiggles-blue)\\">"+e[0]+"</span>";});'
  + 'var uchips="";UL.forEach(function(e,i){uchips+="<span onclick=\\"sscqUL("+i+")\\" style=\\""+CHS+";border:1px solid var(--smiggles-border-neutral-soft);font-size:11px;font-weight:800;color:var(--smiggles-text-muted)\\">"+e[0]+"</span>";});'
  + 'root.innerHTML='
  + '"<div style=\\"font-size:14px;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;color:' + C + ';padding-bottom:9px;margin-bottom:9px;border-bottom:1px solid ' + D + '\\">' + cfg.name + '</div>"'
  + '+"<div id=\\"sscq-body\\">"'
  + '+(chips?"<div style=\\"margin-bottom:10px\\">"+chips+"</div>":"")'
  + '+"<div style=\\"display:flex;gap:8px;margin-bottom:10px\\">"'
  + '+"<div style=\\"flex:1\\"><span style=\\""+FL+";color:' + C + '\\">' + cfg.label_soc + '</span><input id=\\"sscq-s\\" type=\\"number\\" min=\\"0\\" max=\\"100\\" step=\\"1\\" placeholder=\\"off\\" oninput=\\"sscqCostPv()\\" style=\\""+NUM+";border:1px solid ' + D + ';font-size:18px\\"></div>"'
  + '+"<div style=\\"flex:1\\"><span style=\\""+FL+";color:' + C + '\\">' + cfg.label_price + '</span><input id=\\"sscq-p\\" type=\\"number\\" min=\\"0\\" max=\\"200\\" step=\\"0.01\\" placeholder=\\"off\\" oninput=\\"sscqCostPv()\\" style=\\""+NUM+";border:1px solid ' + D + ';font-size:18px\\"></div>"'
  + '+"<div style=\\"flex:0.95\\"><span style=\\""+FL+";color:var(--smiggles-amber)\\">No Reset</span><div id=\\"sscq-r\\" data-on=\\"0\\" onclick=\\"sscqRToggle(this)\\" style=\\"height:37px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;gap:5px;border-radius:6px;cursor:pointer;background:transparent;border:1px solid var(--smiggles-border-neutral)\\"><span style=\\"font-size:11px;font-weight:800;color:var(--smiggles-text-muted)\\">OFF</span></div></div>"'
  + '+"</div>"'
  + (cfg.id === "drain"
      ? '+"<div id=\\"sscq-ph\\" data-on=\\"0\\" onclick=\\"sscqPhToggle(this)\\" style=\\""+PHS(false)+"\\">"+PHI(false)+"</div>"'
      : '')
  + (cfg.id === "any"
      ? '+"<div id=\\"sscq-costpv\\" style=\\"font-size:12px;font-weight:600;line-height:1.5;text-align:center;color:var(--smiggles-text-dim);min-height:16px;margin-bottom:10px\\">set a target SOC to preview cost</div>"'
      : '')
  + '+"<div style=\\"border-top:1px solid var(--smiggles-border-neutral-soft);padding-top:10px;margin-bottom:10px\\">"'
  + '+"<div style=\\""+CHL+"\\">Start for</div><div style=\\"margin-bottom:9px\\">"+dchips+"</div>"'
  + '+"<div style=\\""+CHL+"\\">Run until</div><div style=\\"margin-bottom:10px\\">"+uchips+"</div>"'
  + '+"<div style=\\"display:flex;gap:8px;align-items:flex-end\\">"'
  + '+"<div style=\\"flex:1\\"><span style=\\""+FL+";color:var(--smiggles-blue)\\">Timer h</span><input id=\\"sscq-t\\" type=\\"number\\" min=\\"0\\" max=\\"48\\" step=\\"0.25\\" placeholder=\\"\u2014\\" oninput=\\"sscqIn(0)\\" style=\\""+NUM+";border:1px solid var(--smiggles-blue-border);font-size:16px\\"></div>"'
  + '+"<div style=\\"color:var(--smiggles-text-dim);font-size:10px;font-weight:700;padding-bottom:11px\\">or</div>"'
  + '+"<div style=\\"flex:1\\"><span style=\\""+FL+";color:var(--smiggles-blue)\\">Until</span><input id=\\"sscq-u\\" type=\\"time\\" oninput=\\"sscqIn(1)\\" style=\\""+NUM+";border:1px solid var(--smiggles-blue-border);font-size:16px;color-scheme:dark\\"></div>"'
  + '+"</div>"'
  + '+"<div id=\\"sscq-pv\\" style=\\"font-size:11px;font-weight:700;color:var(--smiggles-text-dim);text-align:center;min-height:15px;margin-top:7px\\"></div>"'
  + '+"</div>"'
  + (cfg.id === "any"
      ? '+"<div onclick=\\"sscqCalc()\\" style=\\"width:100%;box-sizing:border-box;height:40px;border-radius:7px;cursor:pointer;background:var(--smiggles-purple-soft-bg);border:1px solid ' + D + ';color:' + C + ';font-size:12px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:8px\\"><svg viewBox=\\"0 0 24 24\\" style=\\"width:15px;height:15px;fill:' + C + '\\"><path d=\\"M13 2 3 14h7l-1 8 10-12h-7z\\"/></svg>Calculate cheapest price</div>"'
        + '+"<div id=\\"sscq-cx\\" style=\\"font-size:11px;font-weight:600;line-height:1.5;color:var(--smiggles-text-dim);text-align:center;min-height:15px;margin-bottom:10px\\"></div>"'
      : '')
  + '+"<div id=\\"sscq-sv\\" style=\\"text-align:center;min-height:0;margin-bottom:2px\\"></div>"'
  + '+"<div style=\\"display:flex;gap:6px\\">"'
  + '+"<div onclick=\\"sscqClear()\\" style=\\"flex:1;text-align:center;padding:8px 4px;border-radius:6px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;background:transparent;color:var(--smiggles-text-muted);border:1px solid var(--smiggles-border-neutral)\\">Clear</div>"'
  + '+"<div onclick=\\"sscqSaveOpen()\\" style=\\"flex:1;text-align:center;padding:8px 4px;border-radius:6px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;background:transparent;color:var(--smiggles-green);border:1px solid var(--smiggles-green-border-light)\\">Save</div>"'
  + '+"<div onclick=\\"sscqSet()\\" style=\\"flex:1;text-align:center;padding:8px 4px;border-radius:6px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;background:' + W + ';color:' + C + ';border:1px solid ' + D + '\\">Set</div>"'
  + '+"</div>"'
  + '+"</div>"'
  + '+"<div id=\\"sscq-save\\" style=\\"display:none\\">"'
  + '+"<div style=\\"font-size:12px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:var(--smiggles-text-bright);margin-bottom:10px\\">Save preset</div>"'
  + '+"<div style=\\"margin-bottom:10px\\"><span style=\\""+FL+";color:var(--smiggles-text-muted)\\">Name</span><input id=\\"sscq-nm\\" type=\\"text\\" placeholder=\\"e.g. Cheapest fill\\" style=\\"width:100%;box-sizing:border-box;background:var(--smiggles-surface-card);border:1px solid var(--smiggles-border-neutral);border-radius:7px;color:var(--smiggles-text-bright);font-size:15px;font-weight:700;padding:10px 12px\\"></div>"'
  + '+"<div style=\\"font-size:10px;color:var(--smiggles-text-dim);font-weight:700;margin-bottom:12px;text-align:center\\">Saves SOC, price, lock and timer for ' + cfg.name + '</div>"'
  + '+"<div style=\\"display:flex;gap:8px\\"><div onclick=\\"sscqSaveCancel()\\" style=\\"flex:1;text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--smiggles-text-muted);border:1px solid var(--smiggles-border-neutral);cursor:pointer\\">Cancel</div>"'
  + '+"<div onclick=\\"sscqSaveOk()\\" style=\\"flex:1.4;text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--smiggles-green);background:var(--smiggles-green-soft-bg);border:1px solid var(--smiggles-green-border-strong);cursor:pointer\\">Save preset</div></div>"'
  + '+"</div>";'
  + 'Q("#sscq-s").value=parseFloat(P[AS])||"";'
  + 'Q("#sscq-p").value=parseFloat(P[AP])||"";'
  + 'var _tmr=H.states[TMR]||{};if(_tmr.state==="active"&&_tmr.attributes&&_tmr.attributes.finishes_at){Q("#sscq-u").value=L.clk(new Date(_tmr.attributes.finishes_at));}'
  + 'sscqPv();'
  + 'sscqCostPv();'
  + 'if(P[AR]===false||P[AR]==="false"){var rq=Q("#sscq-r");if(rq)sscqRToggle(rq);}'
  + 'var _ph=Q("#sscq-ph");if(_ph&&(P.drainBatteryPlughole===true||P.drainBatteryPlughole==="true"))sscqPhToggle(_ph);'
  + '}catch(sscqE){root.innerHTML="<div style=\\"color:var(--smiggles-darkred);font-size:12px;padding:12px;line-height:1.5;font-family:var(--smiggles-font,sans-serif)\\">Quick-edit error:<br><span style=\\"color:var(--smiggles-darkred)\\">"+(sscqE&&sscqE.message?sscqE.message:sscqE)+"</span></div>";}';
  return '<img src=\'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7\' style=\'display:none\' '
       + 'onload=\'(function sscDraw(root){' + inner + '})(this.nextElementSibling)\'>'
       + '<div style=\'background:var(--smiggles-surface-popup);padding:12px;border-radius:10px;font-family:var(--smiggles-font);\'></div>';
};

window.SSCLIB.isVisible = function(ssc, states, entity, ov_id){
  try{
    var cfg = ssc.overrides.filter(function(o){return o.id===ov_id;})[0];
    if(!cfg) return false;
    var a = entity.attributes;
    var on = (parseFloat(a[cfg.attr_soc])||0)>0 || (parseFloat(a[cfg.attr_price])||0)>0 || (cfg.allow_negative && (parseFloat(a[cfg.attr_price])||0)<0);
    var pins = a.pinnedOverrides || [];
    return on || pins.indexOf(ov_id)>=0;
  }catch(e){ return true; }
};

window.SSCLIB.renderDock = function(variables, states, entity){
  try{ window.SSCLIB.CFG = variables.ssc; }catch(e){}
  var ssc = variables.ssc;
  var html = '<div style="display:flex;flex-direction:column;gap:2px;">';
  (ssc.overrides||[]).forEach(function(o){
    if(window.SSCLIB.isVisible(ssc, states, entity, o.id)){
      html += '<div style="cursor:pointer" onclick="window.SSCLIB.openPopup(\''+o.id+'\',\'tap\')">'
            + window.SSCLIB.renderRow(variables, states, entity, o.id)
            + '</div>';
    }
  });
  html += '</div>';
  return html;
};

window.SSCLIB.openPopup = function(ov_id, type){
  try{
    var ha = document.querySelector('home-assistant'); var hass = ha.hass;
    var states = hass.states; var cfg = window.SSCLIB.CFG; var entity = states[cfg.params_entity];
    var variables = {ssc: cfg};
    var content = window.SSCLIB.buildPopup(variables, states, entity, ov_id);
    hass.callService('browser_mod','popup',{content: content, title: ' ', style: '--mdc-dialog-min-width:320px;--mdc-dialog-max-width:340px;'});
  }catch(e){ try{console.error('SSCLIB.openPopup',e);}catch(_){} }
};
