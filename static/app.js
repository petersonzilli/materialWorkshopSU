// Copyright (c) 2026 Peterson Katagiri Zilli
// SPDX-License-Identifier: Apache-2.0

const state = {
  companies: [],
  runs: [],
  selectedCompany: null,
  selectedCampaign: null,
  activeRunId: null,
  refreshTimer: null,
  sessionToken: null,
};

const stageOrder = [
  "Briefing intake",
  "Estratégia de mensagem",
  "Master copy",
  "Revisão por personas",
  "Adaptação de canal",
  "Validação de regras",
  "Pronto para revisão humana",
];

const statusLabels = {
  ready: "Pronto para iniciar",
  running: "Em execução",
  awaiting_human: "Aguardando intervenção humana",
  complete: "Pronto para revisão humana",
  error: "Execução interrompida",
  stopped: "Parado",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatTimestamp(value) {
  const timestamp = String(value ?? "");
  if (!/(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp)) return timestamp;

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;

  return new Intl.DateTimeFormat(navigator.language || "pt-BR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  }).format(date);
}

function formatTimestampsInText(value, sourceTimezone = null) {
  let text = String(value ?? "");
  text = text.replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})/gi, formatTimestamp);
  if (sourceTimezone === "UTC") {
    text = text.replace(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/g, (timestamp) => {
      return formatTimestamp(`${timestamp.replace(" ", "T")}Z`);
    });
  }
  return text;
}

function normalizeEvidence(value) {
  if (value == null) return [];
  const entries = Array.isArray(value) ? value : [value];
  const firstText = (item, keys) => {
    for (const key of keys) {
      const candidate = item[key];
      if (candidate != null && String(candidate).trim()) {
        return typeof candidate === "string" ? candidate.trim() : JSON.stringify(candidate, null, 2);
      }
    }
    return "";
  };

  return entries.map((item) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const summary = firstText(item, ["summary", "finding", "outcome", "claim", "title", "message"]);
      const source = firstText(item, ["source", "artifact", "file", "reference", "path"]);
      let detail = firstText(item, ["detail", "evidence", "description", "quote", "reason"]);
      const recognizedKeys = new Set([
        "summary", "finding", "outcome", "claim", "title", "message",
        "source", "artifact", "file", "reference", "path",
        "detail", "evidence", "description", "quote", "reason",
      ]);
      const additional = Object.fromEntries(Object.entries(item).filter(([key]) => !recognizedKeys.has(key)));
      if (Object.keys(additional).length) {
        detail = `${detail}${detail ? "\n\n" : ""}Informações adicionais:\n${JSON.stringify(additional, null, 2)}`;
      }
      return {
        summary: summary || (source || detail ? detail || source : JSON.stringify(item, null, 2)),
        source,
        detail,
      };
    }
    if (typeof item === "string") return { summary: item.trim(), source: "", detail: "" };
    return { summary: String(item ?? "").trim(), source: "", detail: "" };
  }).filter((item) => item.summary || item.source || item.detail);
}

function sameNodeKind(current, next) {
  return current.nodeType === next.nodeType
    && (current.nodeType !== Node.ELEMENT_NODE || current.tagName === next.tagName);
}

function domKey(node) {
  return node.nodeType === Node.ELEMENT_NODE ? node.dataset.domKey || null : null;
}

function morphNode(current, next) {
  if (current.nodeType === Node.TEXT_NODE || current.nodeType === Node.COMMENT_NODE) {
    if (current.nodeValue !== next.nodeValue) current.nodeValue = next.nodeValue;
    return current;
  }

  const preserveOpen = current.tagName === "DETAILS";
  for (const attribute of Array.from(current.attributes)) {
    if (preserveOpen && attribute.name === "open") continue;
    if (!next.hasAttribute(attribute.name)) current.removeAttribute(attribute.name);
  }
  for (const attribute of Array.from(next.attributes)) {
    if (preserveOpen && attribute.name === "open") continue;
    if (current.getAttribute(attribute.name) !== attribute.value) {
      current.setAttribute(attribute.name, attribute.value);
    }
  }

  morphChildren(current, next);
  return current;
}

function morphChildren(currentParent, nextParent) {
  const oldChildren = Array.from(currentParent.childNodes);
  const keyedChildren = new Map();
  oldChildren.forEach((node) => {
    const key = domKey(node);
    if (key && !keyedChildren.has(key)) keyedChildren.set(key, node);
  });

  const used = new Set();
  const nextChildren = Array.from(nextParent.childNodes);
  let unkeyedIndex = 0;
  let position = 0;

  nextChildren.forEach((next) => {
    const key = domKey(next);
    let current = key ? keyedChildren.get(key) : null;
    if (current && (used.has(current) || !sameNodeKind(current, next))) current = null;

    if (!key) {
      while (unkeyedIndex < oldChildren.length) {
        const candidate = oldChildren[unkeyedIndex++];
        if (!used.has(candidate) && !domKey(candidate) && sameNodeKind(candidate, next)) {
          current = candidate;
          break;
        }
      }
    }

    let node;
    if (current) {
      used.add(current);
      node = morphNode(current, next);
    } else {
      node = next.cloneNode(true);
      used.add(node);
    }

    const reference = currentParent.childNodes[position] || null;
    if (reference !== node) currentParent.insertBefore(node, reference);
    position += 1;
  });

  oldChildren.forEach((node) => {
    if (!used.has(node) && node.parentNode === currentParent) currentParent.removeChild(node);
  });
}

function updateHtml(container, html) {
  const template = document.createElement("template");
  template.innerHTML = html;
  morphChildren(container, template.content);
}

function safeMarkdownUrl(value) {
  const url = String(value || "").trim();
  if (!url || /[\u0000-\u001f\u007f]/.test(url) || /^(?:\/\/|\\\\)/.test(url)) return null;
  const scheme = url.match(/^([a-z][a-z\d+.-]*):/i)?.[1]?.toLowerCase();
  if (scheme && !["http", "https", "mailto", "tel"].includes(scheme)) return null;
  return url;
}

function renderMarkdownInline(value) {
  const tokens = [];
  const protect = (html) => {
    const token = `\uE000${tokens.length}\uE001`;
    tokens.push(html);
    return token;
  };
  let text = String(value ?? "").replace(/\\([\\`*_{}\[\]()#+\-.!|>])/g, "$1");

  text = text.replace(/`([^`\n]+)`/g, (_match, code) => protect(`<code>${escapeHtml(code)}</code>`));
  text = text.replace(/!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (_match, alt, url) => {
    const safeUrl = safeMarkdownUrl(url);
    if (!safeUrl) return escapeHtml(alt);
    return protect(`<span class="markdown-image-alt">[Imagem: ${escapeHtml(alt || "sem descrição")}]</span>`);
  });
  text = text.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/g, (_match, label, url, title) => {
    const safeUrl = safeMarkdownUrl(url);
    if (!safeUrl) return escapeHtml(label);
    const titleAttribute = title ? ` title="${escapeHtml(title)}"` : "";
    return protect(`<a href="${escapeHtml(safeUrl)}"${titleAttribute}>${renderMarkdownInline(label)}</a>`);
  });
  text = text.replace(/<(https?:\/\/[^>\s]+|mailto:[^>\s]+)>/gi, (_match, url) => {
    const safeUrl = safeMarkdownUrl(url);
    return safeUrl ? protect(`<a href="${escapeHtml(safeUrl)}">${escapeHtml(url)}</a>`) : escapeHtml(url);
  });

  text = escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/~~(.+?)~~/g, "<del>$1</del>")
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=$|[\s).,!?:;])/g, "$1<em>$2</em>")
    .replace(/(^|[\s(])_([^_\n]+)_(?=$|[\s).,!?:;])/g, "$1<em>$2</em>");

  return text.replace(/\uE000(\d+)\uE001/g, (_match, index) => tokens[Number(index)] || "");
}

function splitMarkdownTableRow(line) {
  const cells = [];
  let cell = "";
  let inCode = false;
  let escaped = false;
  for (const character of line.trim()) {
    if (escaped) {
      cell += character;
      escaped = false;
    } else if (character === "\\") {
      cell += character;
      escaped = true;
    } else if (character === "`") {
      inCode = !inCode;
      cell += character;
    } else if (character === "|" && !inCode) {
      cells.push(cell.trim());
      cell = "";
    } else {
      cell += character;
    }
  }
  cells.push(cell.trim());
  if (cells[0] === "") cells.shift();
  if (cells[cells.length - 1] === "") cells.pop();
  return cells;
}

function isMarkdownTableStart(lines, index) {
  if (index + 1 >= lines.length || !lines[index].includes("|")) return false;
  const separators = splitMarkdownTableRow(lines[index + 1]);
  return separators.length > 1 && separators.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function matchMarkdownListItem(line) {
  const match = line.match(/^(\s*)([-+*]|\d+[.)])\s+(.*)$/);
  if (!match) return null;
  return {
    indent: match[1].replace(/\t/g, "    ").length,
    marker: match[2],
    text: match[3],
  };
}

function renderMarkdownList(lines, start, indent) {
  const firstItem = matchMarkdownListItem(lines[start]);
  const ordered = /^\d/.test(firstItem.marker);
  const tag = ordered ? "ol" : "ul";
  const items = [];
  let currentItem = null;
  let index = start;

  while (index < lines.length) {
    const listItem = matchMarkdownListItem(lines[index]);
    if (listItem) {
      if (listItem.indent < indent) break;
      if (listItem.indent > indent) {
        if (!currentItem) break;
        const nested = renderMarkdownList(lines, index, listItem.indent);
        currentItem.children.push(nested.html);
        index = nested.next;
        continue;
      }
      if (/^\d/.test(listItem.marker) !== ordered) break;
      currentItem = { text: listItem.text, children: [] };
      items.push(currentItem);
      index += 1;
      continue;
    }

    if (!lines[index].trim()) {
      const nextItem = matchMarkdownListItem(lines[index + 1] || "");
      if (nextItem && nextItem.indent >= indent) {
        index += 1;
        continue;
      }
      break;
    }

    const continuationIndent = (lines[index].match(/^\s*/) || [""])[0].replace(/\t/g, "    ").length;
    if (currentItem && continuationIndent > indent) {
      currentItem.text += ` ${lines[index].trim()}`;
      index += 1;
      continue;
    }
    break;
  }

  const content = items.map((item) => {
    const task = item.text.match(/^\[([ xX])\]\s+(.*)$/);
    const itemText = task ? task[2] : item.text;
    const checkbox = task
      ? `<input class="markdown-task-checkbox" type="checkbox" disabled${task[1].toLowerCase() === "x" ? " checked" : ""}> `
      : "";
    return `<li>${checkbox}${renderMarkdownInline(itemText)}${item.children.join("")}</li>`;
  }).join("");
  return { html: `<${tag}>${content}</${tag}>`, next: index };
}

function renderMarkdownTable(lines, start) {
  const headings = splitMarkdownTableRow(lines[start]);
  const separators = splitMarkdownTableRow(lines[start + 1]);
  const alignments = headings.map((_heading, index) => {
    const separator = separators[index] || "---";
    if (separator.startsWith(":") && separator.endsWith(":")) return "center";
    if (separator.endsWith(":")) return "right";
    return "left";
  });
  const rows = [];
  let index = start + 2;
  while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
    rows.push(splitMarkdownTableRow(lines[index]));
    index += 1;
  }
  const header = headings.map((heading, column) =>
    `<th scope="col" style="text-align:${alignments[column]}">${renderMarkdownInline(heading)}</th>`).join("");
  const body = rows.map((row) => `<tr>${headings.map((_heading, column) =>
    `<td style="text-align:${alignments[column]}">${renderMarkdownInline(row[column] || "")}</td>`).join("")}</tr>`).join("");
  return {
    html: `<div class="markdown-table-wrap" role="region" aria-label="Tabela" tabindex="0"><table class="markdown-table"><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div>`,
    next: index,
  };
}

function renderMarkdown(value) {
  const lines = formatTimestampsInText(value).replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^\s*(`{3,}|~{3,})(.*)$/);
    if (fence) {
      const fenceMarker = fence[1];
      const language = fence[2].trim().split(/\s+/)[0] || "";
      const className = /^[a-z\d_+-]+$/i.test(language) ? ` class="language-${escapeHtml(language)}"` : "";
      const codeLines = [];
      index += 1;
      while (index < lines.length && !new RegExp(`^\\s*${fenceMarker[0]}{${fenceMarker.length},}\\s*$`).test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push(`<pre><code${className}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      const table = renderMarkdownTable(lines, index);
      blocks.push(table.html);
      index = table.next;
      continue;
    }

    const heading = line.match(/^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const level = heading[1].length;
      blocks.push(`<h${level}>${renderMarkdownInline(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^\s*(?:(?:-{3,})|(?:_{3,})|(?:\*{3,}))\s*$/.test(line)) {
      blocks.push("<hr>");
      index += 1;
      continue;
    }

    if (/^\s*>/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^\s*>/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push(`<blockquote>${renderMarkdown(quoteLines.join("\n"))}</blockquote>`);
      continue;
    }

    const listItem = matchMarkdownListItem(line);
    if (listItem) {
      const list = renderMarkdownList(lines, index, listItem.indent);
      blocks.push(list.html);
      index = list.next;
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length) {
      const nextLine = lines[index];
      if (!nextLine.trim()
        || /^\s*(`{3,}|~{3,})/.test(nextLine)
        || /^ {0,3}#{1,6}\s+/.test(nextLine)
        || /^\s*>/.test(nextLine)
        || matchMarkdownListItem(nextLine)
        || isMarkdownTableStart(lines, index)
        || /^\s*(?:(?:-{3,})|(?:_{3,})|(?:\*{3,}))\s*$/.test(nextLine)) break;
      paragraph.push(nextLine.trim());
      index += 1;
    }
    blocks.push(`<p>${renderMarkdownInline(paragraph.join("\n"))}</p>`);
  }

  return `<div class="markdown-body">${blocks.join("")}</div>`;
}

async function request(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (!["GET", "HEAD"].includes(method)) {
    if (!state.sessionToken) {
      const session = await request("/api/session");
      state.sessionToken = session.token;
    }
    headers["X-Workshop-Token"] = state.sessionToken;
  }
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Erro HTTP ${response.status}`);
  return payload;
}

function showNotice(message, kind = "error") {
  const notice = document.querySelector("#notice");
  notice.textContent = message;
  notice.className = `notice ${kind === "success" ? "success" : ""}`;
  notice.hidden = false;
  window.clearTimeout(showNotice.timeout);
  showNotice.timeout = window.setTimeout(() => { notice.hidden = true; }, 7000);
}

function selectedCase() {
  const company = state.companies.find((item) => item.id === state.selectedCompany);
  const campaign = company?.campaigns.find((item) => item.id === state.selectedCampaign);
  return { company, campaign };
}

function renderCatalog() {
  const catalog = document.querySelector("#catalog");
  document.querySelector("#company-count").textContent = state.companies.length;
  if (!state.companies.length) {
    catalog.innerHTML = '<div class="loading-card">Nenhuma empresa foi encontrada em cases/.</div>';
    return;
  }
  catalog.innerHTML = state.companies.map((company) => {
    const companySelected = company.id === state.selectedCompany;
    return `<article class="company-card ${companySelected ? "selected" : ""}">
      <button class="company-select" data-company="${escapeHtml(company.id)}" type="button">
        <span>${escapeHtml(company.name)}</span><span aria-hidden="true">${companySelected ? "⌄" : "›"}</span>
      </button>
      <span class="company-meta">${company.configurations.length} configurações · ${company.campaigns.length} campanhas</span>
      ${companySelected ? company.campaigns.map((campaign) => `
        <button class="campaign-pick ${campaign.id === state.selectedCampaign ? "selected" : ""}" data-campaign="${escapeHtml(campaign.id)}" type="button">
          <span>${escapeHtml(campaign.id)}</span><small>${campaign.artifacts.length} arquivos</small>
        </button>`).join("") : ""}
    </article>`;
  }).join("");
  catalog.querySelectorAll("[data-company]").forEach((button) => {
    button.addEventListener("click", () => {
      const company = state.companies.find((item) => item.id === button.dataset.company);
      state.selectedCompany = company.id;
      state.selectedCampaign = company.campaigns[0]?.id ?? null;
      renderCatalog();
      renderCase();
    });
  });
  catalog.querySelectorAll("[data-campaign]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedCampaign = button.dataset.campaign;
      renderCatalog();
      renderCase();
    });
  });
}

function renderCase() {
  const panel = document.querySelector("#case-panel");
  const { company, campaign } = selectedCase();
  if (!company || !campaign) {
    panel.innerHTML = '<div class="empty-state"><span class="empty-icon">01</span><h2>Selecione uma campanha</h2><p>Escolha um dos cases para consultar configurações e briefing.</p></div>';
    return;
  }
  const configurations = company.configurations.map((file) => `
    <details class="file-card"><summary>${escapeHtml(file.name)}</summary>${renderMarkdown(file.content)}</details>`).join("");
  const artifactNames = campaign.artifacts.map((name) => `<span class="artifact-chip">${escapeHtml(name)}</span>`).join("");
  panel.innerHTML = `
    <div class="case-header">
      <div>
        <p class="eyebrow">CASE SELECIONADO</p>
        <h2 class="case-title">${escapeHtml(company.name)}</h2>
        <p class="case-subtitle">Campanha ${escapeHtml(campaign.id)} · briefing e contexto usados como base</p>
      </div>
      <div class="case-actions">
        <label class="limit-control">Loop de personas<input id="audience-max" type="number" min="1" max="25" value="5"></label>
        <label class="limit-control">Loop de regras<input id="rules-max" type="number" min="1" max="25" value="5"></label>
        <button id="start-run" class="button" type="button">Iniciar execução</button>
      </div>
    </div>
    <div class="case-grid">
      <section class="subpanel">
        <div class="subpanel-title"><span>Configurações da empresa</span><small>${company.configurations.length} arquivos</small></div>
        <div class="subpanel-body"><div class="file-stack">${configurations || '<p class="muted">Sem arquivos de configuração.</p>'}</div></div>
      </section>
      <section class="subpanel">
        <div class="subpanel-title"><span>Briefing e campanha</span><small>${escapeHtml(campaign.id)}</small></div>
        <div class="subpanel-body">
          <div class="briefing-preview">${renderMarkdown(campaign.briefing || "Briefing indisponível.")}</div>
          <div class="artifact-list">${artifactNames}</div>
          <div class="case-warning">Os arquivos exibidos são referências. Cada execução cria uma cópia de trabalho para preservar o material original.</div>
        </div>
      </section>
    </div>`;
  document.querySelector("#start-run").addEventListener("click", startSelectedCase);
}

async function startSelectedCase() {
  const { company, campaign } = selectedCase();
  if (!company || !campaign) return;
  const button = document.querySelector("#start-run");
  button.disabled = true;
  button.textContent = "Preparando…";
  try {
    const audienceMax = Number(document.querySelector("#audience-max").value);
    const rulesMax = Number(document.querySelector("#rules-max").value);
    const created = await request("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        company: company.id,
        campaign: campaign.id,
        audience_max: audienceMax,
        rules_max: rulesMax,
      }),
    });
    const runId = created.run.id;
    state.activeRunId = runId;
    await request(`/api/runs/${encodeURIComponent(runId)}/start`, { method: "POST", body: "{}" });
    await refreshRuns();
    await selectRun(runId);
    showNotice(`Execução iniciada para ${company.name}.`, "success");
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Iniciar execução";
  }
}

function activeStepIndex(stage, status) {
  if (status === "complete") return stageOrder.length - 1;
  const text = String(stage || "").toLowerCase();
  if (text.includes("briefing")) return 0;
  if (text.includes("estratégia")) return 1;
  if (text.includes("master") || text.includes("copy")) return 2;
  if (text.includes("persona") || text.includes("audiência")) return 3;
  if (text.includes("canal") || text.includes("adaptação")) return 4;
  if (text.includes("regra")) return 5;
  if (text.includes("revisão humana")) return 6;
  return 0;
}

function artifactPhaseIndex(artifact, run) {
  const name = String(artifact.name || "").toLowerCase();
  const content = String(artifact.content || "");

  if (/^briefing(?:-intake)?(?:-reassessment-\d+)?\.md$/.test(name)) return 0;
  if (/^message-strategy(?:-reassessment-\d+)?\.md$/.test(name)) return 1;
  if (/^master-copy(?:-revision-\d+)?\.md$/.test(name)) return 2;
  if (/^(?:audience-review|audience-diagnosis)-\d+\.md$/.test(name)) return 3;
  if (/^channel-copy(?:-revision-\d+)?\.md$/.test(name)) return 4;
  if (/^rules-validation-\d+\.md$/.test(name)) return 5;
  if (/^human-review-package\.md$/.test(name)) return 6;

  if (/^human-decision-request-\d+\.md$/.test(name)) {
    const stage = content.match(/^- Etapa:\s*(.+)$/mi)?.[1]?.trim() || "";
    const stageText = stage.toLowerCase();
    if (stageText.includes("validação de regras")) return 5;
    if (stageText.includes("adaptação de canal")) return 4;
    if (stageText.includes("briefing")) return 0;
    if (stageText.includes("estratégia")) return 1;
    if (stageText.includes("master") || stageText.includes("copy")) return 2;
    if (stageText.includes("persona") || stageText.includes("audiência")) return 3;
    if (stageText.includes("revisão humana") || stageText.includes("pronto para revisão")) return 6;

    if (/tentativa de regras|rules-validation-\d+|ciclo:\s*rules\b/i.test(content)) return 5;
    if (/tentativa de audi[eê]ncia|audience-(?:review|diagnosis)-\d+|ciclo:\s*audience\b/i.test(content)) return 3;
  }

  if (/^human-(?:decision-request|intervention)-\d+\.md$/.test(name)) {
    const loop = content.match(/^- Ciclo:\s*(.+)$/mi)?.[1]?.trim().toLowerCase();
    if (loop === "audience") return 3;
    if (loop === "rules") return 5;
  }

  return activeStepIndex(run.stage, run.status);
}

function sortPhaseArtifacts(artifacts, phaseIndex) {
  return artifacts.slice().sort((left, right) => {
    if (phaseIndex === 3) {
      const leftAttempt = Number(left.name.match(/-(\d+)\.md$/)?.[1] || 0);
      const rightAttempt = Number(right.name.match(/-(\d+)\.md$/)?.[1] || 0);
      if (leftAttempt !== rightAttempt) return leftAttempt - rightAttempt;
      const leftType = left.name.startsWith("audience-review-") ? 0 : 1;
      const rightType = right.name.startsWith("audience-review-") ? 0 : 1;
      if (leftType !== rightType) return leftType - rightType;
    }
    return left.name.localeCompare(right.name, "pt-BR", { numeric: true, sensitivity: "base" });
  });
}

function renderArtifactsByPhase(run) {
  if (!run.artifacts?.length) {
    return '<p class="muted">Os artefatos aparecerão conforme o agente avançar.</p>';
  }

  const groups = stageOrder.map(() => []);
  run.artifacts.forEach((artifact) => {
    const phaseIndex = artifactPhaseIndex(artifact, run);
    groups[phaseIndex].push(artifact);
  });

  return groups.map((artifacts, phaseIndex) => {
    const orderedArtifacts = sortPhaseArtifacts(artifacts, phaseIndex);
    const countLabel = orderedArtifacts.length === 1 ? "1 arquivo" : `${orderedArtifacts.length} arquivos`;
    const files = orderedArtifacts.map((artifact) => `
      <details class="artifact-output" data-dom-key="artifact:${escapeHtml(artifact.name)}"><summary>${escapeHtml(artifact.name)}</summary>${renderMarkdown(artifact.content)}</details>`).join("");
    const contents = files || '<p class="artifact-phase-empty">Ainda não há artefatos nesta fase.</p>';
    return `<section class="artifact-phase" data-dom-key="phase:${phaseIndex}">
      <div class="artifact-phase-heading"><h3>${escapeHtml(stageOrder[phaseIndex])}</h3><span>${countLabel}</span></div>
      <div class="artifact-phase-files">${contents}</div>
    </section>`;
  }).join("");
}

function renderRun(run) {
  const panel = document.querySelector("#run-panel");
  const content = document.querySelector("#run-content");
  if (!run) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const { company, campaign } = selectedCase();
  const displayName = run.company_name || company?.name || run.company;
  const statusLabel = statusLabels[run.status] || run.status || "Estado desconhecido";
  const loopTitles = { audience: "Personas e master copy", rules: "Regras e copy de canal" };
  const iterationRows = ["audience", "rules"].map((key) => {
    const used = Number(run.iterations?.[key] || 0);
    const maximum = Number(run.limits?.[key] || 5);
    const percent = Math.min(100, Math.round((used / maximum) * 100));
    return `<div class="loop-row">
      <div><strong>${loopTitles[key]}</strong><small>${used} de ${maximum} tentativas · limite inclui a primeira</small></div>
      <div><div class="progress" aria-label="${percent}%"><span style="width:${percent}%"></span></div><div class="progress-note">${used}/${maximum}</div></div>
    </div>`;
  }).join("");
  const active = activeStepIndex(run.stage, run.status);
  const steps = stageOrder.map((step, index) => {
    const className = index < active ? "done" : index === active ? "current" : "";
    return `<div class="step ${className}">${escapeHtml(step)}</div>`;
  }).join("");
  const request = run.human_request;
  const evidenceItems = normalizeEvidence(request?.evidence);
  const evidenceMarkup = evidenceItems.length
    ? `<div class="human-evidence"><strong>Evidências:</strong><ul class="human-evidence-list">${evidenceItems.map((item) => `
        <li><span><strong>Resumo:</strong> ${escapeHtml(formatTimestampsInText(item.summary))}</span>
          ${item.source ? `<span><strong>Origem:</strong> ${escapeHtml(formatTimestampsInText(item.source))}</span>` : ""}
          ${item.detail ? `<span><strong>Detalhe:</strong> ${escapeHtml(formatTimestampsInText(item.detail))}</span>` : ""}
        </li>`).join("")}</ul></div>`
    : "";
  const attemptHistory = Array.isArray(request?.attempt_history) && request.attempt_history.length
    ? `<p><strong>Histórico das tentativas:</strong></p><ul class="human-attempt-history">${request.attempt_history.map((item) => `<li>${escapeHtml(formatTimestampsInText(typeof item === "string" ? item : item.summary || item.finding || JSON.stringify(item)))}</li>`).join("")}</ul>`
    : "";
  const humanPanel = run.status === "awaiting_human" && request ? `
    <section class="human-card" data-dom-key="human-card">
      <h3>${escapeHtml(formatTimestampsInText(request.title || "Intervenção humana necessária"))}</h3>
      <p><strong>O que bloqueia:</strong> ${escapeHtml(formatTimestampsInText(request.blocker || "O agente precisa de uma decisão para continuar."))}</p>
      ${evidenceMarkup}
      ${attemptHistory}
      <p><strong>Ação necessária:</strong> ${escapeHtml(formatTimestampsInText(request.action_required || "Registre a decisão ou correção necessária."))}</p>
      <form id="human-form" data-run-id="${escapeHtml(run.id)}">
        <label for="human-response">Decisão ou orientação para o agente</label>
        <textarea id="human-response" name="response" required placeholder="Registre a decisão que permitirá retomar o fluxo…"></textarea>
        <button class="button" type="submit">Registrar e retomar ciclo</button>
      </form>
    </section>` : "";
  const artifactSection = renderArtifactsByPhase(run);
  const events = (run.events || []).slice().reverse().map((event) => `
    <li class="${escapeHtml(event.type || "info")}" data-dom-key="event:${escapeHtml(event.at || "")}:${escapeHtml(event.type || "info")}:${escapeHtml(event.message || "")}"><span>${escapeHtml(formatTimestampsInText(event.message))}<time datetime="${escapeHtml(event.at || "")}">${escapeHtml(formatTimestamp(event.at || ""))}</time></span></li>`).join("");
  const logs = formatTimestampsInText(run.logs?.driver || "Aguardando a primeira saída do Ralph…", run.log_timezone);
  updateHtml(content, `
    <div class="run-title-row" data-dom-key="run-title">
      <div><p class="eyebrow">CASE EM EXECUÇÃO</p><h2>${escapeHtml(displayName)} · ${escapeHtml(run.campaign || campaign?.id || "")}</h2><p>ID ${escapeHtml(run.id)} · iniciado ${escapeHtml(formatTimestamp(run.created_at || ""))}</p></div>
      <span class="status-badge ${escapeHtml(run.status)}">${escapeHtml(statusLabel)}</span>
    </div>
    <p class="case-warning" data-dom-key="demo-disclaimer">Conteúdo fictício para demonstração. Empresas, produtos, ofertas, públicos e condições descritos neste exemplo não representam uma operação comercial real. Conteúdo gerado por IA, sujeito a revisão humana. Personas sintéticas não substituem pesquisa com clientes. A checagem das regras fornecidas não constitui validação jurídica ou regulatória.</p>
    <div class="stage-card" data-dom-key="stage-card"><div><span>Etapa atual</span><strong>${escapeHtml(run.stage || "Aguardando início")}</strong></div><div><span>Ciclo ativo</span><strong>${escapeHtml(loopTitles[run.active_loop] || "Preparação")}</strong></div></div>
    <div class="loop-counters" data-dom-key="loop-counters">${iterationRows}</div>
    <div class="step-track" data-dom-key="step-track" aria-label="Progresso do fluxo">${steps}</div>
    ${humanPanel}
    <div class="run-details" data-dom-key="run-details">
      <details class="detail-box" open><summary>Artefatos e evidências</summary><div class="detail-body">${artifactSection}</div></details>
      <div class="detail-box"><div class="detail-header">Histórico e atividade Ralph</div><div class="detail-body"><ul class="events">${events || '<li><span>Execução criada.</span></li>'}</ul><details style="margin-top:12px"><summary class="muted">Mostrar log do Ralph</summary><pre class="log-output">${escapeHtml(logs)}</pre></details></div></div>
    </div>`);
}

async function submitHumanDecision(event, runId) {
  event.preventDefault();
  const form = event.target.closest("#human-form");
  if (!form) return;
  const button = form.querySelector("button[type=submit]");
  const response = form.querySelector("#human-response").value.trim();
  button.disabled = true;
  button.textContent = "Retomando…";
  try {
    await request(`/api/runs/${encodeURIComponent(runId)}/human`, {
      method: "POST",
      body: JSON.stringify({ response }),
    });
    showNotice("Decisão registrada. O ciclo retomou com uma nova contagem.", "success");
    await selectRun(runId);
  } catch (error) {
    showNotice(error.message);
    button.disabled = false;
    button.textContent = "Registrar e retomar ciclo";
  }
}

function renderHistory() {
  const container = document.querySelector("#run-history");
  if (!state.runs.length) {
    updateHtml(container, '<p class="muted">Nenhuma execução iniciada nesta sessão.</p>');
    return;
  }
  updateHtml(container, state.runs.map((run) => `
    <button type="button" class="history-item ${run.id === state.activeRunId ? "selected" : ""}" data-dom-key="run:${escapeHtml(run.id)}" data-run="${escapeHtml(run.id)}">
      <strong>${escapeHtml(run.company_name || run.company)} · ${escapeHtml(run.campaign)}</strong>
      ${escapeHtml(statusLabels[run.status] || run.status)} · ${escapeHtml(formatTimestamp(run.created_at || ""))}
    </button>`).join(""));
}

async function refreshRuns() {
  const result = await request("/api/runs");
  state.runs = result.runs || [];
  renderHistory();
}

async function selectRun(runId) {
  try {
    state.activeRunId = runId;
    const [result, logs, artifacts] = await Promise.all([
      request(`/api/runs/${encodeURIComponent(runId)}`),
      request(`/api/runs/${encodeURIComponent(runId)}/logs`),
      request(`/api/runs/${encodeURIComponent(runId)}/artifacts`),
    ]);
    const run = result.run;
    const company = state.companies.find((item) => item.id === run.company);
    if (company && (state.selectedCompany !== company.id || state.selectedCampaign !== run.campaign)) {
      state.selectedCompany = company.id;
      state.selectedCampaign = run.campaign;
      renderCatalog();
      renderCase();
    }
    renderRun({ ...run, logs, artifacts: artifacts.artifacts || [] });
    await refreshRuns();
    window.clearTimeout(state.refreshTimer);
    if (result.run.status === "running" || result.run.status === "ready") {
      state.refreshTimer = window.setTimeout(refreshActiveRun, 2500);
    }
  } catch (error) {
    showNotice(error.message);
  }
}

async function refreshActiveRun() {
  if (!state.activeRunId) return;
  await selectRun(state.activeRunId);
}

async function initialize() {
  try {
    const [catalog, runs] = await Promise.all([request("/api/catalog"), request("/api/runs")]);
    state.companies = catalog.companies || [];
    state.runs = runs.runs || [];
    if (state.companies.length) {
      state.selectedCompany = state.companies[0].id;
      state.selectedCampaign = state.companies[0].campaigns[0]?.id ?? null;
    }
    renderCatalog();
    renderCase();
    renderHistory();
    const latest = state.runs[0];
    if (latest) {
      state.activeRunId = latest.id;
      await selectRun(latest.id);
    }
  } catch (error) {
    showNotice(`Não foi possível carregar a demo: ${error.message}`);
  }
}

document.querySelector("#refresh-button").addEventListener("click", async () => {
  try {
    await refreshRuns();
    if (state.activeRunId) await selectRun(state.activeRunId);
    showNotice("Estado atualizado.", "success");
  } catch (error) {
    showNotice(error.message);
  }
});

document.querySelector("#run-history").addEventListener("click", (event) => {
  const button = event.target.closest("[data-run]");
  if (button && event.currentTarget.contains(button)) selectRun(button.dataset.run);
});

document.querySelector("#run-content").addEventListener("submit", (event) => {
  const form = event.target.closest("#human-form");
  if (form) submitHumanDecision(event, form.dataset.runId);
});

initialize();
