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

function speak(text) {
  if (!$("#speakReplies").checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(String(text).slice(0, 1800));
  utterance.lang = "ru-RU";
  utterance.rate = 1;
  const voices = window.speechSynthesis.getVoices();
  const russian = voices.find((voice) => voice.lang.toLowerCase().startsWith("ru"));
  if (russian) utterance.voice = russian;
  window.speechSynthesis.speak(utterance);
}

async function sendCommand(message, source = "text") {
  if (!message.trim()) return;
  bubble(message, "user");
  $("#assistantMode").textContent = source === "voice" ? "Обрабатываю голосовую команду" : "Обрабатываю команду";
  $("#reactor").classList.add("working");
  try {
    const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ message }) });
    const reply = result.reply || JSON.stringify(result);
    bubble(reply);
    speak(reply);
    $("#assistantMode").textContent = "JARVIS готов";
  } catch (error) {
    bubble("Ошибка: " + error.message);
    $("#assistantMode").textContent = "Ошибка выполнения";
  } finally {
    $("#reactor").classList.remove("working");
  }
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
  await sendCommand(message, "text");
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const canSpeak = "speechSynthesis" in window;
$("#voiceState").textContent = SpeechRecognition ? (canSpeak ? "Ввод и озвучивание доступны" : "Доступен ввод") : (canSpeak ? "Доступно озвучивание" : "Недоступно");
$("#voiceConnection").textContent = SpeechRecognition && canSpeak ? "Браузер поддерживает" : "Ограниченная поддержка";
$("#voiceDot").classList.toggle("online", Boolean(SpeechRecognition || canSpeak));
if (!SpeechRecognition) {
  $("#voice").disabled = true;
  $("#voiceHint").textContent = "Для голосового ввода откройте JARVIS в Chrome или Edge";
}

let recognition = null;
let listening = false;

$("#voice").addEventListener("click", () => {
  if (!SpeechRecognition) {
    bubble("Голосовой ввод не поддерживается. Используйте актуальный Chrome или Edge.");
    return;
  }
  if (listening && recognition) {
    recognition.stop();
    return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = "ru-RU";
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.onstart = () => {
    listening = true;
    $("#voice").classList.add("recording");
    $("#reactor").classList.add("listening");
    $("#assistantMode").textContent = "Слушаю вас";
    $("#voiceHint").textContent = "Говорите — команда отправится после распознавания";
    $("#recognitionStatus").textContent = "Микрофон активен";
  };
  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) finalText += event.results[i][0].transcript;
      else interimText += event.results[i][0].transcript;
    }
    $("#message").value = finalText || interimText;
    if (finalText.trim()) {
      $("#message").value = "";
      recognition.stop();
      sendCommand(finalText.trim(), "voice");
    }
  };
  recognition.onerror = (event) => {
    $("#recognitionStatus").textContent = "Ошибка микрофона: " + event.error;
    bubble("Ошибка голосового ввода: " + event.error);
  };
  recognition.onend = () => {
    listening = false;
    $("#voice").classList.remove("recording");
    $("#reactor").classList.remove("listening");
    $("#assistantMode").textContent = "JARVIS готов";
    $("#voiceHint").textContent = "Нажмите микрофон или напишите команду";
    if ($("#recognitionStatus").textContent === "Микрофон активен") $("#recognitionStatus").textContent = "Голос: ожидание";
  };
  try { recognition.start(); }
  catch (error) { bubble("Не удалось включить микрофон: " + error.message); }
});

$("#speakReplies").addEventListener("change", () => {
  if (!$("#speakReplies").checked && canSpeak) window.speechSynthesis.cancel();
});

async function refreshStatus() {
  try {
    const health = await api("/api/health");
    $("#health").textContent = "CORE ONLINE · " + health.version;
    $("#coreState").textContent = "Работает · " + health.version;
  } catch {
    $("#health").textContent = "CORE OFFLINE";
    $("#coreState").textContent = "Нет соединения";
  }
  try {
    const status = await api("/api/obsidian/status");
    $("#obsidian").textContent = status.ok ? "Подключён" : (status.configured ? "Ошибка" : "Не настроен");
    $("#obsidianMode").textContent = status.ok ? (status.mode === "filesystem" ? "Файловый доступ" : "REST API") : "Нет соединения";
    $("#obsidian").title = status.error || status.vault || "";
    $("#obsidianDot").classList.toggle("online", Boolean(status.ok));
  } catch {
    $("#obsidian").textContent = "Недоступен";
    $("#obsidianMode").textContent = "Недоступен";
  }
}

refreshTasks().catch((error) => showPanelError("#taskslist", error.message));
refreshMemory().catch((error) => showPanelError("#memorylist", error.message));
refreshStatus();
