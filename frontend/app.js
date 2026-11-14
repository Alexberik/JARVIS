const $ = (selector) => document.querySelector(selector);
const activity = [];
let recognition = null;
let listening = false;

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

function logActivity(message, kind = "info") {
  const stamp = new Date().toLocaleTimeString("ru-RU", {hour12:false});
  activity.unshift({stamp, message, kind});
  activity.splice(12);
  const target = $("#activityLog");
  target.replaceChildren();
  for (const item of activity) {
    const line = document.createElement("p");
    const mark = document.createElement("span");
    mark.className = "terminal-mark";
    mark.textContent = item.kind === "error" ? "!" : "$";
    line.append(mark, document.createTextNode(item.stamp + " " + item.message));
    target.append(line);
  }
  $("#activityCount").textContent = activity.length + " live";
}

function addMessage(text, kind = "jarvis") {
  const line = document.createElement("div");
  line.className = "message " + kind;
  const mark = document.createElement("span");
  mark.className = "prompt-mark";
  mark.textContent = kind === "user" ? "›" : "»";
  const content = document.createElement("span");
  content.textContent = String(text);
  line.append(mark, content);
  $("#chatlog").append(line);
  $("#chatlog").scrollTop = $("#chatlog").scrollHeight;
}

function setCore(mode, caption) {
  $("#coreStage").classList.remove("listening", "working", "error");
  if (mode !== "standby") $("#coreStage").classList.add(mode);
  $("#coreLabel").textContent = mode === "listening" ? "LISTENING" : mode === "working" ? "PROCESSING" : mode === "error" ? "SYSTEM ERROR" : "STANDBY";
  $("#coreCaption").textContent = caption || (mode === "standby" ? "AWAITING YOUR COMMAND" : "JARVIS IS ACTIVE");
}

function speak(text) {
  if (!$("#speakReplies").checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(String(text).slice(0, 1800));
  utterance.lang = "ru-RU";
  utterance.rate = 1;
  const voice = window.speechSynthesis.getVoices().find(v => v.lang.toLowerCase().startsWith("ru"));
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

async function sendCommand(message, source = "text") {
  if (!message.trim()) return;
  addMessage(message, "user");
  logActivity("COMMAND RECEIVED · " + message.slice(0, 90));
  setCore("working", "ANALYZING REQUEST");
  try {
    const result = await api("/api/chat", {method:"POST", body:JSON.stringify({message})});
    const reply = result.reply || result.message || JSON.stringify(result);
    addMessage(reply);
    logActivity("COMMAND PROCESSED");
    speak(reply);
    setCore("standby", "AWAITING YOUR COMMAND");
  } catch (error) {
    addMessage("System error: " + error.message);
    logActivity("REQUEST FAILED · " + error.message, "error");
    setCore("error", "CHECK ACTIVITY LOG");
  }
}

function updateClock() {
  const now = new Date();
  $("#clock").textContent = now.toLocaleTimeString("en-GB", {hour12:false});
  $("#date").textContent = now.toLocaleDateString("en-GB", {weekday:"short",day:"2-digit",month:"short",year:"numeric"}).toUpperCase();
}
updateClock();
setInterval(updateClock, 1000);

function openModule(name) {
  const names = {tasks:"TASK MANAGER",memory:"LONG-TERM MEMORY",connections:"INTEGRATIONS",settings:"SYSTEM SETTINGS"};
  const drawer = $("#moduleDrawer");
  drawer.hidden = false;
  $("#drawerTitle").textContent = names[name] || "SYSTEM MODULE";
  document.querySelectorAll(".drawer-module").forEach(el => el.hidden = true);
  const module = $("#" + name + "Module");
  if (module) module.hidden = false;
  document.querySelectorAll("[data-module]").forEach(el => el.classList.toggle("active", el.dataset.module === name));
  if (name === "tasks") refreshTasks().catch(e => logActivity("TASK LOAD FAILED · " + e.message, "error"));
  if (name === "memory") refreshMemory().catch(e => logActivity("MEMORY LOAD FAILED · " + e.message, "error"));
}
document.querySelectorAll("[data-module]").forEach(button => button.addEventListener("click", () => openModule(button.dataset.module)));
$("#closeDrawer").addEventListener("click", () => { $("#moduleDrawer").hidden = true; document.querySelectorAll("[data-module]").forEach(el => el.classList.remove("active")); });

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
    toggle.textContent = task.done ? "UNDO" : "DONE";
    toggle.addEventListener("click", async () => {
      try { await api("/api/tasks/" + encodeURIComponent(task.id), {method:"PATCH"}); await refreshTasks(); logActivity("TASK UPDATED"); }
      catch (error) { logActivity("TASK UPDATE FAILED · " + error.message, "error"); }
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.title = "Delete task";
    remove.addEventListener("click", async () => {
      if (!window.confirm("Delete this task?")) return;
      try { await api("/api/tasks/" + encodeURIComponent(task.id), {method:"DELETE"}); await refreshTasks(); logActivity("TASK DELETED"); }
      catch (error) { logActivity("TASK DELETE FAILED · " + error.message, "error"); }
    });
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
    meta.textContent = [memory.tags, memory.created_at ? new Date(memory.created_at).toLocaleString() : ""].filter(Boolean).join(" · ");
    item.append(meta);
    list.append(item);
  }
}

$("#taskform").addEventListener("submit", async event => {
  event.preventDefault();
  const input = $("#tasktitle");
  const title = input.value.trim();
  if (!title) return;
  try {
    await api("/api/tasks", {method:"POST",body:JSON.stringify({title})});
    input.value = "";
    await refreshTasks();
    logActivity("TASK SAVED");
  } catch (error) { logActivity("TASK SAVE FAILED · " + error.message, "error"); }
});

$("#memoryform").addEventListener("submit", async event => {
  event.preventDefault();
  const input = $("#memorytext");
  const content = input.value.trim();
  if (!content) return;
  try {
    await api("/api/memory", {method:"POST",body:JSON.stringify({content,tags:$("#memorytags").value.trim()})});
    input.value = "";
    $("#memorytags").value = "";
    await refreshMemory();
    logActivity("MEMORY ENTRY SAVED");
  } catch (error) { logActivity("MEMORY SAVE FAILED · " + error.message, "error"); }
});

$("#chatform").addEventListener("submit", async event => {
  event.preventDefault();
  const input = $("#message");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  await sendCommand(message);
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const canSpeak = "speechSynthesis" in window;
if (!SpeechRecognition) {
  $("#voice").disabled = true;
  $("#voice").title = "Speech recognition is not supported in this browser";
  $("#recognitionStatus").textContent = "VOICE INPUT UNAVAILABLE";
}
$("#voice").addEventListener("click", () => {
  if (!SpeechRecognition) {
    addMessage("Voice input is not supported in this browser. Please use a current version of Chrome or Edge.");
    return;
  }
  if (listening && recognition) { recognition.stop(); return; }
  recognition = new SpeechRecognition();
  recognition.lang = "ru-RU";
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.onstart = () => {
    listening = true;
    $("#voice").classList.add("recording");
    $("#recognitionStatus").textContent = "MIC ACTIVE";
    setCore("listening", "SPEAK NOW");
    logActivity("MICROPHONE ACTIVATED");
  };
  recognition.onresult = event => {
    let finalText = "";
    let interimText = "";
    for (let i=event.resultIndex;i<event.results.length;i++) {
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
  recognition.onerror = event => {
    $("#recognitionStatus").textContent = "MIC ERROR · " + event.error.toUpperCase();
    logActivity("VOICE INPUT ERROR · " + event.error, "error");
  };
  recognition.onend = () => {
    listening = false;
    $("#voice").classList.remove("recording");
    $("#recognitionStatus").textContent = "MIC STANDBY";
    if ($("#coreStage").classList.contains("listening")) setCore("standby");
  };
  try { recognition.start(); } catch (error) { logActivity("MIC START FAILED · " + error.message, "error"); }
});

$("#speakReplies").addEventListener("change", () => {
  if (!$("#speakReplies").checked && canSpeak) window.speechSynthesis.cancel();
});
$("#speakRepliesAlt").addEventListener("change", event => { $("#speakReplies").checked = event.target.checked; });

async function refreshStatus() {
  try {
    const health = await api("/api/health");
    $("#topStatus").textContent = "CORE ONLINE";
    $("#systemState").textContent = "ONLINE";
    $("#coreMetric").textContent = "ONLINE";
    $("#coreBar").style.width = "100%";
    logActivity("JARVIS CORE ONLINE · v" + health.version);
  } catch {
    $("#topStatus").textContent = "CORE OFFLINE";
    $("#systemState").textContent = "OFFLINE";
    $("#coreMetric").textContent = "OFFLINE";
    $("#coreBar").style.width = "0%";
  }
  try {
    const status = await api("/api/obsidian/status");
    const connected = Boolean(status.ok);
    $("#diskMetric").textContent = connected ? "ONLINE" : "OFFLINE";
    $("#diskBar").style.width = connected ? "100%" : "0%";
    $("#obsidianMode").textContent = connected ? (status.mode === "filesystem" ? "FILESYSTEM · ONLINE" : "REST API · ONLINE") : "NOT CONNECTED";
    $("#obsidianMode").style.color = connected ? "var(--cyan)" : "var(--gold)";
    $("#inboxSummary").innerHTML = connected ? "Local vault connected.<br>Notes and knowledge access ready." : "Obsidian vault is not connected.<br>Check local configuration.";
    $("#inboxState").textContent = connected ? "VAULT ONLINE" : "NOT CONNECTED";
    logActivity(connected ? "OBSIDIAN VAULT CONNECTED" : "OBSIDIAN VAULT NOT CONNECTED");
  } catch {
    $("#diskMetric").textContent = "UNKNOWN";
    $("#diskBar").style.width = "0%";
  }
  const voiceReady = Boolean(SpeechRecognition);
  $("#memoryMetric").textContent = voiceReady ? "READY" : "LIMITED";
  $("#memoryBar").style.width = voiceReady ? "100%" : "35%";
  $("#githubSummary").textContent = "GitHub connector is not connected. Repository activity is not being fetched.";
}
refreshStatus();
refreshTasks().catch(error => logActivity("TASKS UNAVAILABLE · " + error.message, "error"));
logActivity(canSpeak ? "BROWSER SPEECH OUTPUT AVAILABLE" : "BROWSER SPEECH OUTPUT UNAVAILABLE");
