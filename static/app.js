const bootstrapNode = document.getElementById("bootstrap-data");
const bootstrap = bootstrapNode ? JSON.parse(bootstrapNode.textContent) : {};

const messageList = document.getElementById("messageList");
const emptyState = document.getElementById("emptyState");
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("promptInput");
const submitButton = document.getElementById("submitButton");
const resetButton = document.getElementById("resetButton");
const suggestionList = document.getElementById("suggestionList");
const emptySuggestionList = document.getElementById("emptySuggestionList");

function setEmptyStateVisibility() {
  const hasMessages = messageList.children.length > 0;
  emptyState.hidden = hasMessages;
}

function createChip(question) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "chip";
  button.textContent = question;
  button.addEventListener("click", () => {
    promptInput.value = question;
    promptInput.focus();
  });
  return button;
}

function renderSuggestions() {
  const questions = bootstrap.suggestedQuestions || [];
  for (const question of questions) {
    suggestionList.appendChild(createChip(question));
    emptySuggestionList.appendChild(createChip(question));
  }
}

function scrollToBottom() {
  window.requestAnimationFrame(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });
}

function createMessageRow(role, content, options = {}) {
  const row = document.createElement("article");
  row.className = `message-row ${role}${options.pending ? " pending" : ""}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = content;
  row.appendChild(bubble);

  if (role === "assistant") {
    const meta = document.createElement("div");
    meta.className = "assistant-meta";

    if (options.model) {
      const modelBadge = document.createElement("span");
      modelBadge.className = "badge badge-outline";
      modelBadge.textContent = options.model;
      meta.appendChild(modelBadge);
    }

    if (options.retrievalQuery) {
      const retrievalBadge = document.createElement("span");
      retrievalBadge.className = "badge badge-outline";
      retrievalBadge.textContent = "Retrieval da rewrite";
      retrievalBadge.title = options.retrievalQuery;
      meta.appendChild(retrievalBadge);
    }

    if (meta.children.length > 0) {
      bubble.appendChild(meta);
    }

    if (Array.isArray(options.sources) && options.sources.length > 0) {
      const sourceGroup = document.createElement("div");
      sourceGroup.className = "source-group";

      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = `Nguon doi chieu (${options.sources.length})`;
      details.appendChild(summary);

      const sourceList = document.createElement("div");
      sourceList.className = "source-list";

      for (const source of options.sources) {
        const sourceCard = document.createElement("section");
        sourceCard.className = "source-card";

        const heading = document.createElement("h4");
        heading.textContent = source.title || "Nguon phap ly";
        sourceCard.appendChild(heading);

        const metaGrid = document.createElement("div");
        metaGrid.className = "source-meta";
        metaGrid.appendChild(createMetaItem("Official ID", source.official_id || "n/a"));
        metaGrid.appendChild(createMetaItem("Effective date", source.effective_date || "n/a"));
        metaGrid.appendChild(createMetaItem("Score", String(source.score ?? "0.000")));
        metaGrid.appendChild(createLinkMetaItem("URL", source.source_url));
        sourceCard.appendChild(metaGrid);

        const snippet = document.createElement("pre");
        snippet.className = "source-snippet";
        snippet.textContent = source.snippet || "";
        sourceCard.appendChild(snippet);

        sourceList.appendChild(sourceCard);
      }

      details.appendChild(sourceList);
      sourceGroup.appendChild(details);
      bubble.appendChild(sourceGroup);
    }
  }

  return row;
}

function createMetaItem(label, value) {
  const item = document.createElement("span");
  const strong = document.createElement("strong");
  strong.textContent = `${label}: `;
  item.appendChild(strong);
  item.appendChild(document.createTextNode(value));
  return item;
}

function createLinkMetaItem(label, url) {
  const item = document.createElement("span");
  const strong = document.createElement("strong");
  strong.textContent = `${label}: `;
  item.appendChild(strong);

  if (!url) {
    item.appendChild(document.createTextNode("n/a"));
    return item;
  }

  const link = document.createElement("a");
  link.className = "source-link";
  link.href = url;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = "Mo van ban";
  item.appendChild(link);
  return item;
}

function addMessage(role, content, options = {}) {
  const row = createMessageRow(role, content, options);
  messageList.appendChild(row);
  setEmptyStateVisibility();
  scrollToBottom();
  return row;
}

function setSubmittingState(isSubmitting) {
  submitButton.disabled = isSubmitting;
  promptInput.disabled = isSubmitting || !(bootstrap.status || {}).ready;
  submitButton.textContent = isSubmitting ? "Dang tra cuu..." : "Gui cau hoi";
}

async function sendMessage(message) {
  const pendingRow = addMessage("assistant", "Dang truy xuat van ban va tong hop cau tra loi...", { pending: true });

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const payload = await response.json();

    pendingRow.remove();

    if (!response.ok) {
      addMessage("assistant", payload.error || "Khong the xu ly cau hoi luc nay.");
      return;
    }

    addMessage("assistant", payload.answer, {
      model: payload.model,
      sources: payload.sources,
      retrievalQuery: payload.retrievalQuery && payload.retrievalQuery !== message ? payload.retrievalQuery : "",
    });
  } catch (error) {
    pendingRow.remove();
    addMessage("assistant", "Khong ket noi duoc toi server Railway. Hay thu lai sau.");
  }
}

function renderHistory() {
  const history = bootstrap.history || [];
  for (const turn of history) {
    addMessage(turn.role, turn.content);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = promptInput.value.trim();
  if (!message) {
    promptInput.focus();
    return;
  }

  addMessage("user", message);
  promptInput.value = "";
  setSubmittingState(true);
  await sendMessage(message);
  setSubmittingState(false);
  promptInput.focus();
});

promptInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

resetButton.addEventListener("click", async () => {
  resetButton.disabled = true;
  try {
    await fetch("/api/reset", { method: "POST" });
    messageList.innerHTML = "";
    setEmptyStateVisibility();
    promptInput.focus();
  } finally {
    resetButton.disabled = false;
  }
});

renderSuggestions();
renderHistory();
setSubmittingState(false);
setEmptyStateVisibility();
