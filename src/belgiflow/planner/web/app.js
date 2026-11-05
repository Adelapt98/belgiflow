'use strict';
const $ = id => document.getElementById(id);
const clone = value => JSON.parse(JSON.stringify(value));
const fmt = value => new Intl.NumberFormat('en', {maximumFractionDigits: 2}).format(value);
let bootstrap, plan, lastResult, active = 'proposed', adding = false;
let layers = [], markers = [];
const map = L.map('map', {zoomControl: false, preferCanvas: true}).setView([50.846, 4.35], 13);
L.control.zoom({position: 'bottomright'}).addTo(map);
const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
}).addTo(map);
const referenceLayer = L.layerGroup().addTo(map);

function error(message) {
  $('error').textContent = message;
  $('error').hidden = !message;
}

function dirty() {
  $('status').textContent = 'Changes not yet compared';
  $('export').disabled = true;
  $('export-menu').hidden = true;
}

function field(value, title, options, changed) {
  const label = document.createElement('label');
  label.textContent = title;
  const input = document.createElement('input');
  Object.assign(input, options, {value});
  input.setAttribute('aria-label', title);
  input.addEventListener('change', () => {changed(input.value); dirty();});
  label.append(input);
  return label;
}

function renderHubs() {
  const scenario = plan[active];
  $('scenario-name').value = scenario.name;
  $('hub-count').textContent = `(${scenario.hubs.length})`;
  $('hub-list').replaceChildren();
  for (const hub of scenario.hubs) {
    const card = document.createElement('div');
    card.className = 'hub-card';
    const top = document.createElement('div');
    top.className = 'hub-card-top';
    const dot = document.createElement('span');
    dot.className = 'hub-dot';
    dot.style.background = plan.baseline.hubs.some(h => h.id === hub.id) ? '#6388c0' : '#6a9d70';
    const name = document.createElement('input');
    name.value = hub.name;
    name.maxLength = 80;
    name.setAttribute('aria-label', 'Hub name');
    name.addEventListener('change', () => {hub.name = name.value; dirty();});
    const remove = document.createElement('button');
    remove.className = 'remove-hub';
    remove.textContent = '×';
    remove.title = `Remove ${hub.name}`;
    remove.setAttribute('aria-label', `Remove ${hub.name}`);
    remove.addEventListener('click', () => {
      scenario.hubs = scenario.hubs.filter(h => h.id !== hub.id);
      renderHubs(); dirty();
    });
    top.append(dot, name, remove);
    const fields = document.createElement('div');
    fields.className = 'hub-fields';
    fields.append(
      field(hub.latitude, 'Latitude', {type: 'number', step: '0.0001'}, v => hub.latitude = Number(v)),
      field(hub.longitude, 'Longitude', {type: 'number', step: '0.0001'}, v => hub.longitude = Number(v)),
      field(hub.radius_m / 1000, 'Radius · km', {type: 'number', min: '0.1', max: '50', step: '0.1'}, v => hub.radius_m = Number(v) * 1000)
    );
    card.append(top, fields);
    $('hub-list').append(card);
  }
  for (const key of ['baseline', 'proposed']) {
    $(`tab-${key}`).classList.toggle('selected', active === key);
    $(`tab-${key}`).setAttribute('aria-selected', String(active === key));
  }
}

function number(id, value, unit = '') {
  const target = $(id);
  target.replaceChildren(document.createTextNode(fmt(value)));
  if (unit) {
    const small = document.createElement('small');
    small.textContent = ' ' + unit;
    target.append(small);
  }
}

function signed(value, unit = '') {
  return (value > 0 ? '+' : '') + fmt(value) + (unit ? ' ' + unit : '');
}

function comparisonTable(result) {
  $('baseline-title').textContent = result.baseline.name;
  $('proposed-title').textContent = result.proposed.name;
  const a = result.baseline.metrics, b = result.proposed.metrics;
  const rows = [
    ['Service hubs', a.hubs, b.hubs, ''],
    ['Covered service area', a.covered_area_km2, b.covered_area_km2, 'km²'],
    ['Share of study area', a.coverage_percent, b.coverage_percent, '%'],
    ['Buildings covered in sample', a.covered_buildings, b.covered_buildings, ''],
    ['Overlapping service area', a.overlap_area_km2, b.overlap_area_km2, 'km²'],
    ['Uncovered study area', a.uncovered_area_km2, b.uncovered_area_km2, 'km²']
  ];
  $('comparison-rows').replaceChildren();
  for (const [label, before, after, unit] of rows) {
    const tr = document.createElement('tr');
    for (const value of [label, fmt(before) + ' ' + unit, fmt(after) + ' ' + unit, signed(after - before, unit)]) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    $('comparison-rows').append(tr);
  }
}

function geo(geometry, style) {
  const layer = L.geoJSON(geometry, {style, interactive: false}).addTo(map);
  layers.push(layer);
  return layer;
}

function draw(result, fit = false) {
  layers.forEach(layer => map.removeLayer(layer)); layers = [];
  markers.forEach(marker => map.removeLayer(marker)); markers = [];
  geo(result.study_area, {color: '#a9b4a0', weight: 1, dashArray: '5 5', fillOpacity: 0});
  geo(result.baseline.coverage, {color: '#5a80ba', weight: 2, fillColor: '#688fc8', fillOpacity: 0.19});
  geo(result.proposed.coverage, {color: '#4b895a', weight: 2, dashArray: '5 4', fillOpacity: 0});
  geo(result.changes.newly_covered, {color: '#77a26e', weight: 1, fillColor: '#84af78', fillOpacity: 0.24});
  geo(result.proposed.overlap, {color: '#c79d50', weight: 1, fillColor: '#d5ac61', fillOpacity: 0.24});
  geo(result.changes.no_longer_covered, {color: '#be7959', weight: 1, fillColor: '#cd956b', fillOpacity: 0.22});
  const placeMarker = (hub, color) => {
    const label = document.createElement('span'); label.textContent = hub.name;
    const marker = L.circleMarker([hub.latitude, hub.longitude], {
      radius: 7, color: 'white', weight: 3, fillColor: color, fillOpacity: 1
    }).addTo(map).bindTooltip(label, {permanent: true, direction: 'top', offset: [0, -9]});
    markers.push(marker);
  };
  result.baseline.hubs.forEach(h => placeMarker(h, '#5079b7'));
  result.proposed.hubs.filter(h => !result.baseline.hubs.some(b => b.id === h.id && b.latitude === h.latitude && b.longitude === h.longitude))
    .forEach(h => placeMarker(h, '#4c8758'));
  if (fit) fitNetwork();
}

function fitNetwork() {
  if (!lastResult) return;
  let bounds;
  for (const scenario of [lastResult.baseline, lastResult.proposed]) {
    const layer = L.geoJSON(scenario.coverage);
    if (layer.getBounds().isValid()) bounds = bounds ? bounds.extend(layer.getBounds()) : layer.getBounds();
  }
  map.fitBounds(bounds || L.geoJSON(lastResult.study_area).getBounds(), {padding: [50, 60], maxZoom: 14});
}

async function compare(fit = false) {
  error(''); $('compare').disabled = true; $('status').textContent = 'Comparing scenarios';
  try {
    const response = await fetch('/api/compare', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(plan)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Comparison failed');
    lastResult = result;
    number('area', result.proposed.metrics.covered_area_km2, 'km²');
    number('buildings', result.proposed.metrics.covered_buildings);
    number('overlap', result.proposed.metrics.overlap_area_km2, 'km²');
    number('gained', result.changes.added_area_km2, 'km²');
    $('area-change').textContent = signed(result.changes.net_area_km2, 'km²') + ' net change from current';
    $('buildings-change').textContent = signed(result.changes.additional_buildings) + ' sampled building locations covered';
    $('sample-note').textContent = `${result.proposed.metrics.sampled_buildings} of ${bootstrap.total_buildings} sampled footprints in study area · ${bootstrap.provenance.release}`;
    if (!result.proposed.metrics.sampled_buildings) {
      $('buildings').textContent = 'No sample';
      $('buildings-change').textContent = 'Area metrics available. No buildings sampled here.';
    }
    $('gained-detail').textContent = fmt(result.changes.lost_area_km2) + ' km² of current coverage lost';
    $('provenance').textContent = `${result.provenance.mode} · ${result.provenance.release} · comparison ${result.plan_id.slice(0, 8)}`;
    $('status').textContent = 'Comparison up to date';
    $('export').disabled = false;
    $('csv').href = '/api/export?format=csv&plan=' + result.plan_id;
    $('json').href = '/api/export?format=json&plan=' + result.plan_id;
    comparisonTable(result); draw(result, fit);
  } catch (failure) {
    error(failure.message); $('status').textContent = 'Review scenario inputs'; $('export').disabled = true;
  } finally { $('compare').disabled = false; }
}

for (const key of ['baseline', 'proposed']) $(`tab-${key}`).addEventListener('click', () => {active = key; renderHubs();});
$('scenario-name').addEventListener('change', () => {plan[active].name = $('scenario-name').value; dirty();});
$('compare').addEventListener('click', () => compare());
$('reset').addEventListener('click', () => {plan = clone(bootstrap.example); active = 'proposed'; $('study-label').textContent = 'Brussels study area'; renderHubs(); compare(true);});
$('copy-baseline').addEventListener('click', () => {plan.proposed.hubs = clone(plan.baseline.hubs); active = 'proposed'; renderHubs(); dirty();});
$('export').addEventListener('click', () => $('export-menu').hidden = !$('export-menu').hidden);
$('basemap').addEventListener('change', event => event.target.checked ? tiles.addTo(map) : map.removeLayer(tiles));
$('fit-network').addEventListener('click', fitNetwork);
$('use-map-extent').addEventListener('click', () => {
  const bounds = map.getBounds();
  plan.study_area = [Math.max(2.4, bounds.getWest()), Math.max(49.4, bounds.getSouth()), Math.min(6.5, bounds.getEast()), Math.min(51.6, bounds.getNorth())];
  $('study-label').textContent = 'Selected study area';
  compare();
});
$('fit-sample').addEventListener('click', () => map.fitBounds(L.geoJSON(bootstrap.building_sample_extent).getBounds(), {padding: [80, 80], maxZoom: 18}));
$('add-hub').addEventListener('click', () => {
  adding = !adding;
  $('add-hub').classList.toggle('active', adding);
  $('map-hint').textContent = adding ? 'Click a Belgian location on the map to place the new hub.' : 'Choose a location on the map, then adjust its service radius.';
  map.getContainer().style.cursor = adding ? 'crosshair' : '';
});
map.on('click', event => {
  if (!adding) return;
  if (plan[active].hubs.length >= 20) {error('Each scenario supports at most 20 hubs.'); return;}
  plan[active].hubs.push({id: 'hub-' + Date.now(), name: 'New service hub', longitude: +event.latlng.lng.toFixed(6), latitude: +event.latlng.lat.toFixed(6), radius_m: 1500});
  adding = false; $('add-hub').classList.remove('active'); map.getContainer().style.cursor = '';
  $('map-hint').textContent = 'New hub added. Adjust its settings and compare the scenarios.';
  renderHubs(); dirty();
});

(async () => {
  try {
    bootstrap = await (await fetch('/api/bootstrap')).json();
    plan = clone(bootstrap.example);
    const publicData = bootstrap.provenance.mode === 'Overture';
    $('source-label').textContent = publicData ? 'Public map sample' : 'Demo geography';
    $('sample-note').textContent = `${bootstrap.total_buildings} sampled footprints · ${bootstrap.provenance.release} · Buildings are not demand`;
    L.geoJSON(bootstrap.features, {
      filter: f => f.properties.kind === 'building',
      style: {color: '#5d705f', fillColor: '#657b66', fillOpacity: 0.75, weight: 1}
    }).addTo(referenceLayer);
    L.geoJSON(bootstrap.features, {
      filter: f => f.properties.kind === 'segment', style: {color: '#8d9b89', weight: 2, opacity: 0.65}
    }).addTo(referenceLayer);
    map.attributionControl.addAttribution(publicData ? 'Overture Maps Foundation' : 'Synthetic building sample');
    renderHubs(); await compare(true);
  } catch (failure) { error('Could not load reference data: ' + failure.message); }
})();
