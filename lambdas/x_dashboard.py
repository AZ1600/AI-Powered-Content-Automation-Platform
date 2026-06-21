"""Serves a guided dashboard for One Piece X planning and queue management."""

from __future__ import annotations

from common import html_response


def _dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>One Piece X Control Panel</title>
  <style>
    :root {
      --bg: #0a0c13;
      --panel: rgba(17, 22, 35, 0.92);
      --panel-2: #171d2d;
      --line: #2f3850;
      --text: #f5f7fb;
      --muted: #a8b4d1;
      --accent: #48d1c4;
      --gold: #ffc857;
      --red: #ff6b6b;
      --blue: #7cc7ff;
      --shadow: 0 22px 60px rgba(0, 0, 0, 0.28);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(72,209,196,0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(255,200,87,0.12), transparent 24%),
        linear-gradient(180deg, #161b2c 0, #0a0c13 220px);
    }
    .wrap {
      max-width: 1260px;
      margin: 0 auto;
      padding: 26px 18px 80px;
    }
    .hero {
      padding: 34px 30px 30px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(22,27,44,0.98), rgba(11,17,28,0.94));
      box-shadow: var(--shadow);
      margin-bottom: 22px;
      overflow: hidden;
      position: relative;
    }
    .hero:before {
      content: "";
      position: absolute;
      inset: auto -60px -60px auto;
      width: 220px;
      height: 220px;
      background: radial-gradient(circle, rgba(255,200,87,0.18), transparent 68%);
    }
    h1 {
      margin: 0;
      font-size: clamp(2.5rem, 7vw, 5.6rem);
      line-height: 0.92;
      letter-spacing: -0.04em;
    }
    .sub {
      margin: 12px 0 0;
      max-width: 780px;
      color: var(--muted);
      font-size: 1.08rem;
      line-height: 1.45;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 14px;
      margin-top: 24px;
    }
    .metric {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
    }
    .metric strong {
      display: block;
      font-size: 1.5rem;
    }
    .metric span {
      color: var(--muted);
      font-size: 0.9rem;
    }
    .account-summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }
    .account-summary {
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.07);
    }
    .account-summary h3 {
      margin: 0 0 10px;
      font-size: 1.1rem;
    }
    .mini-stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .mini-stat {
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(0,0,0,0.18);
      border: 1px solid rgba(255,255,255,0.05);
    }
    .mini-stat strong {
      display: block;
      font-size: 1.05rem;
    }
    .mini-stat span {
      color: var(--muted);
      font-size: 0.8rem;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin-top: 14px;
      margin-bottom: 14px;
    }
    .summary-box {
      padding: 12px;
      border-radius: 16px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
    }
    .summary-box strong {
      display: block;
      font-size: 1.2rem;
    }
    .summary-box span {
      color: var(--muted);
      font-size: 0.85rem;
    }
    .main-grid {
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 20px;
    }
    .stack {
      display: grid;
      gap: 20px;
      align-content: start;
    }
    .content-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
      align-content: start;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 20px;
      box-shadow: var(--shadow);
    }
    .card h2, .card h3 {
      margin: 0 0 14px;
    }
    .eyebrow {
      display: inline-block;
      padding: 5px 10px;
      border-radius: 999px;
      background: rgba(72,209,196,0.14);
      color: var(--accent);
      font-size: 0.8rem;
      margin-bottom: 12px;
    }
    .playbook {
      display: grid;
      gap: 12px;
    }
    .playbook-item {
      padding: 14px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px;
      background: rgba(255,255,255,0.03);
    }
    .playbook-item strong { display: block; margin-bottom: 4px; }
    .playbook-item span { color: var(--muted); font-size: 0.92rem; line-height: 1.35; }
    .slots {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .slot {
      appearance: none;
      border: 1px solid rgba(124,199,255,0.18);
      padding: 8px 11px;
      border-radius: 999px;
      background: #10182a;
      color: var(--blue);
      font-size: 0.85rem;
      cursor: pointer;
      font: inherit;
    }
    .slot:hover {
      background: rgba(124,199,255,0.12);
    }
    .slot:focus-visible {
      outline: 2px solid rgba(72,209,196,0.7);
      outline-offset: 2px;
    }
    .hint {
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }
    .status {
      margin-top: 14px;
      padding: 14px;
      border: 1px solid var(--line);
      background: #0e1320;
      border-radius: 16px;
      min-height: 64px;
      color: var(--muted);
      white-space: pre-wrap;
      word-break: break-word;
    }
    label {
      display: block;
      margin: 10px 0 6px;
      color: var(--muted);
      font-size: 0.9rem;
    }
    input, select, textarea {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      font: inherit;
    }
    textarea { min-height: 110px; resize: vertical; }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    button {
      margin-top: 14px;
      padding: 12px 18px;
      border: 0;
      border-radius: 999px;
      font-weight: 700;
      cursor: pointer;
      background: var(--accent);
      color: #071017;
    }
    button.secondary { background: var(--gold); color: #221800; }
    button.ghost {
      background: transparent;
      color: var(--text);
      border: 1px solid var(--line);
    }
    .list {
      display: grid;
      gap: 12px;
    }
    .item {
      padding: 14px;
      border-radius: 16px;
      background: #101522;
      border: 1px solid rgba(255,255,255,0.08);
    }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(72,209,196,0.12);
      color: var(--accent);
      font-size: 0.8rem;
      margin-bottom: 8px;
    }
    .plan-post {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid rgba(255,255,255,0.06);
      color: var(--muted);
      font-size: 0.92rem;
    }
    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
      margin-bottom: 8px;
    }
    .meta-pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(124,199,255,0.10);
      color: var(--blue);
      border: 1px solid rgba(124,199,255,0.14);
      font-size: 0.78rem;
    }
    .item-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    .item-actions button {
      margin-top: 0;
      padding: 9px 14px;
      font-size: 0.9rem;
    }
    .wide { grid-column: 1 / -1; }
    @media (max-width: 1024px) {
      .main-grid { grid-template-columns: 1fr; }
      .content-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .row { grid-template-columns: 1fr; }
      .hero { padding: 26px 20px; }
      h1 { font-size: 2.5rem; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">One Piece Growth Ops • Dashboard v2.6</div>
      <h1>One Piece X Control Panel</h1>
      <p class="sub">Run the two connected X accounts as a daily One Piece content system. Queue posts, save plan batches, review saved plans, and keep publishing organized while X billing is still paused.</p>
      <div class="metrics">
        <div class="metric"><strong>2</strong><span>Connected X accounts</span></div>
        <div class="metric"><strong>Queue</strong><span>Manual drafts and scheduler-approved plan posts</span></div>
        <div class="metric"><strong>Daily Plans</strong><span>Stored by account and date</span></div>
        <div class="metric"><strong>Browser UI</strong><span>No more raw curl workflow</span></div>
      </div>
      <div class="account-summary-grid" id="account-summary-grid"></div>
    </section>

    <section class="main-grid">
      <aside class="stack">
        <div class="card">
          <div class="eyebrow">Account Playbooks</div>
          <div class="playbook">
            <div class="playbook-item">
              <strong>account1</strong>
              <span>Manga-first account. Best for chapter reactions, theory prompts, spoiler-contained discussion, and quote-tweet hooks.</span>
            </div>
            <div class="playbook-item">
              <strong>account2</strong>
              <span>Anime-safe account. Best for episode reactions, callbacks, breakdowns, and broad engagement posts without manga spoilers.</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="eyebrow">Posting Windows</div>
          <h3>account1</h3>
          <div class="slots">
            <button type="button" class="slot slot-btn" data-account-id="account1" data-slot="08:30">08:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account1" data-slot="11:30">11:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account1" data-slot="14:30">14:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account1" data-slot="17:30">17:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account1" data-slot="20:30">20:30</button>
          </div>
          <h3 style="margin-top:16px;">account2</h3>
          <div class="slots">
            <button type="button" class="slot slot-btn" data-account-id="account2" data-slot="09:30">09:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account2" data-slot="12:30">12:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account2" data-slot="15:30">15:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account2" data-slot="18:30">18:30</button>
            <button type="button" class="slot slot-btn" data-account-id="account2" data-slot="21:30">21:30</button>
          </div>
          <p class="hint" style="margin-top:12px;">Click a time to add a post template for that slot into the daily plan JSON.</p>
        </div>

        <div class="card">
          <div class="eyebrow">Quick Tips</div>
          <p class="hint">Use queue mode for draft collection. Save a plan first when you want structured daily output, then turn plan entries into queued posts. Keep spoilers limited to account1 unless clearly labeled.</p>
        </div>
      </aside>

      <div class="content-grid">
        <div class="card">
          <div class="eyebrow">Queue Draft</div>
          <h2>Queue a Post</h2>
          <div class="row">
            <div>
              <label for="post-account">Account</label>
              <select id="post-account">
                <option value="account1">account1</option>
                <option value="account2">account2</option>
              </select>
            </div>
            <div>
              <label for="reply-to">Reply To</label>
              <input id="reply-to" placeholder="Optional tweet id" />
            </div>
          </div>
          <label for="post-text">Post Text</label>
          <textarea id="post-text" placeholder="Write the next One Piece post draft here."></textarea>
          <button id="queue-post">Save To Queue</button>
          <div class="status" id="post-result">Ready to save a draft.</div>
        </div>

        <div class="card">
          <div class="eyebrow">Daily Batch</div>
          <h2>Save Daily Plan</h2>
          <div class="row">
            <div>
              <label for="plan-account">Account</label>
              <select id="plan-account">
                <option value="account1">account1</option>
                <option value="account2">account2</option>
              </select>
            </div>
            <div>
              <label for="plan-date">Plan Date</label>
              <input id="plan-date" type="date" />
            </div>
          </div>
          <label for="plan-notes">Notes</label>
          <textarea id="plan-notes" placeholder="Theme, spoiler rules, promotion angle, or thread goals."></textarea>
          <label for="plan-posts">Posts JSON</label>
          <textarea id="plan-posts">[
  {"slot":"08:30","type":"hook","text":"What was the coldest One Piece entrance ever?"},
  {"slot":"17:30","type":"debate","text":"Which Straw Hat has had the best long-term character payoff?"}
]</textarea>
          <div class="row">
            <button class="ghost" id="generate-plan">Generate Today’s Plan</button>
            <button class="secondary" id="save-plan">Save Plan</button>
          </div>
          <button id="save-and-queue-plan">Save + Queue Plan</button>
          <div class="status" id="plan-result">Ready to save a daily plan.</div>
        </div>

        <div class="card wide">
          <div class="eyebrow">Draft Queue</div>
          <h2>Queued Posts</h2>
          <div class="row">
            <div>
              <label for="queue-account">Account</label>
              <select id="queue-account">
                <option value="account1">account1</option>
                <option value="account2">account2</option>
              </select>
            </div>
            <div style="display:flex; align-items:end; gap:12px;">
              <button class="ghost" id="load-queue">Refresh Queue</button>
            </div>
          </div>
          <div class="summary-grid" id="queue-summary"></div>
          <div class="list" id="queue-list"></div>
        </div>

        <div class="card wide">
          <div class="eyebrow">Live Outcomes</div>
          <h2>Recent Activity</h2>
          <div class="row">
            <div>
              <label for="activity-account">Account</label>
              <select id="activity-account">
                <option value="account1">account1</option>
                <option value="account2">account2</option>
              </select>
            </div>
            <div style="display:flex; align-items:end; gap:12px;">
              <button class="ghost" id="load-activity">Refresh Activity</button>
            </div>
          </div>
          <div class="list" id="activity-list"></div>
        </div>

        <div class="card wide">
          <div class="eyebrow">Saved Plans</div>
          <h2>Plan Library</h2>
          <div class="row">
            <div>
              <label for="plans-account">Account</label>
              <select id="plans-account">
                <option value="account1">account1</option>
                <option value="account2">account2</option>
              </select>
            </div>
            <div style="display:flex; align-items:end; gap:12px;">
              <button class="ghost" id="load-plans">Refresh Plans</button>
            </div>
          </div>
          <div class="list" id="plans-list"></div>
        </div>
      </div>
    </section>
  </div>

  <script>
    function pretty(value) {
      return JSON.stringify(value, null, 2);
    }

    function defaultPostTypeForAccount(accountId) {
      return accountId === "account1" ? "hook" : "reaction";
    }

    function parsePlanPostsValue() {
      const raw = document.getElementById("plan-posts").value.trim();
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        throw new Error("Posts JSON must be an array.");
      }
      return parsed;
    }

    function appendPlanSlot(accountId, slot) {
      const planAccount = document.getElementById("plan-account");
      planAccount.value = accountId;

      let posts = [];
      try {
        posts = parsePlanPostsValue();
      } catch (error) {
        setStatus("plan-result", `Posts JSON is invalid: ${error.message}`);
        return;
      }

      const duplicate = posts.find((post) => post && post.slot === slot);
      if (duplicate) {
        setStatus("plan-result", `Slot ${slot} is already in the plan JSON for ${accountId}.`);
        return;
      }

      posts.push({
        slot,
        type: defaultPostTypeForAccount(accountId),
        text: ""
      });
      document.getElementById("plan-posts").value = pretty(posts);
      setStatus("plan-result", `Added ${slot} to the plan JSON for ${accountId}. Fill in the text before saving.`);
      document.getElementById("plan-posts").focus();
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        ...options
      });
      const raw = await response.text();
      let data = {};
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch (_error) {
        throw new Error(`Non-JSON response from ${path}: ${raw.slice(0, 200)}`);
      }
      if (!response.ok) {
        const detail = data.error || data.message || raw || `HTTP ${response.status}`;
        throw new Error(detail);
      }
      return data;
    }

    function setStatus(elementId, value) {
      document.getElementById(elementId).textContent = typeof value === "string" ? value : pretty(value);
    }

    function renderEmpty(targetId, message) {
      document.getElementById(targetId).innerHTML = `<div class="item">${message}</div>`;
    }

    async function loadAccountSummary() {
      const target = document.getElementById("account-summary-grid");
      target.innerHTML = "";
      try {
        const result = await api("/x/summary");
        if (!result.accounts || !result.accounts.length) {
          return;
        }
        target.innerHTML = result.accounts.map((account) => `
        <div class="account-summary">
          <h3>${account.account_id}</h3>
          <div class="mini-stats">
            <div class="mini-stat"><strong>${account.queued}</strong><span>Queued posts</span></div>
            <div class="mini-stat"><strong>${account.saved_plans}</strong><span>Saved plans</span></div>
            <div class="mini-stat"><strong>${account.queued_from_plan}</strong><span>Queued from plans</span></div>
            <div class="mini-stat"><strong>${account.manual_drafts}</strong><span>Manual drafts</span></div>
            <div class="mini-stat"><strong>${account.published || 0}</strong><span>Published</span></div>
            <div class="mini-stat"><strong>${account.failed || 0}</strong><span>Failed</span></div>
          </div>
        </div>
        `).join("");
      } catch (error) {
        target.innerHTML = `<div class="item">Account summary unavailable: ${error.message}</div>`;
      }
    }

    function buildPlanPayload() {
      let posts = [];
      try {
        posts = JSON.parse(document.getElementById("plan-posts").value);
      } catch (_error) {
        throw new Error("Posts JSON is invalid.");
      }

      return {
        account_id: document.getElementById("plan-account").value,
        plan_date: document.getElementById("plan-date").value,
        notes: document.getElementById("plan-notes").value,
        posts
      };
    }

    document.getElementById("queue-post").addEventListener("click", async () => {
      setStatus("post-result", "Saving...");
      const payload = {
        account_id: document.getElementById("post-account").value,
        text: document.getElementById("post-text").value,
        reply_to: document.getElementById("reply-to").value,
        queue_only: true
      };
      try {
        const result = await api("/x/post", { method: "POST", body: JSON.stringify(payload) });
        setStatus("post-result", result);
        document.getElementById("post-text").value = "";
        await loadQueue();
        await loadAccountSummary();
        await loadActivity();
      } catch (error) {
        setStatus("post-result", `Save failed: ${error.message}`);
      }
    });

    document.getElementById("save-plan").addEventListener("click", async () => {
      setStatus("plan-result", "Saving...");
      try {
        const payload = buildPlanPayload();
        const result = await api("/x/plan", { method: "POST", body: JSON.stringify(payload) });
        setStatus("plan-result", result);
        await loadPlans();
        await loadAccountSummary();
      } catch (error) {
        setStatus("plan-result", `Save failed: ${error.message}`);
      }
    });

    document.getElementById("save-and-queue-plan").addEventListener("click", async () => {
      setStatus("plan-result", "Saving plan and queueing posts...");
      try {
        const payload = buildPlanPayload();
        const saved = await api("/x/plan", { method: "POST", body: JSON.stringify(payload) });
        const queued = await api("/x/plan/queue", {
          method: "POST",
          body: JSON.stringify({
            account_id: saved.account_id,
            plan_id: saved.plan_id,
            plan_sk: saved.plan_sk
          })
        });
        setStatus("plan-result", {
          status: "plan_saved_and_queued",
          saved,
          queued
        });
        await loadPlans();
        await loadQueue();
        await loadAccountSummary();
        await loadActivity();
      } catch (error) {
        setStatus("plan-result", `Save + queue failed: ${error.message}`);
      }
    });

    document.getElementById("generate-plan").addEventListener("click", async () => {
      setStatus("plan-result", "Generating...");
      const payload = {
        account_id: document.getElementById("plan-account").value,
        plan_date: document.getElementById("plan-date").value
      };
      try {
        const result = await api("/x/plan/generate", { method: "POST", body: JSON.stringify(payload) });
        if (result.posts) {
          document.getElementById("plan-notes").value = result.notes || "";
          document.getElementById("plan-posts").value = pretty(result.posts);
        }
        setStatus("plan-result", result);
      } catch (error) {
        setStatus("plan-result", `Generate failed: ${error.message}`);
      }
    });

    async function loadQueue() {
      const accountId = document.getElementById("queue-account").value;
      renderEmpty("queue-list", "Loading queue...");
      document.getElementById("queue-summary").innerHTML = "";
      try {
        const result = await api(`/x/queue?account_id=${encodeURIComponent(accountId)}`);
        if (!result.items || !result.items.length) {
          const summary = result.summary || { queued: 0, from_plan: 0, manual: 0 };
          document.getElementById("queue-summary").innerHTML = `
          <div class="summary-box"><strong>${summary.queued}</strong><span>Total queued</span></div>
          <div class="summary-box"><strong>${summary.from_plan}</strong><span>Queued from plans</span></div>
          <div class="summary-box"><strong>${summary.manual}</strong><span>Manual drafts</span></div>
        `;
          renderEmpty("queue-list", "No queued posts yet.");
          return;
        }
        const summary = result.summary || { queued: result.items.length, from_plan: 0, manual: result.items.length };
        document.getElementById("queue-summary").innerHTML = `
        <div class="summary-box"><strong>${summary.queued}</strong><span>Total queued</span></div>
        <div class="summary-box"><strong>${summary.from_plan}</strong><span>Queued from plans</span></div>
        <div class="summary-box"><strong>${summary.manual}</strong><span>Manual drafts</span></div>
      `;
        document.getElementById("queue-list").innerHTML = result.items.map((item) => `
        <div class="item">
          <div class="pill">${item.status}</div>
          <div><strong>${item.account_id}</strong> · ${item.queued_at || "-"}</div>
          <div class="meta-row">
            ${item.slot ? `<span class="meta-pill">slot ${item.slot}</span>` : ""}
            ${item.type ? `<span class="meta-pill">${item.type}</span>` : ""}
            ${item.source_plan_id ? `<span class="meta-pill">plan ${item.source_plan_id}</span>` : ""}
            ${item.publish_mode ? `<span class="meta-pill">${item.publish_mode}</span>` : ""}
            ${item.auto_approved ? `<span class="meta-pill">auto-approved</span>` : ""}
            ${item.scheduled_for ? `<span class="meta-pill">due ${item.scheduled_for}</span>` : ""}
          </div>
          <div style="margin-top:8px;">${item.text || ""}</div>
          <div class="hint" style="margin-top:8px;">Reason: ${item.publish_reason || "-"}</div>
          <div class="item-actions">
            <button
              class="ghost publish-queue-btn"
              data-account-id="${item.account_id || ""}"
              data-post-id="${item.post_id || ""}"
            >Publish Now</button>
            <button
              class="ghost remove-queue-btn"
              data-account-id="${item.account_id || ""}"
              data-post-id="${item.post_id || ""}"
            >Remove</button>
          </div>
        </div>
        `).join("");
      } catch (error) {
        document.getElementById("queue-summary").innerHTML = "";
        renderEmpty("queue-list", `Queue load failed: ${error.message}`);
      }
    }

    async function loadActivity() {
      const accountId = document.getElementById("activity-account").value;
      renderEmpty("activity-list", "Loading activity...");
      try {
        const result = await api(`/x/activity?account_id=${encodeURIComponent(accountId)}`);
        if (!result.items || !result.items.length) {
          renderEmpty("activity-list", "No activity yet.");
          return;
        }
        document.getElementById("activity-list").innerHTML = result.items.map((item) => `
        <div class="item">
          <div class="pill">${item.status}</div>
          <div><strong>${item.account_id}</strong></div>
          <div class="meta-row">
            ${item.slot ? `<span class="meta-pill">slot ${item.slot}</span>` : ""}
            ${item.type ? `<span class="meta-pill">${item.type}</span>` : ""}
            ${item.tweet_id ? `<span class="meta-pill">tweet ${item.tweet_id}</span>` : ""}
          </div>
          <div style="margin-top:8px;">${item.text || ""}</div>
          <div class="hint" style="margin-top:8px;">
            ${item.published_at ? `Published at: ${item.published_at}` : ""}
            ${item.last_error ? `Last error: ${item.last_error}` : ""}
            ${item.removed_at ? `Removed at: ${item.removed_at}` : ""}
          </div>
        </div>
        `).join("");
      } catch (error) {
        renderEmpty("activity-list", `Activity load failed: ${error.message}`);
      }
    }

    async function loadPlans() {
      const accountId = document.getElementById("plans-account").value;
      renderEmpty("plans-list", "Loading plans...");
      try {
        const result = await api(`/x/plans?account_id=${encodeURIComponent(accountId)}`);
        if (!result.items || !result.items.length) {
          renderEmpty("plans-list", "No saved plans yet.");
          return;
        }
        document.getElementById("plans-list").innerHTML = result.items.map((item) => `
        <div class="item">
          <div class="pill">${item.plan_date}</div>
          <div><strong>${item.account_id}</strong> · saved ${item.saved_at || "-"}</div>
          <div class="hint" style="margin-top:8px;">${item.notes || "No notes."}</div>
          ${(item.posts || []).map((post) => `
            <div class="plan-post">
              <strong>${post.slot || "-"}</strong> · ${post.type || "post"}<br />
              ${post.text || ""}
            </div>
          `).join("")}
          <div class="item-actions">
            <button
              class="ghost queue-plan-btn"
              data-account-id="${item.account_id || ""}"
              data-plan-id="${item.plan_id || ""}"
              data-plan-sk="${item.SK || ""}"
            >Queue Plan</button>
          </div>
        </div>
        `).join("");
      } catch (error) {
        renderEmpty("plans-list", `Plans load failed: ${error.message}`);
      }
    }

    async function queuePlan(payload) {
      setStatus("plan-result", "Queueing plan...");
      try {
        const result = await api("/x/plan/queue", { method: "POST", body: JSON.stringify(payload) });
        setStatus("plan-result", result);
        await loadQueue();
        await loadAccountSummary();
        await loadActivity();
      } catch (error) {
        setStatus("plan-result", `Queue plan failed: ${error.message}`);
      }
    }

    async function removeQueuedPost(payload) {
      setStatus("post-result", "Removing queued post...");
      try {
        const result = await api("/x/queue/remove", { method: "POST", body: JSON.stringify(payload) });
        setStatus("post-result", result);
        await loadQueue();
        await loadAccountSummary();
        await loadActivity();
      } catch (error) {
        setStatus("post-result", `Remove failed: ${error.message}`);
      }
    }

    async function publishQueuedPost(payload) {
      setStatus("post-result", "Publishing queued post...");
      try {
        const result = await api("/x/queue/publish", { method: "POST", body: JSON.stringify(payload) });
        setStatus("post-result", result);
        await loadQueue();
        await loadAccountSummary();
        await loadActivity();
      } catch (error) {
        setStatus("post-result", `Publish failed: ${error.message}`);
      }
    }

    document.getElementById("load-queue").addEventListener("click", loadQueue);
    document.getElementById("load-activity").addEventListener("click", loadActivity);
    document.getElementById("load-plans").addEventListener("click", loadPlans);
    document.getElementById("queue-account").addEventListener("change", loadQueue);
    document.getElementById("activity-account").addEventListener("change", loadActivity);
    document.getElementById("plans-account").addEventListener("change", loadPlans);
    document.querySelectorAll(".slot-btn").forEach((button) => {
      button.addEventListener("click", () => {
        appendPlanSlot(button.dataset.accountId, button.dataset.slot);
      });
    });
    document.getElementById("plans-list").addEventListener("click", async (event) => {
      const button = event.target.closest(".queue-plan-btn");
      if (!button) {
        return;
      }
      await queuePlan({
        account_id: button.dataset.accountId,
        plan_id: button.dataset.planId,
        plan_sk: button.dataset.planSk
      });
    });
    document.getElementById("queue-list").addEventListener("click", async (event) => {
      const publishButton = event.target.closest(".publish-queue-btn");
      if (publishButton) {
        if (!window.confirm("Publish this queued post live now?")) {
          return;
        }
        await publishQueuedPost({
          account_id: publishButton.dataset.accountId,
          post_id: publishButton.dataset.postId,
          approved: true
        });
        return;
      }

      const button = event.target.closest(".remove-queue-btn");
      if (!button) {
        return;
      }
      await removeQueuedPost({
        account_id: button.dataset.accountId,
        post_id: button.dataset.postId
      });
    });

    document.getElementById("plan-date").value = new Date().toISOString().slice(0, 10);
    loadAccountSummary();
    loadQueue();
    loadActivity();
    loadPlans();
  </script>
</body>
</html>"""


def lambda_handler(_event, _context):
    return html_response(200, _dashboard_html())
