const COPY = {
  en: {
    allCities: 'All cities', allVenues: 'All venues', allPriorities: 'All priorities',
    viewUpcoming: 'Upcoming', viewArchive: 'Archive', upcoming: 'On the radar', archive: 'Nights we heard',
    selected: 'selected', onRadar: 'on radar', signal: 'The Signal', why: 'Why it matters',
    listen: 'Listen before', appleMusic: 'Listen on Apple Music', official: 'Official tickets', details: 'Details', detailsAndTickets: 'Details & Tickets',
    rule: 'The criterion', ruleText: 'The radar is intentionally incomplete. <b>If it is here, there is a reason.</b>',
    archiveText: 'Dates that became part of the listening life.',
    empty: 'Nothing in this selection. The filter is part of the curation.',
    status: { considering: 'on the radar', going: 'going', attended: 'heard', passed: 'passed' },
    travel: { Local: 'Local', 'Short trip': 'Short trip', Trip: 'Worth the train', Tokyo: 'Build the night around it' },
    categories: { 'Living masters': 'Living masters', 'Modern jazz': 'Modern jazz', 'Brazil / Latin': 'Brazil / Latin', 'Fusion / progressive': 'Fusion / progressive', 'Experimental / rock / metal': 'Experimental / rock / metal', Japan: 'Japan' }
  },
  es: {
    allCities: 'Todas las ciudades', allVenues: 'Todos los recintos', allPriorities: 'Todas las prioridades',
    viewUpcoming: 'Próximos', viewArchive: 'Archivo', upcoming: 'En el radar', archive: 'Noches que escuchamos',
    selected: 'seleccionados', onRadar: 'en el radar', signal: 'La señal', why: 'Por qué importa',
    listen: 'Para escuchar antes', appleMusic: 'Escuchar en Apple Music', official: 'Boletos oficiales', details: 'Información', detailsAndTickets: 'Información y boletos',
    rule: 'El criterio', ruleText: 'El radar es deliberadamente selectivo. <b>Si está aquí, hay una razón.</b>',
    archiveText: 'Fechas que ya forman parte de la memoria de escucha.',
    empty: 'Nada en esta selección. El filtro también es parte de la curaduría.',
    status: { considering: 'en el radar', going: 'voy', attended: 'escuchamos', passed: 'pasó' },
    travel: { Local: 'Local', 'Short trip': 'Escapada corta', Trip: 'Vale el tren', Tokyo: 'Vale construir la noche alrededor' },
    categories: { 'Living masters': 'Maestros vivos', 'Modern jazz': 'Jazz contemporáneo', 'Brazil / Latin': 'Brasil / Latinoamérica', 'Fusion / progressive': 'Fusión / prog', 'Experimental / rock / metal': 'Experimental / rock / metal', Japan: 'Japón' }
  }
};

const lang = document.documentElement.lang.startsWith('es') ? 'es' : 'en';
const t = COPY[lang];
const state = { city: '', venue: '', priority: '', view: 'upcoming' };
const priorityRank = { 'S+': 0, S: 1, 'A+': 2, A: 3 };

const formatDate = value => new Intl.DateTimeFormat(lang === 'es' ? 'es-US' : 'en-US', { month: 'short', day: 'numeric' }).format(new Date(`${value}T12:00:00`));
const range = event => event.dates.end && event.dates.end !== event.dates.start ? `${formatDate(event.dates.start)}–${formatDate(event.dates.end)}` : formatDate(event.dates.start);
const unique = (events, value) => [...new Set(events.map(value).filter(Boolean))].sort();
const editorial = event => event.editorial[lang] || {};
const isArchive = event => event.status === 'attended' || event.status === 'passed';
const travel = event => t.travel[event.geography] || event.geography;

function matches(event) {
  return (!state.city || event.venue.city === state.city) &&
    (!state.venue || event.venue.name === state.venue) &&
    (!state.priority || event.priority === state.priority);
}

function filterButton(text, key, value) {
  const element = document.createElement('button');
  element.className = `filter ${state[key] === value ? 'active' : ''}`;
  element.type = 'button';
  element.textContent = text;
  element.onclick = () => { state[key] = value; buildFilters(); render(); };
  return element;
}

function viewButton(text, value) {
  const element = document.createElement('button');
  element.className = `view ${state.view === value ? 'active' : ''}`;
  element.type = 'button';
  element.textContent = text;
  element.onclick = () => { state.view = value; buildViews(); render(); };
  return element;
}

function buildViews() {
  const root = document.querySelector('#views');
  root.replaceChildren(viewButton(t.viewUpcoming, 'upcoming'), viewButton(t.viewArchive, 'archive'));
}

function buildFilters() {
  const root = document.querySelector('#filters');
  const events = window.eventsData;
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
  element.innerHTML = `<strong>${t.listen}</strong><span></span>`;
  element.querySelector('span').textContent = value;
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

function chooseSignal(events) {
  return [...events].sort((left, right) => {
    const marked = Number(Boolean(right.featured || right.signal)) - Number(Boolean(left.featured || left.signal));
    return marked || (priorityRank[left.priority] ?? 99) - (priorityRank[right.priority] ?? 99) || left.dates.start.localeCompare(right.dates.start);
  })[0];
}

function renderSignal(event) {
  const root = document.querySelector('#signal');
  root.replaceChildren();
  if (!event || state.view !== 'upcoming') { root.hidden = true; return; }
  root.hidden = false;
  const feature = document.createElement('article'); feature.className = 'signal-feature';
  const label = document.createElement('p'); label.className = 'signal-label'; label.textContent = t.signal;
  const title = document.createElement('h2'); title.textContent = event.artist;
  const subtitle = document.createElement('p'); subtitle.className = 'signal-subtitle'; subtitle.textContent = event.subtitle || '';
  const facts = document.createElement('p'); facts.className = 'signal-facts'; facts.textContent = `${range(event)} · ${event.venue.name} · ${event.venue.city}`;
  const priority = document.createElement('p'); priority.className = 'signal-priority'; priority.textContent = event.priority;
  const why = document.createElement('p'); why.className = 'signal-why'; why.textContent = editorial(event).why_it_matters || '';
  feature.append(label, priority, title, subtitle, facts);
  if (why.textContent) { const heading = document.createElement('strong'); heading.className = 'signal-heading'; heading.textContent = t.why; feature.append(heading, why); }
  const listen = listening(event); if (listen) feature.append(listen);
  const actions = eventActions(event, 'signal-actions');
  if (actions) feature.append(actions);
  root.append(feature);
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

function render() {
  const selected = window.eventsData.filter(matches).sort((left, right) => left.dates.start.localeCompare(right.dates.start));
  const upcoming = selected.filter(event => !isArchive(event));
  const archive = selected.filter(isArchive);
  const signal = state.view === 'upcoming' ? chooseSignal(upcoming) : null;
  document.querySelector('#count').textContent = `${selected.length} ${t.selected} · ${window.eventsData.length} ${t.onRadar}`;
  renderSignal(signal);
  const root = document.querySelector('#radar'); root.replaceChildren();
  if (state.view === 'archive') section(t.archive, t.archiveText, archive, root);
  else section(t.upcoming, '', upcoming.filter(event => event.id !== signal?.id), root);
}

fetch(lang === 'es' ? '../events.json' : 'events.json')
  .then(response => response.json())
  .then(payload => {
    window.eventsData = payload.events;
    buildViews(); buildFilters();
    document.querySelector('#rule-title').textContent = t.rule;
    document.querySelector('#rule-text').innerHTML = t.ruleText;
    render();
  })
  .catch(() => { document.querySelector('#radar').innerHTML = '<p class="empty">Could not load event data.</p>'; });
