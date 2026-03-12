// Settings panel logic for simulation UI
const SETTINGS_FIELDS = [
  { key: 'drain_per_unit', label: 'Drain per unit', step: 0.01 },
  { key: 'scan_cost', label: 'Scan cost (%)', step: 0.1 },
  { key: 'safety_margin', label: 'Safety margin (%)', step: 0.5 },
  { key: 'fire_multiplier', label: 'Fire multiplier', step: 0.1 },
  { key: 'smoke_multiplier', label: 'Smoke multiplier', step: 0.1 },
  { key: 'passive_survivor_radius', label: 'Passive survivor radius', step: 1 },
  { key: 'grid_size', label: 'Grid size', step: 10 },
  { key: 'sector_rows', label: 'Sector rows', step: 1 },
  { key: 'sector_cols', label: 'Sector cols', step: 1 },
  { key: 'survivor_min', label: 'Min survivors', step: 1 },
  { key: 'survivor_max', label: 'Max survivors', step: 1 },
  { key: 'wind_speed_kmh', label: 'Wind speed (km/h)', step: 1 },
  { key: 'wind_angle_deg', label: 'Wind angle (deg)', step: 1 }
];

async function fetchSettings() {
  const res = await fetch('http://localhost:8000/settings');
  return await res.json();
}

async function saveSettings(payload) {
  const res = await fetch('http://localhost:8000/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return await res.json();
}

function buildSettingsForm(container, settings) {
  container.innerHTML = '';
  SETTINGS_FIELDS.forEach(f => {
    const row = document.createElement('div');
    row.className = 'settings-row';
    const label = document.createElement('label');
    label.textContent = f.label;
    const input = document.createElement('input');
    input.type = 'number';
    input.step = f.step;
    input.value = settings[f.key] ?? '';
    input.dataset.key = f.key;
    row.appendChild(label);
    row.appendChild(input);
    container.appendChild(row);
  });
}

async function initSettingsUI() {
  const panel = document.getElementById('settings-panel');
  const form = document.getElementById('settings-form');
  const toggle = document.getElementById('settings-toggle');
  const statusEl = document.getElementById('settings-status');

  if (!panel || !form || !toggle) return;

  const settings = await fetchSettings().catch(() => ({}));
  buildSettingsForm(form, settings);

  toggle.addEventListener('click', () => {
    panel.classList.toggle('open');
  });

  document.getElementById('settings-save').addEventListener('click', async () => {
    const payload = {};
    form.querySelectorAll('input').forEach(inp => {
      const val = inp.value;
      if (val !== '') payload[inp.dataset.key] = Number(val);
    });
    statusEl.textContent = 'Saving...';
    try {
      const resp = await saveSettings(payload);
      statusEl.textContent = 'Saved. Mission reset with new settings.';
    } catch (e) {
      statusEl.textContent = 'Save failed';
    }
  });
}

document.addEventListener('DOMContentLoaded', initSettingsUI);
