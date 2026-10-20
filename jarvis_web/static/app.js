"use strict";

const byId = (id) => document.getElementById(id);
const ui = {
  dashboard: document.querySelector(".dashboard"),
  conversation: byId("conversation"),
  form: byId("chat-form"),
  input: byId("message-input"),
  send: document.querySelector(".send-button"),
  mic: byId("mic-toggle"),
  state: byId("assistant-state"),
  stateLight: byId("state-light"),
  coreMode: byId("core-mode"),
  voiceCaption: byId("voice-caption"),
  interim: byId("interim-line"),
  waveform: byId("waveform"),
  toast: byId("toast"),
};

const stateLabels = {
  ready: ["SISTEMI PRONTI", "STANDBY"],
  listening: ["IN ASCOLTO", "VOICE ACTIVE"],
  thinking: ["ANALISI IN CORSO", "PROCESSING"],
  speaking: ["IN RISPOSTA", "VOICE OUTPUT"],
  offline: ["CONNESSIONE ASSENTE", "OFFLINE"],
};

let recognition = null;
let listeningWanted = false;
let sending = false;
let audioContext = null;
let analyser = null;
let microphoneStream = null;
let soundEnabled = false;
let toastTimer = null;
let history = [];
let recognitionRestartTimer = null;
let animationFrame = 0;

function setState(nextState) {
  const [label, mode] = stateLabels[nextState] || stateLabels.ready;
  ui.state.textContent = label;
  ui.coreMode.textContent = mode;
  ui.voiceCaption.textContent = mode === "STANDBY" ? "IN ATTESA DI INPUT" : mode;
  ui.dashboard.classList.remove("busy", "speaking", "listening");
  if (nextState === "thinking") ui.dashboard.classList.add("busy");
  if (nextState === "speaking") ui.dashboard.classList.add("speaking");
  if (nextState === "listening") ui.dashboard.classList.add("listening");
  ui.stateLight.style.background = nextState === "offline" ? "var(--red)" : "var(--cyan)";
  if (nextState === "listening") drawWaveform("mic");
  else if (nextState === "speaking" || nextState === "thinking") drawWaveform("pulse");
  else drawWaveform("idle");
}

function formatTime(date = new Date()) {
  return date.toLocaleTimeString("it-IT", { hour12: false });
}

function typewriterLog(speaker, text, role) {
  const entry = document.createElement("article");
  entry.className = `log-entry ${role}-entry`;
  const meta = document.createElement("span");
  meta.className = "entry-meta";
  const name = document.createElement("b");
  name.textContent = speaker;
  const time = document.createElement("time");
  time.textContent = formatTime();
  meta.append(name, time);
  const paragraph = document.createElement("p");
  paragraph.className = "entry-text";
  entry.append(meta, paragraph);
  ui.conversation.append(entry);
  ui.conversation.scrollTop = ui.conversation.scrollHeight;

  let index = 0;
  const speed = text.length > 280 ? 3 : 1;
  function typeChunk() {
    paragraph.textContent += text.slice(index, index + speed);
    index += speed;
    ui.conversation.scrollTop = ui.conversation.scrollHeight;
    if (index < text.length) window.setTimeout(typeChunk, 12);
  }
  typeChunk();
}

function showToast(message) {
  ui.toast.textContent = message;
  ui.toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => ui.toast.classList.remove("visible"), 3800);
}

function ensureAudio() {
  if (!audioContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) audioContext = new AudioContextClass();
  }
  if (audioContext?.state === "suspended") audioContext.resume().catch(() => {});
}

function playTone(frequency = 660, duration = 0.08, type = "sine") {
  if (!soundEnabled || !audioContext) return;
  try {
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
    gain.gain.setValueAtTime(0.0001, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.045, audioContext.currentTime + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + duration);
    oscillator.connect(gain).connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + duration + 0.02);
  } catch {
    // Gli effetti sonori sono accessori e non devono interrompere la conversazione.
  }
}

async function attachMicrophoneVisualizer() {
  if (!navigator.mediaDevices?.getUserMedia) return;
  try {
    ensureAudio();
    microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (!audioContext) return;
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 128;
    audioContext.createMediaStreamSource(microphoneStream).connect(analyser);
  } catch (error) {
    console.info("Microfono audio per visualizzazione non disponibile", error);
  }
}

function stopMicrophoneVisualizer() {
  microphoneStream?.getTracks().forEach((track) => track.stop());
  microphoneStream = null;
  analyser = null;
}

function drawWaveform(mode = "idle") {
  cancelAnimationFrame(animationFrame);
  const canvas = ui.waveform;
  const context = canvas.getContext("2d");
  if (!context) return;
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * pixelRatio));
  canvas.height = Math.max(1, Math.floor(rect.height * pixelRatio));
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  const width = rect.width;
  const height = rect.height;
  const center = height / 2;
  const bars = 64;
  const frequencies = new Uint8Array(analyser?.frequencyBinCount || bars);
  let phase = 0;

  function render() {
    context.clearRect(0, 0, width, height);
    if (analyser && mode === "mic") analyser.getByteFrequencyData(frequencies);
    const step = width / bars;
    for (let index = 0; index < bars; index += 1) {
      const normalized = index / bars;
      const envelope = Math.pow(Math.sin(normalized * Math.PI), 0.65);
      let amplitude = mode === "idle" ? 1.5 : 4 + Math.abs(Math.sin(phase + index * 0.36)) * 14;
      if (mode === "mic" && analyser) {
        amplitude = Math.max(2, (frequencies[index] / 255) * 30 * envelope);
      } else if (mode === "pulse") {
        amplitude *= 0.52 + envelope * 0.8;
      } else {
        amplitude *= envelope;
      }
      const x = index * step + step * 0.22;
      const barWidth = Math.max(1, step * 0.48);
      const alpha = mode === "idle" ? 0.2 : 0.48 + envelope * 0.45;
      context.fillStyle = `rgba(91, 220, 238, ${alpha})`;
      context.fillRect(x, center - amplitude / 2, barWidth, amplitude);
    }
    phase += 0.12;
    if (mode !== "idle") animationFrame = requestAnimationFrame(render);
  }
  render();
}

function addHistory(role, content) {
  history.push({ role, content });
  history = history.slice(-12);
}

async function sendMessage(rawMessage, source = "text") {
  const message = rawMessage.trim();
  if (!message || sending) return;
  sending = true;
  ui.send.disabled = true;
  ui.interim.textContent = "";
  typewriterLog("Signore", message, "user");
  addHistory("user", message);
  ui.input.value = "";
  setState("thinking");
  playTone(520, 0.06);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history.slice(0, -1) }),
    });
    if (!response.ok) throw new Error(`Richiesta non riuscita (${response.status})`);
    const result = await response.json();
    const reply = typeof result.reply === "string" ? result.reply : "Risposta non disponibile.";
    addHistory("assistant", reply);
    typewriterLog("J.A.R.V.I.S.", reply, "assistant");
    byId("provider-label").textContent = `CANALE LOCALE / ${String(result.mode || "simulated").toUpperCase()}`;
    byId("model-diagnostic").textContent = String(result.mode || "simulated").toUpperCase();
    speak(reply);
  } catch (error) {
    setState("ready");
    showToast(`Collegamento al backend non disponibile: ${error.message}`);
    typewriterLog("Sistema", "Backend non raggiungibile. Avvia il server locale per continuare.", "system");
  } finally {
    sending = false;
    ui.send.disabled = false;
    if (source !== "voice" && listeningWanted) scheduleRecognitionRestart();
  }
}

function speak(text) {
  if (!("speechSynthesis" in window)) {
    setState(listeningWanted ? "listening" : "ready");
    if (listeningWanted) scheduleRecognitionRestart();
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "it-IT";
  utterance.pitch = Number(byId("pitch-range").value);
  utterance.rate = Number(byId("rate-range").value);
  utterance.onstart = () => {
    setState("speaking");
    playTone(820, 0.05);
  };
  utterance.onend = () => {
    setState(listeningWanted ? "listening" : "ready");
    if (listeningWanted) scheduleRecognitionRestart();
  };
  utterance.onerror = () => {
    setState(listeningWanted ? "listening" : "ready");
    if (listeningWanted) scheduleRecognitionRestart();
  };
  window.speechSynthesis.speak(utterance);
}

function setupRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    ui.mic.disabled = true;
    ui.mic.title = "Il browser non supporta la Web Speech API. Prova Chrome o Edge.";
    byId("speech-diagnostic").textContent = "NON SUPPORTATO";
    showToast("Riconoscimento vocale non supportato da questo browser. Puoi comunque scrivere.");
    return;
  }
  byId("speech-diagnostic").textContent = "DISPONIBILE";
  recognition = new Recognition();
  recognition.lang = "it-IT";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    if (!sending) setState("listening");
    ui.mic.classList.add("listening");
    ui.mic.setAttribute("aria-pressed", "true");
    ui.mic.querySelector("span").textContent = "INTERROMPI ASCOLTO";
    attachMicrophoneVisualizer();
  };
  recognition.onresult = (event) => {
    let interim = "";
    let finalText = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0].transcript;
      if (event.results[index].isFinal) finalText += transcript;
      else interim += transcript;
    }
    ui.interim.textContent = interim ? `› ${interim}` : "";
    if (finalText.trim()) {
      recognition.stop();
      stopMicrophoneVisualizer();
      ui.interim.textContent = "";
      sendMessage(finalText, "voice");
    }
  };
  recognition.onerror = (event) => {
    if (event.error !== "no-speech" && event.error !== "aborted") {
      showToast(`Errore microfono: ${event.error}`);
    }
  };
  recognition.onend = () => {
    stopMicrophoneVisualizer();
    if (!listeningWanted) {
      ui.mic.classList.remove("listening");
      ui.mic.setAttribute("aria-pressed", "false");
      ui.mic.querySelector("span").textContent = "AVVIA ASCOLTO";
      setState("ready");
    } else if (!sending && !window.speechSynthesis.speaking) {
      scheduleRecognitionRestart();
    }
  };
}

function startRecognition() {
  if (!recognition || !listeningWanted || sending) return;
  try {
    ensureAudio();
    recognition.start();
    playTone(720, 0.08);
  } catch (error) {
    if (error.name !== "InvalidStateError") showToast("Non riesco ad avviare il microfono.");
  }
}

function scheduleRecognitionRestart() {
  window.clearTimeout(recognitionRestartTimer);
  if (!listeningWanted || sending || window.speechSynthesis.speaking) return;
  recognitionRestartTimer = window.setTimeout(startRecognition, 450);
}

function stopRecognition() {
  listeningWanted = false;
  window.clearTimeout(recognitionRestartTimer);
  recognition?.stop();
  stopMicrophoneVisualizer();
  window.speechSynthesis?.cancel();
  ui.mic.classList.remove("listening");
  ui.mic.setAttribute("aria-pressed", "false");
  ui.mic.querySelector("span").textContent = "AVVIA ASCOLTO";
  setState("ready");
}

async function updateSystemStatus() {
  byId("connection-label").textContent = navigator.onLine ? "CONNESSIONE" : "OFFLINE";
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error("API offline");
    const data = await response.json();
    byId("api-diagnostic").textContent = "ONLINE";
    byId("api-diagnostic").style.color = "#65dcae";
    if (data.cpu_percent !== null) {
      byId("cpu-value").textContent = `${Math.round(data.cpu_percent)}%`;
      byId("cpu-meter").style.width = `${Math.min(100, Math.max(0, data.cpu_percent))}%`;
      byId("cpu-note").textContent = "CARICO SERVER";
    }
    if (data.memory_percent !== null) {
      byId("memory-value").textContent = `${Math.round(data.memory_percent)}%`;
      byId("memory-meter").style.width = `${Math.min(100, Math.max(0, data.memory_percent))}%`;
      byId("memory-used").textContent = data.memory_used_mb === null
        ? "RAM SERVER"
        : `${data.memory_used_mb} MB USATI`;
    }
    byId("model-diagnostic").textContent = String(data.provider).toUpperCase();
    byId("provider-label").textContent = `CANALE LOCALE / ${String(data.provider).toUpperCase()}`;
  } catch {
    byId("api-diagnostic").textContent = "OFFLINE";
    byId("api-diagnostic").style.color = "var(--red)";
  }
}

async function toggleCamera() {
  const video = byId("camera-video");
  if (video.srcObject) {
    video.srcObject.getTracks().forEach((track) => track.stop());
    video.srcObject = null;
    byId("camera-box").classList.remove("live");
    byId("camera-diagnostic").textContent = "STANDBY";
    byId("camera-toggle").classList.remove("active");
    byId("camera-toggle").querySelector("span").textContent = "ATTIVA WEBCAM";
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    showToast("Webcam disponibile solo su localhost/HTTPS e browser compatibili.");
    return;
  }
  try {
    video.srcObject = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    byId("camera-box").classList.add("live");
    byId("camera-diagnostic").textContent = "LIVE";
    byId("camera-toggle").classList.add("active");
    byId("camera-toggle").querySelector("span").textContent = "DISATTIVA WEBCAM";
    playTone(900, 0.07);
  } catch (error) {
    showToast(`Accesso webcam non riuscito: ${error.message}`);
  }
}

function initializeClock() {
  const clock = byId("clock");
  const tick = () => { clock.textContent = formatTime(); };
  tick();
  window.setInterval(tick, 1000);
}

ui.form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(ui.input.value);
});

ui.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    ui.form.requestSubmit();
  }
});

ui.mic.addEventListener("click", () => {
  if (listeningWanted) stopRecognition();
  else {
    listeningWanted = true;
    startRecognition();
  }
});

byId("camera-toggle").addEventListener("click", toggleCamera);
byId("clear-log").addEventListener("click", () => {
  ui.conversation.replaceChildren();
  history = [];
});
byId("sound-toggle").addEventListener("click", (event) => {
  soundEnabled = !soundEnabled;
  event.currentTarget.classList.toggle("active", soundEnabled);
  if (soundEnabled) {
    ensureAudio();
    playTone(680, 0.08);
  }
});
byId("pitch-range").addEventListener("input", (event) => {
  byId("pitch-value").value = Number(event.target.value).toFixed(1);
});
byId("rate-range").addEventListener("input", (event) => {
  byId("rate-value").value = Number(event.target.value).toFixed(2).replace(/0$/, "");
});
window.addEventListener("resize", () => drawWaveform("idle"));
window.addEventListener("online", updateSystemStatus);
window.addEventListener("offline", () => {
  byId("connection-label").textContent = "OFFLINE";
});
window.addEventListener("beforeunload", () => {
  stopMicrophoneVisualizer();
  byId("camera-video").srcObject?.getTracks().forEach((track) => track.stop());
  window.speechSynthesis?.cancel();
});

initializeClock();
setupRecognition();
drawWaveform("idle");
updateSystemStatus();
window.setInterval(updateSystemStatus, 5000);