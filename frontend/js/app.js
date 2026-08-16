const routeColors = ["#47d7b2", "#72a6ff", "#f0b35a", "#d58bff", "#ff7b8b", "#8ad46e", "#56c8e8", "#e5dc6c"];

const state = {
  map: null,
  routeLayers: [],
  stopLayers: [],
  depotLayer: null,
  demo: null,
  result: null,
  planMode: "optimized",
  productMode: "dispatch",
};

const $ = (id) => document.getElementById(id);
const fmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

function initMap() {
  state.map = L.map("map", { zoomControl: false }).setView([42.355, -71.075], 12.2);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "OpenStreetMap",
    maxZoom: 18,
  }).addTo(state.map);
}

function minuteLabel(value) {
  const total = Math.max(0, Math.round(value));
  const h = 8 + Math.floor(total / 60);
  const m = total % 60;
  const hour = ((h - 1) % 12) + 1;
  return `${hour}:${String(m).padStart(2, "0")} ${h >= 12 ? "PM" : "AM"}`;
}

async function loadDemo() {
  const response = await fetch("/api/demo");
  state.demo = await response.json();
  $("datasetLabel").textContent = state.demo.dataset.label;
  populateVehicles();
  renderStopsOnly();
  await runOptimization();
}

function populateVehicles() {
  const select = $("vehicleSelect");
  for (const vehicle of state.demo.vehicles) {
    const option = document.createElement("option");
    option.value = vehicle.vehicle_id;
    option.textContent = `${vehicle.vehicle_id} unavailable`;
    select.appendChild(option);
  }
}

function scenarioPayload() {
  return {
    traffic_multiplier: Number($("traffic").value),
    demand_spike_percent: Number($("demand").value),
    unavailable_vehicle_id: $("vehicleSelect").value || null,
    average_speed_kph: Number($("speed").value),
    preference_weight: 0,
  };
}

async function runOptimization() {
  const button = $("optimizeButton");
  button.disabled = true;
  button.textContent = "OPTIMIZING";
  try {
    const response = await fetch("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenarioPayload()),
    });
    if (!response.ok) throw new Error(`Optimizer returned ${response.status}`);
    state.result = await response.json();
    renderAll();
  } catch (error) {
    $("comparisonHeadline").textContent = `Optimization failed: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "OPTIMIZE NETWORK";
  }
}

function activePlan() {
  return state.result?.[state.planMode] || null;
}

function renderAll() {
  renderKPIs();
  renderComparison();
  renderRoutes();
  renderRouteTable();
  renderModeOverlay();
}

function renderKPIs() {
  const plan = state.result.optimized;
  const base = state.result.baseline;
  const metrics = [
    ["Total distance", `${fmt.format(plan.total_distance_km)} km`, delta(base.total_distance_km, plan.total_distance_km)],
    ["Driver hours", `${fmt.format(plan.total_driver_hours)} h`, delta(base.total_driver_hours, plan.total_driver_hours)],
    ["Late deliveries", `${plan.late_stops}`, delta(base.late_stops, plan.late_stops)],
    ["Vehicles used", `${plan.vehicles_used}`, delta(base.vehicles_used, plan.vehicles_used)],
    ["Fleet utilization", `${fmt.format(plan.average_utilization * 100)}%`, `${plan.on_time_rate.toFixed(1)}% on time`],
    ["Estimated cost", money.format(plan.estimated_cost), delta(base.estimated_cost, plan.estimated_cost)],
  ];
  $("kpiRow").innerHTML = metrics.map(([label, value, change]) => {
    const cls = change.startsWith("-") ? "good" : change.startsWith("+") ? "bad" : "";
    return `<article class="kpi-card"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-delta ${cls}">${change}</div></article>`;
  }).join("");
}

function delta(oldValue, newValue) {
  if (!Number.isFinite(oldValue) || oldValue === 0) return "baseline calculated";
  const pct = ((newValue - oldValue) / oldValue) * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}% vs current`;
}

function renderComparison() {
  const base = state.result.baseline;
  const opt = state.result.optimized;
  const distanceSaved = base.total_distance_km - opt.total_distance_km;
  const costSaved = base.estimated_cost - opt.estimated_cost;
  $("comparisonHeadline").textContent = `${fmt.format(Math.max(0, distanceSaved))} km and ${money.format(Math.max(0, costSaved))} estimated savings`;
  const cards = [
    ["Distance", `${fmt.format(base.total_distance_km)} km`, `${fmt.format(opt.total_distance_km)} km`, base.total_distance_km, opt.total_distance_km],
    ["Driver hours", `${fmt.format(base.total_driver_hours)} h`, `${fmt.format(opt.total_driver_hours)} h`, base.total_driver_hours, opt.total_driver_hours],
    ["Late stops", `${base.late_stops}`, `${opt.late_stops}`, base.late_stops, opt.late_stops],
    ["Vehicles", `${base.vehicles_used}`, `${opt.vehicles_used}`, base.vehicles_used, opt.vehicles_used],
    ["Operating cost", money.format(base.estimated_cost), money.format(opt.estimated_cost), base.estimated_cost, opt.estimated_cost],
  ];
  $("comparisonGrid").innerHTML = cards.map(([label, oldText, newText, oldValue, newValue]) => {
    const pct = oldValue ? ((newValue - oldValue) / oldValue) * 100 : 0;
    return `<div class="comparison-card"><span>${label}</span><div class="comparison-values"><div class="old">${oldText}</div><div class="new">${newText}</div></div><div class="comparison-delta">${pct <= 0 ? "Reduced" : "Increased"} ${Math.abs(pct).toFixed(1)}%</div></div>`;
  }).join("");
}

function clearMapLayers() {
  for (const layer of [...state.routeLayers, ...state.stopLayers]) state.map.removeLayer(layer);
  state.routeLayers = [];
  state.stopLayers = [];
  if (state.depotLayer) state.map.removeLayer(state.depotLayer);
}

function renderStopsOnly() {
  clearMapLayers();
  const depot = state.demo.depot;
  state.depotLayer = L.marker([depot.lat, depot.lng], {
    icon: L.divIcon({ className: "", html: '<div class="depot-marker"></div>', iconSize: [18, 18] }),
  }).addTo(state.map).bindTooltip("Depot", { direction: "top" });
  for (const stop of state.demo.stops) {
    const marker = L.marker([stop.lat, stop.lng], {
      icon: L.divIcon({ className: "", html: '<div class="stop-marker"></div>', iconSize: [8, 8] }),
    }).addTo(state.map);
    state.stopLayers.push(marker);
  }
}

function renderRoutes() {
  if (!state.result) return;
  clearMapLayers();
  const plan = activePlan();
  const depot = state.demo.depot;
  state.depotLayer = L.marker([depot.lat, depot.lng], {
    icon: L.divIcon({ className: "", html: '<div class="depot-marker"></div>', iconSize: [18, 18] }),
  }).addTo(state.map).bindTooltip("Depot", { direction: "top" });

  plan.routes.forEach((route, index) => {
    const color = routeColors[index % routeColors.length];
    const latlngs = route.geometry.map((point) => [point.lat, point.lng]);
    const line = L.polyline(latlngs, { color, weight: 4, opacity: .86 }).addTo(state.map);
    line.on("click", () => inspectRoute(route));
    line.bindTooltip(`${route.vehicle_id} · ${route.stop_ids.length} stops`, { sticky: true });
    state.routeLayers.push(line);

    route.route_stops.forEach((routeStop) => {
      const point = route.geometry.find((g) => g.stop_id === routeStop.stop_id);
      const late = routeStop.late_minutes > 0;
      const marker = L.marker([point.lat, point.lng], {
        icon: L.divIcon({ className: "", html: `<div class="stop-marker ${late ? "late" : ""}" style="box-shadow:0 0 0 1px ${color}"></div>`, iconSize: [late ? 11 : 8, late ? 11 : 8] }),
      }).addTo(state.map);
      marker.bindTooltip(`${routeStop.stop_id} · ${minuteLabel(routeStop.arrival_minute)}${late ? ` · ${Math.round(routeStop.late_minutes)}m late` : ""}`);
      state.stopLayers.push(marker);
    });
  });
}

function inspectRoute(route) {
  $("routeTitle").textContent = route.vehicle_id;
  const lateStops = route.route_stops.filter((s) => s.late_minutes > 0).length;
  $("routeSummary").classList.remove("empty-state");
  $("routeSummary").innerHTML = `<div class="route-metrics">
    <div class="route-metric"><span>Distance</span><strong>${fmt.format(route.distance_km)} km</strong></div>
    <div class="route-metric"><span>Stops</span><strong>${route.stop_ids.length}</strong></div>
    <div class="route-metric"><span>Utilization</span><strong>${route.utilization_percent}%</strong></div>
    <div class="route-metric"><span>Late stops</span><strong>${lateStops}</strong></div>
    <div class="route-metric"><span>Overtime</span><strong>${fmt.format(route.overtime_minutes)} min</strong></div>
    <div class="route-metric"><span>Cost</span><strong>${money.format(route.cost)}</strong></div>
  </div>`;
  $("stopList").innerHTML = route.route_stops.map((stop, idx) => `<div class="stop-row">
    <span class="stop-index">${String(idx + 1).padStart(2, "0")}</span>
    <span class="stop-id">${stop.stop_id}</span>
    <span class="stop-time ${stop.late_minutes > 0 ? "late" : ""}">${minuteLabel(stop.arrival_minute)}</span>
  </div>`).join("");
}

function renderRouteTable() {
  const plan = state.result.optimized;
  $("routeCount").textContent = `${plan.routes.length} active routes`;
  $("routeTableBody").innerHTML = plan.routes.map((route) => {
    const driverHours = (route.drive_minutes + route.service_minutes + route.waiting_minutes) / 60;
    const lateStops = route.route_stops.filter((s) => s.late_minutes > 0).length;
    return `<tr data-route="${route.vehicle_id}"><td>${route.vehicle_id}</td><td>${route.stop_ids.length}</td><td>${fmt.format(route.distance_km)} km</td><td>${fmt.format(driverHours)} h</td><td>${route.utilization_percent}%</td><td>${lateStops}</td><td>${fmt.format(route.overtime_minutes)} m</td><td>${money.format(route.cost)}</td></tr>`;
  }).join("");
  document.querySelectorAll("#routeTableBody tr").forEach((row) => row.addEventListener("click", () => {
    const route = plan.routes.find((item) => item.vehicle_id === row.dataset.route);
    inspectRoute(route);
  }));
}

function renderModeOverlay() {
  const overlay = $("modeOverlay");
  if (state.productMode === "dispatch") {
    overlay.classList.add("hidden");
    return;
  }
  overlay.classList.remove("hidden");
  if (state.productMode === "recovery") {
    const payload = scenarioPayload();
    const issues = [];
    if (payload.unavailable_vehicle_id) issues.push(`${payload.unavailable_vehicle_id} removed from fleet`);
    if (payload.demand_spike_percent) issues.push(`${payload.demand_spike_percent}% package-demand spike`);
    if (payload.traffic_multiplier > 1.05) issues.push(`${payload.traffic_multiplier.toFixed(2)}x traffic conditions`);
    overlay.innerHTML = `<div class="panel-heading"><div><p class="eyebrow">RECOVERY MODE</p><h2>Disruption impact and recovery actions</h2></div></div>
      <div class="overlay-grid">
        <div class="overlay-card"><h3>Active disruptions</h3><p>${issues.length ? issues.join(". ") : "No disruption is active. Use the left controls to remove a vehicle, add a demand spike or increase traffic."}</p></div>
        <div class="overlay-card"><h3>Recovery engine</h3><p>The optimizer rebuilds route assignments under the changed capacity and travel-time constraints, then resequences stops using time-window urgency and local-search improvements.</p></div>
        <div class="overlay-card"><h3>Decision boundary</h3><p>The demo estimates route operating cost and service risk. It does not model driver labor agreements, real-time road incidents or commercial navigation restrictions unless supplied as inputs.</p></div>
      </div>`;
  } else {
    overlay.innerHTML = `<div class="panel-heading"><div><p class="eyebrow">DATASET LAB</p><h2>Amazon Last Mile Routing Research Challenge adapter</h2></div></div>
      <div class="overlay-grid">
        <div class="overlay-card"><h3>Real research data</h3><p>9,184 anonymized historical Amazon routes from five U.S. metro areas. The repository supports the route, package, travel-time and actual-sequence files without bundling the 3.1 GB dataset.</p><div class="code-line">aws s3 sync --no-sign-request s3://amazon-last-mile-challenges/almrrc2021/ data/amazon/</div></div>
        <div class="overlay-card"><h3>Route importer</h3><p>Normalize one official challenge route into depot, vehicle, package volume, service time, time-window and asymmetric travel-time inputs.</p><div class="code-line">python scripts/import_amazon_route.py --help</div></div>
        <div class="overlay-card"><h3>Driver preference learner</h3><p>Learn zone-to-zone transition probabilities from actual historical stop sequences and use them as a transparent soft penalty during route optimization.</p><div class="code-line">python scripts/train_zone_preferences.py --help</div></div>
      </div>`;
  }
}

function bindControls() {
  const controls = [
    ["traffic", "trafficValue", (v) => `${Number(v).toFixed(2)}x`],
    ["demand", "demandValue", (v) => `${v}%`],
    ["speed", "speedValue", (v) => `${v} km/h`],
  ];
  for (const [inputId, outputId, format] of controls) {
    $(inputId).addEventListener("input", (event) => { $(outputId).textContent = format(event.target.value); });
  }
  $("optimizeButton").addEventListener("click", runOptimization);
  $("resetButton").addEventListener("click", () => {
    $("traffic").value = 1; $("trafficValue").textContent = "1.00x";
    $("demand").value = 0; $("demandValue").textContent = "0%";
    $("speed").value = 27; $("speedValue").textContent = "27 km/h";
    $("vehicleSelect").value = "";
    runOptimization();
  });
  $("baselineToggle").addEventListener("click", () => setPlanMode("baseline"));
  $("optimizedToggle").addEventListener("click", () => setPlanMode("optimized"));
  document.querySelectorAll(".mode-tab").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".mode-tab").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    state.productMode = button.dataset.mode;
    renderModeOverlay();
  }));
}

function setPlanMode(mode) {
  state.planMode = mode;
  $("baselineToggle").classList.toggle("active", mode === "baseline");
  $("optimizedToggle").classList.toggle("active", mode === "optimized");
  $("mapTitle").textContent = mode === "baseline" ? "Current delivery plan" : "Optimized delivery network";
  renderRoutes();
}

initMap();
bindControls();
loadDemo();
