#!/usr/bin/env node
/**
 * share_fetch.mjs — fetch a PUBLIC chat share link via a real (headed) browser,
 * bypassing CloudFront bot-verification with puppeteer-extra + stealth, and save
 * the conversation JSON the page's SPA fetches from its share API.
 *
 * Proven on DeepSeek public share links (chat.deepseek.com/share/<id>), whose
 * SPA calls api/v0/share/content?share_id=… — a plain curl/WebFetch gets 403
 * ("Human Verification"); a headed stealth browser gets 200.
 *
 *   node tools/share_fetch.mjs <url> <out.json>
 *
 * Requires: a Chrome at $CHROME (default google-chrome-beta) and the
 * puppeteer-extra modules under $PUPPETEER_NM (default ~/perplexport/node_modules).
 * Needs a display (headed). After it saves, ingest with:
 *   chatdrill ingest <out.json>
 */
import { createRequire } from "module";
import { writeFileSync } from "fs";

const [url, out] = process.argv.slice(2);
if (!url || !out) {
  console.error("usage: node tools/share_fetch.mjs <url> <out.json>");
  process.exit(2);
}
const NM = process.env.PUPPETEER_NM || `${process.env.HOME}/perplexport/node_modules`;
const CHROME = process.env.CHROME || "/usr/bin/google-chrome-beta";
const require = createRequire(NM + "/");
const puppeteer = require("puppeteer-extra");
puppeteer.use(require("puppeteer-extra-plugin-stealth")());

const browser = await puppeteer.launch({
  headless: false,                              // headed passes the bot challenge
  executablePath: CHROME,
  userDataDir: process.env.PUPPETEER_PROFILE || `${process.env.HOME}/pupchrome`,
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--no-first-run"],
});
const page = (await browser.pages())[0] || await browser.newPage();
const hits = [];
page.on("response", async (r) => {
  const ct = r.headers()["content-type"] || "";
  if (ct.includes("json") &&
      /share|history|message|conversation|mapping|biz_data/i.test(r.url())) {
    try { const t = await r.text(); if (t.length > 200) hits.push({ url: r.url(), t }); }
    catch { /* body gone */ }
  }
});
const resp = await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
await new Promise((r) => setTimeout(r, 4000));
console.error(`status ${resp?.status()} · title ${await page.title()} · json hits ${hits.length}`);
await browser.close();

if (!hits.length) { console.error("no conversation JSON captured"); process.exit(1); }
const big = hits.sort((a, b) => b.t.length - a.t.length)[0];
writeFileSync(out, big.t);
console.error(`saved ${big.t.length} bytes from ${big.url} → ${out}`);
