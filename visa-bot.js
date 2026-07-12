// --- visa-bot.js — GUI-driven, no hardcoded secrets ---

import { chromium } from "playwright";
import { exec } from "node:child_process";
import { AIGuard } from "./ai_guard.mjs";

// ===== Read everything from GUI via ENV =====
const ENV = process.env;
const EMAIL = ENV.APP_EMAIL || "";
const PASS  = ENV.APP_PASS  || "";
const guard = new AIGuard({
  AI_ENABLE:      process.env.AI_ENABLE,
  AI_MODE:        process.env.AI_MODE,
  AI_MODEL:       process.env.AI_MODEL,
  OPENAI_API_KEY: process.env.OPENAI_API_KEY,
  MAX_RPS:        process.env.MAX_RPS,
});

const OFFICE_NAME  = ENV.OFFICE_NAME  || "";
const PRICING_NAME = ENV.PRICING_NAME || "";
const VISA_NAME    = ENV.VISA_NAME    || "";
const CITY         = ENV.CITY         || "";
const TRIP_DATE    = ENV.TRIP_DATE    || ""; // DD/MM/YYYY

const HALT_ON_FOUND  = ENV.HALT_ON_FOUND  === "1"; // stop after finding slots
const AUTO_CHECK     = ENV.AUTO_CHECK     === "1"; // click "Check availability"
const AUTO_PROCEED   = ENV.AUTO_PROCEED   === "1"; // click "Proceed with appointment"
const BEEP_ON_FOUND  = ENV.BEEP_ON_FOUND  === "1"; // console beep
const ALERT_ON_FOUND = ENV.ALERT_ON_FOUND === "1"; // extra log

const DAYS_AHEAD = Number(ENV.DAYS_AHEAD || 14);

// NEW: execution timestamp (sec) coming from GUI (مثال 08:59:50)
const START_AT_TS = Number(ENV.START_AT_TS || 0);

// ===== Optional ID overrides from ENV =====
const FORCE_OFFICE_ID        = ENV.FORCE_OFFICE_ID ? Number(ENV.FORCE_OFFICE_ID) : null;
const FORCE_VISA_ID          = ENV.FORCE_VISA_ID   ? Number(ENV.FORCE_VISA_ID)   : null;
const FORCE_SERVICELEVEL_ID  = ENV.FORCE_SERVICELEVEL_ID ? Number(ENV.FORCE_SERVICELEVEL_ID) : null;
const NO_LEVEL               = ENV.NO_LEVEL === "1";     // اجبر الاستعلام من غير serviceLevelId
const TEST_DATE              = ENV.TEST_DATE || "";      // YYYY-MM-DD (اختياري للتجربة)


// ===== NEW: optional extra log (tee to file for CMD window) =====
const EXTRA_LOG = ENV.EXTRA_LOG || "";
let __logStream = null;
(async () => {
  if (EXTRA_LOG) {
    try {
      const fs = await import("node:fs");
      __logStream = fs.createWriteStream(EXTRA_LOG, { flags: "a" });
      const stamp = new Date().toISOString();
      __logStream.write(
        `\n===== RUN @ ${stamp} =====\nEMAIL=${EMAIL}\nOFFICE="${OFFICE_NAME}" PRICING="${PRICING_NAME}" VISA="${VISA_NAME}"\nCITY="${CITY}" TRIP_DATE="${TRIP_DATE}" DAYS_AHEAD=${DAYS_AHEAD}\nSTART_AT_TS=${START_AT_TS}\n=========================================\n`
      );
      const _clog = console.log;
      console.log = (...args) => {
        _clog(...args);
        try {
          const line =
            "[" + new Date().toISOString() + "] " +
            args.map(a => (typeof a === "string" ? a : JSON.stringify(a))).join(" ");
          __logStream?.write(line + "\n");
        } catch {}
      };
      process.on("exit", () => { try { __logStream?.end(); } catch {} });
    } catch {}
  }
})();

// ===== Derived IDs from names coming from GUI =====
const OFFICE_ID       = /alex/i.test(OFFICE_NAME) ? 2 : 1;  // Cairo=1, Alexandria=2
const SERVICELEVEL_ID = /(vip|3810)/i.test(PRICING_NAME) ? 2 : 1;


// Robust visa-name → id (case/spacing insensitive)
const VISA_MAP = new Map([
  ["employment visa (d)", 3],
  ["family reunion visa for children (d)", 20],
  ["family reunion visa for spouses (d)", 18],
  ["family reunion visa for parents, (d)", 19],
  ["study visa (d)", 8],
  ["study visa (c)", 9],
  ["tourism visa (c)", 1],
  ["business visa (c)", 5],
  ["re-entry visa (d)", 4],
]);
function visaIdFromName(name) {
  const key = String(name || "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
  if (/family reunion visa for children \(d\)/i.test(key)) return 20;
  return VISA_MAP.get(key) ?? 3;
}
const VISA_ID = visaIdFromName(VISA_NAME);

// ===== Rate & hunt window (من الواجهة) =====
const RPS          = Math.max(1, Math.min(10, parseInt(ENV.MAX_RPS || "2")));   // طلب/ث لكل إيميل
const MAX_BURST    = Math.max(1, parseInt(ENV.MAX_BURST || "2"));               // سماحية دفعة فوق RPS
const HUNT_SECONDS = Math.max(5, parseInt(ENV.HUNT_SECONDS || "25"));           // نافذة صيد لكل إيميل
const MAX_CHECKS   = Math.max(1, parseInt(ENV.MAX_CHECKS || "60"));             // أقصى عدد محاولات
const BACKOFF_429  = Math.max(200, parseInt(ENV.BACKOFF_429_MS || "2000"));     // backoff عند 429 (ms)
const PRINT_429    = (ENV.PRINT_429 || "0") === "1";                            // طباعة 429 ولا لأ

// Token Bucket بسيط يحقق RPS
let tokens = MAX_BURST;
setInterval(() => {
  tokens = Math.min(tokens + RPS, RPS + MAX_BURST);
}, 1000);
const sleep = (ms)=>new Promise(r=>setTimeout(r,ms));
async function takeToken() {
  while (tokens < 1) await sleep(10);
  tokens -= 1;
}

// ===== APIs =====
const BASE = "https://egyapi.almaviva-visa.it/reservation-manager/api";
const PLAN = `${BASE}/planning/v1`;

// ===== Poll pacing (burst around 9:00) =====
const NORMAL_POLL_MS = 900;
const BURST_POLL_MS  = 300;
let burstUntil = null;
(function setBurstWindow() {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  if ((h === 8 && m >= 58) || (h === 9 && m <= 1)) {
    burstUntil = Date.now() + 90_000;
  }
})();
function currentPollMs() {
  return (burstUntil && Date.now() < burstUntil) ? BURST_POLL_MS : NORMAL_POLL_MS;
}

// ===== Auth capture =====
let authState = { authz: null };
function wireAuthCapture(page) {
  page.on("request", (req) => {
    const url = req.url();
    if (!url.includes("egyapi.almaviva-visa.it")) return;
    const h = req.headers();
    const auth = h["authorization"] || h["Authorization"];
    if (auth && /^bearer\s+/i.test(auth)) {
      authState.authz = auth;
      try { guard.setAuth(auth); } catch {}
    }
  });
}
function apiHeaders() {
  return {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en",
    "Origin": "https://egy.almaviva-visa.it",
    "Referer": "https://egy.almaviva-visa.it/",
    "X-Requested-With": "XMLHttpRequest",
    "X-Tenant": "EGY",
    "Authorization": authState.authz || "",
  };
}

// ===== Helpers =====
async function apiGet(page, url) {
  // cache buster بسيط ضد CDN
  const u = new URL(url);
  u.searchParams.set("_", String(Date.now() % 1e9));
  url = u.toString();

  const base = apiHeaders();

  // الهيدرز المستخدمة لكل الفروع
  const commonHeaders = {
    Accept: "application/json, text/plain, */*",
    Authorization: base.Authorization,
    "X-Tenant": "EGY",
    "X-Requested-With": "XMLHttpRequest",
  };

  // هيدرز لفـرع المتصفح (يفيد بعض السيرفرات في الذروة)
  const browserHeaders = {
    ...commonHeaders,
    Origin: "https://egy.almaviva-visa.it",
    Referer: "https://egy.almaviva-visa.it/",
  };

  const doApiRequest = async () => {
    const r = await page.request.get(url, {
      headers: {
        // مهم: نفس بصمة المتصفح لمنع ردود Forbidden/CSRF
        Accept: "application/json, text/plain, */*",
        Authorization: apiHeaders().Authorization,
        "X-Tenant": "EGY",
        "X-Requested-With": "XMLHttpRequest",
        Origin: "https://egy.almaviva-visa.it",
        Referer: "https://egy.almaviva-visa.it/",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.7",
      },
      timeout: 45_000
    });
    const headersObj = r.headers();
    let body = null;
    try {
      const ct = (headersObj["content-type"] || "").toLowerCase();
      body = ct.includes("json") ? await r.json() : await r.text();
    } catch {}
    return { ok: r.ok(), status: r.status(), body, headers: headersObj };
  };

  const doBrowserFetch = async () => {
    return await page.evaluate(async ({ url, headers }) => {
      try {
        const r = await fetch(url, {
          method: "GET",
          headers,
          cache: "no-store",
          credentials: "include",
          redirect: "follow",
          mode: "cors"
        });
        const ct = (r.headers.get("content-type") || "").toLowerCase();
        const headersObj = {};
        try { r.headers.forEach((v, k) => headersObj[k] = v); } catch {}
        const body = ct.includes("json") ? await r.json() : await r.text();
        return { ok: r.ok, status: r.status, body, headers: headersObj };
      } catch (e) {
        // نعيد كود مميز عشان نفرّق "Failed to fetch"
        return { ok: false, status: -1, body: "BROWSER_FETCH_FAILED:" + (e && e.message || "unknown"), headers: {} };
      }
    }, { url, headers: browserHeaders });
  };

  for (let attempt = 1; attempt <= 8; attempt++) {
    try {
      // 1) ابدأ بالـ APIRequest (أكثر ثباتًا ضد CORS)
      let resp = await doApiRequest();

      // 2) لو Auth/Forbidden (ممكن محتاج كوكي/كابتشا) جرّب فرع المتصفح
      if (resp.status === 401 || resp.status === 403) {
        const br = await doBrowserFetch();
        if (br.status !== -1) resp = br; // قبلناه لو نجح (مش failed-to-fetch)
      }

      // 429: طبّق backoff الذكي بتاعك
      const retryMs = guard.observeResponse({ url, status: resp.status, headers: resp.headers || {} });
      if (resp.status === 429) {
        await sleep(guard.onRateLimit(Math.max(400, BACKOFF_429)));
        continue;
      }
      if (retryMs) await sleep(retryMs);

      // لو فرع المتصفح رجّع Failed to fetch جرّب الـAPIRequest فورًا من غير ما تفشل المحاولة كلها
      if (resp.status === -1 && String(resp.body || "").startsWith("BROWSER_FETCH_FAILED")) {
        // جرّبة ثانية سريعة عبر API
        resp = await doApiRequest();
      }

      return resp;
    } catch (e) {
      const msg = String(e?.message || e);
      const transient = /(ECONNRESET|ETIMEDOUT|EAI_AGAIN|socket|TLS|timeout|ABORTED|net::ERR)/i.test(msg);
      console.log(`[apiGet] attempt ${attempt} failed: ${msg.split("\n")[0]}`);
      if (!transient || attempt === 8) throw e;
      await page.waitForTimeout(250 * attempt + Math.floor(Math.random() * 200));
    }
  }
}


// === Cairo-timezone-safe dates (بدون تغيير استدعاءاتك) ===
function todayISO() {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Africa/Cairo",
    year: "numeric", month: "2-digit", day: "2-digit",
  });
  return fmt.format(new Date()); // YYYY-MM-DD
}
function addDaysISO(d0, add) {
  // d0 بصيغة YYYY-MM-DD
  const [Y,M,D] = String(d0).split("-").map(Number);
  // نثبت على 12:00 UTC لتفادي انزلاق اليوم
  const base = new Date(Date.UTC(Y, (M||1)-1, (D||1), 12));
  base.setUTCDate(base.getUTCDate() + (add||0));
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Africa/Cairo",
    year: "numeric", month: "2-digit", day: "2-digit",
  });
  return fmt.format(base);
}

async function robustGoto(page, url) {
  for (let attempt = 1; attempt <= 8; attempt++) {
    try {
      await page.request.get(url, { timeout: 15_000 }).catch(() => {});
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
      return;
    } catch (e) {
      const msg = String(e?.message || e);
      const transient = /(ERR_CONNECTION_RESET|ECONNRESET|ERR_TIMED_OUT|timeout|EAI_AGAIN|ENOTFOUND|TLS|ERR_ABORTED)/i.test(msg);
      console.log(`[GOTO] attempt ${attempt} failed: ${msg.split("\n")[0]}`);
      if (!transient || attempt === 8) throw e;
      await page.waitForTimeout(800 * attempt + Math.floor(Math.random() * 500));
    }
  }
}
async function setDateRobust(page, dateStr) {
  const [dd, mm, yyyy] = dateStr.split("/").map(n => Number(n));
  const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  const monthName = monthNames[mm - 1];
  const candidates = page.locator([
    'input[placeholder="DD/MM/YYYY"]',
    'input[aria-label="DD/MM/YYYY"]',
    'input[formcontrolname="date"]',
    'input.mat-input-element',
  ].join(", ")).first();
  if (!await candidates.count().catch(()=>0)) return;
  const dateInput = candidates;
  await dateInput.waitFor({ state: "visible", timeout: 3000 }).catch(()=>{});
  try {
    const ro = await dateInput.getAttribute("readonly");
    if (!ro) {
      await dateInput.click({ clickCount: 3 });
      await dateInput.type(dateStr, { delay: 20 });
      await dateInput.evaluate(el => {
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      });
      await dateInput.blur();
      const v = (await dateInput.inputValue().catch(()=>"")) || "";
      if (v.includes(String(yyyy))) return;
    }
  } catch {}
  let opened = false;
  for (const sel of ['mat-datepicker-toggle button','button[aria-label*="calendar"]','button[aria-label*="Calendar"]','button[aria-label*="التقويم"]']) {
    try { await page.locator(sel).first().click({ timeout: 1200 }); opened = true; break; } catch {}
  }
  if (!opened) { try { await dateInput.click({ timeout: 1200 }); opened = true; } catch {} }
  const dpRoot = page.locator("mat-datepicker-content");
  await dpRoot.waitFor({ timeout: 5000 }).catch(()=>{});
  try { await dpRoot.locator(".mat-calendar-period-button").click({ timeout: 1000 }); } catch {}
  try { await dpRoot.locator(".mat-calendar-period-button").click({ timeout: 1000 }); } catch {}
  try { await dpRoot.getByRole("button", { name: new RegExp(`^${yyyy}$`) }).click({ timeout: 2500 }); }
  catch { await dpRoot.locator(`[aria-label="${yyyy}"]`).click({ timeout: 2500 }).catch(()=>{}); }
  const monthRegex = new RegExp(`^(${monthName}|${monthName.slice(0,3)}\\.?)(\\s+${yyyy})?$`, "i");
  try { await dpRoot.getByRole("button", { name: monthRegex }).click({ timeout: 2500 }); }
  catch { await dpRoot.locator(`[aria-label*="${monthName}"]`).first().click({ timeout: 2500 }).catch(()=>{}); }
  const fullAria = `${dd} ${monthName} ${yyyy}`;
  try { await dpRoot.getByRole("button", { name: new RegExp(fullAria) }).click({ timeout: 2500 }); }
  catch {
    await dpRoot.locator(`[aria-label*="${fullAria}"]`).click({ timeout: 2500 }).catch(async () => {
      await dpRoot.getByRole("gridcell", { name: String(dd) }).first().click({ timeout: 2500 }).catch(()=>{});
    });
  }
  await page.waitForTimeout(150);
  await dateInput.blur();
}

function beep(times = 2) {
  try { process.stdout.write("\x07"); } catch {}
  if (process.platform === "win32") {
    const pattern = Array(times)
      .fill('[console]::beep(1000,250); Start-Sleep -Milliseconds 120; [console]::beep(1400,300); Start-Sleep -Milliseconds 180;')
      .join(' ');
    exec(`powershell -NoProfile -Command "${pattern}"`);
  }
}
function alertFound(msg) {
  if (BEEP_ON_FOUND) beep();
  if (ALERT_ON_FOUND) console.log(`[ALERT] ${msg}`);
}

function requireValue(name, val) {
  if (!val) throw new Error(`Missing required value: ${name} (from GUI)`);
}

// NEW: tiny helpers for timestamp wait + button click
async function waitUntilTimestamp(tsSeconds) {
  if (!tsSeconds || Number.isNaN(tsSeconds)) return;
  const target = tsSeconds * 1000;
  console.log(`[TIMER] waiting until ${tsSeconds} (now=${Math.floor(Date.now()/1000)}; Δ=${Math.max(0, target - Date.now())}ms)`);
  while (Date.now() < target - 3) {
    await sleep(60);
  }
  console.log(`[TIMER] fire @ ${new Date().toISOString()}`);
}

// ========= IDs لايف (من API نفس الجلسة) =========
function norm(s) {
  return String(s || "")
    .toLowerCase()
    .normalize("NFKC")
    .replace(/\s+/g, " ")
    .trim();
}
async function resolveIdsLive(page, officeIdFallback, pricingName, visaName) {
  const officeId = officeIdFallback;
  const url = `https://egyapi.almaviva-visa.it/configuration-manager/api/visas/v1/list/web?office=${officeId}`;
  const r = await apiGet(page, url);
  if (!r?.ok) {
    console.log("[IDS] list/web failed → using fallbacks.");
    return {
      officeId,
      serviceLevelId: SERVICELEVEL_ID,
      visaId: VISA_ID,
      meta: { from: "fallback" }
    };
  }
  const body = r.body || {};
  const levels = Array.isArray(body.serviceLevels) ? body.serviceLevels
               : Array.isArray(body.levels)        ? body.levels
               : [];
  const visas  = Array.isArray(body.visas) ? body.visas : [];

  const wantLevel = norm(pricingName);
  const wantVisa  = norm(visaName);

  const levelHit = levels.find(l => norm(l?.name).includes(wantLevel));
  const visaHit  = visas.find(v => {
    const n = norm(v?.name);
    return n === wantVisa || n.includes(wantVisa) || wantVisa.includes(n);
  });

  const resolved = {
    officeId,
    serviceLevelId: levelHit?.id ?? SERVICELEVEL_ID,
    visaId:        visaHit?.id  ?? VISA_ID,
    meta: {
      from: "live",
      levelMatched: levelHit?.name || null,
      visaMatched:  visaHit?.name  || null
    }
  };

  if (!levelHit) console.log(`[IDS] service level not matched exactly → using ${resolved.serviceLevelId} (fallback or partial)`);
  if (!visaHit)  console.log(`[IDS] visa not matched exactly → using ${resolved.visaId} (fallback or partial)`);

  console.log(`[IDS] resolved (live): officeId=${resolved.officeId} serviceLevelId=${resolved.serviceLevelId} visaId=${resolved.visaId}`);
  return resolved;
}


async function fetchConfigList(page, officeId) {
  const url = `https://egyapi.almaviva-visa.it/configuration-manager/api/visas/v1/list/web?office=${officeId}`;
  const r = await apiGet(page, url);
  if (!r?.ok) return { visas: [], levels: [] };
  const body = r.body || {};
  return {
    visas: Array.isArray(body.visas) ? body.visas : [],
    levels: Array.isArray(body.serviceLevels) ? body.serviceLevels
           : Array.isArray(body.levels) ? body.levels : [],
  };
}

// اختيارات أكتر للـvisa/level بالاسم
function pickNearMatches(items, wanted, key = "name", limit = 3) {
  const W = norm(wanted);
  const scored = items
    .map(it => ({ it, n: norm(it?.[key] ?? "") }))
    .map(({ it, n }) => ({
      it,
      score:
        n === W ? 100 :
        n.includes(W) ? 80 :
        W.includes(n) ? 70 :
        60 - Math.abs(n.length - W.length) // تقريب بسيط
    }))
    .sort((a,b)=>b.score - a.score)
    .slice(0, limit)
    .map(x => x.it);
  return scored;
}

// جرّب عدة combinations بسرعة لحد ما تلاقي أي Slots
async function probeCombinations(page, { officeId, visaId, serviceLevelId }, daysAhead = 7) {
  const { visas, levels } = await fetchConfigList(page, officeId);
  const visaCandidates = [
    { id: visaId },
    ...pickNearMatches(visas, VISA_NAME).map(v => ({ id: v.id, name: v.name })),
  ]
  .filter((v,i,self)=> self.findIndex(x=>x.id===v.id)===i)
  .slice(0, 4);

  const levelCandidates = [
    { id: serviceLevelId },
    { id: 1 }, { id: 2 },
  ]
  .filter((l,i,self)=> self.findIndex(x=>x.id===l.id)===i);

  const baseISO = todayISO();

  // ترتيب تجارب سريعة: (with level) ثم (بدون level)
  const tries = [];
  for (const v of visaCandidates) {
    for (const L of levelCandidates) {
      tries.push({ v: v.id, L: L.id, withLevel: true });
    }
    tries.push({ v: v.id, L: null, withLevel: false }); // تجربة بدون serviceLevelId
  }

  for (const t of tries) {
    for (let i = 0; i <= Math.min(daysAhead, DAYS_AHEAD); i++) {
      const dateISO = addDaysISO(baseISO, i);
      const url = t.withLevel
        ? `${BASE}/slots/v1/free?officeId=${officeId}&visaId=${t.v}&serviceLevelId=${t.L}&date=${dateISO}&quantity=1&type=WEB`
        : `${BASE}/slots/v1/free?officeId=${officeId}&visaId=${t.v}&date=${dateISO}&quantity=1&type=WEB`;

      const r = await apiGet(page, url);
      if (r.status === 429) { await sleep(Math.max(400, BACKOFF_429)); i--; continue; }

      const arr = Array.isArray(r.body) ? r.body : [];
      if (r.ok && arr.length) {
        console.log(`[PROBE-FOUND] date=${dateISO} slots=${arr.length} visaId=${t.v} serviceLevelId=${t.L ?? "NONE"}`);
        console.log(`[HIT] url=${url}`);
        // Log first slot structure for debugging
        if (arr.length > 0) {
          console.log(`[PROBE-DEBUG] First slot:`, JSON.stringify(arr[0], null, 2));
        }
        return { dateISO, slots: arr, visaId: t.v, serviceLevelId: t.L };
      }
    }
  }
  console.log("[PROBE] no slots across combinations.");
  return null;
}
function escRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
async function waitMatSelectEnabled(page, index, name) {
  const sel = page.locator("mat-select").nth(index);

  console.log(`[WAIT] ${name}: waiting for mat-select to be enabled`);

  await page.waitForFunction(
    el => el && el.getAttribute("aria-disabled") === "false",
    await sel.elementHandle(),
    { timeout: 45000 }
  );

  await sel.scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);

  console.log(`[OK] ${name}: mat-select enabled`);
  return sel;
}


// افتح mat-select القريب من label نصه (أفضل من #mat-select-value-1)
// لو labels مش ثابتة عندك، سيبي labelRegex = null واستعملي fallbackNth
async function openMatSelect(page, { labelRegex = null, fallbackNth = null }) {
  let trigger = null;

  if (labelRegex) {
    // يدور على mat-form-field فيه label مطابق
    trigger = page.locator("mat-form-field", {
      has: page.locator("label", { hasText: labelRegex })
    }).locator("mat-select").first();

    if (await trigger.count().catch(()=>0) === 0) trigger = null;
  }

  if (!trigger && fallbackNth !== null) {
    trigger = page.locator("mat-select").nth(fallbackNth);
  }

  if (!trigger) throw new Error("openMatSelect: cannot locate mat-select trigger");

  await trigger.scrollIntoViewIfNeeded().catch(()=>{});
  await trigger.waitFor({ state: "visible", timeout: 20000 });
  await trigger.click({ timeout: 20000 });
  return trigger;
}

// اختيار option من overlay بشكل ثابت (بدون ما نعتمد على #mat-select-value-*)
async function pickOption(page, optionText) {
  const opt = page.getByRole("option", {
    name: new RegExp(`^${escRe(optionText)}$`, "i")
  }).first();

  await opt.waitFor({ state: "visible", timeout: 20000 });
  await opt.click({ timeout: 20000 });

  // استنى overlay يقفل
  await page.waitForTimeout(200);
}

// استنى لحد ما الصفحة تخلص re-render بعد اختيار Office (مهم)
async function waitAfterOfficeChange(page) {
  // 1) استنى أي تحميل/طلبات تهدى
  await page.waitForLoadState("networkidle").catch(()=>{});
  // 2) استنى شوية بسيطة لتحديث الـ Angular bindings
  await page.waitForTimeout(400);
}


// ===== Main =====
(async () => {
  // sanity check from GUI
  requireValue("APP_EMAIL", EMAIL);
  requireValue("APP_PASS", PASS);
  requireValue("OFFICE_NAME", OFFICE_NAME);
  requireValue("PRICING_NAME", PRICING_NAME);
  requireValue("VISA_NAME", VISA_NAME);
  requireValue("CITY", CITY);
  requireValue("TRIP_DATE", TRIP_DATE);

  const launchOpts = {
    headless:  false,
    args: [
      "--disable-quic",
      "--ignore-certificate-errors",
      "--disable-features=BlockInsecurePrivateNetworkRequests",
    ],
  };

  // Use installed Chrome/Chromium instead of Playwright's Chromium
  // Set USE_CHROME=1 in environment to use your installed Chrome
  if (ENV.USE_CHROME === "1") {
    // macOS Chrome paths
    const chromePaths = [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "/Applications/Chromium.app/Contents/MacOS/Chromium",
      "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    ];
    
    // Find first available Chrome
    const fs = await import("node:fs");
    for (const path of chromePaths) {
      if (fs.existsSync(path)) {
        launchOpts.executablePath = path;
        console.log("[BOOT] Using installed Chrome at:", path);
        break;
      }
    }
    
    if (!launchOpts.executablePath) {
      console.log("[WARN] USE_CHROME=1 but no Chrome found, falling back to Playwright Chromium");
    }
  }

  // Optional proxy from GUI
  
  if ((ENV.PROXY_SERVER || "").trim()) {
    const bypassList = process.env.PROXY_BYPASS || "";
    launchOpts.proxy = {
      server: ENV.PROXY_SERVER,
      username: ENV.PROXY_USER || undefined,
      password: ENV.PROXY_PASS || undefined,
       bypass:   bypassList || undefined,
    };
    if (bypassList) {
       launchOpts.args.push(`--proxy-bypass-list=${bypassList}`);
  }

     console.log("[BOOT] launching WITH proxy:", ENV.PROXY_SERVER, "bypass=", bypassList);
  } else {
    console.log("[BOOT] launching WITHOUT proxy");
  }

  const browser = await chromium.launch(launchOpts);
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    locale: "en-US",
  });
  await context.setExtraHTTPHeaders({ "Accept-Language": "en-US,en;q=0.9,ar;q=0.7" });

  // Cut heavy/analytics — اسمحي دائمًا بدومين الـAPI
  await context.route("**/*", (route) => {
    const url = route.request().url();

    if (url.includes("egyapi.almaviva-visa.it")) return route.continue(); // مهم

    if (/\.(png|jpe?g|gif|webp|ico)$/i.test(url)) return route.abort();
    if (/\.(woff2?|ttf|otf)$/i.test(url) || /fonts\.(gstatic|googleapis)\.com/i.test(url)) return route.abort();
    if (/google-analytics|gtag|facebook|hotjar|segment|doubleclick/i.test(url)) return route.abort();
    return route.continue();
  });

  const page = await context.newPage();
  page.setDefaultTimeout(45_000);
  page.setDefaultNavigationTimeout(60_000);

  wireAuthCapture(page);
  page.on("requestfailed", (r) => {
    const u = r.url();
    if (/\.(png|jpe?g|gif|webp|ico|woff2?|ttf|otf)$/i.test(u) ||
        /googleapis|gstatic|googletagmanager|doubleclick|facebook|hotjar|segment/i.test(u)) return;
    console.log("[REQFAIL]", u, r.failure()?.errorText);
  });

  // === UI flow ===
  await robustGoto(page, "https://egy.almaviva-visa.it/");

  await page.getByRole("button").filter({ hasText: "person_outline" }).click();
  await page.getByRole("textbox", { name: "Email" }).fill(EMAIL);
  await page.getByRole("textbox", { name: "Password" }).fill(PASS);
  await page.getByRole("button", { name: /Sign ?In|Login/i }).click();
  await page.waitForLoadState("networkidle").catch(()=>{});

  // تأكيد التقاط التوكن لو wireAuthCapture اتأخر
  try {
    const req = await page.waitForRequest(
      r => r.url().includes("egyapi.almaviva-visa.it") &&
           !!(r.headers()["authorization"] || r.headers()["Authorization"]),
      { timeout: 15000 }
    );
    const authz = req.headers()["authorization"] || req.headers()["Authorization"];
    if (authz && /^bearer\s+/i.test(authz)) {
      authState.authz = authz;
      try { guard.setAuth(authz); } catch {}
      console.log("[OK] Authorization caught via waitForRequest");
    }
  } catch {}

  await page.getByRole("link", { name: "Book" }).click();
  // ✅ تأكيد إن فورم الحجز اتفتح فعلاً (لو ده ما ظهرش يبقى المشكلة قبل الـ selects)
  const cityBoxWait = page.getByRole("textbox", { name: /Indicate the first city of/i }).first();
  await cityBoxWait.waitFor({ state: "visible", timeout: 45000 });
  console.log("[OK] Booking form is visible");

// ===== Use recorded selectors (from your script) =====

// Office
await page.locator('#mat-select-value-1').click();
await page.getByRole('option', { name: new RegExp(`^${escRe(OFFICE_NAME)}$`, 'i') }).click();

// Pricing
await page.locator('#mat-select-value-5').click();
await page.getByRole('option', { name: new RegExp(escRe(PRICING_NAME), 'i') }).click();

// Visa
await page.locator('#mat-select-value-3').click();
await page.getByText(new RegExp(escRe(VISA_NAME), 'i')).click();
// Trip Date (from GUI)
await setDateRobust(page, TRIP_DATE);
try {
  const dateInput = page.locator('input[placeholder="DD/MM/YYYY"]').first();
  const v = await dateInput.inputValue().catch(()=> "");
  console.log(`[DBG] date after set = ${v}`);
} catch {}


// (اختياري) Debug: اطبعي القيمة بعد ما يتحط
const dateInputDbg = page.locator('input[placeholder="DD/MM/YYYY"], input[aria-label="DD/MM/YYYY"]').first();
console.log("[DBG] date after set =", await dateInputDbg.inputValue().catch(()=>"(no input)"));



  // City
  const cityBox = page.getByRole("textbox", { name: /Indicate the first city of/i }).first();
  await cityBox.waitFor({ state: "visible", timeout: 20000 });
  await cityBox.fill("");
  await cityBox.type(CITY, { delay: 20 });
  await cityBox.evaluate(el => {
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
});
  await cityBox.blur();


  // T&Cs
  try { await page.locator("#mat-mdc-checkbox-1-input").check(); } catch {}
  try { await page.locator("#mat-mdc-checkbox-2-input").check(); } catch {}

  // wait auth capture (fallback)
  const t0 = Date.now();
  while (!authState.authz && Date.now() - t0 < 15_000) {
    await page.waitForTimeout(200);
  }
  if (authState.authz) console.log("[OK] Authorization captured.", guard.shortHash(authState.authz));
  else console.log("[WARN] No Authorization yet — will try anyway.");
  console.log(`[ENV] HALT_ON_FOUND=${HALT_ON_FOUND}  AUTO_CHECK=${AUTO_CHECK}  AUTO_PROCEED=${AUTO_PROCEED}`);

  // NEW: انتظري لحدّ START_AT_TS (لو مبعوت) — بدون أي ضغط Check
  if (START_AT_TS > 0) {
    console.log(`[ENV] AUTO_CHECK=${AUTO_CHECK} AUTO_PROCEED=${AUTO_PROCEED} START_AT_TS=${START_AT_TS}`);
    console.log(`[ENV] now=${Math.floor(Date.now()/1000)} (sec)  diff=${START_AT_TS - Math.floor(Date.now()/1000)}s`);
    await waitUntilTimestamp(START_AT_TS);
    console.log("[SKIP] مؤجل: لن نضغط Check عند START_AT_TS — هنضغطه فقط بعد ما نلاقي مواعيد.");
  }

  // === IDs لايف من الـAPI لنفس المكتب المختار ===
  const { officeId: OFFICE_ID_RES,
          serviceLevelId: SERVICELEVEL_ID_RES,
          visaId: VISA_ID_RES } = await resolveIdsLive(page, OFFICE_ID, PRICING_NAME, VISA_NAME);

  console.log(`[IDS] using officeId=${OFFICE_ID_RES}, serviceLevelId=${SERVICELEVEL_ID_RES}, visaId=${VISA_ID_RES}`);

  // IDs النهائية بعد الـresolve + أي Overrides من ENV
  let OFFICE_ID_USE        = FORCE_OFFICE_ID       ?? OFFICE_ID_RES;
  let SERVICELEVEL_ID_USE  = FORCE_SERVICELEVEL_ID ?? SERVICELEVEL_ID_RES;
  let VISA_ID_USE          = FORCE_VISA_ID         ?? VISA_ID_RES;

  if (NO_LEVEL) {
    console.log("[CFG] NO_LEVEL=1 → سنستعلم بدون serviceLevelId في المسح الأساسي.");
  }
  console.log(`[IDS] FINAL officeId=${OFFICE_ID_USE}, visaId=${VISA_ID_USE}, serviceLevelId=${NO_LEVEL ? "NONE" : SERVICELEVEL_ID_USE}`);

  console.log(`[WATCH] officeId=${OFFICE_ID_USE}, serviceLevelId=${SERVICELEVEL_ID_USE}, visaId=${VISA_ID_USE}, daysAhead=${DAYS_AHEAD}, pollMs=${currentPollMs()} (normal=${NORMAL_POLL_MS}, burst=${BURST_POLL_MS})`);

  // 1) planning/checks — نافذة زمنية + RPS + backoff 429 (+ type=WEB)
  const checksUrl = NO_LEVEL
    ? `${PLAN}/checks?officeId=${OFFICE_ID_USE}&visaId=${VISA_ID_USE}&type=WEB`
    : `${PLAN}/checks?officeId=${OFFICE_ID_USE}&visaId=${VISA_ID_USE}&serviceLevelId=${SERVICELEVEL_ID_USE}&type=WEB`;
  console.log(`[DBG] checksUrl=${checksUrl}`);

  let checksCount = 0;
  const checksStart = Date.now();
  let last429ChecksLog = 0;

  while ((Date.now() - checksStart) < HUNT_SECONDS * 1000 && checksCount < MAX_CHECKS) {
    await takeToken();            // احترم RPS
    checksCount++;

    const ck = await apiGet(page, checksUrl);

    if (ck.status === 429) {
      const now = Date.now();
      if (PRINT_429) {
        console.log(`[API] checks ${checksCount} -> 429 (backoff)`);
      } else if (now - last429ChecksLog > 2000) {
        last429ChecksLog = now;
        console.log(`[API] checks -> 429…`);
      }
      await sleep(guard.onRateLimit(BACKOFF_429));
      continue;
    }

    const isOpen = ck.ok && (String(ck.body).toLowerCase() === "true" || ck.body === true);
    if (isOpen) {
      console.log(`[API] checks #${checksCount} -> 200 body=true — OPEN`);
      break; // نكمل للسكان
    } else {
      if (checksCount % 5 === 0) {
        console.log(`[API] checks #${checksCount} -> ${ck.status} — closed`);
      }
    }

    await sleep(guard.nextDelay(currentPollMs()) + Math.floor(Math.random()*100));
  }

  // 2) slots free scan — نافذة زمنية + RPS + backoff 429 + عرض أوقات مختصرة
  let found = null;
  const scanStart = Date.now();
  let scanChecks = 0;
  let last429SlotsLog = 0;

  while (!found && (Date.now() - scanStart) < HUNT_SECONDS * 1000 && (checksCount + scanChecks) < MAX_CHECKS) {
    for (let i = 0; i <= DAYS_AHEAD; i++) {
      await takeToken();  // RPS
      scanChecks++;

      const dateISO  = TEST_DATE || addDaysISO(todayISO(), i);
      const slotsUrl = NO_LEVEL
        ? `${BASE}/slots/v1/free?officeId=${OFFICE_ID_USE}&visaId=${VISA_ID_USE}&date=${dateISO}&quantity=1&type=WEB`
        : `${BASE}/slots/v1/free?officeId=${OFFICE_ID_USE}&visaId=${VISA_ID_USE}&serviceLevelId=${SERVICELEVEL_ID_USE}&date=${dateISO}&quantity=1&type=WEB`;

      if (scanChecks === 1) console.log(`[DBG] first slotsUrl=${slotsUrl}`);

      const r = await apiGet(page, slotsUrl);

      if (scanChecks === 1) console.log(`[DBG] first slots resp -> status=${r.status}`);

      if (r.status === 429) {
        const now = Date.now();
        if (PRINT_429) {
          console.log(`[API] free ${dateISO} -> 429 (backoff)`);
        } else if (now - last429SlotsLog > 2000) {
          last429SlotsLog = now;
          console.log(`[API] free -> 429…`);
        }
        await sleep(guard.onRateLimit(BACKOFF_429));
        continue;
      }

      const arr = Array.isArray(r.body) ? r.body : [];
      if (r.ok && arr.length) {
        // === DEBUG: Log first slot structure to understand the API response ===
        if (arr.length > 0) {
          console.log(`[DEBUG] First slot structure:`, JSON.stringify(arr[0], null, 2));
          console.log(`[DEBUG] All slot keys:`, Object.keys(arr[0] || {}));
        }

        // === عرض عدد الـslots + عيّنة أوقات مفهومة ===
        const fmtHM = (v) => {
          try {
            if (!v) return null;
            // Handle string with time pattern (HH:MM or HH:MM:SS)
            if (typeof v === "string") {
              // Try to extract time from ISO string or time-only string
              const timeMatch = v.match(/(\d{2}:\d{2}(?::\d{2})?)/);
              if (timeMatch) return timeMatch[1].slice(0, 5); // Return HH:MM only
            }
            // Handle Date object or timestamp
            const d = new Date(v);
            if (!isNaN(+d)) {
              // Format in Cairo timezone
              return d.toLocaleTimeString("en-GB", { 
                timeZone: "Africa/Cairo", 
                hour: "2-digit", 
                minute: "2-digit",
                hour12: false 
              });
            }
          } catch (e) {
            console.log(`[WARN] Failed to parse time from:`, v, e.message);
          }
          return null;
        };

        // Try all possible field names that Almaviva might use
        const getTimeFromSlot = (s) => {
          if (!s || typeof s !== "object") return null;
          
          // Log all fields for debugging (only first slot)
          if (arr.indexOf(s) === 0) {
            console.log(`[DEBUG] Trying to extract time from fields:`, Object.keys(s));
          }
          
          // Try common field names in order of likelihood
          const candidates = [
            s.startTime,      // Most common
            s.start,
            s.slotStartTime,
            s.time,
            s.dateTime,
            s.slotTime,
            s.from,
            s.startDate,
            s.appointmentTime,
            s.slot?.startTime,
            s.slot?.start,
          ];
          
          for (const candidate of candidates) {
            const formatted = fmtHM(candidate);
            if (formatted) return formatted;
          }
          
          // If nothing worked, log the entire slot object
          if (arr.indexOf(s) === 0) {
            console.log(`[WARN] Could not extract time from slot:`, JSON.stringify(s, null, 2));
          }
          
          return null;
        };

        const times = arr.map(getTimeFromSlot).filter(Boolean);
        const preview = times.slice(0, 12).join(", ");
        const more = times.length > 12 ? `, +${times.length - 12} more` : "";

        console.log(`[FOUND] slots on ${dateISO} (#${arr.length})`);
        console.log(`[HIT] url=${slotsUrl}`);
        if (preview) {
          console.log(`[SLOTS] ${dateISO}: total=${arr.length} → ${preview}${more}`);
        } else {
          console.log(`[WARN] Found ${arr.length} slots but could not extract times!`);
          console.log(`[WARN] Sample slot:`, JSON.stringify(arr[0], null, 2));
        }

        found = { dateISO, slots: arr };
        break;
      } else {
        if ((scanChecks % 5 === 0) && i === 0) {
          console.log(`[NONE] no slots yet (checks=${checksCount + scanChecks})`);
        }
      }

      if ((Date.now() - scanStart) >= HUNT_SECONDS * 1000 || (checksCount + scanChecks) >= MAX_CHECKS) break;
    }

    if (!found) {
      await sleep(guard.nextDelay(currentPollMs()) + Math.floor(Math.random()*100));
    }
  }

  // لو مفيش ضمن النافذة — جرّب probe combinations قبل الإنهاء
  if (!found) {
    const probe = await probeCombinations(page, {
      officeId: OFFICE_ID_USE,
      visaId:   VISA_ID_USE,
      serviceLevelId: SERVICELEVEL_ID_USE
    }, /*daysAhead*/ Math.min(10, DAYS_AHEAD));

    if (probe) {
      // لقّطنا مواعيد من خلال probe — كمّل بنفس منطقك
      found = { dateISO: probe.dateISO, slots: probe.slots };
      console.log(`[IDS] switching to visaId=${probe.visaId} serviceLevelId=${probe.serviceLevelId ?? "NONE"}`);
    } else {
      console.log(`[NONE] finished (checks=${checksCount + scanChecks}, window=${HUNT_SECONDS}s, probe=no hits)`);
      try { await context.close(); await browser.close(); } catch {}
      process.exit(0);
    }
  }

  // 3) On found: beep/log; optionally Check; optionally Proceed
  if (found) {
    alertFound(`slots on ${found.dateISO} (#${found.slots.length})`);
    console.log(`[FOUND] slots on ${found.dateISO} (#${found.slots.length})`);

    // اضغطي Check لو مفعّل — هنضغطه دائمًا بعد ما نلاقي Slots
    try {
      const checkBtn = page.getByRole("button", { name: /^Check availability$/i });
      await checkBtn.waitFor({ state: "visible", timeout: 15_000 }).catch(()=>{});
      for (let i = 0; i < 3; i++) {
        try {
          await Promise.all([
            page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {}),
            checkBtn.click(),
          ]);
          break;
        } catch { await page.waitForTimeout(150); }
      }
      console.log("[PRESS] Check availability clicked.");
    } catch (e) {
      console.log("[WARN] Could not click Check availability:", String(e).split("\n")[0]);
    }

    // أولوية Proceed: لو مفعّل هنضغط حتى لو HALT_ON_FOUND=1
    if (AUTO_PROCEED) {
      let proceedClicked = false;
      try {
        const proceedBtn = page.getByRole("button", { name: /^Proceed with appointment$/i });
        await proceedBtn.waitFor({ state: "visible", timeout: 10_000 });
        for (let i = 0; i < 3; i++) {
          try { await proceedBtn.click(); proceedClicked = true; break; }
          catch { await page.waitForTimeout(150); }
        }
      } catch {}
      if (!proceedClicked) {
        const proceedDiv = page.locator("div").filter({ hasText: /^Proceed with appointment$/ });
        await proceedDiv.first().waitFor({ state: "visible", timeout: 10_000 }).catch(()=>{});
        for (let i = 0; i < 3; i++) {
          try { await proceedDiv.first().click(); proceedClicked = true; break; }
          catch { await page.waitForTimeout(150); }
        }
      }
      console.log("[PRESS] Proceed clicked.");
    } else if (HALT_ON_FOUND) {
      console.log("[HALT] HALT_ON_FOUND=1 — مش هندوس Proceed. كمّلي يدوي من المتصفح.");
      return; // سيب المتصفح مفتوح
    } else {
      console.log("[INFO] AUTO_PROCEED=0 و HALT_ON_FOUND=0 — لن نضغط Proceed تلقائيًا.");
    }
  }

  try { await context.close(); await browser.close(); } catch {}
  process.exit(900); // ← لقِطنا مواعيد

})().catch(err => {
  console.log("[ERR]", String(err && err.message || err));
  process.exit(1);
});
