// Copyright (c) 2026 Peterson Katagiri Zilli
// SPDX-License-Identifier: Apache-2.0
// Exercise request-token forwarding, Markdown escaping, and timestamp display.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const calls = [];
process.env.TZ = "America/Sao_Paulo";
const context = vm.createContext({
  Intl, Date, navigator: { language: "pt-BR" },
  fetch: async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => url === "/api/session" ? { token: "test-session" } : { ok: true } };
  },
});
const source = fs.readFileSync(path.join(__dirname, "../static/app.js"), "utf8");
vm.runInContext(source.split('document.querySelector("#refresh-button")')[0], context);
(async () => {
  await vm.runInContext('request("/api/runs", {method: "POST", body: "{}"})', context);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "/api/session");
  assert.equal(calls[1].options.headers["X-Workshop-Token"], "test-session");
  assert.equal(calls[1].options.credentials, "same-origin");
  const html = vm.runInContext('renderMarkdown("<script>alert(1)</script>\\n\\n[x](javascript:alert)\\n\\n| A | B |\\n| --- | --- |\\n| 1 | 2 |")', context);
  assert(!html.includes("<script>"));
  assert(!html.includes('href="javascript:'));
  assert(html.includes("<table"));
  const formatted = vm.runInContext('formatTimestamp("2026-10-17T17:00:00+00:00")', context);
  assert(formatted.includes("14:00:00"), formatted);
  assert.equal(vm.runInContext('formatTimestampsInText("2026-10-17 17:00:00")', context), "2026-10-17 17:00:00");
  assert(vm.runInContext('formatTimestampsInText("2026-10-17 17:00:00", "UTC")', context).includes("14:00:00"));
  console.log("Browser helper checks passed.");
})().catch((error) => { console.error(error); process.exitCode = 1; });
