import { installPack as installOfflinePack, listInstalledPacks, loadInstalledPack, removePack as removeOfflinePack } from './offline-db.js';

const API = {
  bootstrap: '/api/bootstrap',
  taxa: '/api/taxa',
  taxon: id => `/api/taxa/${encodeURIComponent(id)}`,
  deck: '/api/decks/preview',
  packs: '/api/packs',
  pack: key => `/api/packs/${encodeURIComponent(key)}`
};

const STORAGE = {
  filters: 'arbotflash.v0_5.savedFilterStack',
  progress: 'arbotflash.v0_5.progress',
  offlinePack: 'arbotflash.v0_5.offlineSeedPack',
  session: 'arbotflash.v0_5.session'
};

const loadJson = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
};

const state = {
  definitions: [],
  active: new Map(),
  search: '',
  results: [],
  resultCount: 0,
  facets: {},
  offlineTaxa: [],
  offlineProfiles: {},
  deck: [],
  cardIndex: 0,
  questionMode: 'common-to-scientific',
  progress: loadJson(STORAGE.progress, loadJson('arbotflash.v0_3.progress', {})),
  session: { correct: 0, incorrect: 0, streak: 0, bestStreak: 0 },
  profileCache: new Map(),
  online: true,
  requestSerial: 0,
  meta: {}
};

const byId = id => document.getElementById(id);
const elements = {
  filters: byId('filters'),
  active: byId('activeFilters'),
  clear: byId('clearAll'),
  resultList: byId('resultList'),
  resultCount: byId('resultCount'),
  matchCount: byId('matchCount'),
  search: byId('nameSearch'),
  save: byId('saveStack'),
  build: byId('buildDeck'),
  deckSize: byId('deckSize'),
  customSize: byId('customDeckSize'),
  customSizeWrap: byId('customDeckSizeWrap'),
  selection: byId('selectionMode'),
  question: byId('questionMode'),
  deckMessage: byId('deckMessage'),
  study: byId('studyArea'),
  prompt: byId('cardPrompt'),
  answer: byId('cardAnswer'),
  reveal: byId('revealAnswer'),
  previous: byId('previousCard'),
  next: byId('nextCard'),
  correct: byId('markCorrect'),
  incorrect: byId('markIncorrect'),
  speak: byId('speakCard'),
  cardPosition: byId('cardPosition'),
  sessionCorrect: byId('sessionCorrect'),
  sessionIncorrect: byId('sessionIncorrect'),
  sessionStreak: byId('sessionStreak'),
  status: byId('dataStatus'),
  databaseSummary: byId('databaseSummary'),
  error: byId('errorBanner'),
  packStatus: byId('packStatus'),
  packMessage: byId('packMessage'),
  installPack: byId('installPack'),
  removePack: byId('removePack')
};

const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[character]));

function showError(message) {
  elements.error.textContent = message;
  elements.error.classList.toggle('hidden', !message);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function serialiseActive() {
  return Object.fromEntries([...state.active].map(([key, values]) => [key, [...values]]));
}

function activeFilterTokens() {
  return [...state.active].flatMap(([key, values]) => [...values].map(value => `${key}:${value}`));
}

function groups() {
  return [...new Set(state.definitions.map(definition => definition.group))];
}

function selectedValues(key) {
  return state.active.get(key) || new Set();
}

function relevant(definition) {
  if (!definition.appliesTo) return true;
  const selectedKingdoms = selectedValues('kingdom');
  if (selectedKingdoms.size) return [...selectedKingdoms].some(value => definition.appliesTo.includes(value));
  const kingdoms = new Set(state.results.map(taxon => taxon.kingdom).filter(Boolean));
  return definition.appliesTo.some(kingdom => kingdoms.has(kingdom));
}

function renderFilters() {
  elements.filters.innerHTML = groups().map(group => {
    const defs = state.definitions
      .filter(definition => definition.group === group && relevant(definition))
      .map(definition => ({ definition, options: state.facets[definition.key] || [] }))
      .filter(item => item.options.length > 0);
    if (!defs.length) return '';
    const open = ['Taxonomy', 'Universal', 'Data quality', 'Plant identification'].includes(group) ? 'open' : '';
    return `<details ${open}><summary>${escapeHtml(group)} <span>${defs.length}</span></summary>${defs.map(({ definition, options }) => `
      <div class="filter-row">
        <label for="filter-${escapeHtml(definition.key)}">${escapeHtml(definition.label)}</label>
        <select id="filter-${escapeHtml(definition.key)}" data-filter="${escapeHtml(definition.key)}">
          <option value="">Add a value…</option>
          ${options.map(option => {
            const chosen = selectedValues(definition.key).has(String(option.value));
            return `<option value="${escapeHtml(option.value)}" ${chosen ? 'disabled' : ''}>${escapeHtml(option.value)} (${option.count})${chosen ? ' ✓' : ''}</option>`;
          }).join('')}
        </select>
      </div>`).join('')}</details>`;
  }).join('');

  elements.filters.querySelectorAll('[data-filter]').forEach(select => {
    select.addEventListener('change', event => {
      const key = event.target.dataset.filter;
      const value = event.target.value;
      if (!value) return;
      if (!state.active.has(key)) state.active.set(key, new Set());
      state.active.get(key).add(value);
      event.target.value = '';
      applyFilters();
    });
  });
}

function renderActive() {
  if (!state.active.size && !state.search) {
    elements.active.innerHTML = '<span class="empty-chip">No filters — showing the complete 80-taxon seed pack</span>';
    return;
  }
  const chips = [];
  if (state.search) chips.push(`<span class="chip">Search: ${escapeHtml(state.search)}<button data-clear-search aria-label="Clear search">×</button></span>`);
  for (const [key, values] of state.active) {
    const label = state.definitions.find(definition => definition.key === key)?.label || key;
    for (const value of values) {
      chips.push(`<span class="chip">${escapeHtml(label)}: ${escapeHtml(value)}<button data-remove-key="${escapeHtml(key)}" data-remove-value="${escapeHtml(value)}" aria-label="Remove ${escapeHtml(label)} ${escapeHtml(value)}">×</button></span>`);
    }
  }
  elements.active.innerHTML = chips.join('');
  elements.active.querySelectorAll('[data-remove-key]').forEach(button => button.addEventListener('click', () => {
    const values = state.active.get(button.dataset.removeKey);
    values?.delete(button.dataset.removeValue);
    if (!values?.size) state.active.delete(button.dataset.removeKey);
    applyFilters();
  }));
  elements.active.querySelector('[data-clear-search]')?.addEventListener('click', () => {
    state.search = '';
    elements.search.value = '';
    applyFilters();
  });
}

function valueMatches(recordValue, selectedValuesForKey) {
  if (!selectedValuesForKey.size) return true;
  if (Array.isArray(recordValue)) return recordValue.some(value => selectedValuesForKey.has(String(value)));
  return selectedValuesForKey.has(String(recordValue));
}

function localFilter(taxa) {
  const search = state.search.trim().toLowerCase();
  return taxa.filter(taxon => {
    const searchable = `${taxon.commonName} ${taxon.scientificName} ${taxon.family} ${taxon.genus} ${taxon.order || ''}`.toLowerCase();
    if (search && !searchable.includes(search)) return false;
    return [...state.active].every(([key, values]) => valueMatches(taxon[key], values));
  });
}

function buildLocalFacets(taxa) {
  const facets = {};
  for (const definition of state.definitions) {
    const counts = new Map();
    for (const taxon of taxa) {
      const value = taxon[definition.key];
      const values = Array.isArray(value) ? value : [value];
      for (const item of new Set(values.filter(Boolean).map(String))) counts.set(item, (counts.get(item) || 0) + 1);
    }
    if (counts.size) facets[definition.key] = [...counts].sort((a, b) => a[0].localeCompare(b[0])).map(([value, count]) => ({ value, count }));
  }
  return facets;
}

async function applyFilters() {
  const serial = ++state.requestSerial;
  renderActive();
  elements.resultList.innerHTML = '<p class="muted">Querying taxon database…</p>';
  const params = new URLSearchParams({ search: state.search, limit: '500' });
  for (const token of activeFilterTokens()) params.append('filter', token);
  try {
    const payload = await fetchJson(`${API.taxa}?${params}`);
    if (serial !== state.requestSerial) return;
    state.results = payload.items;
    state.resultCount = payload.count;
    state.facets = payload.facets;
    state.online = true;
    elements.status.textContent = 'Database connected';
    elements.status.className = 'connection-status connected';
    showError('');
  } catch (error) {
    if (serial !== state.requestSerial) return;
    state.online = false;
    state.results = localFilter(state.offlineTaxa);
    state.resultCount = state.results.length;
    state.facets = buildLocalFacets(state.offlineTaxa);
    elements.status.textContent = 'Offline seed-pack mode';
    elements.status.className = 'connection-status offline';
    showError(`The API is unavailable, so ArbotFlash is filtering the cached 80-tree offline pack. ${error.message}`);
  }
  renderResults();
  renderFilters();
}

function renderResults() {
  elements.resultCount.textContent = state.resultCount;
  elements.matchCount.textContent = state.resultCount;
  if (!state.results.length) {
    elements.resultList.innerHTML = '<p class="muted">No loaded taxa match this filter stack.</p>';
    return;
  }
  elements.resultList.innerHTML = state.results.map(taxon => `<article class="result" data-taxon="${escapeHtml(taxon.id)}">
    <div class="result-heading"><div><h3>${escapeHtml(taxon.commonName)}</h3><p class="scientific">${escapeHtml(taxon.scientificName)}</p></div><span class="data-dot" title="${escapeHtml(taxon.verification)}"></span></div>
    <div class="result-meta"><span>${escapeHtml(taxon.family)}</span><span>${escapeHtml(taxon.genus)}</span><span>${escapeHtml(taxon.profileStatus || 'Profile pending')}</span><span>${escapeHtml(taxon.taxonomyReconciliation || 'Taxonomy pending')}</span></div>
  </article>`).join('');
  elements.resultList.querySelectorAll('[data-taxon]').forEach(card => card.addEventListener('click', () => {
    const taxon = state.results.find(item => item.id === card.dataset.taxon) || state.offlineTaxa.find(item => item.id === card.dataset.taxon);
    if (!taxon) return;
    state.deck = [taxon];
    state.cardIndex = 0;
    state.questionMode = elements.question.value;
    elements.study.classList.remove('hidden');
    renderCard();
    elements.study.scrollIntoView({ behavior: 'smooth' });
  }));
}

function progressFor(taxon) {
  return state.progress[taxon.id] || { attempts: 0, correct: 0, incorrect: 0, lastStudiedAt: null };
}

function selectDeckLocally() {
  let deck = [...localFilter(state.offlineTaxa)];
  const mode = elements.selection.value;
  const score = taxon => {
    const progress = progressFor(taxon);
    if (mode === 'new') return progress.attempts === 0 ? 0 : 1;
    if (mode === 'incorrect') return progress.incorrect > 0 ? -progress.incorrect : 1;
    if (mode === 'least') return progress.attempts;
    if (mode === 'difficult') return progress.attempts ? progress.correct / progress.attempts : 1;
    return 0;
  };
  if (mode === 'alphabetical') deck.sort((a, b) => a.scientificName.localeCompare(b.scientificName));
  else if (['new', 'incorrect', 'least', 'difficult'].includes(mode)) deck.sort((a, b) => score(a) - score(b));
  else deck.sort(() => Math.random() - 0.5);
  if (mode === 'new') deck = deck.filter(taxon => progressFor(taxon).attempts === 0);
  if (mode === 'incorrect') deck = deck.filter(taxon => progressFor(taxon).incorrect > 0);
  return deck;
}

async function buildDeck() {
  const size = elements.deckSize.value === 'all'
    ? 'all'
    : elements.deckSize.value === 'custom'
      ? Math.max(1, Number(elements.customSize.value) || 1)
      : Number(elements.deckSize.value);
  let deck;
  try {
    const payload = await fetchJson(API.deck, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        search: state.search,
        filters: serialiseActive(),
        size,
        selectionMode: elements.selection.value,
        progress: state.progress
      })
    });
    deck = payload.items;
  } catch {
    deck = selectDeckLocally();
    const resolvedSize = size === 'all' ? deck.length : size;
    deck = deck.slice(0, Math.min(resolvedSize, deck.length));
  }

  state.deck = deck;
  state.cardIndex = 0;
  state.questionMode = elements.question.value;
  state.session = { correct: 0, incorrect: 0, streak: 0, bestStreak: 0 };
  renderSessionStats();
  elements.deckMessage.textContent = deck.length
    ? `Deck built with ${deck.length} taxa using ${elements.selection.value} selection.`
    : `No taxa currently qualify for ${elements.selection.value} selection.`;
  elements.study.classList.toggle('hidden', !deck.length);
  if (deck.length) {
    renderCard();
    elements.study.scrollIntoView({ behavior: 'smooth' });
  }
}

function questionFor(taxon) {
  switch (state.questionMode) {
    case 'scientific-to-common': return [taxon.scientificName, taxon.commonName, 'Scientific name', 'Common name'];
    case 'genus-to-family': return [taxon.genus, taxon.family, 'Genus', 'Family'];
    case 'family-to-genus': return [taxon.family, taxon.genus, 'Family', 'Genus'];
    default: return [taxon.commonName, taxon.scientificName, 'Common name', 'Scientific name'];
  }
}

function sectionBody(profile, key, fallback) {
  const section = profile?.profileSections?.find(item => item.section_key === key);
  return section?.body_markdown || fallback;
}

function renderProfileShell(taxon) {
  byId('profileName').textContent = taxon.commonName;
  byId('profileScientific').textContent = taxon.scientificName;
  byId('profileBadges').innerHTML = [taxon.domain, taxon.kingdom, taxon.phylum, taxon.family, taxon.lifeStatus, taxon.verification]
    .filter(Boolean).map(value => `<span class="chip">${escapeHtml(value)}</span>`).join('');
  byId('profileClassification').innerHTML = [taxon.domain, taxon.kingdom, taxon.phylum, taxon.class, taxon.order, taxon.family, taxon.genus, taxon.scientificName]
    .filter(Boolean).map(value => `<span>${escapeHtml(value)}</span>`).join('<b>›</b>');
  byId('profileSummary').textContent = 'Loading sourced profile sections…';
  byId('profileFeatures').textContent = '';
  byId('profileDistribution').textContent = '';
  byId('profileAdditionalSections').innerHTML = '';
  byId('profileAdditionalWrap').classList.add('hidden');
  byId('profileNames').innerHTML = '<p class="muted">Loading name records…</p>';
  byId('profileReconciliation').innerHTML = '<p class="muted">Loading source matches…</p>';
  byId('profileSources').innerHTML = '';
  byId('profileMedia').textContent = 'Loading media records…';
}

const PROFILE_LABELS = {
  habitat: 'Habitat',
  phenology: 'Flowering and seasonal timing',
  conservation_status: 'Conservation status',
  exudates: 'Sap, kino, gum, resin and exudates',
  fire_response: 'Fire response',
  ecology: 'Ecology',
  data_quality: 'Data quality and review notes'
};

function renderAdditionalSections(profile) {
  const coreKeys = new Set(['summary', 'identifying_features', 'distribution']);
  const sections = (profile.profileSections || []).filter(item => !coreKeys.has(item.section_key));
  const wrap = byId('profileAdditionalWrap');
  if (!sections.length) {
    wrap.classList.add('hidden');
    byId('profileAdditionalSections').innerHTML = '';
    return;
  }
  wrap.classList.remove('hidden');
  byId('profileAdditionalSections').innerHTML = sections.map(item => `
    <article class="profile-detail">
      <div class="profile-detail-heading">
        <h4>${escapeHtml(PROFILE_LABELS[item.section_key] || item.section_key.replaceAll('_', ' '))}</h4>
        <span class="verification-tag">${escapeHtml(item.verification_status.replaceAll('_', ' '))}</span>
      </div>
      <p>${escapeHtml(item.body_markdown)}</p>
      ${item.source_revision ? `<small>${escapeHtml(item.source_revision)}</small>` : ''}
    </article>`).join('');
}

function renderDetailedProfile(profile) {
  byId('profileSummary').textContent = sectionBody(profile, 'summary', 'No sourced summary is attached yet.');
  byId('profileFeatures').textContent = sectionBody(profile, 'identifying_features', 'No sourced identification description is attached yet.');
  byId('profileDistribution').textContent = sectionBody(profile, 'distribution', 'No sourced distribution record is attached yet.');
  byId('profileClassification').innerHTML = (profile.classifications || []).map(item => `<span><small>${escapeHtml(item.rank)}</small>${escapeHtml(item.name)}</span>`).join('<b>›</b>');
  renderAdditionalSections(profile);
  byId('profileNames').innerHTML = (profile.names || []).map(item => `<div class="data-row"><strong>${escapeHtml(item.name)}${item.authorship ? ` ${escapeHtml(item.authorship)}` : ''}</strong><span>${escapeHtml(item.status)}${item.language_code ? ` · ${escapeHtml(item.language_code)}` : ''} · ${escapeHtml(item.verification_status.replaceAll('_', ' '))}</span></div>`).join('') || '<p class="muted">No name records.</p>';
  byId('profileReconciliation').innerHTML = (profile.reconciliation || []).map(item => `<div class="data-row"><strong>${escapeHtml(item.source_title)}</strong><span>${escapeHtml(item.status.replaceAll('_', ' '))}</span><p>${escapeHtml(item.notes || '')}</p></div>`).join('') || '<p class="muted">No reconciliation records.</p>';
  const uniqueCitations = [...new Map((profile.citations || []).map(item => [`${item.citation_text}|${item.source_url}`, item])).values()];
  byId('profileSources').innerHTML = uniqueCitations.map(item => `<li><strong>${escapeHtml(item.source_title || 'Source')}</strong>: ${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.citation_text)}</a>` : escapeHtml(item.citation_text)}${item.release_key ? ` · release ${escapeHtml(item.release_key)}` : ''}</li>`).join('') || '<li>No citations attached.</li>';
  if (profile.media?.length) {
    byId('profileMedia').innerHTML = profile.media.map(item => `<figure>
      <a href="${escapeHtml(item.source_page_url || item.original_url)}" target="_blank" rel="noopener noreferrer"><img src="${escapeHtml(item.display_url || item.storage_key || item.original_url)}" alt="${escapeHtml(item.caption || profile.commonName)}" loading="lazy"></a>
      <figcaption>${escapeHtml(item.caption || item.category)}<br>${escapeHtml(item.creator || 'Unknown creator')} · ${item.licence_url ? `<a href="${escapeHtml(item.licence_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.licence_code)}</a>` : escapeHtml(item.licence_code)} · ${escapeHtml(item.verification_status.replaceAll('_', ' '))}</figcaption>
    </figure>`).join('');
  } else {
    byId('profileMedia').textContent = 'No licensed species images attached yet. Image records will retain creator, source, licence and verification status.';
  }
}

async function loadProfile(taxon) {
  const requestedId = taxon.id;
  if (state.profileCache.has(requestedId)) {
    renderDetailedProfile(state.profileCache.get(requestedId));
    return;
  }
  try {
    const profile = await fetchJson(API.taxon(requestedId));
    state.profileCache.set(requestedId, profile);
    if (state.deck[state.cardIndex]?.id === requestedId) renderDetailedProfile(profile);
  } catch {
    const installedProfile = state.offlineProfiles[requestedId];
    if (installedProfile) {
      state.profileCache.set(requestedId, installedProfile);
      if (state.deck[state.cardIndex]?.id === requestedId) renderDetailedProfile(installedProfile);
      return;
    }
    const fallback = {
      ...taxon,
      classifications: [
        ['domain', taxon.domain], ['kingdom', taxon.kingdom], ['phylum', taxon.phylum], ['class', taxon.class],
        ['order', taxon.order], ['family', taxon.family], ['genus', taxon.genus]
      ].filter(([, name]) => name).map(([rank, name]) => ({ rank, name })),
      names: [
        { name: taxon.scientificName, status: 'accepted study name' },
        { name: taxon.commonName, status: 'common', language_code: 'en' }
      ],
      profileSections: [], citations: [], reconciliation: [], media: []
    };
    if (state.deck[state.cardIndex]?.id === requestedId) renderDetailedProfile(fallback);
  }
}

function renderCard() {
  const taxon = state.deck[state.cardIndex];
  if (!taxon) return;
  const [prompt, answer, promptLabel, answerLabel] = questionFor(taxon);
  byId('cardPromptLabel').textContent = promptLabel;
  byId('cardAnswerLabel').textContent = answerLabel;
  elements.prompt.textContent = prompt;
  elements.answer.textContent = answer;
  elements.answer.classList.add('hidden');
  byId('answerActions').classList.add('hidden');
  elements.reveal.textContent = 'Reveal answer';
  elements.cardPosition.textContent = `${state.cardIndex + 1} / ${state.deck.length}`;
  renderProfileShell(taxon);
  loadProfile(taxon);
}

function renderSessionStats() {
  elements.sessionCorrect.textContent = state.session.correct;
  elements.sessionIncorrect.textContent = state.session.incorrect;
  elements.sessionStreak.textContent = state.session.streak;
}

function markAnswer(correct) {
  const taxon = state.deck[state.cardIndex];
  if (!taxon) return;
  const progress = progressFor(taxon);
  progress.attempts += 1;
  if (correct) progress.correct += 1;
  else progress.incorrect += 1;
  progress.lastStudiedAt = new Date().toISOString();
  state.progress[taxon.id] = progress;
  localStorage.setItem(STORAGE.progress, JSON.stringify(state.progress));
  if (correct) {
    state.session.correct += 1;
    state.session.streak += 1;
    state.session.bestStreak = Math.max(state.session.bestStreak, state.session.streak);
  } else {
    state.session.incorrect += 1;
    state.session.streak = 0;
  }
  renderSessionStats();
  if (state.deck.length > 1) {
    state.cardIndex = (state.cardIndex + 1) % state.deck.length;
    renderCard();
  }
}

function speakCurrentCard() {
  if (!('speechSynthesis' in window)) return;
  const taxon = state.deck[state.cardIndex];
  if (!taxon) return;
  const [prompt, answer] = questionFor(taxon);
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(`${prompt}. ${answer}.`);
  utterance.lang = 'en-AU';
  speechSynthesis.speak(utterance);
}

let searchTimer;
elements.search.addEventListener('input', event => {
  state.search = event.target.value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(applyFilters, 180);
});
elements.clear.addEventListener('click', () => {
  state.active.clear();
  state.search = '';
  elements.search.value = '';
  applyFilters();
});
elements.save.addEventListener('click', () => {
  const saved = {
    savedAt: new Date().toISOString(),
    filters: serialiseActive(),
    search: state.search,
    matchingTaxonIds: state.results.map(taxon => taxon.id),
    sourcePack: 'Tree ID Trainer 80',
    databaseSchema: state.meta.schema_version || '0.12.0'
  };
  localStorage.setItem(STORAGE.filters, JSON.stringify(saved));
  elements.save.textContent = 'Saved locally';
  setTimeout(() => { elements.save.textContent = 'Save filter stack'; }, 1300);
});
elements.deckSize.addEventListener('change', () => {
  elements.customSizeWrap.classList.toggle('hidden', elements.deckSize.value !== 'custom');
});
elements.build.addEventListener('click', buildDeck);
elements.reveal.addEventListener('click', () => {
  const hidden = elements.answer.classList.toggle('hidden');
  byId('answerActions').classList.toggle('hidden', hidden);
  elements.reveal.textContent = hidden ? 'Reveal answer' : 'Hide answer';
});
elements.previous.addEventListener('click', () => {
  if (!state.deck.length) return;
  state.cardIndex = (state.cardIndex - 1 + state.deck.length) % state.deck.length;
  renderCard();
});
elements.next.addEventListener('click', () => {
  if (!state.deck.length) return;
  state.cardIndex = (state.cardIndex + 1) % state.deck.length;
  renderCard();
});
elements.correct.addEventListener('click', () => markAnswer(true));
elements.incorrect.addEventListener('click', () => markAnswer(false));
elements.speak.addEventListener('click', speakCurrentCard);

async function refreshPackStatus() {
  try {
    const packs = await listInstalledPacks();
    const installed = packs.find(pack => pack.packKey === 'tree-id-80');
    if (installed) {
      elements.packStatus.textContent = `Installed v${installed.version}`;
      elements.packStatus.className = 'connection-status connected';
      elements.packMessage.textContent = `Installed ${new Date(installed.installedAt).toLocaleString()} · ${installed.manifest.coverage.taxonCount} taxa · ${installed.manifest.coverage.localMediaCount} local images.`;
      elements.removePack.classList.remove('hidden');
      elements.installPack.textContent = 'Update offline pack';
    } else {
      elements.packStatus.textContent = 'Not installed';
      elements.packStatus.className = 'connection-status offline';
      elements.packMessage.textContent = 'The app still has a small static fallback, but installing the pack preserves full profiles and reviewed images offline.';
      elements.removePack.classList.add('hidden');
      elements.installPack.textContent = 'Install offline pack';
    }
  } catch (error) {
    elements.packStatus.textContent = 'Storage unavailable';
    elements.packStatus.className = 'connection-status offline';
    elements.packMessage.textContent = error.message;
  }
}

async function useInstalledPack() {
  const installed = await loadInstalledPack('tree-id-80');
  if (!installed) return false;
  const definitions = await fetchJson('./data/filter-definitions.json');
  state.definitions = definitions;
  state.results = installed.taxa;
  state.resultCount = installed.taxa.length;
  state.offlineTaxa = installed.taxa;
  state.offlineProfiles = installed.profiles;
  state.facets = buildLocalFacets(installed.taxa);
  state.meta = { schema_version: installed.manifest.version, installedPack: installed.manifest };
  state.online = false;
  elements.status.textContent = 'Installed offline pack';
  elements.status.className = 'connection-status offline';
  elements.databaseSummary.textContent = `${installed.taxa.length} taxa loaded from the installed Tree ID 80 pack · ${installed.manifest.coverage.enrichedTaxa} source-enriched · ${installed.manifest.coverage.localMediaCount} locally stored images.`;
  return true;
}

async function useStaticFallback() {
  const [definitions, taxa] = await Promise.all([
    fetchJson('./data/filter-definitions.json'),
    fetchJson('./data/treeid-seed-80.json')
  ]);
  state.definitions = definitions;
  state.results = taxa;
  state.resultCount = taxa.length;
  state.offlineTaxa = taxa;
  state.offlineProfiles = {};
  state.facets = buildLocalFacets(taxa);
  state.online = false;
  elements.status.textContent = 'Static seed fallback';
  elements.status.className = 'connection-status offline';
  elements.databaseSummary.textContent = `${taxa.length} taxa loaded from the lightweight static fallback. Install the full regional pack for sourced profiles and reviewed media offline.`;
}

async function initialise() {
  await refreshPackStatus();
  try {
    const payload = await fetchJson(API.bootstrap);
    state.definitions = payload.definitions;
    state.results = payload.taxa;
    state.resultCount = payload.taxa.length;
    state.facets = payload.facets;
    state.offlineTaxa = payload.taxa;
    state.meta = payload.meta;
    elements.status.textContent = 'Database connected';
    elements.status.className = 'connection-status connected';
    elements.databaseSummary.textContent = `${payload.meta.taxonCount} taxa · ${payload.meta.enrichedTaxa} source-enriched · ${payload.meta.locallyStoredMediaCount} locally stored licensed images · ${payload.meta.profileShellCount} transparent profile shells · ${payload.meta.pendingReconciliations} global matches still queued`;
  } catch (error) {
    try {
      const loaded = await useInstalledPack();
      if (!loaded) await useStaticFallback();
      showError(loaded
        ? `The API is unavailable, so ArbotFlash loaded the installed offline pack. ${error.message}`
        : `The API and installed pack are unavailable, so ArbotFlash loaded the lightweight static seed. ${error.message}`);
    } catch (fallbackError) {
      elements.status.textContent = 'Database unavailable';
      elements.status.className = 'connection-status offline';
      showError(`ArbotFlash could not load the API, an installed pack or the static fallback: ${fallbackError.message}`);
      return;
    }
  }
  renderActive();
  renderResults();
  renderFilters();
  renderSessionStats();
}

async function installSelectedPack() {
  elements.installPack.disabled = true;
  elements.packStatus.textContent = 'Installing…';
  elements.packMessage.textContent = 'Downloading taxa, profiles and reviewed media into offline storage.';
  try {
    const installed = await installOfflinePack('tree-id-80');
    elements.packMessage.textContent = `Installed ${installed.taxa.length} taxa and ${installed.manifest.coverage.localMediaCount} locally cached images.`;
    await refreshPackStatus();
  } catch (error) {
    elements.packStatus.textContent = 'Install failed';
    elements.packStatus.className = 'connection-status offline';
    elements.packMessage.textContent = error.message;
  } finally {
    elements.installPack.disabled = false;
  }
}

async function removeSelectedPack() {
  elements.removePack.disabled = true;
  try {
    await removeOfflinePack('tree-id-80');
    await refreshPackStatus();
  } catch (error) {
    elements.packMessage.textContent = error.message;
  } finally {
    elements.removePack.disabled = false;
  }
}

elements.installPack.addEventListener('click', installSelectedPack);
elements.removePack.addEventListener('click', removeSelectedPack);

initialise();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(() => {});
