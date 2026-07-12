// ai_guard.mjs — طبقة ذكاء خفيفة + دعم LLM اختياري (نسخة مُصحَّحة)
import crypto from "node:crypto";

export class AIGuard {
  constructor(cfg = {}) {
    this.enabled       = (cfg.AI_ENABLE || "1") === "1";
    this.mode          = (cfg.AI_MODE || "simple").toLowerCase(); // "simple" | "llm"
    this.model         = cfg.AI_MODEL || "gpt-4o-mini";
    this.apiKey        = cfg.OPENAI_API_KEY || "";
    this.maxRps        = Math.max(1, Number(cfg.MAX_RPS || 2));
    this.extraHeaders  = { "X-Tenant": "EGY", Accept: "application/json, text/plain, */*" };

    // مراقبة الـrate/latency
    this.window = [];
    this.winMs  = 15_000;
    this.penalty = 0;
    this.lastAdviseTs = 0;

    // auth
    this.authz = null;

    // LLM (تحميل كسول عند الحاجة)
    this.openai = null;
    this._llmInitPromise = null;
  }

  setAuth(authz) { if (authz) this.authz = authz; }

  async _ensureLLM() {
    if (this.mode !== "llm" || !this.apiKey || this.openai) return;
    if (!this._llmInitPromise) {
      this._llmInitPromise = (async () => {
        try {
          const mod = await import("openai");
          this.openai = new mod.default({ apiKey: this.apiKey });
        } catch {
          this.mode = "simple";
        }
      })();
    }
    await this._llmInitPromise;
  }

  // مراجعة/تصحيح قبل الإرسال
  async prepareRequest(req) {
    if (!this.enabled) return req;

    const headers = { ...(req.headers || {}) };
    for (const [k, v] of Object.entries(this.extraHeaders)) if (!headers[k]) headers[k] = v;
    if (this.authz && !headers.Authorization) headers.Authorization = this.authz;

    let url = String(req.url || "");
    url = url.replace(/([?&])quantity=\d+/i, "$1quantity=1");
    if (!/[?&]type=WEB/i.test(url)) url += (url.includes("?") ? "&" : "?") + "type=WEB";

    if (this.mode === "llm") {
      await this._ensureLLM();
      if (this.openai) {
        try {
          const payload = { url, headers };
          const prompt = `You are a strict HTTP request checker. Given this JSON
{url, headers}, suggest only minimal fixes for headers or query params for a GET
request to an appointments API. Ensure Authorization (if present) is "Bearer ...",
X-Tenant=EGY, Accept proper, and avoid adding anything risky. Return *only* JSON.`;
          const res = await this.openai.chat.completions.create({
            model: this.model,
            messages: [
              { role: "system", content: "You return strict JSON with fields {url, headers}." },
              { role: "user", content: prompt + "\n\n" + JSON.stringify(payload) }
            ],
            temperature: 0
          });
          const txt = res.choices?.[0]?.message?.content?.trim();
          if (txt && txt.startsWith("{")) {
            const j = JSON.parse(txt);
            if (j.url) url = j.url;
            if (j.headers && typeof j.headers === "object") Object.assign(headers, j.headers);
          }
        } catch { /* نتجاهل أي فشل */ }
      }
    }

    return { ...req, url, headers };
  }

  // تعلّم من الردود (429/5xx/Retry-After)
  observeResponse({ url, status, headers }) {
    const now = Date.now();
    this.window.push({ t: now, status });
    while (this.window.length && now - this.window[0].t > this.winMs) this.window.shift();

    if (status === 429) this.penalty += 2;
    else if (status >= 500) this.penalty += 1;
    else if (status >= 200 && status < 300) this.penalty = Math.max(0, this.penalty - 1);

    const ra = (headers?.["retry-after"] || headers?.["Retry-After"]);
    let retryMs = 0;
    if (ra) {
      const v = String(ra).trim();
      if (/^\d+$/.test(v)) retryMs = parseInt(v, 10) * 1000;
    }
    return retryMs;
  }

  // تأخير ذكي إضافي
  nextDelay(baseMs) {
    const factor = 1 + Math.min(2, this.penalty * 0.25); // 1..3
    return Math.round(baseMs * factor);
  }

  // backoff عند 429
  onRateLimit(backoffMs = 2000) {
    this.penalty += 1;
    const jitter = Math.floor(Math.random() * 250);
    return backoffMs + jitter;
  }

  shortHash(s) { return crypto.createHash("md5").update(String(s)).digest("hex").slice(0, 6); }
}
