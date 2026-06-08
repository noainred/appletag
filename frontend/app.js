// AppleTag tracker frontend: device list + Leaflet/OpenStreetMap tracks.

const COLORS = [
  "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
  "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
];

const map = L.map("map").setView([37.5665, 126.978], 11); // 기본: 서울
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

// device_id -> { color, layer (L.layerGroup) }
const layers = new Map();
const colorFor = (() => {
  let i = 0;
  const cache = new Map();
  return (id) => {
    if (!cache.has(id)) cache.set(id, COLORS[i++ % COLORS.length]);
    return cache.get(id);
  };
})();

function setStatus(msg, kind) {
  const el = document.getElementById("status");
  el.textContent = msg || "";
  el.className = "status" + (kind ? " " + kind : "");
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

function fmtTime(ms) {
  if (!ms) return "위치 정보 없음";
  return new Date(ms).toLocaleString("ko-KR");
}

async function loadDevices() {
  const list = document.getElementById("device-list");
  list.innerHTML = "";
  let devices;
  try {
    devices = await api("/api/devices");
    setStatus("", "");
  } catch (err) {
    setStatus("기기 목록을 불러올 수 없습니다: " + err.message, "error");
    return;
  }

  if (devices.length === 0) {
    setStatus("등록된 AppleTag가 없습니다.", "error");
    return;
  }

  for (const d of devices) {
    const li = document.createElement("li");
    li.className = "device";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = d.selected;
    cb.addEventListener("change", () => onToggle(d, cb.checked));

    const swatch = document.createElement("div");
    swatch.className = "swatch";
    swatch.style.background = colorFor(d.device_id);

    const meta = document.createElement("div");
    meta.className = "meta";
    const loc = d.latitude != null
      ? `${d.latitude.toFixed(5)}, ${d.longitude.toFixed(5)}`
      : "위치 없음";
    meta.innerHTML =
      `<div class="name">${escapeHtml(d.name)}</div>` +
      `<div class="sub">${escapeHtml(d.address || loc)}</div>` +
      `<div class="sub">최근 측위: ${fmtTime(d.timestamp)}</div>`;

    li.append(cb, swatch, meta);
    list.appendChild(li);

    if (d.selected) drawTrack(d.device_id);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function onToggle(device, selected) {
  try {
    await api("/api/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: device.device_id, selected }),
    });
  } catch (err) {
    setStatus("선택 저장 실패: " + err.message, "error");
    return;
  }
  if (selected) {
    drawTrack(device.device_id);
  } else {
    clearTrack(device.device_id);
  }
}

function clearTrack(deviceId) {
  const entry = layers.get(deviceId);
  if (entry) {
    map.removeLayer(entry.layer);
    layers.delete(deviceId);
  }
}

async function drawTrack(deviceId) {
  let points;
  try {
    points = await api(`/api/track/${encodeURIComponent(deviceId)}`);
  } catch (err) {
    setStatus("경로를 불러올 수 없습니다: " + err.message, "error");
    return;
  }

  clearTrack(deviceId);
  const color = colorFor(deviceId);
  const group = L.layerGroup().addTo(map);

  const latlngs = points
    .filter((p) => p.latitude != null && p.longitude != null)
    .map((p) => [p.latitude, p.longitude]);

  if (latlngs.length === 0) {
    layers.set(deviceId, { color, layer: group });
    return;
  }

  L.polyline(latlngs, { color, weight: 3, opacity: 0.8 }).addTo(group);

  points.forEach((p, idx) => {
    if (p.latitude == null) return;
    const isLast = idx === points.length - 1;
    const marker = L.circleMarker([p.latitude, p.longitude], {
      radius: isLast ? 8 : 4,
      color,
      fillColor: color,
      fillOpacity: isLast ? 1 : 0.5,
      weight: isLast ? 3 : 1,
    }).addTo(group);
    marker.bindPopup(
      `<b>${escapeHtml(p.name || "")}</b><br>` +
      `측위 시각: ${fmtTime(p.timestamp)}<br>` +
      `기록 시각: ${fmtTime(p.recorded_at)}<br>` +
      `정확도: ${p.accuracy != null ? p.accuracy.toFixed(0) + "m" : "?"}`
    );
  });

  layers.set(deviceId, { color, layer: group });
  map.fitBounds(L.latLngBounds(latlngs).pad(0.2));
}

document.getElementById("refresh").addEventListener("click", loadDevices);
document.getElementById("poll-now").addEventListener("click", async () => {
  try {
    const r = await api("/api/poll-now", { method: "POST" });
    setStatus(`위치 기록 완료 (새 지점 ${r.inserted}개).`, "ok");
    for (const id of layers.keys()) drawTrack(id);
  } catch (err) {
    setStatus("기록 실패: " + err.message, "error");
  }
});

// 선택된 태그의 경로를 30초마다 자동 갱신.
setInterval(() => {
  for (const id of layers.keys()) drawTrack(id);
}, 30 * 1000);

loadDevices();
