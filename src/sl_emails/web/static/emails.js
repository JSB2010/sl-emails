(() => {
  const defaults = window.__EMAIL_REVIEW_DEFAULTS__ || {};
  const SOURCE_COLORS = {
    athletics: '#0C3A6B',
    arts: '#A11919',
    custom: '#8C6A00',
  };
  const EMPTY_PREVIEW = '<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;padding:32px;color:#4a607c;">Preview not generated yet.</body></html>';

  const state = {
    weekId: defaults.weekId || '',
    week: null,
    outputs: null,
    dirty: false,
    filters: {
      query: '',
      source: 'all',
      visibility: 'all',
    },
  };

  const els = {
    weekId: document.getElementById('week-id'),
    loadBtn: document.getElementById('load-week'),
    createBtn: document.getElementById('create-from-source'),
    saveBtn: document.getElementById('save-week'),
    previewBtn: document.getElementById('preview-week'),
    approveBtn: document.getElementById('approve-week'),
    markUnsentBtn: document.getElementById('mark-unsent'),
    addBtn: document.getElementById('add-custom'),
    exportBtn: document.getElementById('export-csv'),
    heading: document.getElementById('week-heading'),
    notes: document.getElementById('week-notes'),
    eventSearch: document.getElementById('event-search'),
    sourceFilter: document.getElementById('event-source-filter'),
    visibilityFilter: document.getElementById('event-visibility-filter'),
    clearFiltersBtn: document.getElementById('clear-event-filters'),
    filteredCount: document.getElementById('filtered-count'),
    tbody: document.getElementById('events-tbody'),
    flash: document.getElementById('flash'),
    weekSummary: document.getElementById('week-summary'),
    stateBanner: document.getElementById('state-banner'),
    stateTitle: document.getElementById('state-title'),
    stateDetail: document.getElementById('state-detail'),
    stateMeta: document.getElementById('state-meta'),
    eventCount: document.getElementById('event-count'),
    previewStatus: document.getElementById('preview-status'),
    msSubject: document.getElementById('ms-subject'),
    usSubject: document.getElementById('us-subject'),
    msCount: document.getElementById('ms-count'),
    usCount: document.getElementById('us-count'),
    msFrame: document.getElementById('preview-middle-school'),
    usFrame: document.getElementById('preview-upper-school'),
    statusIngest: document.getElementById('status-ingest'),
    statusRefresh: document.getElementById('status-refresh'),
    statusReviewEmail: document.getElementById('status-review-email'),
    statusApproval: document.getElementById('status-approval'),
    statusSend: document.getElementById('status-send'),
  };

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function weekEndFromStart(startValue) {
    const date = new Date(`${startValue}T00:00:00`);
    if (Number.isNaN(date.getTime())) return startValue;
    date.setDate(date.getDate() + 6);
    return date.toISOString().slice(0, 10);
  }

  function normalizeAudiences(raw) {
    const values = Array.isArray(raw) ? raw : (raw ? [raw] : []);
    const normalized = [];
    values.forEach((value) => {
      const text = String(value).trim().toLowerCase().replaceAll('_', '-');
      if (text === 'all' || text === 'both' || text === 'both-audiences') {
        normalized.push('middle-school', 'upper-school');
      }
      if (text === 'middle-school' || text === 'middle school' || text === 'ms') normalized.push('middle-school');
      if (text === 'upper-school' || text === 'upper school' || text === 'us') normalized.push('upper-school');
    });
    return Array.from(new Set(normalized));
  }

  function looksMiddleSchool(label) {
    const value = ` ${String(label || '').toLowerCase()} `;
    return ['middle school', ' ms ', ' 6th', ' 7th', ' 8th', 'sixth', 'seventh', 'eighth']
      .some((indicator) => value.includes(indicator));
  }

  function inferAudiences(event) {
    const explicit = normalizeAudiences(event.audiences || event.audience || event.school_levels || event.school_level);
    if (explicit.length) return explicit;

    const source = String(event.source || 'custom').trim().toLowerCase() || 'custom';
    const label = String(event.team || event.title || '').trim();
    if (source === 'custom') return ['middle-school', 'upper-school'];
    if (looksMiddleSchool(label)) return ['middle-school'];
    if (source === 'athletics' || source === 'arts') return ['upper-school'];
    return ['middle-school', 'upper-school'];
  }

  function audienceChoiceForEvent(event) {
    const audiences = normalizeAudiences(event.audiences);
    if (audiences.includes('middle-school') && audiences.includes('upper-school')) return 'both';
    if (audiences[0] === 'middle-school') return 'middle-school';
    return 'upper-school';
  }

  function audiencesFromChoice(choice) {
    if (choice === 'middle-school') return ['middle-school'];
    if (choice === 'upper-school') return ['upper-school'];
    return ['middle-school', 'upper-school'];
  }

  function resetFilters() {
    state.filters = { query: '', source: 'all', visibility: 'all' };
  }

  function filtersAreActive() {
    return Boolean(state.filters.query || state.filters.source !== 'all' || state.filters.visibility !== 'all');
  }

  function filteredEventRows() {
    if (!state.week) return [];
    const query = state.filters.query.trim().toLowerCase();
    return state.week.events
      .map((event, index) => ({ event, index }))
      .filter(({ event }) => {
        const matchesQuery = !query || [event.title, event.subtitle, event.location, event.category, event.team, event.opponent]
          .join(' ')
          .toLowerCase()
          .includes(query);
        const matchesSource = state.filters.source === 'all' || event.source === state.filters.source;
        const isHidden = event.status === 'hidden';
        const matchesVisibility = state.filters.visibility === 'all'
          || (state.filters.visibility === 'hidden' && isHidden)
          || (state.filters.visibility === 'visible' && !isHidden);
        return matchesQuery && matchesSource && matchesVisibility;
      });
  }

  function defaultAccent(source) {
    return SOURCE_COLORS[source] || SOURCE_COLORS.custom;
  }

  function sourceClass(source) {
    if (source === 'athletics') return 'source-athletics';
    if (source === 'arts') return 'source-arts';
    return 'source-custom';
  }

  function deriveOpponent(subtitle) {
    return String(subtitle || '').replace(/^vs\.?\s*/i, '').replace(/^@\s*/i, '').trim();
  }

  function normalizeEvent(event) {
    const source = String(event.source || 'custom').trim().toLowerCase() || 'custom';
    const title = String(event.title || event.team || '').trim();
    const opponent = String(event.opponent || '').trim();
    const audiences = inferAudiences(event);
    return {
      id: String(event.id || crypto.randomUUID()),
      source,
      kind: String(event.kind || (opponent ? 'game' : 'event')).trim().toLowerCase() || 'event',
      title,
      subtitle: String(event.subtitle || (opponent ? `vs. ${opponent}` : '')).trim(),
      start_date: String(event.start_date || event.date || state.weekId || defaults.weekId || '').trim(),
      end_date: String(event.end_date || event.start_date || event.date || state.weekId || defaults.weekId || '').trim(),
      time_text: String(event.time_text || event.time || 'TBA').trim() || 'TBA',
      location: String(event.location || 'On Campus').trim() || 'On Campus',
      category: String(event.category || 'School Event').trim() || 'School Event',
      audiences,
      status: String(event.status || 'active').trim().toLowerCase() || 'active',
      link: String(event.link || '').trim(),
      description: String(event.description || '').trim(),
      badge: String(event.badge || (source === 'custom' ? 'SPECIAL' : 'EVENT')).trim() || 'EVENT',
      priority: Number(event.priority || 3),
      accent: String(event.accent || defaultAccent(source)).trim() || defaultAccent(source),
      team: String(event.team || title).trim(),
      opponent,
      is_home: event.is_home !== false,
      metadata: typeof event.metadata === 'object' && event.metadata ? event.metadata : {},
      source_id: String(event.source_id || '').trim(),
      created_at: String(event.created_at || '').trim(),
      updated_at: String(event.updated_at || '').trim(),
    };
  }

  function blankWeek(weekId) {
    return {
      week_id: weekId,
      start_date: weekId,
      end_date: weekEndFromStart(weekId),
      heading: 'This Week at Kent Denver',
      status: 'draft',
      approval: { approved: false, approved_at: '', approved_by: '' },
      sent: { sent: false, sent_at: '', sent_by: '', sending: false, sending_at: '', sending_by: '' },
      notes: '',
      events: [],
    };
  }

  function createCustomEventTemplate() {
    return normalizeEvent({
      source: 'custom',
      kind: 'event',
      title: 'Custom Event',
      subtitle: 'School Event',
      start_date: state.week?.start_date || state.weekId || defaults.weekId || '',
      end_date: state.week?.start_date || state.weekId || defaults.weekId || '',
      time_text: '6:00 PM',
      location: 'Kent Denver',
      category: 'School Event',
      audiences: ['middle-school', 'upper-school'],
      status: 'active',
      badge: 'SPECIAL',
      accent: SOURCE_COLORS.custom,
    });
  }

  let _flashTimer = null;

  function setFlash(message, isError = false) {
    clearTimeout(_flashTimer);
    els.flash.textContent = message;
    els.flash.classList.toggle('flash-error', isError);
    els.flash.classList.add('flash-show');
    _flashTimer = setTimeout(() => {
      els.flash.classList.remove('flash-show');
    }, 5000);
  }

  function setButtonBusy(button, busy) {
    button.disabled = busy;
  }

  async function fetchJson(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => null);
    if (response.status === 401 && data && data.login_url) {
      window.location.href = data.login_url;
      throw new Error('Authentication required');
    }
    if (response.status === 403 && data && data.access_denied_url) {
      window.location.href = data.access_denied_url;
      throw new Error('Access denied');
    }
    if (!response.ok || (data && data.ok === false)) {
      throw new Error((data && data.error) || `Request failed (${response.status})`);
    }
    return data || {};
  }

  function formatActivity(activity, emptyText) {
    if (!activity || typeof activity !== 'object') return emptyText;
    const status = String(activity.status || '').trim();
    const actor = String(activity.actor || '').trim();
    const occurredAt = String(activity.occurred_at || '').trim();
    const message = String(activity.message || '').trim();
    const parts = [];
    if (status) parts.push(status);
    if (actor) parts.push(`by ${actor}`);
    if (occurredAt) parts.push(`at ${occurredAt}`);
    if (message) parts.push(message);
    if (activity.source_summary && Number(activity.source_summary.total_events || 0) > 0) {
      parts.push(`${Number(activity.source_summary.total_events || 0)} imported events`);
    }
    return parts.length ? parts.join(' · ') : emptyText;
  }

  function applyWeek(week) {
    resetFilters();
    state.week = {
      ...week,
      events: (week.events || []).map(normalizeEvent),
    };
    state.weekId = state.week.week_id;
    state.dirty = false;
    render();
  }

  function markDirty(flag = true) {
    state.dirty = flag;
    renderMeta();
  }

  function renderMeta() {
    const week = state.week;
    if (!week) {
      els.weekSummary.textContent = 'No draft loaded';
      els.stateBanner.className = 'state-banner state-draft';
      els.stateTitle.textContent = 'Draft';
      els.stateDetail.textContent = 'Load a week to review imported events and prepare previews.';
      els.stateMeta.textContent = 'Waiting for a weekly draft.';
      els.eventCount.textContent = '0 events';
      els.previewStatus.textContent = 'Preview not generated';
      return;
    }

    const events = week.events || [];
    const hidden = events.filter((event) => event.status === 'hidden').length;
    const visible = events.length - hidden;
    const custom = events.filter((event) => event.source === 'custom').length;
    const unsaved = state.dirty ? ' · unsaved changes' : '';
    const approved = week.approval?.approved;
    const sent = Boolean(week.sent?.sent);
    const sending = Boolean(week.sent?.sending);

    els.weekSummary.textContent = `${week.start_date} → ${week.end_date}`;
    els.eventCount.textContent = `${events.length} events (${visible} visible, ${custom} custom)`;

    if (sent) {
      els.stateBanner.className = 'state-banner state-sent';
      els.stateTitle.textContent = 'Already sent';
      els.stateDetail.textContent = 'This week has already been marked sent. Use “Mark Unsent” to reopen it for edits or resend prep.';
      els.stateMeta.textContent = `Sent by ${week.sent.sent_by || 'sender'} at ${week.sent.sent_at || 'an unknown time'}${unsaved}`;
    } else if (sending) {
      els.stateBanner.className = 'state-banner state-sent';
      els.stateTitle.textContent = 'Send in progress';
      els.stateDetail.textContent = 'This week is currently marked sending. Use “Mark Unsent” to clear the send lock before editing or retrying.';
      els.stateMeta.textContent = `Claimed by ${week.sent.sending_by || 'sender'} at ${week.sent.sending_at || 'an unknown time'}${unsaved}`;
    } else if (approved) {
      els.stateBanner.className = 'state-banner state-approved';
      els.stateTitle.textContent = 'Approved';
      els.stateDetail.textContent = 'This week is approved and ready for sender output.';
      els.stateMeta.textContent = `Approved by ${week.approval.approved_by || 'admin'} at ${week.approval.approved_at || 'an unknown time'}${unsaved}`;
    } else {
      els.stateBanner.className = 'state-banner state-draft';
      els.stateTitle.textContent = state.dirty ? 'Draft · unsaved changes' : 'Draft';
      els.stateDetail.textContent = hidden ? `Hidden events stay in the draft but will be omitted from preview and sender output.` : 'Draft changes can be previewed and approved when ready.';
      els.stateMeta.textContent = `${visible} visible event${visible === 1 ? '' : 's'} · ${hidden} hidden${unsaved}`;
    }

    els.previewStatus.textContent = state.outputs ? 'Preview ready' : 'Preview not generated';
  }

  function renderPreviewAudience(output, subjectEl, countEl, frameEl) {
    if (!output) {
      subjectEl.textContent = 'No preview yet';
      countEl.textContent = '0 events';
      frameEl.srcdoc = EMPTY_PREVIEW;
      return;
    }

    subjectEl.textContent = output.subject || 'No subject';
    countEl.textContent = `${output.source_event_count || 0} events`;
    frameEl.srcdoc = output.html || EMPTY_PREVIEW;
  }

  function renderPreview() {
    renderPreviewAudience(state.outputs?.['middle-school'], els.msSubject, els.msCount, els.msFrame);
    renderPreviewAudience(state.outputs?.['upper-school'], els.usSubject, els.usCount, els.usFrame);
  }

  function renderStatus() {
    const week = state.week;
    if (!week) {
      els.statusIngest.textContent = 'No week loaded yet.';
      els.statusRefresh.textContent = 'No week loaded yet.';
      els.statusReviewEmail.textContent = 'No week loaded yet.';
      els.statusApproval.textContent = 'No week loaded yet.';
      els.statusSend.textContent = 'No week loaded yet.';
      return;
    }

    const metadata = week.metadata || {};
    els.statusIngest.textContent = formatActivity(metadata.scheduled_ingest, 'No automation run recorded yet.');
    els.statusRefresh.textContent = formatActivity(metadata.manual_refresh, 'No manual refresh recorded yet.');
    els.statusReviewEmail.textContent = formatActivity(metadata.review_notification, 'No review notification recorded yet.');
    els.statusApproval.textContent = week.approval?.approved
      ? `approved by ${week.approval.approved_by || 'admin'} at ${week.approval.approved_at || 'unknown time'}`
      : 'Week has not been approved yet.';
    if (week.sent?.sent) {
      els.statusSend.textContent = `sent by ${week.sent.sent_by || 'automation'} at ${week.sent.sent_at || 'unknown time'}`;
    } else if (week.sent?.sending) {
      els.statusSend.textContent = `claimed for sending by ${week.sent.sending_by || 'automation'} at ${week.sent.sending_at || 'unknown time'}`;
    } else {
      els.statusSend.textContent = formatActivity(metadata.send, 'No send claim or completion recorded yet.');
    }
  }

  function renderFilters() {
    els.eventSearch.value = state.filters.query;
    els.sourceFilter.value = state.filters.source;
    els.visibilityFilter.value = state.filters.visibility;

    if (!state.week) {
      els.filteredCount.textContent = 'No events loaded';
      els.clearFiltersBtn.disabled = true;
      return;
    }

    const total = state.week.events.length;
    const shown = filteredEventRows().length;
    els.filteredCount.textContent = filtersAreActive() ? `Showing ${shown} of ${total}` : `All ${total} events shown`;
    els.clearFiltersBtn.disabled = !filtersAreActive();
  }

  function rowMarkup(event, index) {
    const isHidden = event.status === 'hidden';
    const audienceChoice = audienceChoiceForEvent(event);
    return `
      <tr data-index="${index}" class="${isHidden ? 'row-hidden' : ''}">
        <td>
          <span class="source-pill ${sourceClass(event.source)}">${escapeHtml(event.source)}</span>
        </td>
        <td>
          <div class="cell-stack">
            <select class="mini-select" data-field="kind">
              <option value="event" ${event.kind === 'event' ? 'selected' : ''}>Event</option>
              <option value="game" ${event.kind === 'game' ? 'selected' : ''}>Game</option>
            </select>
            <input class="mini-input" type="text" data-field="title" value="${escapeHtml(event.title)}" placeholder="Title" />
            <input class="mini-input" type="text" data-field="subtitle" value="${escapeHtml(event.subtitle)}" placeholder="Subtitle or opponent" />
            <input class="mini-input" type="text" data-field="category" value="${escapeHtml(event.category)}" placeholder="Category" />
          </div>
        </td>
        <td>
          <div class="inline-pair">
            <label class="inline-field">Start
              <input class="mini-input" type="date" data-field="start_date" value="${escapeHtml(event.start_date)}" />
            </label>
            <label class="inline-field">End
              <input class="mini-input" type="date" data-field="end_date" value="${escapeHtml(event.end_date)}" />
            </label>
          </div>
        </td>
        <td>
          <div class="cell-stack">
            <input class="mini-input" type="text" data-field="time_text" value="${escapeHtml(event.time_text)}" placeholder="Time" />
            <input class="mini-input" type="text" data-field="location" value="${escapeHtml(event.location)}" placeholder="Location" />
          </div>
        </td>
        <td>
          <div class="cell-stack">
            <select class="mini-select" data-field="audience_choice">
              <option value="middle-school" ${audienceChoice === 'middle-school' ? 'selected' : ''}>Middle School</option>
              <option value="upper-school" ${audienceChoice === 'upper-school' ? 'selected' : ''}>Upper School</option>
              <option value="both" ${audienceChoice === 'both' ? 'selected' : ''}>Both Audiences</option>
            </select>
            <p class="field-note">Controls which preview and sender output includes this row.</p>
          </div>
        </td>
        <td>
          <div class="cell-stack">
            <select class="mini-select" data-field="status">
              <option value="active" ${event.status !== 'hidden' ? 'selected' : ''}>Visible</option>
              <option value="hidden" ${event.status === 'hidden' ? 'selected' : ''}>Hidden</option>
            </select>
            <p class="field-note">${isHidden ? 'Hidden rows are omitted from preview and sender output.' : 'Visible rows appear in preview and sender output.'}</p>
          </div>
        </td>
        <td>
          <div class="cell-stack">
            <input class="mini-input" type="url" data-field="link" value="${escapeHtml(event.link)}" placeholder="Optional link URL" />
            <textarea class="mini-textarea" data-field="description" placeholder="Optional notes or details">${escapeHtml(event.description)}</textarea>
          </div>
        </td>
        <td>
          <div class="row-actions">
            <button class="row-action" data-action="duplicate" type="button">Duplicate</button>
            <button class="row-remove row-action-danger" data-action="remove" type="button">Delete</button>
          </div>
        </td>
      </tr>
    `;
  }

  function renderRows() {
    if (!state.week) {
      els.tbody.innerHTML = '<tr><td colspan="8" class="empty-row">Load a week to begin reviewing events.</td></tr>';
      return;
    }

    if (!state.week.events.length) {
      els.tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No events yet. Create a draft from source events or add a custom announcement.</td></tr>';
      return;
    }

    const rows = filteredEventRows();
    if (!rows.length) {
      els.tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No events match the current filters. Clear filters to review the full draft.</td></tr>';
      return;
    }

    els.tbody.innerHTML = rows.map(({ event, index }) => rowMarkup(event, index)).join('');
  }

  function render() {
    els.weekId.value = state.weekId;
    els.heading.value = state.week?.heading || 'This Week at Kent Denver';
    els.notes.value = state.week?.notes || '';
    renderMeta();
    renderFilters();
    renderRows();
    renderPreview();
    renderStatus();

    const isSent = Boolean(state.week?.sent?.sent);
    const isSending = Boolean(state.week?.sent?.sending);
    const isSendLocked = isSent || isSending;
    els.exportBtn.disabled = !state.week || !(state.week.events || []).length;
    els.createBtn.disabled = !state.week || isSendLocked;
    els.addBtn.disabled = !state.week || isSendLocked;
    els.saveBtn.disabled = !state.week || isSendLocked;
    els.previewBtn.disabled = !state.week;
    els.approveBtn.disabled = !state.week || isSendLocked;
    els.markUnsentBtn.hidden = !isSendLocked;
    els.markUnsentBtn.disabled = !state.week || !isSendLocked;
  }

  function currentWeekId() {
    const value = String(els.weekId.value || state.weekId || '').trim();
    if (!value) throw new Error('Choose a Monday week start first.');
    return value;
  }

  function syncWeekFields() {
    if (!state.week) return;
    state.week.heading = els.heading.value.trim() || 'This Week at Kent Denver';
    state.week.notes = els.notes.value.trim();
  }

  async function loadWeek() {
    const weekId = currentWeekId();
    state.weekId = weekId;
    setButtonBusy(els.loadBtn, true);
    setFlash(`Loading week ${weekId}...`);

    try {
      const data = await fetchJson(`/api/emails/weeks/${weekId}`);
      state.outputs = null;
      applyWeek(data.week);
      setFlash(`Loaded weekly draft for ${weekId}.`);
      await previewWeek({ silent: true, autoSave: false });
    } catch (error) {
      if (/No weekly draft found/i.test(error.message)) {
        state.outputs = null;
        applyWeek(blankWeek(weekId));
        setFlash('No saved draft found for this week yet. Create one from source events or start with custom rows.');
      } else {
        setFlash(error.message || 'Unable to load week.', true);
      }
    } finally {
      setButtonBusy(els.loadBtn, false);
    }
  }

  function mapFetchedEvent(event) {
    return normalizeEvent({
      source: event.source,
      kind: event.kind || (event.source === 'athletics' ? 'game' : 'event'),
      title: event.title,
      subtitle: event.subtitle,
      start_date: event.date,
      end_date: event.date,
      time_text: event.time,
      location: event.location,
      category: event.category,
      audiences: event.audiences,
      badge: event.badge,
      priority: event.priority,
      accent: event.accent,
      team: event.team || event.title,
      opponent: event.opponent || deriveOpponent(event.subtitle),
      is_home: event.is_home,
      metadata: event.metadata,
      source_id: event.source_id,
    });
  }

  function serializeEvent(event) {
    const opponent = deriveOpponent(event.subtitle) || event.opponent;
    return {
      id: event.id,
      source: event.source,
      kind: event.kind,
      title: event.title,
      subtitle: event.subtitle,
      start_date: event.start_date,
      end_date: event.end_date || event.start_date,
      time_text: event.time_text,
      location: event.location,
      category: event.category,
      audiences: event.audiences,
      status: event.status,
      link: event.link,
      description: event.description,
      badge: event.badge,
      priority: event.priority,
      accent: event.accent,
      source_id: event.source_id,
      metadata: event.metadata,
      created_at: event.created_at,
      updated_at: event.updated_at,
      team: event.team || event.title,
      opponent: event.kind === 'game' ? opponent : event.opponent,
      is_home: event.is_home,
    };
  }

  function serializeWeek() {
    syncWeekFields();
    return {
      start_date: state.week.start_date,
      end_date: state.week.end_date,
      heading: state.week.heading,
      notes: state.week.notes,
      events: state.week.events.map(serializeEvent),
    };
  }

  async function createDraftFromSource() {
    const weekId = currentWeekId();
    if (!state.week) {
      setFlash('Load a week first.', true);
      return;
    }

    const hasExistingDraft = Boolean(state.week.events?.length);
    const isApproved = Boolean(state.week.approval?.approved);
    const confirmationMessage = hasExistingDraft
      ? 'Refresh imported source events for this week? Custom events and notes will be kept, but imported events will be replaced and approval will reset.'
      : 'Fetch source events and create the weekly draft for this week?';
    if (hasExistingDraft && typeof window.confirm === 'function' && !window.confirm(confirmationMessage)) {
      return;
    }

    setButtonBusy(els.createBtn, true);
    setFlash(`Refreshing source events for ${weekId}...`);

    try {
      const saved = await fetchJson(`/api/emails/weeks/${weekId}/source-refresh`, {
        method: 'POST',
      });
      state.outputs = null;
      applyWeek(saved.week);
      const summary = saved.source_summary || {};
      const importedCount = Number(summary.total_events || 0);
      if (saved.action === 'refreshed') {
        setFlash(
          isApproved
            ? `Source events refreshed. ${importedCount} imported events reloaded and approval reset.`
            : `Source events refreshed. ${importedCount} imported events reloaded; custom events were kept.`
        );
      } else {
        setFlash(`Created weekly draft with ${importedCount} imported events.`);
      }
      await previewWeek({ silent: true, autoSave: false });
    } catch (error) {
      setFlash(error.message || 'Unable to refresh source events.', true);
    } finally {
      setButtonBusy(els.createBtn, false);
    }
  }

  async function saveWeek({ silent = false } = {}) {
    if (!state.week) return null;
    syncWeekFields();
    setButtonBusy(els.saveBtn, true);
    if (!silent) setFlash(`Saving draft for ${state.week.week_id}...`);

    try {
      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}`, {
        method: 'PUT',
        body: JSON.stringify(serializeWeek()),
      });
      state.outputs = null;
      applyWeek(data.week);
      if (!silent) setFlash('Draft saved. Refresh preview to verify the updated email output.');
      return data.week;
    } catch (error) {
      setFlash(error.message || 'Unable to save the draft.', true);
      throw error;
    } finally {
      setButtonBusy(els.saveBtn, false);
    }
  }

  async function previewWeek({ silent = false, autoSave = true } = {}) {
    if (!state.week) return;
    setButtonBusy(els.previewBtn, true);

    try {
      if (autoSave && state.dirty) {
        await saveWeek({ silent: true });
      }

      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/preview`, { method: 'POST' });
      state.outputs = data.outputs || null;
      applyWeek(data.week);
      if (!silent) setFlash('Preview refreshed for both audiences.');
    } catch (error) {
      setFlash(error.message || 'Unable to build preview output.', true);
    } finally {
      setButtonBusy(els.previewBtn, false);
    }
  }

  async function approveWeek() {
    if (!state.week) return;
    setButtonBusy(els.approveBtn, true);

    try {
      if (state.dirty) {
        await saveWeek({ silent: true });
      }

      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/approve`, {
        method: 'POST',
        headers: { 'X-Email-Actor': 'admin-ui' },
      });

      state.outputs = data.outputs || null;
      applyWeek(data.week);
      setFlash('Week approved. Sender output can now fetch the reviewed content.');
    } catch (error) {
      setFlash(error.message || 'Unable to approve the week.', true);
    } finally {
      setButtonBusy(els.approveBtn, false);
    }
  }

  async function markWeekUnsent() {
    if (!state.week) return;
    const isSending = Boolean(state.week.sent?.sending);
    const confirmed = typeof window.confirm !== 'function'
      || window.confirm(
        isSending
          ? 'Clear the current sending lock and mark this week unsent? This will make the draft editable again.'
          : 'Mark this week unsent so it can be edited or resent again?'
      );
    if (!confirmed) return;

    setButtonBusy(els.markUnsentBtn, true);

    try {
      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/sent`, {
        method: 'POST',
        headers: { 'X-Email-Actor': 'admin-ui' },
        body: JSON.stringify({ state: 'unsent' }),
      });

      applyWeek(data.week);
      setFlash(isSending ? 'Sending lock cleared. The week can be edited or resent again.' : 'Week marked unsent. The normal review workflow is available again.');
    } catch (error) {
      setFlash(error.message || 'Unable to clear the send state.', true);
    } finally {
      setButtonBusy(els.markUnsentBtn, false);
    }
  }

  function csvCell(value) {
    const str = String(value ?? '');
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return '"' + str.replaceAll('"', '""') + '"';
    }
    return str;
  }

  function formatAudiences(audiences) {
    if (!audiences || !audiences.length) return 'Both';
    return audiences.map((a) => (a === 'middle-school' ? 'Middle School' : a === 'upper-school' ? 'Upper School' : a)).join(', ');
  }

  function exportEvents() {
    if (!state.week || !state.week.events.length) return;

    const week = state.week;
    const headers = ['Date', 'Day', 'End Date', 'Time', 'Title', 'Subtitle', 'Category', 'Source', 'Location', 'Audience', 'Status', 'Link', 'Description'];

    const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    function dayName(isoDate) {
      if (!isoDate) return '';
      const d = new Date(`${isoDate}T00:00:00`);
      return Number.isNaN(d.getTime()) ? '' : DAY_NAMES[d.getDay()];
    }

    const rows = week.events.map((event) => [
      csvCell(event.start_date),
      csvCell(dayName(event.start_date)),
      csvCell(event.end_date !== event.start_date ? event.end_date : ''),
      csvCell(event.time_text),
      csvCell(event.title),
      csvCell(event.subtitle),
      csvCell(event.category),
      csvCell(event.source),
      csvCell(event.location),
      csvCell(formatAudiences(event.audiences)),
      csvCell(event.status === 'hidden' ? 'Hidden' : 'Visible'),
      csvCell(event.link),
      csvCell(event.description),
    ]);

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kd-events-${week.week_id || 'export'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setFlash(`Exported ${week.events.length} events to CSV.`);
  }

  function addCustomEvent() {
    if (!state.week) {
      setFlash('Load or create a week first.', true);
      return;
    }

    resetFilters();
    state.week.events.push(createCustomEventTemplate());
    renderFilters();
    renderRows();
    markDirty();
    setFlash('Custom event added. Save the draft when you are ready.');
  }

  function onHeadingInput() {
    if (!state.week) return;
    syncWeekFields();
    markDirty();
  }

  function onFilterInput() {
    state.filters.query = els.eventSearch.value.trim();
    state.filters.source = els.sourceFilter.value;
    state.filters.visibility = els.visibilityFilter.value;
    renderFilters();
    renderRows();
  }

  function clearEventFilters() {
    resetFilters();
    renderFilters();
    renderRows();
  }

  function onTableInput(event) {
    const row = event.target.closest('tr[data-index]');
    if (!row || !state.week) return;

    const index = Number(row.dataset.index);
    const item = state.week.events[index];
    if (!item) return;

    const field = event.target.dataset.field;

    if (field === 'audience_choice') {
      item.audiences = audiencesFromChoice(event.target.value);
      markDirty();
      return;
    }

    if (!field) return;

    item[field] = event.target.value;
    if (field === 'kind' && event.target.value === 'event') {
      item.opponent = '';
    }
    if (field === 'title') {
      item.team = item.title;
    }
    if (field === 'subtitle' && item.kind === 'game') {
      item.opponent = deriveOpponent(item.subtitle);
    }
    if (field === 'status' && item.status !== 'hidden' && !item.audiences.length) {
      item.audiences = inferAudiences(item);
      renderRows();
    }
    markDirty();
  }

  function onTableClick(event) {
    const button = event.target.closest('[data-action]');
    if (!button || !state.week) return;

    const row = button.closest('tr[data-index]');
    if (!row) return;

    const index = Number(row.dataset.index);
    if (!Number.isFinite(index)) return;

    const action = button.dataset.action;
    const item = state.week.events[index];
    if (!item) return;

    if (action === 'duplicate') {
      resetFilters();
      state.week.events.splice(index + 1, 0, normalizeEvent({
        ...item,
        id: crypto.randomUUID(),
        created_at: '',
        updated_at: '',
      }));
      renderFilters();
      renderRows();
      markDirty();
      setFlash(`Duplicated ${item.title || 'event'}. Save to keep both rows.`);
      return;
    }

    if (action !== 'remove') return;

    const confirmed = typeof window.confirm !== 'function'
      || window.confirm(`Delete “${item.title || 'this event'}” from this draft? Reload the week to undo an unsaved deletion.`);
    if (!confirmed) return;

    state.week.events.splice(index, 1);
    renderFilters();
    renderRows();
    markDirty();
    setFlash('Event removed from the draft. Save to persist the change.');
  }

  function initPreviewTabs() {
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach((b) => {
          b.classList.toggle('tab-active', b.dataset.tab === tab);
          b.setAttribute('aria-selected', String(b.dataset.tab === tab));
        });
        document.querySelectorAll('.tab-panel').forEach((p) => {
          p.classList.toggle('tab-active', p.id === `tab-${tab}`);
        });
      });
    });
  }

  function bind() {
    els.loadBtn.addEventListener('click', loadWeek);
    els.createBtn.addEventListener('click', createDraftFromSource);
    els.saveBtn.addEventListener('click', () => saveWeek());
    els.previewBtn.addEventListener('click', () => previewWeek());
    els.approveBtn.addEventListener('click', approveWeek);
    els.markUnsentBtn.addEventListener('click', markWeekUnsent);
    els.exportBtn.addEventListener('click', exportEvents);
    els.addBtn.addEventListener('click', addCustomEvent);
    els.heading.addEventListener('input', onHeadingInput);
    els.notes.addEventListener('input', onHeadingInput);
    els.eventSearch.addEventListener('input', onFilterInput);
    els.sourceFilter.addEventListener('change', onFilterInput);
    els.visibilityFilter.addEventListener('change', onFilterInput);
    els.clearFiltersBtn.addEventListener('click', clearEventFilters);
    els.tbody.addEventListener('input', onTableInput);
    els.tbody.addEventListener('change', onTableInput);
    els.tbody.addEventListener('click', onTableClick);
  }

  async function init() {
    els.msFrame.srcdoc = EMPTY_PREVIEW;
    els.usFrame.srcdoc = EMPTY_PREVIEW;
    render();
    bind();
    initPreviewTabs();
    await loadWeek();
  }

  init();
})();
