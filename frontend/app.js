const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  if (!response.ok) {
    let message = await response.text();
    try { message = JSON.parse(message).error || message; } catch {}
    throw new Error(message.slice(0, 300) || response.statusText);
  }
  if (response.status === 204) return null;
  return response.json();
}

function bubble(text, kind = "jarvis") {
  const element = document.createElement("div");
  element.className = "bubble " + kind;
  element.textContent = String(text);
  $("#chatlog").append(element);
  $("#chatlog").scrollTop = $("#chatlog").scrollHeight;
}

function showPanelError(selector, message) {
  const target = $(selector);
  if (target) target.textContent = "Ошибка: " + message;
}

async function refreshTasks() {
  const tasks = await api("/api/tasks");
  $("#taskcount").textContent = tasks.length;
  const list = $("#taskslist");
  list.replaceChildren();
  for (const task of tasks) {
    const item = document.createElement("li");
    if (task.done) item.classList.add("done");
    const title = document.createElement("span");
    title.textContent = task.title;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = task.done ? "↶" : "✓";
    toggle.title = task.done ? "Вернуть в активные" : "Выполнено";
    toggle.onclick = async () => {
      try { await api("/api/tasks/" + encodeURIComponent(task.id), { method: "PATCH" }); await refreshTasks(); }
      catch (error) { bubble("Не удалось обновить задачу: " + error.message); }
    };
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.title = "Удалить задачу";
    remove.onclick = async () => {
      if (!window.confirm("Удалить эту задачу?")) return;
      try { await api("/api/tasks/" + encodeURIComponent(task.id), { method: "DELETE" }); await refreshTasks(); }
      catch (error) { bubble("Не удалось удалить задачу: " + error.message); }
    };
    item.append(title, toggle, remove);
    list.append(item);
  }
}

async function refreshMemory() {
  const memories = await api("/api/memory");
  const list = $("#memorylist");
  list.replaceChildren();
  for (const memory of memories) {
    const item = document.createElement("div");
    item.className = "memory-item";
    item.textContent = memory.content;
    const meta = document.createElement("small");
    const date = memory.created_at ? new Date(memory.created_at).toLocaleString() : "";
    meta.textContent = [memory.tags, date].filter(Boolean).join(" · ");
    item.append(meta);
    list.append(item);
  }
}

$("#taskform").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#tasktitle");
  const title = input.value.trim();
  if (!title) return;
  try {
    await api("/api/tasks", { method: "POST", body: JSON.stringify({ title }) });
    input.value = "";
    await refreshTasks();
  } catch (error) { bubble("Не удалось сохранить задачу: " + error.message); }
});

$("#memoryform").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#memorytext");
  const content = input.value.trim();
  if (!content) return;
  try {
    await api("/api/memory", {
      method: "POST",
      body: JSON.stringify({ content, tags: $("#memorytags").value.trim() })
    });
    input.value = "";
    await refreshMemory();
  } catch (error) { bubble("Не удалось сохранить память: " + error.message); }
});

$("#chatform").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#message");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  bubble(message, "user");
  try {
    const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ message }) });
    bubble(result.reply || JSON.stringify(result));
  } catch (error) { bubble("Ошибка: " + error.message); }
});

async function refreshStatus() {
  try {
    const health = await api("/api/health");
    $("#health").textContent = "CORE ONLINE · " + health.version;
  } catch {
    $("#health").textContent = "CORE OFFLINE";
  }
  try {
    const status = await api("/api/obsidian/status");
    $("#obsidian").textContent = status.ok ? "Подключён" :
      (status.configured ? "Ошибка соединения" : "Не настроен");
    $("#obsidian").title = status.error || "";
  } catch {
    $("#obsidian").textContent = "Недоступен";
  }
}

$("#voice").addEventListener("click", () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    bubble("Голосовой ввод не поддерживается этим браузером. Используйте Chrome или Edge.");
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = "ru-RU";
  recognition.interimResults = false;
  recognition.onresult = (event) => { $("#message").value = event.results[0][0].transcript; };
  recognition.onerror = (event) => bubble("Ошибка голосового ввода: " + event.error);
  recognition.start();
});

refreshTasks().catch((error) => showPanelError("#taskslist", error.message));
refreshMemory().catch((error) => showPanelError("#memorylist", error.message));
refreshStatus();
