const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const topKInput = document.querySelector("#top-k");
const submitButton = document.querySelector("#submit-button");
const statusPill = document.querySelector("#status-pill");
const refusalBadge = document.querySelector("#refusal-badge");
const answerEl = document.querySelector("#answer");
const citationsEl = document.querySelector("#citations");
const sourcesEl = document.querySelector("#sources");
const citationCountEl = document.querySelector("#citation-count");
const sourceCountEl = document.querySelector("#source-count");
const jsonOutputEl = document.querySelector("#json-output");

function setStatus(text, className = "") {
  statusPill.textContent = text;
  statusPill.className = `status-pill ${className}`.trim();
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Asking" : "Ask";
  setStatus(isLoading ? "Working" : "Ready", isLoading ? "loading" : "");
}

function clearNode(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function meta(label, value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const pill = document.createElement("span");
  pill.className = "meta-pill";
  pill.textContent = `${label}: ${value}`;
  return pill;
}

function renderMetadata(container, item) {
  [
    meta("doc", item.document),
    meta("page", item.page_number),
    meta("clause", item.clause),
    meta("tag", item.tag),
    meta("appendix", item.appendix),
  ]
    .filter(Boolean)
    .forEach((pill) => container.appendChild(pill));
}

function renderCitations(citations) {
  clearNode(citationsEl);
  citationCountEl.textContent = String(citations.length);

  if (!citations.length) {
    citationsEl.className = "list empty";
    citationsEl.textContent = "No citations.";
    return;
  }

  citationsEl.className = "list";
  citations.forEach((citation) => {
    const item = document.createElement("article");
    item.className = "item";

    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = citation.source_id;

    const metadata = document.createElement("div");
    metadata.className = "metadata";
    renderMetadata(metadata, citation);

    item.append(title, metadata);
    citationsEl.appendChild(item);
  });
}

function renderSources(sources) {
  clearNode(sourcesEl);
  sourceCountEl.textContent = String(sources.length);

  if (!sources.length) {
    sourcesEl.className = "list empty";
    sourcesEl.textContent = "No sources.";
    return;
  }

  sourcesEl.className = "list";
  sources.forEach((source) => {
    const item = document.createElement("article");
    item.className = "item";

    const title = document.createElement("div");
    title.className = "item-title";
    const titleText = document.createElement("span");
    titleText.textContent = source.source_id;
    const score = document.createElement("span");
    score.className = "muted";
    score.textContent = Number(source.score).toFixed(3);
    title.append(titleText, score);

    const metadata = document.createElement("div");
    metadata.className = "metadata";
    renderMetadata(metadata, source);

    const text = document.createElement("div");
    text.className = "source-text";
    text.textContent = source.text;

    item.append(title, metadata, text);
    sourcesEl.appendChild(item);
  });
}

function renderResponse(payload) {
  refusalBadge.classList.toggle("hidden", !payload.refused);
  answerEl.classList.remove("muted");
  answerEl.textContent = payload.answer || "No answer returned.";
  renderCitations(payload.citations || []);
  renderSources(payload.sources || []);
  jsonOutputEl.textContent = JSON.stringify(payload, null, 2);
}

function renderError(error) {
  refusalBadge.classList.add("hidden");
  answerEl.classList.remove("muted");
  answerEl.textContent = error;
  renderCitations([]);
  renderSources([]);
  jsonOutputEl.textContent = JSON.stringify({ error }, null, 2);
  setStatus("Error", "error");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  const topK = Number(topKInput.value || 5);

  if (!question) {
    renderError("Question is required.");
    return;
  }

  setLoading(true);
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Request failed.");
    }

    renderResponse(payload);
    setStatus(payload.refused ? "Refused" : "Answered", payload.refused ? "error" : "");
  } catch (error) {
    renderError(error.message || "Request failed.");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Ask";
  }
});
