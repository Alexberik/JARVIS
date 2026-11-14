const $ = (selector) => document.querySelector(selector);
const activity = [];
let recognition = null;
let listening = false;
let handsFreeEnabled = false;
let processingVoice = false;
let commandArmedUntil = 0;
let voiceRestartTimer = null;

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
  $("#activityCount").textContent = activity.length + " events";
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

function speak(text, onDone) {
  if (!$("#speakReplies").checked || !("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(String(text).slice(0, 1800));
  utterance.lang = "ru-RU";
  utterance.rate = 1;
  const voice = window.speechSynthesis.getVoices().find(v => v.lang.toLowerCase().startsWith("ru"));
  if (voice) utterance.voice = voice;
  utterance.onend = () => { if (onDone) onDone(); };
  utterance.onerror = () => { if (onDone) onDone(); };
  window.speechSynthesis.speak(utterance);
  return true;
}

function resumeVoice() {
  processingVoice = false;
  if (!handsFreeEnabled || !SpeechRecognition) return;
  clearTimeout(voiceRestartTimer);
  voiceRestartTimer = setTimeout(startRecognition, 650);
}

async function sendCommand(message, source = "text") {
  if (!message.trim()) return;
  const fromVoice = source === "voice";
  if (fromVoice) processingVoice = true;
  addMessage(message, "user");
  logActivity("COMMAND RECEIVED · " + message.slice(0, 90));
  setCore("working", "ANALYZING REQUEST");
  try {
    const result = await api("/api/chat", {method:"POST", body:JSON.stringify({message})});
    const reply = result.reply || result.message || JSON.stringify(result);
    addMessage(reply);
    logActivity("COMMAND PROCESSED" + (result.tool ? " · " + result.tool : ""));
    const voiceStarted = speak(reply, fromVoice ? resumeVoice : undefined);
    if (fromVoice && !voiceStarted) resumeVoice();
    setCore("standby", "AWAITING YOUR COMMAND");
  } catch (error) {
    addMessage("System error: " + error.message);
    logActivity("REQUEST FAILED · " + error.message, "error");
    setCore("error", "CHECK ACTIVITY LOG");
    if (fromVoice) resumeVoice();
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

function startRecognition() {
  if (!SpeechRecognition || !handsFreeEnabled || listening || processingVoice) return;
  recognition = new SpeechRecognition();
  recognition.lang = "ru-RU";
  recognition.interimResults = false;
  recognition.continuous = true;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    listening = true;
    $("#voice").classList.add("recording");
    $("#recognitionStatus").textContent = "WAITING FOR «ДЖАРВИС»";
    setCore("listening", "WAKE WORD ACTIVE");
  };
  recognition.onresult = event => {
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (!event.results[i].isFinal) continue;
      const heard = event.results[i][0].transcript.trim();
      if (!heard) continue;
      const wake = heard.match(/(?:джарвис|jarvis)[,\\s.!?—-]*(.*)/i);
      if (wake) {
        const command = (wake[1] || "").trim();
        commandArmedUntil = command ? 0 : Date.now() + 12000;
        processingVoice = true;
        recognition.stop();
        if (command) {
          sendCommand(command, "voice");
        } else {
          logActivity("WAKE WORD DETECTED");
          speak("Слушаю.", resumeVoice);
        }
        return;
      }
      if (Date.now() < commandArmedUntil) {
        commandArmedUntil = 0;
        processingVoice = true;
        recognition.stop();
        sendCommand(heard, "voice");
        return;
      }
    }
  };
  recognition.onerror = event => {
    if (!["no-speech", "aborted"].includes(event.error)) {
      $("#recognitionStatus").textContent = "MIC ERROR · " + event.error.toUpperCase();
      logActivity("VOICE INPUT ERROR · " + event.error, "error");
    }
  };
  recognition.onend = () => {
    listening = false;
    $("#voice").classList.toggle("recording", handsFreeEnabled);
    if (!handsFreeEnabled) {
      $("#recognitionStatus").textContent = "VOICE OFF";
      setCore("standby", "AWAITING YOUR COMMAND");
    } else if (!processingVoice) {
      $("#recognitionStatus").textContent = "RECONNECTING MICROPHONE";
      clearTimeout(voiceRestartTimer);
      voiceRestartTimer = setTimeout(startRecognition, 900);
    }
  };
  try {
    recognition.start();
  } catch (error) {
    logActivity("MIC START FAILED · " + error.message, "error");
    listening = false;
    clearTimeout(voiceRestartTimer);
    voiceRestartTimer = setTimeout(startRecognition, 1500);
  }
}

if (!SpeechRecognition) {
  $("#voice").disabled = true;
  $("#voice").title = "Speech recognition is not supported in this browser";
  $("#recognitionStatus").textContent = "VOICE INPUT UNAVAILABLE";
} else {
  $("#recognitionStatus").textContent = "VOICE OFF · CLICK ONCE TO ACTIVATE";
}
$("#voice").addEventListener("click", () => {
  if (!SpeechRecognition) {
    addMessage("Для голосового режима открой JARVIS в актуальном Chrome или Edge.");
    return;
  }
  if (handsFreeEnabled) {
    handsFreeEnabled = false;
    processingVoice = false;
    commandArmedUntil = 0;
    clearTimeout(voiceRestartTimer);
    if (recognition && listening) recognition.stop();
    if (canSpeak) window.speechSynthesis.cancel();
    $("#voice").classList.remove("recording");
    $("#recognitionStatus").textContent = "VOICE OFF";
    logActivity("HANDS-FREE VOICE DISABLED");
    return;
  }
  handsFreeEnabled = true;
  commandArmedUntil = 0;
  $("#recognitionStatus").textContent = "REQUESTING MICROPHONE";
  logActivity("HANDS-FREE VOICE ACTIVATION REQUESTED");
  startRecognition();
});

$("#speakReplies").addEventListener("change", () => {
  if (!$("#speakReplies").checked && canSpeak) window.speechSynthesis.cancel();
});
$("#speakRepliesAlt").addEventListener("change", event => { $("#speakReplies").checked = event.target.checked; });

async function refreshAudit() {
  try {
    const events = await api("/api/audit");
    activity.length = 0;
    for (const event of [...events].reverse()) {
      const stamp = event.created_at ? new Date(event.created_at).toLocaleTimeString("ru-RU", {hour12:false}) : "--:--:--";
      activity.unshift({stamp, message: [event.event, event.details].filter(Boolean).join(" · "), kind:"info"});
    }
    activity.splice(12);
    const target = $("#activityLog");
    target.replaceChildren();
    for (const item of activity) {
      const line = document.createElement("p");
      const mark = document.createElement("span");
      mark.className = "terminal-mark";
      mark.textContent = "$";
      line.append(mark, document.createTextNode(item.stamp + " " + item.message));
      target.append(line);
    }
    $("#activityCount").textContent = activity.length + " events";
  } catch (error) {
    logActivity("AUDIT HISTORY UNAVAILABLE · " + error.message, "error");
  }
}

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
    $("#vaultMetric").textContent = connected ? "ONLINE" : "OFFLINE";
    $("#vaultBar").style.width = connected ? "100%" : "0%";
    $("#obsidianMode").textContent = connected ? (status.mode === "filesystem" ? "FILESYSTEM · ONLINE" : "REST API · ONLINE") : "NOT CONNECTED";
    $("#obsidianMode").style.color = connected ? "var(--cyan)" : "var(--gold)";
    logActivity(connected ? "OBSIDIAN VAULT CONNECTED" : "OBSIDIAN VAULT NOT CONNECTED");
    $("#inboxState").textContent = "NOT CONNECTED";
    $("#inboxSummary").textContent = "Gmail is not connected. Inbox preview is unavailable until authorization.";
  } catch {
    $("#diskMetric").textContent = "UNKNOWN";
    $("#diskBar").style.width = "0%";
  }
  const voiceReady = Boolean(SpeechRecognition);
  $("#voiceMetric").textContent = voiceReady ? "READY" : "LIMITED";
  $("#voiceBar").style.width = voiceReady ? "100%" : "35%";
  $("#inboxState").textContent = "NOT CONNECTED";
  $("#inboxSummary").textContent = "Gmail is not connected. Inbox preview is unavailable until authorization.";
  $("#githubSummary").textContent = "GitHub connector is not connected. Repository activity is not being fetched.";
}
refreshStatus();
refreshAudit();
refreshTasks().catch(error => logActivity("TASKS UNAVAILABLE · " + error.message, "error"));
logActivity(canSpeak ? "BROWSER SPEECH OUTPUT AVAILABLE" : "BROWSER SPEECH OUTPUT UNAVAILABLE");
