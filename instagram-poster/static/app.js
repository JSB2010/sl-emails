(() => {
  const defaults = window.__POSTER_DEFAULTS__ || {};

  const state = {
    mode: defaults.mode || 'next',
    startDate: defaults.startDate || '',
    endDate: defaults.endDate || '',
    heading: 'This Week at Kent Denver',
    posterStyle: 'v1',
    events: [],
    slides: [],
    currentSlideIndex: 0,
  };

  const els = {
    mode: document.getElementById('week-mode'),
    start: document.getElementById('start-date'),
    end: document.getElementById('end-date'),
    heading: document.getElementById('poster-heading'),
    tbody: document.getElementById('events-tbody'),
    status: document.getElementById('status'),
    posterFrame: document.getElementById('poster-frame'),
    previewStage: document.getElementById('preview-stage'),
    fetchBtn: document.getElementById('fetch-events'),
    renderBtn: document.getElementById('render-poster'),
    addBtn: document.getElementById('add-custom'),
    downloadCurrentBtn: document.getElementById('download-png'),
    downloadAllBtn: document.getElementById('download-all-png'),
    jsonBtn: document.getElementById('download-json'),
    prevBtn: document.getElementById('prev-slide'),
    nextBtn: document.getElementById('next-slide'),
    slideIndicator: document.getElementById('slide-indicator'),
    slideSummary: document.getElementById('slide-event-summary'),
    slideDots: document.getElementById('slide-dots'),
    styleV1Btn: document.getElementById('style-v1'),
    styleV2Btn: document.getElementById('style-v2'),
    eventCount: document.getElementById('event-count'),
  };

  let renderTimer = null;

  function sourceClass(source) {
    if (source === 'athletics') return 'source-athletics';
    if (source === 'arts') return 'source-arts';
    return 'source-custom';
  }

  function setStatus(message, isError = false) {
    els.status.textContent = message;
    els.status.classList.toggle('status-error', isError);
  }

  function updateEventCount() {
    if (!els.eventCount) return;

    const total = state.events.length;
    const customCount = state.events.filter((event) => event.source === 'custom').length;
    const sourceCount = total - customCount;

    if (!total) {
      els.eventCount.textContent = '0 events';
      return;
    }

    const noun = total === 1 ? 'event' : 'events';
    els.eventCount.textContent = `${total} ${noun} (${sourceCount} source, ${customCount} custom)`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function customTemplate() {
    return {
      source: 'custom',
      date: state.startDate || new Date().toISOString().slice(0, 10),
      time: '6:00 PM',
      title: 'Custom Event',
      subtitle: 'School Event',
      location: 'Kent Denver',
      category: 'School Event',
      badge: 'SPECIAL',
      priority: 3,
      accent: '#8C6A00',
    };
  }

  function normalizeEvent(event) {
    return {
      source: String(event.source || 'custom'),
      date: String(event.date || ''),
      time: String(event.time || 'TBA'),
      title: String(event.title || ''),
      subtitle: String(event.subtitle || ''),
      location: String(event.location || ''),
      category: String(event.category || ''),
      badge: String(event.badge || 'EVENT'),
      priority: Number(event.priority || 2),
      accent: String(event.accent || '#0C3A6B'),
    };
  }

  function renderEventRows() {
    updateEventCount();

    if (!state.events.length) {
      els.tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:#4e6078;">No events loaded yet. Fetch events or add custom events.</td></tr>';
      return;
    }

    els.tbody.innerHTML = state.events
      .map((event, index) => {
        const source = escapeHtml(event.source);
        return `
          <tr data-index="${index}">
            <td><span class="source-chip ${sourceClass(event.source)}">${source}</span></td>
            <td><input type="date" data-field="date" value="${escapeHtml(event.date)}" /></td>
            <td><input type="text" data-field="time" value="${escapeHtml(event.time)}" /></td>
            <td><input class="col-title" type="text" data-field="title" value="${escapeHtml(event.title)}" /></td>
            <td><input type="text" data-field="subtitle" value="${escapeHtml(event.subtitle)}" /></td>
            <td><input type="text" data-field="location" value="${escapeHtml(event.location)}" /></td>
            <td><input type="text" data-field="badge" value="${escapeHtml(event.badge)}" /></td>
            <td>
              <select data-field="priority">
                <option value="1" ${event.priority === 1 ? 'selected' : ''}>1</option>
                <option value="2" ${event.priority === 2 ? 'selected' : ''}>2</option>
                <option value="3" ${event.priority === 3 ? 'selected' : ''}>3</option>
                <option value="4" ${event.priority === 4 ? 'selected' : ''}>4</option>
                <option value="5" ${event.priority === 5 ? 'selected' : ''}>5</option>
              </select>
            </td>
            <td><input type="color" data-field="accent" value="${escapeHtml(event.accent)}" /></td>
            <td><button class="btn-row-delete" data-action="delete">Remove</button></td>
          </tr>
        `;
      })
      .join('');
  }

  function syncStateFromControls() {
    state.mode = els.mode.value;
    state.startDate = els.start.value;
    state.endDate = els.end.value;
    state.heading = els.heading.value.trim() || 'This Week at Kent Denver';
  }

  function scalePoster() {
    const containerWidth = Math.max(340, els.previewStage.clientWidth - 28);
    const scale = Math.min(1, containerWidth / 1080);
    els.posterFrame.style.transform = `scale(${scale})`;
    els.posterFrame.style.marginBottom = `${(1 - scale) * 1350}px`;
  }

  function updateSlideUi() {
    const total = state.slides.length;
    const idx = state.currentSlideIndex;

    els.slideIndicator.textContent = `Slide ${Math.min(idx + 1, Math.max(total, 1))} / ${Math.max(total, 1)}`;
    els.prevBtn.disabled = idx <= 0;
    els.nextBtn.disabled = total === 0 || idx >= total - 1;

    if (!total) {
      els.slideSummary.textContent = 'No slides rendered yet.';
      return;
    }

    const slide = state.slides[idx];
    els.slideSummary.textContent = `${slide.day} (${slide.date}): ${slide.events_total} events${slide.overflow_count ? `, +${slide.overflow_count} summarized` : ''}.`;
  }

  function showSlide(index) {
    if (!state.slides.length) {
      updateSlideUi();
      return;
    }

    const clamped = Math.max(0, Math.min(index, state.slides.length - 1));
    state.currentSlideIndex = clamped;
    els.posterFrame.innerHTML = state.slides[clamped].poster_html;
    scalePoster();
    updateSlideUi();
    updateSlideDots();
  }

  async function fetchSourceEvents() {
    syncStateFromControls();

    els.fetchBtn.disabled = true;
    setStatus('Fetching athletics + arts events...');

    try {
      const payload = { mode: state.mode };
      if (state.mode === 'custom') {
        payload.start_date = state.startDate;
        payload.end_date = state.endDate;
      }

      const response = await fetch('/api/fetch-events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || 'Unable to fetch events.');
      }

      state.startDate = data.start_date;
      state.endDate = data.end_date;
      state.events = (data.events || []).map(normalizeEvent);

      els.start.value = state.startDate;
      els.end.value = state.endDate;

      renderEventRows();
      await renderCarousel();
      setStatus(`${data.message} You can now add custom events.`);
    } catch (err) {
      setStatus(err.message || 'Failed to fetch events.', true);
    } finally {
      els.fetchBtn.disabled = false;
    }
  }

  function splitEvents() {
    const baseEvents = [];
    const customEvents = [];

    state.events.forEach((event) => {
      if (event.source === 'custom') customEvents.push(event);
      else baseEvents.push(event);
    });

    return { baseEvents, customEvents };
  }

  async function renderCarousel() {
    syncStateFromControls();
    const { baseEvents, customEvents } = splitEvents();

    els.renderBtn.disabled = true;
    try {
      const response = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: state.startDate,
          end_date: state.endDate,
          heading: state.heading,
          style: state.posterStyle,
          base_events: baseEvents,
          custom_events: customEvents,
        }),
      });

      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || 'Unable to render carousel.');
      }

      state.slides = data.slides || [];
      buildSlideDots();
      const nextIndex = Number.isFinite(data.current_index) ? data.current_index : state.currentSlideIndex;
      showSlide(nextIndex);

      if (data.invalid_custom && data.invalid_custom.length) {
        const msg = data.invalid_custom.map((item) => `Row ${Number(item.index) + 1}: ${item.error}`).join(' | ');
        setStatus(`Rendered with warnings. ${msg}`, true);
      } else {
        setStatus(`Carousel ready: ${data.slide_count} daily slides.`);
      }
    } catch (err) {
      setStatus(err.message || 'Render failed.', true);
    } finally {
      els.renderBtn.disabled = false;
    }
  }

  function queueRender() {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(() => {
      renderCarousel();
    }, 220);
  }

  async function exportCurrentSlide(filename) {
    const poster = els.posterFrame.querySelector('.poster');
    if (!poster) {
      throw new Error('Slide is not ready.');
    }

    const originalTransform = els.posterFrame.style.transform;
    const originalMarginBottom = els.posterFrame.style.marginBottom;

    try {
      els.posterFrame.style.transform = 'none';
      els.posterFrame.style.marginBottom = '0px';
      await new Promise((resolve) => setTimeout(resolve, 80));

      const canvas = await window.html2canvas(poster, {
        width: 1080,
        height: 1350,
        scale: 1,
        backgroundColor: null,
        onclone: (doc) => {
          let clonedPoster = null;

          if (poster.id) {
            clonedPoster = doc.getElementById(poster.id);
          }

          if (!clonedPoster) {
            clonedPoster = doc.querySelector('.poster');
          }

          if (clonedPoster) {
            clonedPoster.classList.add('poster-export');
          }
        },
      });

      const link = document.createElement('a');
      link.download = filename;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } finally {
      els.posterFrame.style.transform = originalTransform;
      els.posterFrame.style.marginBottom = originalMarginBottom;
      scalePoster();
    }
  }

  function safeFileName(name) {
    return name.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-').replaceAll(/^-+|-+$/g, '');
  }

  async function downloadCurrentSlidePng() {
    if (!state.slides.length) {
      setStatus('No slides available yet.', true);
      return;
    }

    els.downloadCurrentBtn.disabled = true;
    setStatus('Rendering current slide PNG...');

    try {
      const slide = state.slides[state.currentSlideIndex];
      const filename = `kent-denver-${slide.date}-${safeFileName(slide.day)}.png`;
      await exportCurrentSlide(filename);
      setStatus(`Downloaded slide ${state.currentSlideIndex + 1}.`);
    } catch (err) {
      setStatus(err.message || 'Current slide export failed.', true);
    } finally {
      els.downloadCurrentBtn.disabled = false;
    }
  }

  async function downloadAllSlidesPng() {
    if (!state.slides.length) {
      setStatus('No slides available yet.', true);
      return;
    }

    els.downloadAllBtn.disabled = true;
    els.downloadCurrentBtn.disabled = true;

    const originalIndex = state.currentSlideIndex;

    try {
      for (let i = 0; i < state.slides.length; i += 1) {
        showSlide(i);
        const slide = state.slides[i];
        setStatus(`Exporting slide ${i + 1} of ${state.slides.length}...`);
        await new Promise((resolve) => setTimeout(resolve, 120));
        const filename = `kent-denver-${slide.date}-${safeFileName(slide.day)}.png`;
        await exportCurrentSlide(filename);
        await new Promise((resolve) => setTimeout(resolve, 120));
      }

      setStatus(`Downloaded all ${state.slides.length} daily slides.`);
    } catch (err) {
      setStatus(err.message || 'Bulk export failed.', true);
    } finally {
      showSlide(originalIndex);
      els.downloadAllBtn.disabled = false;
      els.downloadCurrentBtn.disabled = false;
    }
  }

  function downloadJson() {
    const payload = {
      start_date: state.startDate,
      end_date: state.endDate,
      heading: state.heading,
      events: state.events,
      exported_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const today = new Date().toISOString().slice(0, 10);
    link.href = url;
    link.download = `kent-denver-events-${today}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus('Events JSON downloaded.');
  }

  function onTableInput(event) {
    const row = event.target.closest('tr[data-index]');
    if (!row) return;

    const index = Number(row.dataset.index);
    if (!Number.isFinite(index) || !state.events[index]) return;

    const field = event.target.dataset.field;
    if (!field) return;

    if (field === 'priority') {
      state.events[index][field] = Number(event.target.value || 2);
    } else {
      state.events[index][field] = event.target.value;
    }

    queueRender();
  }

  function onTableClick(event) {
    const button = event.target.closest('button[data-action="delete"]');
    if (!button) return;

    const row = button.closest('tr[data-index]');
    if (!row) return;

    const index = Number(row.dataset.index);
    if (!Number.isFinite(index)) return;

    state.events.splice(index, 1);
    renderEventRows();
    queueRender();
  }

  function onModeChange() {
    const mode = els.mode.value;
    const disableManualDates = mode !== 'custom';
    els.start.disabled = disableManualDates;
    els.end.disabled = disableManualDates;
  }

  function addCustomEvent() {
    state.events.push(customTemplate());
    renderEventRows();
    queueRender();
  }

  function buildSlideDots() {
    if (!els.slideDots) return;
    els.slideDots.innerHTML = state.slides
      .map((_, i) => `<button class="slide-dot${i === state.currentSlideIndex ? ' active' : ''}" data-dot="${i}" aria-label="Slide ${i + 1}"></button>`)
      .join('');
  }

  function updateSlideDots() {
    if (!els.slideDots) return;
    els.slideDots.querySelectorAll('.slide-dot').forEach((dot, i) => {
      dot.classList.toggle('active', i === state.currentSlideIndex);
    });
  }

  function bind() {
    els.mode.addEventListener('change', () => {
      onModeChange();
      queueRender();
    });
    els.start.addEventListener('change', queueRender);
    els.end.addEventListener('change', queueRender);
    els.heading.addEventListener('input', queueRender);
    els.fetchBtn.addEventListener('click', fetchSourceEvents);
    els.renderBtn.addEventListener('click', renderCarousel);
    els.addBtn.addEventListener('click', addCustomEvent);
    els.downloadCurrentBtn.addEventListener('click', downloadCurrentSlidePng);
    els.downloadAllBtn.addEventListener('click', downloadAllSlidesPng);
    els.jsonBtn.addEventListener('click', downloadJson);
    els.prevBtn.addEventListener('click', () => showSlide(state.currentSlideIndex - 1));
    els.nextBtn.addEventListener('click', () => showSlide(state.currentSlideIndex + 1));
    els.tbody.addEventListener('input', onTableInput);
    els.tbody.addEventListener('change', onTableInput);
    els.tbody.addEventListener('click', onTableClick);
    window.addEventListener('resize', scalePoster);

    if (els.slideDots) {
      els.slideDots.addEventListener('click', (e) => {
        const dot = e.target.closest('[data-dot]');
        if (dot) showSlide(Number(dot.dataset.dot));
      });
    }

    els.styleV1Btn.addEventListener('click', () => {
      state.posterStyle = 'v1';
      els.styleV1Btn.classList.add('btn-active');
      els.styleV2Btn.classList.remove('btn-active');
      renderCarousel();
    });
    els.styleV2Btn.addEventListener('click', () => {
      state.posterStyle = 'v2';
      els.styleV2Btn.classList.add('btn-active');
      els.styleV1Btn.classList.remove('btn-active');
      renderCarousel();
    });
  }

  function init() {
    els.mode.value = state.mode;
    els.start.value = state.startDate;
    els.end.value = state.endDate;
    onModeChange();
    bind();
    renderEventRows();

    const initialCount = Number(defaults.slideCount || 0);
    if (initialCount > 0) {
      state.slides = Array.from({ length: initialCount }, (_, idx) => ({
        index: idx,
        day: 'Day',
        date: state.startDate,
        events_total: 0,
        overflow_count: 0,
        poster_html: idx === 0 ? els.posterFrame.innerHTML : '',
      }));
    }

    scalePoster();
    updateSlideUi();
    fetchSourceEvents();
  }

  init();
})();
