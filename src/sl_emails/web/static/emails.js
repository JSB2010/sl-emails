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
  };

  const els = {
    weekId: document.getElementById('week-id'),
    loadBtn: document.getElementById('load-week'),
    createBtn: document.getElementById('create-from-source'),
    saveBtn: document.getElementById('save-week'),
    previewBtn: document.getElementById('preview-week'),
    approveBtn: document.getElementById('approve-week'),
    addBtn: document.getElementById('add-custom'),
    heading: document.getElementById('week-heading'),
    notes: document.getElementById('week-notes'),
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
      if (text === 'middle-school' || text === 'middle school' || text === 'ms') normalized.push('middle-school');
      if (text === 'upper-school' || text === 'upper school' || text === 'us') normalized.push('upper-school');
    });
    return Array.from(new Set(normalized));
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
      audiences: normalizeAudiences(event.audiences).length ? normalizeAudiences(event.audiences) : ['middle-school', 'upper-school'],
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
      sent: { sent: false, sent_at: '', sent_by: '' },
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

  function setFlash(message, isError = false) {
    els.flash.textContent = message;
    els.flash.classList.toggle('status-error', isError);
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
    if (!response.ok || (data && data.ok === false)) {
      throw new Error((data && data.error) || `Request failed (${response.status})`);
    }
    return data || {};
  }

  function applyWeek(week) {
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
    const sent = week.sent?.sent;

    els.weekSummary.textContent = `${week.start_date} → ${week.end_date}`;
    els.eventCount.textContent = `${events.length} events (${visible} visible, ${custom} custom)`;

    if (sent) {
      els.stateBanner.className = 'state-banner state-sent';
      els.stateTitle.textContent = 'Already sent';
      els.stateDetail.textContent = 'This week has already been marked sent. Review-only mode is safest.';
      els.stateMeta.textContent = `Sent by ${week.sent.sent_by || 'sender'} at ${week.sent.sent_at || 'an unknown time'}${unsaved}`;
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

  function rowMarkup(event, index) {
    const isHidden = event.status === 'hidden';
    return `
      <tr data-index="${index}">
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
          <div class="audience-stack">
            <label class="check"><input type="checkbox" data-audience="middle-school" ${event.audiences.includes('middle-school') ? 'checked' : ''} ${isHidden ? '' : ''}/>Middle School</label>
            <label class="check"><input type="checkbox" data-audience="upper-school" ${event.audiences.includes('upper-school') ? 'checked' : ''} ${isHidden ? '' : ''}/>Upper School</label>
          </div>
        </td>
        <td>
          <div class="cell-stack">
            <select class="mini-select" data-field="status">
              <option value="active" ${event.status !== 'hidden' ? 'selected' : ''}>Visible</option>
              <option value="hidden" ${event.status === 'hidden' ? 'selected' : ''}>Hidden</option>
            </select>
            <input class="mini-input" type="url" data-field="link" value="${escapeHtml(event.link)}" placeholder="Optional link" />
          </div>
        </td>
        <td>
          <textarea class="mini-textarea" data-field="description" placeholder="Optional details">${escapeHtml(event.description)}</textarea>
        </td>
        <td>
          <button class="row-remove" data-action="remove">Remove</button>
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

    els.tbody.innerHTML = state.week.events.map((event, index) => rowMarkup(event, index)).join('');
  }

  function render() {
    els.weekId.value = state.weekId;
    els.heading.value = state.week?.heading || 'This Week at Kent Denver';
    els.notes.value = state.week?.notes || '';
    renderMeta();
    renderRows();
    renderPreview();

    const isSent = Boolean(state.week?.sent?.sent);
    els.addBtn.disabled = !state.week || isSent;
    els.saveBtn.disabled = !state.week || isSent;
    els.previewBtn.disabled = !state.week;
    els.approveBtn.disabled = !state.week || isSent;
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
      kind: event.source === 'athletics' ? 'game' : 'event',
      title: event.title,
      subtitle: event.subtitle,
      start_date: event.date,
      end_date: event.date,
      time_text: event.time,
      location: event.location,
      category: event.category,
      badge: event.badge,
      priority: event.priority,
      accent: event.accent,
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
      team: event.kind === 'game' ? (event.title || event.team) : '',
      opponent: event.kind === 'game' ? opponent : '',
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
    setButtonBusy(els.createBtn, true);
    setFlash(`Creating draft for ${weekId} from athletics and arts sources...`);

    try {
      const endDate = weekEndFromStart(weekId);
      const fetched = await fetchJson('/api/fetch-events', {
        method: 'POST',
        body: JSON.stringify({ mode: 'custom', start_date: weekId, end_date: endDate }),
      });

      const payload = {
        start_date: weekId,
        end_date: endDate,
        heading: state.week?.heading || 'This Week at Kent Denver',
        notes: state.week?.notes || '',
        events: (fetched.events || []).map(mapFetchedEvent).map(serializeEvent),
      };

      const saved = await fetchJson(`/api/emails/weeks/${weekId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });

      state.outputs = null;
      applyWeek(saved.week);
      setFlash(`Created weekly draft with ${(saved.week.events || []).length} imported events.`);
      await previewWeek({ silent: true, autoSave: false });
    } catch (error) {
      setFlash(error.message || 'Unable to create the draft.', true);
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

  function addCustomEvent() {
    if (!state.week) {
      setFlash('Load or create a week first.', true);
      return;
    }

    state.week.events.push(createCustomEventTemplate());
    renderRows();
    markDirty();
    setFlash('Custom event added. Save the draft when you are ready.');
  }

  function onHeadingInput() {
    if (!state.week) return;
    syncWeekFields();
    markDirty();
  }

  function onTableInput(event) {
    const row = event.target.closest('tr[data-index]');
    if (!row || !state.week) return;

    const index = Number(row.dataset.index);
    const item = state.week.events[index];
    if (!item) return;

    const field = event.target.dataset.field;
    const audience = event.target.dataset.audience;

    if (audience) {
      const nextAudiences = normalizeAudiences(
        item.audiences.filter((value) => value !== audience).concat(event.target.checked ? [audience] : [])
      );
      if (!nextAudiences.length && item.status !== 'hidden') {
        event.target.checked = true;
        setFlash('Visible events must target at least one audience. Use Hidden to remove an event from previews.', true);
        return;
      }
      item.audiences = nextAudiences;
      markDirty();
      return;
    }

    if (!field) return;

    item[field] = event.target.value;
    if (field === 'kind' && event.target.value === 'event') {
      item.opponent = '';
    }
    if (field === 'title' && item.kind === 'game') {
      item.team = item.title;
    }
    if (field === 'subtitle' && item.kind === 'game') {
      item.opponent = deriveOpponent(item.subtitle);
    }
    if (field === 'status' && item.status !== 'hidden' && !item.audiences.length) {
      item.audiences = ['middle-school', 'upper-school'];
      renderRows();
    }
    markDirty();
  }

  function onTableClick(event) {
    const button = event.target.closest('[data-action="remove"]');
    if (!button || !state.week) return;

    const row = button.closest('tr[data-index]');
    if (!row) return;

    const index = Number(row.dataset.index);
    if (!Number.isFinite(index)) return;

    state.week.events.splice(index, 1);
    renderRows();
    markDirty();
    setFlash('Event removed from the draft. Save to persist the change.');
  }

  function bind() {
    els.loadBtn.addEventListener('click', loadWeek);
    els.createBtn.addEventListener('click', createDraftFromSource);
    els.saveBtn.addEventListener('click', () => saveWeek());
    els.previewBtn.addEventListener('click', () => previewWeek());
    els.approveBtn.addEventListener('click', approveWeek);
    els.addBtn.addEventListener('click', addCustomEvent);
    els.heading.addEventListener('input', onHeadingInput);
    els.notes.addEventListener('input', onHeadingInput);
    els.tbody.addEventListener('input', onTableInput);
    els.tbody.addEventListener('change', onTableInput);
    els.tbody.addEventListener('click', onTableClick);
  }

  async function init() {
    els.msFrame.srcdoc = EMPTY_PREVIEW;
    els.usFrame.srcdoc = EMPTY_PREVIEW;
    render();
    bind();
    await loadWeek();
  }

  init();
})();