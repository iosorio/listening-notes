const COPY = {
  en: {
    allAreas: 'All areas', allVenues: 'All venues', allPriorities: 'All priorities',
    areaGroup: 'Scenes and areas', venueGroup: 'Venues', priorityGroup: 'Priorities',
    noMatches: '0 events with the current filters',
    areas: { dmv: 'DMV / local scene', baltimore: 'Baltimore', philadelphia: 'Philadelphia', newark: 'Newark', new_york: 'New York', tokyo: 'Tokyo', kanagawa: 'Kanagawa / Kantō', saitama: 'Saitama / Kantō', new_jersey: 'New Jersey', unassigned: 'Area to review' },
    viewUpcoming: 'Upcoming', viewArchive: 'Archive', upcoming: 'On the radar', archive: 'RADAR archive',
    shown: 'shown', upcomingCount: 'upcoming', archiveCount: 'archived', signal: 'The Signal', whyNow: 'Why now',
    recentSignals: 'Recent Signals', listen: 'Listen before', appleMusic: 'Listen on Apple Music',
    official: 'Official tickets', details: 'Details', detailsAndTickets: 'Details & Tickets',
    rule: 'The criterion', ruleText: 'The radar is intentionally selective. Its choices are editorial, not comprehensive.',
    archiveText: 'Attended nights and finished dates retained in the RADAR record.',
    empty: 'Nothing in this selection. The filter is part of the curation.',
    loadError: 'Could not load event data.',
    discovered: 'Discovered', discoveryUnknown: 'Discovery time unknown',
    operations: {
      on: 'ON', off: 'OFF', healthy: 'HEALTHY', stale: 'STALE', error: 'ERROR', unknown: 'UNKNOWN',
      desired: 'Requested state', desiredNote: 'The requested state does not confirm that the external executor is running.',
      lastRun: 'Last run', lastSuccess: 'Last successful scan', noHeartbeat: 'No repository heartbeat has been recorded.',
      latestResult: 'Latest result', nextExpected: 'Next expected scan', cadence: 'Expected cadence',
      stats: ({sources, candidates, published, updates}) => `${sources} sources checked · ${candidates} candidates reviewed · ${published} new · ${updates} updates`,
      cadenceValue: value => value === 'hourly' ? 'hourly' : value.replaceAll('_', ' '),
      manage: 'Edit requested state', guide: 'Operations guide', unavailable: 'Operational data unavailable or invalid.'
    },
    status: { considering: 'on the radar', going: 'going', attended: 'heard', passed: 'passed' },
    travel: { Local: 'Local', 'Short trip': 'Short trip', Trip: 'Worth the train', Tokyo: 'Build the night around it' },
    categories: { 'Living masters': 'Living masters', 'Modern jazz': 'Modern jazz', 'Brazil / Latin': 'Brazil / Latin', 'Fusion / progressive': 'Fusion / progressive', 'Experimental / rock / metal': 'Experimental / rock / metal', Japan: 'Japan' }
  },
  es: {
    allAreas: 'Todas las áreas', allVenues: 'Todos los recintos', allPriorities: 'Todas las prioridades',
    areaGroup: 'Escenas y zonas', venueGroup: 'Recintos', priorityGroup: 'Prioridades',
    noMatches: '0 eventos con los filtros actuales',
    areas: { dmv: 'DMV / escena local', baltimore: 'Baltimore', philadelphia: 'Filadelfia', newark: 'Newark', new_york: 'Nueva York', tokyo: 'Tokio', kanagawa: 'Kanagawa / Kantō', saitama: 'Saitama / Kantō', new_jersey: 'Nueva Jersey', unassigned: 'Zona por revisar' },
    viewUpcoming: 'Próximos', viewArchive: 'Archivo', upcoming: 'En el radar', archive: 'Archivo RADAR',
    shown: 'mostrados', upcomingCount: 'próximos', archiveCount: 'archivados', signal: 'La señal', whyNow: 'Por qué ahora',
    recentSignals: 'Señales recientes', listen: 'Para escuchar antes', appleMusic: 'Escuchar en Apple Music',
    official: 'Boletos oficiales', details: 'Información', detailsAndTickets: 'Información y boletos',
    rule: 'El criterio', ruleText: 'El radar es deliberadamente selectivo. Sus elecciones son editoriales, no exhaustivas.',
    archiveText: 'Noches asistidas y fechas terminadas que se conservan en el registro de RADAR.',
    empty: 'Nada en esta selección. El filtro también es parte de la curaduría.',
    loadError: 'No fue posible cargar los eventos.',
    discovered: 'Descubierto', discoveryUnknown: 'Hora de descubrimiento desconocida',
    operations: {
      on: 'ENCENDIDO', off: 'APAGADO', healthy: 'SALUDABLE', stale: 'ATRASADO', error: 'ERROR', unknown: 'DESCONOCIDO',
      desired: 'Estado solicitado', desiredNote: 'El estado solicitado no confirma que el ejecutor externo esté funcionando.',
      lastRun: 'Última ejecución', lastSuccess: 'Último escaneo exitoso', noHeartbeat: 'No hay un latido registrado en el repositorio.',
      latestResult: 'Resultado más reciente', nextExpected: 'Próximo escaneo esperado', cadence: 'Frecuencia esperada',
      stats: ({sources, candidates, published, updates}) => `${sources} fuentes revisadas · ${candidates} candidatos evaluados · ${published} nuevos · ${updates} actualizaciones`,
      cadenceValue: value => value === 'hourly' ? 'cada hora' : value.replaceAll('_', ' '),
      manage: 'Editar estado solicitado', guide: 'Guía de operación', unavailable: 'Datos operativos no disponibles o inválidos.'
    },
    status: { considering: 'en el radar', going: 'voy', attended: 'escuchamos', passed: 'pasó' },
    travel: { Local: 'Local', 'Short trip': 'Escapada corta', Trip: 'Vale el tren', Tokyo: 'Vale construir la noche alrededor' },
    categories: { 'Living masters': 'Maestros vivos', 'Modern jazz': 'Jazz contemporáneo', 'Brazil / Latin': 'Brasil / Latinoamérica', 'Fusion / progressive': 'Fusión / prog', 'Experimental / rock / metal': 'Experimental / rock / metal', Japan: 'Japón' }
  }
};

const hasDocument = typeof document !== 'undefined';
const lang = hasDocument && document.documentElement.lang.startsWith('es') ? 'es' : 'en';
const t = COPY[lang];
const requestedView = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('view') : null;
const state = { radar_area: '', venue: '', priority: '', view: requestedView === 'archive' ? 'archive' : 'upcoming' };
const AREA_ORDER = ['dmv', 'baltimore', 'philadelphia', 'newark', 'new_york', 'tokyo', 'kanagawa', 'saitama', 'new_jersey', 'unassigned'];

const formatDate = value => new Intl.DateTimeFormat(lang === 'es' ? 'es-US' : 'en-US', { month: 'short', day: 'numeric' }).format(new Date(`${value}T12:00:00`));
const formatTimestamp = value => new Intl.DateTimeFormat(lang === 'es' ? 'es-US' : 'en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
const range = event => event.dates.end && event.dates.end !== event.dates.start ? `${formatDate(event.dates.start)}–${formatDate(event.dates.end)}` : formatDate(event.dates.start);
const editorial = event => event.editorial[lang] || {};
const finalDate = event => event.dates.end || event.dates.start;
const localDate = () => {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now - offset).toISOString().slice(0, 10);
};
const isArchiveAt = (event, today) => event.status === 'attended' || event.status === 'passed' || finalDate(event) < today;
const isArchive = event => isArchiveAt(event, localDate());
const travel = event => t.travel[event.geography] || event.geography;
const hasActiveFilters = viewState => Boolean(viewState.radar_area || viewState.venue || viewState.priority);
const radarAreaFor = (event, registry) => {
  const area = registry?.venues?.[event.venue.id]?.radar_area;
  return AREA_ORDER.includes(area) ? area : 'unassigned';
};
const availableAreas = (events, registry) => {
  const areas = new Set(events.map(event => radarAreaFor(event, registry)));
  return [...areas].sort((left, right) => AREA_ORDER.indexOf(left) - AREA_ORDER.indexOf(right));
};

function matchesState(event, viewState, registry) {
  return (!viewState.radar_area || radarAreaFor(event, registry) === viewState.radar_area) &&
    (!viewState.venue || event.venue.id === viewState.venue) &&
    (!viewState.priority || event.priority === viewState.priority);
}

function selectFacet(viewState, key, value, registry) {
  const next = { ...viewState, [key]: value };
  if (key === 'radar_area' && (value === '' || value !== viewState.radar_area)) next.venue = '';
  if (key === 'venue' && value) {
    const area = registry?.venues?.[value]?.radar_area;
    next.radar_area = AREA_ORDER.includes(area) ? area : 'unassigned';
  }
  return next;
}

function facetCounts(viewEvents, viewState, registry, options) {
  const count = (key, value) => {
    const candidate = key === 'venue'
      ? { ...viewState, venue: value }
      : selectFacet(viewState, key, value, registry);
    return viewEvents.filter(event => matchesState(event, candidate, registry)).length;
  };
  return {
    radar_area: new Map(options.radar_area.map(value => [value, count('radar_area', value)])),
    venue: new Map(options.venue.map(value => [value, count('venue', value)])),
    priority: new Map(options.priority.map(value => [value, count('priority', value)]))
  };
}

const visibleFacetValues = (values, counts, selected) =>
  values.filter(value => counts.get(value) > 0 || value === selected);

function validFacetState(viewEvents, viewState, registry) {
  const next = { ...viewState };
  const possible = () => viewEvents.some(event => matchesState(event, next, registry));
  if (possible() || !hasActiveFilters(next)) return next;
  for (const key of ['venue', 'radar_area', 'priority']) {
    next[key] = '';
    if (possible()) break;
  }
  return next;
}

function deriveRadarView(events, viewState, currentSignalEvent, today, registry) {
  const archiveView = viewState.view === 'archive';
  const viewEvents = events.filter(event => archiveView ? isArchiveAt(event, today) : !isArchiveAt(event, today));
  const selected = viewEvents.filter(event => matchesState(event, viewState, registry))
    .sort((left, right) => left.dates.start.localeCompare(right.dates.start));
  const signalVisible = !archiveView && !hasActiveFilters(viewState) && Boolean(
    currentSignalEvent && selected.some(event => event.id === currentSignalEvent.id)
  );
  const results = signalVisible
    ? selected.filter(event => event.id !== currentSignalEvent.id)
    : selected;
  return { viewEvents, selected, results, signalVisible };
}

function resolveSignalState(payload, events) {
  const unavailable = { valid: false, current: null, recent: [] };
  if (!payload || payload.schema_version !== 1 || !Array.isArray(payload.signals)) return unavailable;
  const currentRecords = payload.signals.filter(record => record && record.replaced_on === null && record.replaced_by === null);
  if (currentRecords.length !== 1) return unavailable;
  const eventIndex = new Map(events.map(event => [event.id, event]));
  const currentEvent = eventIndex.get(currentRecords[0].event_id);
  if (!currentEvent) return unavailable;
  const recent = payload.signals
    .filter(record => record && record.replaced_on && record.replaced_by && eventIndex.has(record.event_id))
    .sort((left, right) => right.replaced_on.localeCompare(left.replaced_on))
    .slice(0, 2)
    .map(record => ({ record, event: eventIndex.get(record.event_id) }));
  return { valid: true, current: { record: currentRecords[0], event: currentEvent }, recent };
}

function deriveOperationalHealth(status, runPayload, now = new Date()) {
  const unavailable = { state: 'unknown', available: false, latestRun: null, lastSuccess: null, nextExpectedAt: null };
  if (!status || status.schema_version !== 1 || typeof status.enabled !== 'boolean' ||
      typeof status.cadence !== 'string' || !status.cadence.trim() ||
      !Number.isFinite(status.expected_max_silence_hours) || status.expected_max_silence_hours <= 0) {
    return unavailable;
  }
  // OFF is the requested state, even if telemetry is temporarily unavailable.
  const invalidTelemetry = { ...unavailable, state: status.enabled ? 'unknown' : 'off' };
  if (!runPayload || runPayload.schema_version !== 1 || !Array.isArray(runPayload.runs) ||
      !Number.isFinite(now.getTime())) return invalidTelemetry;
  const runs = runPayload.runs;
  const timestamp = value => typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
  const counters = ['sources_checked', 'candidates_reviewed', 'events_admitted', 'events_published', 'material_updates'];
  const seen = new Set();
  let previous = -Infinity;
  for (const run of runs) {
    if (!run || typeof run.run_id !== 'string' || !run.run_id.trim() || seen.has(run.run_id) ||
        !timestamp(run.started_at) || !timestamp(run.completed_at) ||
        Date.parse(run.completed_at) < Date.parse(run.started_at) || Date.parse(run.started_at) <= previous ||
        Date.parse(run.completed_at) > now.getTime() ||
        !['success', 'partial', 'error'].includes(run.status) || !['scheduled', 'manual', 'external'].includes(run.trigger) ||
        typeof run.executor !== 'string' || !run.executor.trim() ||
        !Array.isArray(run.threads_checked) || run.threads_checked.some(item => typeof item !== 'string' || !item.trim()) ||
        counters.some(key => !Number.isInteger(run[key]) || run[key] < 0) ||
        (run.status === 'success' ? run.error_summary !== null : typeof run.error_summary !== 'string' || !run.error_summary.trim())) return invalidTelemetry;
    previous = Date.parse(run.started_at);
    seen.add(run.run_id);
  }
  const latestRun = runs.at(-1) || null;
  const lastSuccess = [...runs].reverse().find(run => run.status === 'success') || null;
  const lastOutcome = [...runs].reverse().find(run => run.status !== 'partial') || null;
  let state = 'unknown';
  if (!status.enabled) state = 'off';
  else if (lastOutcome?.status === 'error') state = 'error';
  else if (lastSuccess) {
    const threshold = Number(status.expected_max_silence_hours) * 3_600_000;
    state = now.getTime() <= new Date(lastSuccess.completed_at).getTime() + threshold ? 'healthy' : 'stale';
  }
  let cadenceMs = null;
  if (status.cadence === 'hourly') cadenceMs = 3_600_000;
  else {
    const match = /^every_(\d+)_hours$/.exec(status.cadence || '');
    if (match) cadenceMs = Number(match[1]) * 3_600_000;
  }
  const nextExpectedAt = status.enabled && lastSuccess && cadenceMs
    ? new Date(new Date(lastSuccess.completed_at).getTime() + cadenceMs).toISOString()
    : null;
  return { state, available: true, latestRun, lastSuccess, nextExpectedAt };
}

function renderOperationalStatus(status, runPayload) {
  const root = document.querySelector('#radar-status');
  root.replaceChildren();
  root.hidden = false;
  const model = deriveOperationalHealth(status, runPayload);
  const title = document.createElement('h2');
  title.className = `radar-status-title radar-status--${model.state}`;
  title.textContent = `RADAR — ${t.operations[model.state]}`;
  root.append(title);
  if (status?.schema_version === 1 && typeof status.enabled === 'boolean') {
    const desired = document.createElement('p');
    desired.textContent = `${t.operations.desired}: ${status.enabled ? t.operations.on : t.operations.off}. ${t.operations.desiredNote}`;
    root.append(desired);
  }
  if (!model.available) {
    const unavailable = document.createElement('p'); unavailable.textContent = t.operations.unavailable; root.append(unavailable);
  } else {
    const facts = document.createElement('div'); facts.className = 'radar-status-facts';
    const fact = (label, value) => {
      const item = document.createElement('p');
      const strong = document.createElement('strong'); strong.textContent = `${label}: `;
      item.append(strong, document.createTextNode(value)); facts.append(item);
    };
    if (model.latestRun) fact(t.operations.lastRun, formatTimestamp(model.latestRun.completed_at));
    if (model.lastSuccess) fact(t.operations.lastSuccess, formatTimestamp(model.lastSuccess.completed_at));
    if (!model.latestRun) { const empty = document.createElement('p'); empty.textContent = t.operations.noHeartbeat; facts.append(empty); }
    if (model.latestRun) {
      fact(t.operations.latestResult, model.latestRun.status.toUpperCase());
      const stats = document.createElement('p'); stats.textContent = t.operations.stats({
        sources: model.latestRun.sources_checked,
        candidates: model.latestRun.candidates_reviewed,
        published: model.latestRun.events_published,
        updates: model.latestRun.material_updates
      }); facts.append(stats);
      if (model.latestRun.error_summary) fact(t.operations.latestResult, model.latestRun.error_summary);
    }
    fact(t.operations.cadence, t.operations.cadenceValue(status.cadence));
    if (model.nextExpectedAt) fact(t.operations.nextExpected, formatTimestamp(model.nextExpectedAt));
    root.append(facts);
  }
  const actions = document.createElement('div'); actions.className = 'radar-status-actions';
  actions.append(
    link(t.operations.manage, 'https://github.com/iosorio/listening-notes/edit/main/radar/discovery/status.json'),
    link(t.operations.guide, 'https://github.com/iosorio/listening-notes/blob/main/docs/RADAR_OPERATIONS.md')
  );
  root.append(actions);
}

function filterButton(label, key, value, count) {
  const element = document.createElement('button');
  const active = state[key] === value;
  element.className = `filter ${active ? 'active' : ''}`;
  element.type = 'button';
  element.setAttribute('aria-pressed', String(active));
  element.dataset.key = key;
  element.dataset.value = value;
  element.textContent = label;
  if (value && count === 0) {
    element.disabled = true;
    element.classList.add('unavailable');
    const zero = document.createElement('span');
    zero.className = 'filter-zero';
    zero.setAttribute('aria-hidden', 'true');
    zero.textContent = '0';
    element.append(zero);
    element.setAttribute('aria-label', `${label} · ${t.noMatches}`);
  }
  element.onclick = () => {
    Object.assign(state, selectFacet(state, key, value, window.venueRegistry));
    render();
    const replacement = [...document.querySelectorAll('#filters button')].find(button =>
      button.dataset.key === key && button.dataset.value === value
    );
    replacement?.focus({ preventScroll: true });
  };
  return element;
}

function filterGroup(label, buttons) {
  const group = document.createElement('div');
  group.className = 'filter-group';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', label);
  group.append(...buttons);
  return group;
}

function viewButton(text, value) {
  const element = document.createElement('button');
  const active = state.view === value;
  element.className = `view ${active ? 'active' : ''}`;
  element.type = 'button';
  element.setAttribute('aria-pressed', String(active));
  element.dataset.value = value;
  element.textContent = text;
  element.onclick = () => {
    state.view = value;
    state.radar_area = '';
    state.venue = '';
    state.priority = '';
    const url = new URL(window.location.href);
    if (value === 'archive') url.searchParams.set('view', 'archive');
    else url.searchParams.delete('view');
    window.history.replaceState({}, '', url);
    updateViewButtons(); render();
    element.focus();
  };
  return element;
}

function updateViewButtons() {
  document.querySelectorAll('#views button').forEach(element => {
    const active = state.view === element.dataset.value;
    element.classList.toggle('active', active);
    element.setAttribute('aria-pressed', String(active));
  });
}

function buildViews() {
  document.querySelector('#views').replaceChildren(
    viewButton(t.viewUpcoming, 'upcoming'),
    viewButton(t.viewArchive, 'archive')
  );
}

function buildFilters(viewEvents) {
  const root = document.querySelector('#filters');
  const venueNames = new Map(viewEvents.map(event => [event.venue.id, event.venue.name]));
  const options = {
    radar_area: availableAreas(viewEvents, window.venueRegistry),
    venue: [...venueNames.keys()].sort((left, right) => venueNames.get(left).localeCompare(venueNames.get(right)) || left.localeCompare(right)),
    priority: ['S+', 'S', 'A+', 'A']
  };
  const counts = facetCounts(viewEvents, state, window.venueRegistry, options);
  root.replaceChildren(
    filterGroup(t.areaGroup, [filterButton(t.allAreas, 'radar_area', ''),
      ...options.radar_area.map(value => filterButton(t.areas[value] || value, 'radar_area', value, counts.radar_area.get(value)))]),
    filterGroup(t.venueGroup, [filterButton(t.allVenues, 'venue', ''),
      ...visibleFacetValues(options.venue, counts.venue, state.venue)
        .map(value => filterButton(venueNames.get(value), 'venue', value, counts.venue.get(value)))]),
    filterGroup(t.priorityGroup, [filterButton(t.allPriorities, 'priority', ''),
      ...visibleFacetValues(options.priority, counts.priority, state.priority)
        .map(value => filterButton(value, 'priority', value, counts.priority.get(value)))])
  );
}

function link(text, href, className = 'text-link') {
  const element = document.createElement('a');
  element.className = className;
  element.href = href;
  element.target = '_blank';
  element.rel = 'noreferrer';
  element.textContent = text;
  return element;
}

function sameDestination(left, right) {
  if (!left || !right) return false;
  try {
    const normalize = value => {
      const url = new URL(value);
      url.hash = '';
      url.pathname = url.pathname.replace(/\/$/, '') || '/';
      return url.toString();
    };
    return normalize(left) === normalize(right);
  } catch {
    return left === right;
  }
}

function verifiedAppleMusicUrl(event) {
  const recommendation = (event.recommended_listening || []).find(item => {
    if (!item || typeof item.apple_music_url !== 'string') return false;
    try {
      const url = new URL(item.apple_music_url);
      return url.protocol === 'https:' && url.hostname === 'music.apple.com' && /\/(album|song|playlist)\//.test(url.pathname);
    } catch {
      return false;
    }
  });
  return recommendation?.apple_music_url || null;
}

function eventActions(event, className = 'event-actions') {
  const actions = document.createElement('div');
  actions.className = className;
  const details = event.links.official_event;
  const tickets = event.links.official_tickets;
  if (sameDestination(details, tickets)) actions.append(link(t.detailsAndTickets, details));
  else {
    if (details) actions.append(link(t.details, details));
    if (tickets) actions.append(link(t.official, tickets));
  }
  return actions.children.length ? actions : null;
}

function meta(event) {
  const element = document.createElement('div');
  element.className = 'event-meta';
  element.innerHTML = `<span>${range(event)} · ${event.dates.start.slice(0, 4)}</span><span class="priority">${event.priority || t.archive}</span>`;
  return element;
}

function listening(event) {
  const recommendations = event.recommended_listening || [];
  const value = editorial(event).listen_before || recommendations
    .map(item => [item.artist, item.title].filter(Boolean).join(' — '))
    .filter(Boolean)
    .join('; ');
  if (!value) return null;
  const element = document.createElement('div');
  element.className = 'listening';
  const heading = document.createElement('strong'); heading.textContent = t.listen;
  const copy = document.createElement('span'); copy.textContent = value;
  element.append(heading, copy);
  const appleMusicUrl = verifiedAppleMusicUrl(event);
  if (appleMusicUrl) element.append(link(t.appleMusic, appleMusicUrl));
  return element;
}

function eventCard(event) {
  const article = document.createElement('article');
  const feature = event.priority === 'S+' ? ' event--splus' : event.priority === 'S' ? ' event--s' : event.priority === 'A+' ? ' event--aplus' : '';
  article.className = `event${feature}${isArchive(event) ? ' event--archive' : ''}`;
  article.dataset.eventId = event.id;
  article.dataset.priority = event.priority || 'archive';
  const title = document.createElement('h3'); title.textContent = event.artist;
  const subtitle = document.createElement('p'); subtitle.className = 'subtitle'; subtitle.textContent = event.subtitle || '';
  const venue = document.createElement('p'); venue.className = 'venue'; venue.textContent = `${event.venue.name} · ${event.venue.city}`;
  const travelLine = document.createElement('p'); travelLine.className = 'travel'; travelLine.textContent = travel(event);
  const why = document.createElement('p'); why.className = 'why'; why.textContent = editorial(event).why_it_matters || '';
  const discovery = document.createElement('p'); discovery.className = 'discovery';
  discovery.textContent = event.discovered_at ? `${t.discovered}: ${formatTimestamp(event.discovered_at)}` : t.discoveryUnknown;
  article.append(meta(event), title, subtitle, venue, travelLine, discovery);
  if (why.textContent) article.append(why);
  const listen = listening(event); if (listen) article.append(listen);
  if (!isArchive(event)) {
    const actions = eventActions(event);
    if (actions) article.append(actions);
  }
  return article;
}

function renderSignal(entry) {
  const root = document.querySelector('#signal');
  root.replaceChildren();
  if (!entry) { root.hidden = true; return; }
  root.hidden = false;
  const { event, record } = entry;
  const feature = document.createElement('article'); feature.className = 'signal-feature';
  const label = document.createElement('p'); label.className = 'signal-label'; label.textContent = t.signal;
  const title = document.createElement('h2'); title.textContent = event.artist;
  const subtitle = document.createElement('p'); subtitle.className = 'signal-subtitle'; subtitle.textContent = event.subtitle || '';
  const facts = document.createElement('p'); facts.className = 'signal-facts'; facts.textContent = `${range(event)} · ${event.venue.name} · ${event.venue.city}`;
  const priority = document.createElement('p'); priority.className = 'signal-priority'; priority.textContent = event.priority;
  const heading = document.createElement('strong'); heading.className = 'signal-heading'; heading.textContent = t.whyNow;
  const why = document.createElement('p'); why.className = 'signal-why'; why.textContent = record.editorial?.[lang]?.why_now || '';
  feature.append(label, priority, title, subtitle, facts, heading, why);
  const listen = listening(event); if (listen) feature.append(listen);
  const actions = eventActions(event, 'signal-actions'); if (actions) feature.append(actions);
  root.append(feature);
}

function renderRecentSignals(entries, visible) {
  const root = document.querySelector('#recent-signals');
  const list = document.querySelector('#recent-signal-list');
  list.replaceChildren();
  if (!visible || !entries.length) { root.hidden = true; return; }
  entries.forEach(({ event }) => {
    const card = document.createElement('article'); card.className = 'recent-signal';
    const title = document.createElement('h3'); title.textContent = event.artist;
    const facts = document.createElement('p'); facts.className = 'recent-signal-facts'; facts.textContent = `${range(event)} · ${event.venue.name} · ${event.venue.city}`;
    const priority = document.createElement('span'); priority.className = 'recent-signal-priority'; priority.textContent = event.priority;
    card.append(priority, title, facts);
    list.append(card);
  });
  root.hidden = false;
}

function section(title, subtext, events, root) {
  const wrap = document.createElement('section');
  const heading = document.createElement('div'); heading.className = 'section-head';
  heading.innerHTML = `<p class="kicker">${title}</p>${subtext ? `<p>${subtext}</p>` : ''}`;
  const grid = document.createElement('div'); grid.className = 'grid';
  if (events.length) events.forEach(event => grid.append(eventCard(event)));
  else { const empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = t.empty; grid.append(empty); }
  wrap.append(heading, grid); root.append(wrap);
}

function renderCount(model) {
  const total = model.viewEvents.length;
  const noun = state.view === 'archive' ? t.archiveCount : t.upcomingCount;
  document.querySelector('#count').textContent = hasActiveFilters(state)
    ? `${model.selected.length} ${t.shown} · ${total} ${noun}`
    : `${total} ${noun}`;
}

function render() {
  const current = window.signalState.current;
  const today = localDate();
  const initial = deriveRadarView(window.eventsData, state, current?.event || null, today, window.venueRegistry);
  Object.assign(state, validFacetState(initial.viewEvents, state, window.venueRegistry));
  const model = deriveRadarView(window.eventsData, state, current?.event || null, today, window.venueRegistry);
  buildFilters(model.viewEvents);
  const showEditorialSignal = window.signalState.valid && model.signalVisible;
  renderCount(model);
  renderSignal(showEditorialSignal ? current : null);
  renderRecentSignals(window.signalState.recent, showEditorialSignal);
  const root = document.querySelector('#radar'); root.replaceChildren();
  if (state.view === 'archive') section(t.archive, t.archiveText, model.results, root);
  else section(t.upcoming, '', model.results, root);
}

function fetchJson(url, options) {
  return fetch(url, options).then(response => {
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    return response.json();
  });
}

function loadOperationalStatus() {
  const statusUrl = lang === 'es' ? '../discovery/status.json' : 'discovery/status.json';
  const runsUrl = lang === 'es' ? '../discovery/runs.json' : 'discovery/runs.json';
  return Promise.all([fetchJson(statusUrl, {cache: 'no-store'}).catch(() => null), fetchJson(runsUrl, {cache: 'no-store'}).catch(() => null)])
    .then(([statusPayload, runPayload]) => renderOperationalStatus(statusPayload, runPayload));
}

function loadRadar() {
  // Status must remain visible even if the event catalog fails to load.
  loadOperationalStatus();
  // Refresh telemetry and visitor-time staleness while the page stays open.
  window.setInterval(loadOperationalStatus, 60_000);
  const eventUrl = lang === 'es' ? '../events.json' : 'events.json';
  const signalUrl = lang === 'es' ? '../signals.json' : 'signals.json';
  const venueUrl = lang === 'es' ? '../venue_identities.json' : 'venue_identities.json';
  Promise.all([fetchJson(eventUrl), fetchJson(venueUrl), fetchJson(signalUrl).catch(() => null)])
    .then(([eventPayload, venuePayload, signalPayload]) => {
      window.eventsData = eventPayload.events;
      window.venueRegistry = venuePayload;
      window.signalState = resolveSignalState(signalPayload, window.eventsData);
      buildViews();
      document.querySelector('#rule-title').textContent = t.rule;
      document.querySelector('#rule-text').textContent = t.ruleText;
      render();
    })
    .catch(() => { document.querySelector('#radar').innerHTML = `<p class="empty">${t.loadError}</p>`; });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AREA_ORDER, COPY, availableAreas, deriveOperationalHealth, deriveRadarView, facetCounts, hasActiveFilters, isArchiveAt, radarAreaFor, resolveSignalState, selectFacet, validFacetState, visibleFacetValues };
}

if (hasDocument) loadRadar();
