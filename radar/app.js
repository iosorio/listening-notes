const COPY = {
  en: {
    allCities: 'All cities', allVenues: 'All venues', allPriorities: 'All priorities',
    viewUpcoming: 'Upcoming', viewArchive: 'Archive', upcoming: 'On the radar', archive: 'RADAR archive',
    shown: 'shown', upcomingCount: 'upcoming', archiveCount: 'archived', signal: 'The Signal', whyNow: 'Why now',
    recentSignals: 'Recent Signals', listen: 'Listen before', appleMusic: 'Listen on Apple Music',
    official: 'Official tickets', details: 'Details', detailsAndTickets: 'Details & Tickets',
    rule: 'The criterion', ruleText: 'The radar is intentionally selective. Its choices are editorial, not comprehensive.',
    archiveText: 'Attended nights and finished dates retained in the RADAR record.',
    empty: 'Nothing in this selection. The filter is part of the curation.',
    loadError: 'Could not load event data.',
    status: { considering: 'on the radar', going: 'going', attended: 'heard', passed: 'passed' },
    travel: { Local: 'Local', 'Short trip': 'Short trip', Trip: 'Worth the train', Tokyo: 'Build the night around it' },
    categories: { 'Living masters': 'Living masters', 'Modern jazz': 'Modern jazz', 'Brazil / Latin': 'Brazil / Latin', 'Fusion / progressive': 'Fusion / progressive', 'Experimental / rock / metal': 'Experimental / rock / metal', Japan: 'Japan' }
  },
  es: {
    allCities: 'Todas las ciudades', allVenues: 'Todos los recintos', allPriorities: 'Todas las prioridades',
    viewUpcoming: 'Próximos', viewArchive: 'Archivo', upcoming: 'En el radar', archive: 'Archivo RADAR',
    shown: 'mostrados', upcomingCount: 'próximos', archiveCount: 'archivados', signal: 'La señal', whyNow: 'Por qué ahora',
    recentSignals: 'Señales recientes', listen: 'Para escuchar antes', appleMusic: 'Escuchar en Apple Music',
    official: 'Boletos oficiales', details: 'Información', detailsAndTickets: 'Información y boletos',
    rule: 'El criterio', ruleText: 'El radar es deliberadamente selectivo. Sus elecciones son editoriales, no exhaustivas.',
    archiveText: 'Noches asistidas y fechas terminadas que se conservan en el registro de RADAR.',
    empty: 'Nada en esta selección. El filtro también es parte de la curaduría.',
    loadError: 'No fue posible cargar los eventos.',
    status: { considering: 'en el radar', going: 'voy', attended: 'escuchamos', passed: 'pasó' },
    travel: { Local: 'Local', 'Short trip': 'Escapada corta', Trip: 'Vale el tren', Tokyo: 'Vale construir la noche alrededor' },
    categories: { 'Living masters': 'Maestros vivos', 'Modern jazz': 'Jazz contemporáneo', 'Brazil / Latin': 'Brasil / Latinoamérica', 'Fusion / progressive': 'Fusión / prog', 'Experimental / rock / metal': 'Experimental / rock / metal', Japan: 'Japón' }
  }
};

const hasDocument = typeof document !== 'undefined';
const lang = hasDocument && document.documentElement.lang.startsWith('es') ? 'es' : 'en';
const t = COPY[lang];
const requestedView = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('view') : null;
const state = { city: '', venue: '', priority: '', view: requestedView === 'archive' ? 'archive' : 'upcoming' };

const formatDate = value => new Intl.DateTimeFormat(lang === 'es' ? 'es-US' : 'en-US', { month: 'short', day: 'numeric' }).format(new Date(`${value}T12:00:00`));
const range = event => event.dates.end && event.dates.end !== event.dates.start ? `${formatDate(event.dates.start)}–${formatDate(event.dates.end)}` : formatDate(event.dates.start);
const unique = (events, value) => [...new Set(events.map(value).filter(Boolean))].sort();
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
const hasActiveFilters = viewState => Boolean(viewState.city || viewState.venue || viewState.priority);

function matchesState(event, viewState) {
  return (!viewState.city || event.venue.city === viewState.city) &&
    (!viewState.venue || event.venue.name === viewState.venue) &&
    (!viewState.priority || event.priority === viewState.priority);
}

function deriveRadarView(events, viewState, currentSignalEvent, today) {
  const archiveView = viewState.view === 'archive';
  const viewEvents = events.filter(event => archiveView ? isArchiveAt(event, today) : !isArchiveAt(event, today));
  const selected = viewEvents.filter(event => matchesState(event, viewState))
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

function eventsInView() {
  return window.eventsData.filter(event => state.view === 'archive' ? isArchive(event) : !isArchive(event));
}

function filterButton(text, key, value) {
  const element = document.createElement('button');
  const active = state[key] === value;
  element.className = `filter ${active ? 'active' : ''}`;
  element.type = 'button';
  element.setAttribute('aria-pressed', String(active));
  element.textContent = text;
  element.onclick = () => { state[key] = value; buildFilters(); render(); };
  return element;
}

function viewButton(text, value) {
  const element = document.createElement('button');
  const active = state.view === value;
  element.className = `view ${active ? 'active' : ''}`;
  element.type = 'button';
  element.setAttribute('aria-pressed', String(active));
  element.textContent = text;
  element.onclick = () => {
    state.view = value;
    state.city = '';
    state.venue = '';
    state.priority = '';
    const url = new URL(window.location.href);
    if (value === 'archive') url.searchParams.set('view', 'archive');
    else url.searchParams.delete('view');
    window.history.replaceState({}, '', url);
    buildViews(); buildFilters(); render();
  };
  return element;
}

function buildViews() {
  document.querySelector('#views').replaceChildren(
    viewButton(t.viewUpcoming, 'upcoming'),
    viewButton(t.viewArchive, 'archive')
  );
}

function buildFilters() {
  const root = document.querySelector('#filters');
  const events = eventsInView();
  root.replaceChildren(
    filterButton(t.allCities, 'city', ''),
    ...unique(events, event => event.venue.city).map(value => filterButton(value, 'city', value)),
    filterButton(t.allVenues, 'venue', ''),
    ...unique(events, event => event.venue.name).map(value => filterButton(value, 'venue', value)),
    filterButton(t.allPriorities, 'priority', ''),
    ...['S+', 'S', 'A+', 'A'].map(value => filterButton(value, 'priority', value))
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
  article.dataset.priority = event.priority || 'archive';
  const title = document.createElement('h3'); title.textContent = event.artist;
  const subtitle = document.createElement('p'); subtitle.className = 'subtitle'; subtitle.textContent = event.subtitle || '';
  const venue = document.createElement('p'); venue.className = 'venue'; venue.textContent = `${event.venue.name} · ${event.venue.city}`;
  const travelLine = document.createElement('p'); travelLine.className = 'travel'; travelLine.textContent = travel(event);
  const why = document.createElement('p'); why.className = 'why'; why.textContent = editorial(event).why_it_matters || '';
  article.append(meta(event), title, subtitle, venue, travelLine);
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
  const model = deriveRadarView(window.eventsData, state, current?.event || null, localDate());
  const showEditorialSignal = window.signalState.valid && model.signalVisible;
  renderCount(model);
  renderSignal(showEditorialSignal ? current : null);
  renderRecentSignals(window.signalState.recent, showEditorialSignal);
  const root = document.querySelector('#radar'); root.replaceChildren();
  if (state.view === 'archive') section(t.archive, t.archiveText, model.results, root);
  else section(t.upcoming, '', model.results, root);
}

function fetchJson(url) {
  return fetch(url).then(response => {
    if (!response.ok) throw new Error(`${url}: ${response.status}`);
    return response.json();
  });
}

function loadRadar() {
  const eventUrl = lang === 'es' ? '../events.json' : 'events.json';
  const signalUrl = lang === 'es' ? '../signals.json' : 'signals.json';
  Promise.all([fetchJson(eventUrl), fetchJson(signalUrl).catch(() => null)])
    .then(([eventPayload, signalPayload]) => {
      window.eventsData = eventPayload.events;
      window.signalState = resolveSignalState(signalPayload, window.eventsData);
      buildViews(); buildFilters();
      document.querySelector('#rule-title').textContent = t.rule;
      document.querySelector('#rule-text').textContent = t.ruleText;
      render();
    })
    .catch(() => { document.querySelector('#radar').innerHTML = `<p class="empty">${t.loadError}</p>`; });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { deriveRadarView, hasActiveFilters, isArchiveAt, resolveSignalState };
}

if (hasDocument) loadRadar();
