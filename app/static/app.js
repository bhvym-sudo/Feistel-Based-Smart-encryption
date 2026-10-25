const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const bits = (value, length = 8) => Number(value).toString(2).padStart(length, "0");

let currentTab = "simulation";
let simulationSequence = 1;
let automationRunning = false;
let latestAutomationId = null;
let polling = false;

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error("Request failed");
  return response.json();
}

function toast(text) {
  const box = $("#toast");
  box.textContent = text;
  box.classList.add("show");
  setTimeout(() => box.classList.remove("show"), 1800);
}

function getSettings() {
  const rawKey = $("#keyInput").value.trim();
  if (!/^[0-9a-f]{1,4}$/i.test(rawKey)) throw new Error("Invalid key");
  return {
    key: parseInt(rawKey, 16),
    rounds: Number($("#roundsInput").value),
  };
}

function reset(roundCount) {
  $("#meterStatus").className = "";
  $("#meterStatus").textContent = "Loading";
  $("#roundStatus").className = "";
  $("#roundStatus").textContent = "Waiting";
  $("#gatewayStatus").className = "";
  $("#gatewayStatus").textContent = "Waiting";
  $("#cipherBits").textContent = "--------";
  $("#cipherValue").textContent = "—";
  $("#packetCipher").textContent = "—";
  $("#packetTag").textContent = "—";
  $("#integrityValue").textContent = "—";
  $("#sequenceCheck").textContent = "—";
  $("#recoveredValue").textContent = "—";
  $("#result").className = "result";
  $("#result").innerHTML = "<span>○</span><strong>Waiting</strong>";
  $("#rounds").innerHTML = Array.from({ length: roundCount }, (_, index) => `<div class="round" data-round="${index + 1}"><span>R${index + 1}</span><strong>----</strong></div>`).join("");
}

function renderMeter(readings) {
  const reading = readings.at(-1);
  $("#usageValue").textContent = Number(reading.usage_kwh).toFixed(3);
  $("#powerValue").textContent = `${Number(reading.power_kw).toFixed(2)} kW`;
  $("#voltageValue").textContent = `${Number(reading.voltage).toFixed(1)} V`;
  $("#currentValue").textContent = `${Number(reading.current).toFixed(2)} A`;
  $("#sequenceValue").textContent = `#${reading.sequence}`;
  $("#plainBits").textContent = reading.plaintext_bits || bits(reading.quantized_value);
  $("#plainDecimal").textContent = `decimal ${reading.quantized_value}`;
  $("#leftBits").textContent = bits(reading.quantized_value).slice(0, 4);
  $("#rightBits").textContent = bits(reading.quantized_value).slice(4);
  $("#readingRows").innerHTML = readings.slice(-6).map((item, index, visible) => `<div class="data-row ${index === visible.length - 1 ? "latest" : ""}"><span>${new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span><span>${Number(item.power_kw).toFixed(2)} kW</span><span>${Number(item.usage_kwh).toFixed(3)}</span></div>`).join("");
  $("#meterStatus").className = "active";
  $("#meterStatus").textContent = "Ready";
  return reading;
}

async function animate(trace, roundCount) {
  $("#roundStatus").className = "active";
  for (const row of trace) {
    renderRound(row, roundCount);
    await wait(430);
  }
  finishRounds();
}

function renderRound(row, roundCount) {
  $("#roundStatus").textContent = `${row.round} / ${roundCount}`;
  $("#leftBits").textContent = row.left_in_bits;
  $("#rightBits").textContent = row.right_in_bits;
  $("#subkeyBits").textContent = row.subkey_bits;
  $("#xorBits").textContent = row.xor_input_bits;
  $("#sboxBits").textContent = row.sbox_output_bits;
  $("#permutationBits").textContent = row.permutation_output_bits;
  $$(".round").forEach((element, index) => {
    element.classList.toggle("active", index === row.round - 1);
    element.classList.toggle("done", index < row.round - 1);
  });
  const chip = $(`.round[data-round='${row.round}']`);
  if (chip) $("strong", chip).textContent = `${row.left_out_bits}|${row.right_out_bits}`;
}

function finishRounds() {
  $$(".round").forEach(element => { element.classList.remove("active"); element.classList.add("done"); });
  $("#roundStatus").className = "good";
  $("#roundStatus").textContent = "Done";
}

function renderPacket(response) {
  const packet = response.packet;
  $("#packetSequence").textContent = `#${packet.sequence}`;
  $("#packetCipher").textContent = `0x${packet.ciphertext.toString(16).padStart(2, "0").toUpperCase()}`;
  $("#packetTag").textContent = packet.tag.toUpperCase();
  $("#gatewayStatus").className = response.accepted ? "good" : "bad";
  $("#gatewayStatus").textContent = response.accepted ? "Accepted" : "Rejected";
  $("#result").className = `result ${response.accepted ? "good" : "bad"}`;
  $("#result").innerHTML = `<span>${response.accepted ? "✓" : "×"}</span><strong>${response.accepted ? "Packet accepted" : "Packet rejected"}</strong>`;
  $("#integrityValue").textContent = response.integrity_valid ? "VALID" : "FAILED";
  $("#integrityValue").className = response.integrity_valid ? "ok" : "failed";
  $("#sequenceCheck").textContent = response.sequence_valid ? "NEW" : "STALE";
  $("#sequenceCheck").className = response.sequence_valid ? "ok" : "failed";
  $("#recoveredValue").textContent = response.recovered_plaintext === null ? "BLOCKED" : response.recovered_plaintext;
}

function renderSimulationMetrics(response, rounds) {
  const result = response.configurations.find(item => item.rounds === rounds);
  $("#avalancheValue").textContent = `${result.avalanche.average_percent}%`;
  $("#timingValue").textContent = `${result.timing.average_us} µs`;
  $("#energyValue").textContent = `${result.energy_estimate.estimated_energy_uj} µJ`;
}

async function runSimulation() {
  const button = $("#runButton");
  try {
    const { key, rounds } = getSettings();
    const scenario = $("#scenarioInput").value;
    button.disabled = true;
    button.textContent = "Running…";
    reset(rounds);
    const data = await api(`/api/readings?count=6&interval_minutes=15&seed=${Date.now() % 100000}&meter_id=SM-2048`);
    const reading = renderMeter(data.readings);
    const encryptionRequest = api("/api/cipher/encrypt", { method: "POST", body: JSON.stringify({ plaintext: reading.quantized_value, key, rounds }) });
    const metricsRequest = api("/api/analysis/run", { method: "POST", body: JSON.stringify({ key, samples: 32, iterations: 3000, voltage: 3.3, active_current_ma: 8 }) });
    const encrypted = await encryptionRequest;
    await animate(encrypted.trace, rounds);
    $("#cipherBits").textContent = encrypted.ciphertext_bits;
    $("#cipherValue").textContent = `0x${encrypted.ciphertext.toString(16).padStart(2, "0").toUpperCase()} · ${encrypted.ciphertext}`;
    const packet = await api("/api/packet/simulate", { method: "POST", body: JSON.stringify({ plaintext: reading.quantized_value, key, rounds, meter_id: "SM-2048", sequence: simulationSequence, iv: 90, attack_mode: scenario }) });
    renderPacket(packet);
    renderSimulationMetrics(await metricsRequest, rounds);
    if (scenario === "none") simulationSequence += 1;
    toast("Simulation complete");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Run simulation";
  }
}

async function toggleAutomation() {
  const button = $("#runButton");
  button.disabled = true;
  try {
    if (automationRunning) {
      await api("/api/automation/stop", { method: "POST" });
      automationRunning = false;
      button.textContent = "Start automation";
      toast("Automation stopped");
    } else {
      const { key, rounds } = getSettings();
      reset(rounds);
      await api("/api/automation/start", { method: "POST", body: JSON.stringify({ key, rounds, interval_seconds: Number($("#intervalInput").value), meter_id: "SM-2048" }) });
      automationRunning = true;
      button.textContent = "Stop automation";
      toast("Automation started");
      await wait(120);
      await syncAutomation(true);
    }
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
  }
}

async function syncAutomation(force = false) {
  if (polling) return;
  polling = true;
  try {
    const status = await api("/api/automation/status");
    automationRunning = status.running;
    $("#graphStatus").textContent = status.running ? "Running" : "Stopped";
    $("#graphStatus").className = `graph-status ${status.running ? "running" : ""}`;
    if (currentTab === "automation") $("#runButton").textContent = status.running ? "Stop automation" : "Start automation";
    if (status.latest && (force || status.latest.id !== latestAutomationId)) {
      latestAutomationId = status.latest.id;
      const recordsResponse = await api("/api/automation/records?limit=200");
      if (currentTab === "automation") renderAutomation(status.latest, recordsResponse.records, status.metrics);
      if (currentTab === "graph") renderGraph(recordsResponse.records, status.running);
    } else if (currentTab === "graph") {
      const recordsResponse = await api("/api/automation/records?limit=200");
      renderGraph(recordsResponse.records, status.running);
    }
    if (currentTab === "data") {
      const recordsResponse = await api("/api/automation/records?limit=2000");
      renderData(recordsResponse.records);
    }
  } catch (_) {
    $("#graphStatus").textContent = "Offline";
  } finally {
    polling = false;
  }
}

function renderAutomation(latest, records, metrics) {
  reset(latest.rounds);
  renderMeter(records);
  latest.trace.forEach(row => renderRound(row, latest.rounds));
  finishRounds();
  $("#leftBits").textContent = latest.ciphertext_bits.slice(0, 4);
  $("#rightBits").textContent = latest.ciphertext_bits.slice(4);
  $("#cipherBits").textContent = latest.ciphertext_bits;
  $("#cipherValue").textContent = `0x${latest.ciphertext.toString(16).padStart(2, "0").toUpperCase()} · ${latest.ciphertext}`;
  renderPacket(latest);
  $("#avalancheValue").textContent = `${metrics?.avalanche_percent ?? "—"}%`;
  $("#timingValue").textContent = `${latest.encryption_us} µs`;
  $("#energyValue").textContent = `${latest.estimated_energy_uj} µJ`;
}

function graphPath(values, width = 1000, height = 330) {
  if (!values.length) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values.map((value, index) => {
    const x = 25 + index * (950 / Math.max(1, values.length - 1));
    const y = 25 + (1 - (value - min) / range) * (height - 35);
    return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function renderGraph(records, running) {
  $("#graphCount").textContent = `${records.length} sample${records.length === 1 ? "" : "s"}`;
  $("#graphStatus").textContent = running ? "Running" : "Stopped";
  $("#graphStatus").className = `graph-status ${running ? "running" : ""}`;
  $("#emptyGraph").classList.toggle("hidden", records.length > 0);
  $("#powerPath").setAttribute("d", graphPath(records.map(item => Number(item.power_kw))));
  $("#usagePath").setAttribute("d", graphPath(records.map(item => Number(item.usage_kwh))));
  const grid = $("#chartGrid");
  if (!grid.childElementCount) grid.innerHTML = [70, 140, 210, 280, 350].map(y => `<line x1="20" y1="${y}" x2="980" y2="${y}"></line>`).join("");
  $("#graphRows").innerHTML = records.length ? records.slice(-20).reverse().map(item => `<div class="record-row"><span data-label="Time">${new Date(item.timestamp).toLocaleTimeString()}</span><span data-label="Sequence">#${item.sequence}</span><span data-label="Power">${Number(item.power_kw).toFixed(2)} kW</span><span data-label="Usage">${Number(item.usage_kwh).toFixed(3)}</span><span data-label="Plaintext">${bits(item.quantized_value)}</span><span data-label="Ciphertext">${item.ciphertext_bits}</span></div>`).join("") : '<p class="empty">No automation records</p>';
}

function renderData(records) {
  $("#dataCount").textContent = `${records.length} record${records.length === 1 ? "" : "s"}`;
  $("#savedDataRows").innerHTML = records.length ? records.slice().reverse().map(item => `
    <div class="saved-data-row">
      <span data-label="ID">${item.id}</span>
      <span data-label="Timestamp">${new Date(item.timestamp).toLocaleString()}</span>
      <span data-label="Sequence">#${item.sequence}</span>
      <span data-label="Voltage">${Number(item.voltage).toFixed(1)} V</span>
      <span data-label="Current">${Number(item.current).toFixed(2)} A</span>
      <span data-label="Power">${Number(item.power_kw).toFixed(2)} kW</span>
      <span data-label="Usage">${Number(item.usage_kwh).toFixed(4)} kWh</span>
      <span data-label="Plaintext">${bits(item.quantized_value)}</span>
      <span data-label="Ciphertext">${item.ciphertext_bits}</span>
      <span data-label="Rounds">${item.rounds}</span>
      <span data-label="Time">${Number(item.encryption_us).toFixed(3)} µs</span>
      <span data-label="Integrity" class="${item.integrity_valid ? "valid" : "failed"}">${item.integrity_valid ? "VALID" : "FAILED"}</span>
    </div>`).join("") : '<p class="empty">No automation records</p>';
}

async function refreshData() {
  const response = await api("/api/automation/records?limit=2000");
  renderData(response.records);
}

function exportData() {
  window.location.href = "/api/automation/export.xlsx";
  toast("Excel export started");
}

async function clearGraph() {
  await api("/api/automation/records", { method: "DELETE" });
  latestAutomationId = null;
  renderGraph([], automationRunning);
  toast("Automation data cleared");
}

function switchTab(tab) {
  currentTab = tab;
  $$(".tab").forEach(button => button.classList.toggle("active", button.dataset.tab === tab));
  $("#graphView").classList.toggle("hidden", tab !== "graph");
  $("#dataView").classList.toggle("hidden", tab !== "data");
  $("#simulatorView").classList.toggle("hidden", tab === "graph" || tab === "data");
  $$(".simulation-only").forEach(element => element.classList.toggle("hidden", tab !== "simulation"));
  $$(".automation-only").forEach(element => element.classList.toggle("hidden", tab !== "automation"));
  if (tab === "simulation") $("#runButton").textContent = "Run simulation";
  if (tab === "automation") {
    $("#runButton").textContent = automationRunning ? "Stop automation" : "Start automation";
    syncAutomation(true);
  }
  if (tab === "graph") syncAutomation(true);
  if (tab === "data") refreshData();
}

$("#runButton").addEventListener("click", () => currentTab === "automation" ? toggleAutomation() : runSimulation());
$("#clearGraph").addEventListener("click", clearGraph);
$("#refreshData").addEventListener("click", refreshData);
$("#exportData").addEventListener("click", exportData);
$$(".tab").forEach(button => button.addEventListener("click", () => switchTab(button.dataset.tab)));
setInterval(() => syncAutomation(), 1000);
syncAutomation();
