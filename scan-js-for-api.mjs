// scan-js-for-api.mjs — نسخة تعمل على Node 18+ بدون node-fetch
import { JSDOM } from "jsdom";

const ROOT = process.argv[2];
if (!ROOT) {
  console.error("Usage: node scan-js-for-api.mjs <ROOT_URL>");
  process.exit(1);
}

const res = await fetch(ROOT);
const html = await res.text();
const dom = new JSDOM(html);
const scripts = [...dom.window.document.querySelectorAll("script[src]")]
  .map(s => new URL(s.src, ROOT).href);

const found = new Set();
const patterns = [
  /https?:\/\/[a-z0-9.-]+\/(?:api|v\d+|graphql)[^"' )]*/gi, // روابط مطلقة
  /["'`](\/(?:api|v\d+|graphql|status)[^"'`]*)["'`]/gi,      // مسارات نسبية
  /baseURL\s*:\s*["'`](.*?)["'`]/gi,                         // axios baseURL
  /window\.__APP_CONFIG__\s*=\s*(\{[\s\S]*?\});/g            // config عالمي
];

for (const src of scripts) {
  try {
    const jsRes = await fetch(src);
    const js = await jsRes.text();
    for (const re of patterns) {
      let m;
      while ((m = re.exec(js)) !== null) {
        found.add(m[1] || m[0]);
      }
    }
  } catch (e) {
    // تجاهل أي سكربتات تفشل
  }
}

console.log([...found].join("\n"));
