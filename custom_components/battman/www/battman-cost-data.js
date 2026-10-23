// Battman cost data: what the Cost chart and Cost compare cards share.
//
// Each day's buy, sell and network fee come from the cost totals' long-term statistics (the daily
// `change` of each cumulative $ total), so they survive the recorder's purge. A "bank it" (all
// three totals set back to zero) shows as a negative day; that day is rebuilt from hourly
// statistics without the reset hour. Bill cycles start on the parameters' billDayOfMonth.

export const num = (v) => { const n = Number(v); return isFinite(n) ? n : 0; };
export const money = (v) => (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(2);
export function midnight(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
const pad2 = (n) => String(n).padStart(2, "0");
export const toDateStr = (d) => d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
export function fromDateStr(s) { const p = s.split("-").map(Number); return new Date(p[0], p[1] - 1, p[2]); }

// hass: the card's hass (read when needed); e: { buy, sell, fee, param } entity IDs
export function costData(getHass, e) {
  // bill cycle: the day-of-month from the parameters sensor (19 if it has none)
  function billDay() {
    const P = getHass().states[e.param];
    const d = P && Number(P.attributes.billDayOfMonth);
    return (isFinite(d) && d >= 1 && d <= 31) ? d : 19;
  }
  // start date of the cycle `back` cycles before the one containing `ref` (back=0 -> current)
  function cycleStart(ref, back) {
    const bd = billDay();
    const y = ref.getFullYear();
    let m = ref.getMonth();
    if (ref.getDate() < bd) m -= 1;   // before this month's bill day -> cycle began last month
    m -= back;
    const d = new Date(y, m, 1);      // JS normalises month over/underflow
    const dim = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
    d.setDate(Math.min(bd, dim));     // clamp (e.g. bill day 31 in a short month)
    return midnight(d);
  }
  const flatFee = () => num(getHass().states[e.param] && getHass().states[e.param].attributes.dailyNetworkCharge);

  async function fetchStats(startDate, endDate, period) {
    try {
      return await getHass().connection.sendMessagePromise({
        type: "recorder/statistics_during_period",
        start_time: startDate.toISOString(),
        end_time: endDate.toISOString(),
        statistic_ids: [e.buy, e.sell, e.fee],
        period: period || "day",
        types: ["change", "state"],
      });
    } catch (x) { return null; }
  }
  function changeByDay(rows) {
    const m = {};
    (rows || []).forEach((r) => { m[toDateStr(midnight(new Date(r.start)))] = Number(r.change) || 0; });
    return m;
  }
  // per-day network fee from the odometer's daily `change`. `present` marks which days the sensor
  // recorded: days before it existed have no row, and the caller uses the flat current fee for
  // those. The odometer's first row reports change 0 (no prior point), so that birth day counts
  // as no data too.
  function feeByDay(rows) {
    const feeM = {}, present = {}; let first = true;
    (rows || []).forEach((r) => {
      const k = toDateStr(midnight(new Date(r.start)));
      const c = Number(r.change) || 0;
      if (first) { first = false; if (c === 0) return; }
      feeM[k] = c; present[k] = true;
    });
    return { feeM, present };
  }
  // Days a cumulative $ total ran down (negative daily change). These totals only climb in normal
  // trading, so a negative day is a reset, found by sign alone (also on the first day in view).
  function negDays(rows) {
    const out = {};
    (rows || []).forEach((r) => { if ((Number(r.change) || 0) < -0.01) out[toDateStr(midnight(new Date(r.start)))] = true; });
    return out;
  }
  // A "bank it" zeroes buy, sell AND fee together. The fee total only accrues, so any negative fee
  // day is a bank. Before the fee sensor existed: buy AND sell both negative the same day (both,
  // so a one-off credit on just one isn't taken for a bank).
  function bankDays(res) {
    const out = Object.assign({}, negDays(res[e.fee]));
    const buy = negDays(res[e.buy]), sell = negDays(res[e.sell]);
    for (const k in buy) if (sell[k]) out[k] = true;
    return out;
  }
  // a reset day's true values from hourly change, without the reset hour: the largest change
  // either way (a drop when the total was positive, a jump up when buy had run negative)
  async function reconstructDay(dayStart) {
    const s = midnight(dayStart), en = new Date(midnight(dayStart)); en.setDate(en.getDate() + 1);
    const res = await fetchStats(s, en, "hour");
    const rec = (ent) => {
      const hrs = ((res && res[ent]) || []).map((r) => Number(r.change) || 0);
      if (!hrs.length) return 0;
      let reset = 0;
      for (const h of hrs) if (Math.abs(h) > Math.abs(reset)) reset = h;
      return Number((hrs.reduce((a, b) => a + b, 0) - reset).toFixed(4));
    };
    return { buy: rec(e.buy), sell: rec(e.sell), fee: rec(e.fee) };
  }

  // per-day maps for [start, end] (whole days), bank days rebuilt. null if statistics can't be read.
  async function days(start, end) {
    const qEnd = new Date(midnight(end)); qEnd.setDate(qEnd.getDate() + 1);   // exclusive: include the last day
    const res = await fetchStats(midnight(start), qEnd);
    if (!res) return null;
    const buyM = changeByDay(res[e.buy]), sellM = changeByDay(res[e.sell]);
    const { feeM, present } = feeByDay(res[e.fee]);
    const resets = bankDays(res);
    for (const k in resets) {
      const rec = await reconstructDay(fromDateStr(k));
      buyM[k] = rec.buy; sellM[k] = rec.sell;
      if (present[k]) feeM[k] = rec.fee;
    }
    return { buyM, sellM, feeM, present };
  }
  // one day's values from those maps: today's fee is the flat fee (statistics lag ~1 h) and its
  // buy / sell are the totals' live `day`; older days use the odometer where it recorded, else
  // the flat current fee (days before the sensor existed)
  function day(maps, d) {
    const h = getHass(), k = toDateStr(d), today = k === toDateStr(midnight(new Date()));
    let buy = maps.buyM[k] || 0, sell = maps.sellM[k] || 0;
    const fee = today ? flatFee() : (maps.present[k] ? (maps.feeM[k] || 0) : flatFee());
    if (today) {
      const bd = Number(h.states[e.buy] && h.states[e.buy].attributes.day);
      const sd = Number(h.states[e.sell] && h.states[e.sell].attributes.day);
      if (isFinite(bd)) buy = bd;
      if (isFinite(sd)) sell = sd;
    }
    return { buy, sell, fee };
  }

  return { billDay, cycleStart, days, day };
}
