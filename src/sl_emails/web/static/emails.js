(() => {
  const defaults = window.__EMAIL_REVIEW_DEFAULTS__ || {};
  const ICON_OPTIONS = Array.isArray(defaults.iconOptions) ? defaults.iconOptions : [];
  const ICON_LABELS = new Map(
    ICON_OPTIONS.flatMap((group) => (
      Array.isArray(group.options)
        ? group.options.map((option) => [String(option.value || "").trim(), String(option.label || option.value || "").trim()])
        : []
    )),
  );
  const SOURCE_COLORS = {
    athletics: "#0C3A6B",
    arts: "#A11919",
    custom: "#8C6A00",
  };
  const EMPTY_PREVIEW = "<!DOCTYPE html><html><body style=\"font-family:Arial,sans-serif;padding:32px;color:#4a607c;\">Preview not generated yet.</body></html>";
  const DEFAULT_SEND_TIME = "16:00";
  const AUDIENCES = ["middle-school", "upper-school"];

  const state = {
    weekId: normalizeWeekId(defaults.weekId || ""),
    week: null,
    weekCache: {},
    outputs: null,
    requests: [],
    activity: [],
    dirty: false,
    editorialAudience: "middle-school",
    expandedEventIds: new Set(),
    filters: {
      query: "",
      source: "all",
      visibility: "all",
    },
  };

  const els = {
    weekId: document.getElementById("week-id"),
    weekRail: document.getElementById("week-picker-rail"),
    loadPastWeeks: document.getElementById("load-past-weeks"),
    loadFutureWeeks: document.getElementById("load-future-weeks"),
    createBtn: document.getElementById("create-from-source"),
    saveBtn: document.getElementById("save-week"),
    previewBtn: document.getElementById("preview-week"),
    approveBtn: document.getElementById("approve-week"),
    sendNowBtn: document.getElementById("send-now"),
    markUnsentBtn: document.getElementById("mark-unsent"),
    addBtn: document.getElementById("add-custom"),
    exportBtn: document.getElementById("export-csv"),
    generateAiBtn: document.getElementById("generate-ai"),
    clearWeekBtn: document.getElementById("clear-week"),
    requestSummary: document.getElementById("request-summary"),
    requestList: document.getElementById("request-list"),
    heading: document.getElementById("week-heading"),
    notes: document.getElementById("week-notes"),
    heroText: document.getElementById("copy-hero-text"),
    introTitle: document.getElementById("copy-intro-title"),
    introText: document.getElementById("copy-intro-text"),
    spotlightLabel: document.getElementById("copy-spotlight-label"),
    scheduleLabel: document.getElementById("copy-schedule-label"),
    alsoLabel: document.getElementById("copy-also-label"),
    emptyDayTemplate: document.getElementById("copy-empty-day-template"),
    ctaEyebrow: document.getElementById("copy-cta-eyebrow"),
    ctaTitle: document.getElementById("copy-cta-title"),
    ctaText: document.getElementById("copy-cta-text"),
    copyAudienceButtons: Array.from(document.querySelectorAll("[data-copy-audience]")),
    msSubjectInput: document.getElementById("week-subject-ms"),
    usSubjectInput: document.getElementById("week-subject-us"),
    deliverySummary: document.getElementById("delivery-summary"),
    deliveryOptions: Array.from(document.querySelectorAll('input[name="delivery-mode"]')),
    eventSearch: document.getElementById("event-search"),
    sourceFilter: document.getElementById("event-source-filter"),
    visibilityFilter: document.getElementById("event-visibility-filter"),
    clearFiltersBtn: document.getElementById("clear-event-filters"),
    filteredCount: document.getElementById("filtered-count"),
    tbody: document.getElementById("events-tbody"),
    flash: document.getElementById("flash"),
    weekSummary: document.getElementById("week-summary"),
    stateBanner: document.getElementById("state-banner"),
    stateTitle: document.getElementById("state-title"),
    stateDetail: document.getElementById("state-detail"),
    stateMeta: document.getElementById("state-meta"),
    eventCount: document.getElementById("event-count"),
    previewStatus: document.getElementById("preview-status"),
    msSubject: document.getElementById("ms-subject"),
    usSubject: document.getElementById("us-subject"),
    msCount: document.getElementById("ms-count"),
    usCount: document.getElementById("us-count"),
    msFrame: document.getElementById("preview-middle-school"),
    usFrame: document.getElementById("preview-upper-school"),
    statusIngest: document.getElementById("status-ingest"),
    statusRefresh: document.getElementById("status-refresh"),
    statusReviewEmail: document.getElementById("status-review-email"),
    statusDelivery: document.getElementById("status-delivery"),
    statusApproval: document.getElementById("status-approval"),
    statusSend: document.getElementById("status-send"),
    statusStepIngest: document.getElementById("status-step-ingest"),
    statusStepRefresh: document.getElementById("status-step-refresh"),
    statusStepReviewEmail: document.getElementById("status-step-review-email"),
    statusStepDelivery: document.getElementById("status-step-delivery"),
    statusStepApproval: document.getElementById("status-step-approval"),
    statusStepSend: document.getElementById("status-step-send"),
    activityList: document.getElementById("activity-list"),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  }

  function parseIsoDate(value) {
    const normalized = String(value || "").trim();
    if (!normalized) return null;
    const date = new Date(`${normalized}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isoDate(date) {
    return date ? date.toISOString().slice(0, 10) : "";
  }

  function addDays(date, days) {
    const copy = new Date(date.getTime());
    copy.setDate(copy.getDate() + Number(days || 0));
    return copy;
  }

  function normalizeWeekId(value) {
    const date = parseIsoDate(value);
    if (!date) return "";
    const weekday = (date.getDay() + 6) % 7;
    date.setDate(date.getDate() - weekday);
    return isoDate(date);
  }

  function weekEndFromStart(startValue) {
    const start = parseIsoDate(startValue);
    return start ? isoDate(addDays(start, 6)) : String(startValue || "");
  }

  function sundayBeforeWeek(weekId) {
    const start = parseIsoDate(weekId);
    return start ? isoDate(addDays(start, -1)) : "";
  }

  function formatDateShort(value, options = {}) {
    const date = parseIsoDate(value);
    if (!date) return value;
    return date.toLocaleDateString("en-US", options);
  }

  function dayName(value) {
    return formatDateShort(value, { weekday: "long" });
  }

  function weekCardLabel(weekId) {
    const start = parseIsoDate(weekId);
    if (!start) return weekId;
    return start.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function dateRangeLabel(startValue, endValue) {
    const start = parseIsoDate(startValue);
    const end = parseIsoDate(endValue);
    if (!start || !end) return "";

    const startMonth = start.toLocaleDateString("en-US", { month: "long" });
    const endMonth = end.toLocaleDateString("en-US", { month: "long" });
    const startDay = start.getDate();
    const endDay = end.getDate();
    const startYear = start.getFullYear();
    const endYear = end.getFullYear();

    if (startMonth === endMonth && startYear === endYear) {
      return `${startMonth} ${startDay}\u2013${endDay}, ${startYear}`;
    }
    if (startYear === endYear) {
      return `${startMonth} ${startDay}\u2013${endMonth} ${endDay}, ${startYear}`;
    }
    return `${startMonth} ${startDay}, ${startYear}\u2013${endMonth} ${endDay}, ${endYear}`;
  }

  function formatTimeLabel(value) {
    if (value === DEFAULT_SEND_TIME) return "4:00 PM MT";
    return value || DEFAULT_SEND_TIME;
  }

  function defaultCopyOverrides() {
    return {
      hero_text: "",
      intro_title: "",
      intro_text: "",
      spotlight_label: "",
      schedule_label: "",
      also_on_schedule_label: "",
      empty_day_template: "",
      cta_eyebrow: "",
      cta_title: "",
      cta_text: "",
    };
  }

  function defaultAudienceCopyOverrides() {
    return AUDIENCES.reduce((acc, audience) => {
      acc[audience] = defaultCopyOverrides();
      return acc;
    }, {});
  }

  function normalizeAudienceCopyOverrides(copyByAudience, sharedCopy) {
    const shared = { ...defaultCopyOverrides(), ...(sharedCopy && typeof sharedCopy === "object" ? sharedCopy : {}) };
    const source = copyByAudience && typeof copyByAudience === "object" ? copyByAudience : {};
    return AUDIENCES.reduce((acc, audience) => {
      acc[audience] = {
        ...shared,
        ...(source[audience] && typeof source[audience] === "object" ? source[audience] : {}),
      };
      return acc;
    }, {});
  }

  function copyOverridesForAudience(audience) {
    if (!state.week) return defaultCopyOverrides();
    return {
      ...defaultCopyOverrides(),
      ...(state.week.copy_overrides && typeof state.week.copy_overrides === "object" ? state.week.copy_overrides : {}),
      ...((state.week.copy_overrides_by_audience || {})[audience] || {}),
    };
  }

  function readCopyFields() {
    return {
      hero_text: els.heroText.value.trim(),
      intro_title: els.introTitle.value.trim(),
      intro_text: els.introText.value.trim(),
      spotlight_label: els.spotlightLabel.value.trim(),
      schedule_label: els.scheduleLabel.value.trim(),
      also_on_schedule_label: els.alsoLabel.value.trim(),
      empty_day_template: els.emptyDayTemplate.value.trim(),
      cta_eyebrow: els.ctaEyebrow.value.trim(),
      cta_title: els.ctaTitle.value.trim(),
      cta_text: els.ctaText.value.trim(),
    };
  }

  function writeCopyFields(copy) {
    els.heroText.value = copy.hero_text || "";
    els.introTitle.value = copy.intro_title || "";
    els.introText.value = copy.intro_text || "";
    els.spotlightLabel.value = copy.spotlight_label || "";
    els.scheduleLabel.value = copy.schedule_label || "";
    els.alsoLabel.value = copy.also_on_schedule_label || "";
    els.emptyDayTemplate.value = copy.empty_day_template || "";
    els.ctaEyebrow.value = copy.cta_eyebrow || "";
    els.ctaTitle.value = copy.cta_title || "";
    els.ctaText.value = copy.cta_text || "";
  }

  function syncCurrentCopyFields() {
    if (!state.week) return;
    state.week.copy_overrides_by_audience = normalizeAudienceCopyOverrides(
      state.week.copy_overrides_by_audience,
      state.week.copy_overrides,
    );
    state.week.copy_overrides_by_audience[state.editorialAudience] = readCopyFields();
    state.week.copy_overrides = defaultCopyOverrides();
  }

  function defaultDelivery(weekId) {
    return {
      mode: "default",
      send_on: sundayBeforeWeek(weekId),
      send_time: DEFAULT_SEND_TIME,
      updated_at: "",
      updated_by: "",
    };
  }

  function normalizeDelivery(delivery, weekId) {
    const fallback = defaultDelivery(weekId);
    const source = delivery && typeof delivery === "object" ? delivery : {};
    const mode = String(source.mode || fallback.mode).trim().toLowerCase();
    const normalizedMode = ["default", "postpone", "skip"].includes(mode) ? mode : fallback.mode;
    const sendOn = String(source.send_on || "").trim();
    return {
      mode: normalizedMode,
      send_on: normalizedMode === "skip" ? "" : (sendOn || (normalizedMode === "default" ? fallback.send_on : weekId)),
      send_time: String(source.send_time || fallback.send_time).trim() || fallback.send_time,
      updated_at: String(source.updated_at || "").trim(),
      updated_by: String(source.updated_by || "").trim(),
    };
  }

  function deliveryChoiceFromState(delivery, weekId) {
    const current = normalizeDelivery(delivery, weekId);
    if (current.mode === "skip") return "skip";
    if (current.mode === "postpone") {
      const monday = normalizeWeekId(weekId);
      const offsets = ["monday", "tuesday", "wednesday", "thursday"];
      const target = offsets.find((_, index) => current.send_on === isoDate(addDays(parseIsoDate(monday), index)));
      return target ? `postpone-${target}` : "postpone-monday";
    }
    return "default";
  }

  function deliveryFromChoice(choice, weekId, currentDelivery) {
    const current = normalizeDelivery(currentDelivery, weekId);
    if (choice === "skip") {
      return { ...current, mode: "skip", send_on: "", send_time: DEFAULT_SEND_TIME };
    }
    if (choice === "default") {
      return { ...current, mode: "default", send_on: sundayBeforeWeek(weekId), send_time: DEFAULT_SEND_TIME };
    }

    const [, weekday] = String(choice || "").split("-");
    const offsets = { monday: 0, tuesday: 1, wednesday: 2, thursday: 3 };
    const offset = offsets[weekday];
    if (offset === undefined) {
      return { ...current, mode: "default", send_on: sundayBeforeWeek(weekId), send_time: DEFAULT_SEND_TIME };
    }
    return {
      ...current,
      mode: "postpone",
      send_on: isoDate(addDays(parseIsoDate(weekId), offset)),
      send_time: DEFAULT_SEND_TIME,
    };
  }

  function deliverySummaryText(delivery, weekId) {
    const current = normalizeDelivery(delivery, weekId);
    if (current.mode === "skip") return "No email this week";
    const label = current.mode === "default" ? "Sunday default" : dayName(current.send_on);
    return `${label} · ${formatTimeLabel(current.send_time)}`;
  }

  function deliveryStatusText(delivery, weekId) {
    const current = normalizeDelivery(delivery, weekId);
    if (current.mode === "skip") {
      return "Skipped for this week. Sunday review is suppressed and no audience send will run.";
    }
    if (current.mode === "default") {
      return `Review Sunday morning. Audience send ${dayName(current.send_on)}, ${formatDateShort(current.send_on, { month: "short", day: "numeric" })} at ${formatTimeLabel(current.send_time)}.`;
    }
    return `Review Sunday morning. Audience send moved to ${dayName(current.send_on)}, ${formatDateShort(current.send_on, { month: "short", day: "numeric" })} at ${formatTimeLabel(current.send_time)}.`;
  }

  function normalizeAudiences(raw) {
    const values = Array.isArray(raw) ? raw : (raw ? [raw] : []);
    const normalized = [];
    values.forEach((value) => {
      const text = String(value).trim().toLowerCase().replaceAll("_", "-");
      if (text === "all" || text === "both" || text === "both-audiences") {
        normalized.push("middle-school", "upper-school");
      }
      if (text === "middle-school" || text === "middle school" || text === "ms") normalized.push("middle-school");
      if (text === "upper-school" || text === "upper school" || text === "us") normalized.push("upper-school");
    });
    return Array.from(new Set(normalized));
  }

  function looksMiddleSchool(label) {
    const value = ` ${String(label || "").toLowerCase()} `;
    return ["middle school", " ms ", " 6th", " 7th", " 8th", "sixth", "seventh", "eighth"]
      .some((indicator) => value.includes(indicator));
  }

  function inferAudiences(event) {
    const explicit = normalizeAudiences(event.audiences || event.audience || event.school_levels || event.school_level);
    if (explicit.length) return explicit;

    const source = String(event.source || "custom").trim().toLowerCase() || "custom";
    const label = String(event.team || event.title || "").trim();
    if (source === "custom") return ["middle-school", "upper-school"];
    if (looksMiddleSchool(label)) return ["middle-school"];
    if (source === "athletics" || source === "arts") return ["upper-school"];
    return ["middle-school", "upper-school"];
  }

  function audienceChoiceForEvent(event) {
    const audiences = normalizeAudiences(event.audiences);
    if (audiences.includes("middle-school") && audiences.includes("upper-school")) return "both";
    if (audiences[0] === "middle-school") return "middle-school";
    return "upper-school";
  }

  function audiencesFromChoice(choice) {
    if (choice === "middle-school") return ["middle-school"];
    if (choice === "upper-school") return ["upper-school"];
    return ["middle-school", "upper-school"];
  }

  function resetFilters() {
    state.filters = { query: "", source: "all", visibility: "all" };
  }

  function filtersAreActive() {
    return Boolean(state.filters.query || state.filters.source !== "all" || state.filters.visibility !== "all");
  }

  function filteredEventRows() {
    if (!state.week) return [];
    const query = state.filters.query.trim().toLowerCase();
    return state.week.events
      .map((event, index) => ({ event, index }))
      .filter(({ event }) => {
        const matchesQuery = !query || [event.title, event.subtitle, event.location, event.category, event.team, event.opponent]
          .join(" ")
          .toLowerCase()
          .includes(query);
        const matchesSource = state.filters.source === "all" || event.source === state.filters.source;
        const isHidden = event.status === "hidden";
        const matchesVisibility = state.filters.visibility === "all"
          || (state.filters.visibility === "hidden" && isHidden)
          || (state.filters.visibility === "visible" && !isHidden);
        return matchesQuery && matchesSource && matchesVisibility;
      });
  }

  function defaultAccent(source) {
    return SOURCE_COLORS[source] || SOURCE_COLORS.custom;
  }

  function sourceClass(source) {
    if (source === "athletics") return "source-athletics";
    if (source === "arts") return "source-arts";
    return "source-custom";
  }

  function deriveOpponent(subtitle) {
    return String(subtitle || "").replace(/^vs\.?\s*/i, "").replace(/^@\s*/i, "").trim();
  }

  function normalizeEvent(event) {
    const source = String(event.source || "custom").trim().toLowerCase() || "custom";
    const title = String(event.title || event.team || "").trim();
    const opponent = String(event.opponent || "").trim();
    const audiences = inferAudiences(event);
    return {
      id: String(event.id || crypto.randomUUID()),
      source,
      kind: String(event.kind || (opponent ? "game" : "event")).trim().toLowerCase() || "event",
      title,
      subtitle: String(event.subtitle || (opponent ? `vs. ${opponent}` : "")).trim(),
      start_date: String(event.start_date || event.date || state.weekId || defaults.weekId || "").trim(),
      end_date: String(event.end_date || event.start_date || event.date || state.weekId || defaults.weekId || "").trim(),
      time_text: String(event.time_text || event.time || "TBA").trim() || "TBA",
      location: String(event.location || "On Campus").trim() || "On Campus",
      category: String(event.category || "School Event").trim() || "School Event",
      audiences,
      status: String(event.status || "active").trim().toLowerCase() || "active",
      link: String(event.link || "").trim(),
      description: String(event.description || "").trim(),
      badge: String(event.badge || (source === "custom" ? "SPECIAL" : "EVENT")).trim() || "EVENT",
      icon: String(event.icon || "").trim(),
      priority: Number(event.priority || 3),
      accent: String(event.accent || defaultAccent(source)).trim() || defaultAccent(source),
      team: String(event.team || title).trim(),
      opponent,
      is_home: event.is_home !== false,
      metadata: typeof event.metadata === "object" && event.metadata ? event.metadata : {},
      source_id: String(event.source_id || "").trim(),
      created_at: String(event.created_at || "").trim(),
      updated_at: String(event.updated_at || "").trim(),
    };
  }

  function normalizeRequest(item) {
    return {
      request_id: String(item.request_id || item.id || crypto.randomUUID()),
      week_id: normalizeWeekId(String(item.week_id || state.weekId || "").trim()),
      title: String(item.title || item.team || "Untitled Request").trim(),
      start_date: String(item.start_date || item.date || state.weekId || "").trim(),
      end_date: String(item.end_date || item.start_date || item.date || state.weekId || "").trim(),
      time_text: String(item.time_text || item.time || "TBA").trim() || "TBA",
      location: String(item.location || "On Campus").trim() || "On Campus",
      category: String(item.category || "School Event").trim() || "School Event",
      audiences: normalizeAudiences(item.audiences || item.audience) || ["middle-school", "upper-school"],
      requester_name: String(item.requester_name || "").trim(),
      requester_email: String(item.requester_email || "").trim(),
      kind: String(item.kind || "event").trim().toLowerCase() || "event",
      subtitle: String(item.subtitle || "").trim(),
      description: String(item.description || "").trim(),
      link: String(item.link || "").trim(),
      requester_notes: String(item.requester_notes || item.notes || "").trim(),
      team: String(item.team || item.title || "").trim(),
      opponent: String(item.opponent || "").trim(),
      is_home: item.is_home !== false,
      status: String(item.status || "pending").trim().toLowerCase() || "pending",
      review: {
        decision: String(item.review?.decision || "").trim().toLowerCase(),
        reviewed_at: String(item.review?.reviewed_at || "").trim(),
        reviewed_by: String(item.review?.reviewed_by || "").trim(),
        reviewer_notes: String(item.review?.reviewer_notes || "").trim(),
        resolved_event_id: String(item.review?.resolved_event_id || "").trim(),
      },
      submitted_at: String(item.submitted_at || "").trim(),
      updated_at: String(item.updated_at || "").trim(),
    };
  }

  function normalizeWeek(week) {
    const weekId = normalizeWeekId(week.week_id || week.start_date || state.weekId || defaults.weekId || "");
    return {
      ...week,
      week_id: weekId,
      start_date: weekId,
      end_date: String(week.end_date || weekEndFromStart(weekId)).trim() || weekEndFromStart(weekId),
      heading: String(week.heading || "This Week at Kent Denver").trim() || "This Week at Kent Denver",
      notes: String(week.notes || "").trim(),
      subject_overrides: typeof week.subject_overrides === "object" && week.subject_overrides ? week.subject_overrides : {},
      delivery: normalizeDelivery(week.delivery, weekId),
      copy_overrides: { ...defaultCopyOverrides(), ...(week.copy_overrides && typeof week.copy_overrides === "object" ? week.copy_overrides : {}) },
      copy_overrides_by_audience: normalizeAudienceCopyOverrides(week.copy_overrides_by_audience, week.copy_overrides),
      approval: week.approval && typeof week.approval === "object" ? week.approval : { approved: false, approved_at: "", approved_by: "" },
      sent: week.sent && typeof week.sent === "object"
        ? { sent: false, sent_at: "", sent_by: "", sending: false, sending_at: "", sending_by: "", ...week.sent }
        : { sent: false, sent_at: "", sent_by: "", sending: false, sending_at: "", sending_by: "" },
      metadata: week.metadata && typeof week.metadata === "object" ? week.metadata : {},
      events: Array.isArray(week.events) ? week.events.map(normalizeEvent) : [],
    };
  }

  function blankWeek(weekId) {
    const normalizedWeekId = normalizeWeekId(weekId);
    return normalizeWeek({
      week_id: normalizedWeekId,
      start_date: normalizedWeekId,
      end_date: weekEndFromStart(normalizedWeekId),
      heading: "This Week at Kent Denver",
      status: "draft",
      approval: { approved: false, approved_at: "", approved_by: "" },
      sent: { sent: false, sent_at: "", sent_by: "", sending: false, sending_at: "", sending_by: "" },
      notes: "",
      subject_overrides: {},
      delivery: defaultDelivery(normalizedWeekId),
      copy_overrides: defaultCopyOverrides(),
      copy_overrides_by_audience: defaultAudienceCopyOverrides(),
      events: [],
      metadata: {},
    });
  }

  function createCustomEventTemplate() {
    return normalizeEvent({
      source: "custom",
      kind: "event",
      title: "Custom Event",
      subtitle: "School Event",
      start_date: state.week?.start_date || state.weekId || defaults.weekId || "",
      end_date: state.week?.start_date || state.weekId || defaults.weekId || "",
      time_text: "6:00 PM",
      location: "Kent Denver",
      category: "School Event",
      audiences: ["middle-school", "upper-school"],
      status: "active",
      badge: "SPECIAL",
      accent: SOURCE_COLORS.custom,
    });
  }

  let flashTimer = null;

  function setFlash(message, isError = false) {
    clearTimeout(flashTimer);
    els.flash.textContent = message;
    els.flash.classList.toggle("flash-error", isError);
    els.flash.classList.add("flash-show");
    flashTimer = setTimeout(() => {
      els.flash.classList.remove("flash-show");
    }, 5000);
  }

  function setButtonBusy(button, busy) {
    if (button) button.disabled = busy;
  }

  async function fetchJson(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => null);
    if (response.status === 401 && data && data.login_url) {
      window.location.href = data.login_url;
      throw new Error("Authentication required");
    }
    if (response.status === 403 && data && data.access_denied_url) {
      window.location.href = data.access_denied_url;
      throw new Error("Access denied");
    }
    if (!response.ok || (data && data.ok === false)) {
      throw new Error((data && data.error) || `Request failed (${response.status})`);
    }
    return data || {};
  }

  function formatActivity(activity, emptyText) {
    if (!activity || typeof activity !== "object") return emptyText;
    const status = String(activity.status || "").trim();
    const actor = String(activity.actor || "").trim();
    const occurredAt = String(activity.occurred_at || "").trim();
    const message = String(activity.message || "").trim();
    const parts = [];
    if (status) parts.push(status);
    if (actor) parts.push(`by ${actor}`);
    if (occurredAt) parts.push(`at ${occurredAt}`);
    if (message) parts.push(message);
    if (activity.source_summary && Number(activity.source_summary.total_events || 0) > 0) {
      parts.push(`${Number(activity.source_summary.total_events || 0)} imported events`);
    }
    if (Array.isArray(activity.source_health)) {
      const failedSources = activity.source_health
        .filter((item) => item && item.ok === false)
        .map((item) => `${item.source}: ${item.error || "failed"}`);
      if (failedSources.length) parts.push(`source failures: ${failedSources.join(", ")}`);
    }
    return parts.length ? parts.join(" · ") : emptyText;
  }

  function activityDetailsText(record) {
    const details = record && typeof record.details === "object" ? record.details : {};
    const parts = [];
    if (details.day_id) parts.push(`day ${details.day_id}`);
    if (details.state) parts.push(`state ${details.state}`);
    if (details.action) parts.push(`action ${details.action}`);
    if (details.reason) parts.push(`reason ${details.reason}`);
    if (details.source_summary && Number(details.source_summary.total_events || 0) >= 0) {
      parts.push(`${Number(details.source_summary.total_events || 0)} imported events`);
    }
    if (Array.isArray(details.source_health)) {
      const failed = details.source_health
        .filter((item) => item && item.ok === false)
        .map((item) => `${item.source}: ${item.error || "failed"}`);
      if (failed.length) parts.push(`source failures: ${failed.join(", ")}`);
    }
    return parts.join(" · ");
  }

  function defaultSubjectForAudience(audience) {
    const week = state.week;
    if (!week) return "Sports This Week";
    const visibleEvents = (week.events || []).filter((event) => event.status !== "hidden" && (event.audiences || []).includes(audience));
    const hasArts = visibleEvents.some((event) => event.kind !== "game");
    const base = hasArts ? "Sports and Performances This Week" : "Sports This Week";
    const range = dateRangeLabel(week.start_date, week.end_date);
    return range ? `${base}: ${range.replace("\u2013", " - ").replace(/, \d{4}$/, "")}` : base;
  }

  function resolveSubjectInputValue(audience) {
    const override = String((state.week?.subject_overrides || {})[audience] || "").trim();
    if (override) return override;
    const previewDefault = String((state.outputs?.[audience] || {}).default_subject || "").trim();
    if (previewDefault) return previewDefault;
    return defaultSubjectForAudience(audience);
  }

  function iconLabel(value) {
    const iconName = String(value || "").trim();
    if (!iconName) return "Auto Select";
    return ICON_LABELS.get(iconName) || iconName.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function iconUrl(value) {
    const iconName = String(value || "").trim();
    if (!iconName) return "";
    const base = String(defaults.iconBaseUrl || "").trim().replace(/\/$/, "");
    return `${base}/static/icons/${iconName}.svg`;
  }

  function iconSwatchMarkup(value, label) {
    const url = iconUrl(value);
    if (!url) {
      return "<span class=\"icon-picker-swatch\"><span>Auto</span></span>";
    }
    return `<span class="icon-picker-swatch"><img src="${escapeHtml(url)}" alt="${escapeHtml(label)}" /></span>`;
  }

  function buildIconOptionsMarkup(selectedValue) {
    const knownValues = new Set(ICON_LABELS.keys());
    const selectedLabel = iconLabel(selectedValue);
    const groupsMarkup = ICON_OPTIONS.map((group) => {
      const groupLabel = escapeHtml(group.label || "Icons");
      const options = Array.isArray(group.options) ? group.options : [];
      const optionButtons = options.map((option) => {
        const value = String(option.value || "").trim();
        if (!value) return "";
        const label = escapeHtml(option.label || value);
        const isActive = selectedValue === value ? " icon-option-active" : "";
        return `
          <button class="icon-option${isActive}" data-action="set-icon" data-icon-value="${escapeHtml(value)}" type="button">
            ${iconSwatchMarkup(value, option.label || value)}
            <span>${label}</span>
          </button>
        `;
      }).join("");
      if (!optionButtons) return "";
      return `
        <div class="icon-picker-group">
          <p class="icon-picker-group-title">${groupLabel}</p>
          <div class="icon-picker-options">${optionButtons}</div>
        </div>
      `;
    }).join("");

    const unknownOptionMarkup = selectedValue && !knownValues.has(selectedValue)
      ? `
        <div class="icon-picker-group">
          <p class="icon-picker-group-title">Current Value</p>
          <div class="icon-picker-options">
            <button class="icon-option icon-option-active" data-action="set-icon" data-icon-value="${escapeHtml(selectedValue)}" type="button">
              ${iconSwatchMarkup(selectedValue, selectedLabel)}
              <span>${escapeHtml(selectedLabel)}</span>
            </button>
          </div>
        </div>
      `
      : "";

    return `
      <details class="icon-picker">
        <summary class="icon-picker-trigger">
          ${iconSwatchMarkup(selectedValue, selectedLabel)}
          <span class="icon-picker-copy">
            <strong>${escapeHtml(selectedLabel)}</strong>
            <span>${selectedValue ? escapeHtml(selectedValue) : "Use the category or source default icon."}</span>
          </span>
        </summary>
        <div class="icon-picker-panel">
          <div class="icon-picker-group">
            <p class="icon-picker-group-title">Automatic</p>
            <div class="icon-picker-options">
              <button class="icon-option${selectedValue ? "" : " icon-option-active"}" data-action="set-icon" data-icon-value="" type="button">
                ${iconSwatchMarkup("", "Auto")}
                <span>Auto Select</span>
              </button>
            </div>
          </div>
          ${unknownOptionMarkup}
          ${groupsMarkup}
        </div>
      </details>
    `;
  }

  function formatEventDate(event) {
    const start = String(event.start_date || "").trim();
    const end = String(event.end_date || "").trim();
    if (!start) return "Date not set";
    if (end && end !== start) return `${start} to ${end}`;
    return start;
  }

  function cacheWeek(week) {
    if (!week || !week.week_id) return;
    state.weekCache[week.week_id] = normalizeWeek(week);
  }

  function weekStatusSummary(week) {
    if (!week) return "Not loaded";
    if (week.delivery?.mode === "skip") return "Skipped";
    if (week.sent?.sent) return "Sent";
    if (week.sent?.sending) return "Sending";
    if (week.approval?.approved) return "Approved";
    if (week.delivery?.mode === "postpone") return "Postponed";
    if ((week.events || []).length) return "Draft";
    return "Blank";
  }

  function weekStatusTone(week) {
    const status = weekStatusSummary(week);
    if (status === "Sent" || status === "Approved") return "week-status-good";
    if (status === "Skipped" || status === "Postponed") return "week-status-warn";
    return "week-status-neutral";
  }

  function buildWeekIds() {
    const center = parseIsoDate(state.weekId || defaults.weekId || "");
    if (!center) return [];
    const ids = [];
    for (let offset = -2; offset <= 2; offset += 1) {
      ids.push(isoDate(addDays(center, offset * 7)));
    }
    return ids;
  }

  function renderWeekRail() {
    const weekIds = buildWeekIds();
    if (!weekIds.length) {
      els.weekRail.innerHTML = "<div class=\"empty-row\">No weeks available.</div>";
      return;
    }
    els.weekRail.innerHTML = weekIds.map((weekId) => {
      const cached = state.weekCache[weekId] || (state.week?.week_id === weekId ? state.week : null);
      const selected = state.weekId === weekId;
      const status = weekStatusSummary(cached);
      const detail = cached
        ? `${(cached.events || []).filter((event) => event.status !== "hidden").length} visible`
        : "Open week";
      return `
        <button class="week-card${selected ? " week-card-active" : ""}" data-week-id="${weekId}" type="button">
          <span class="week-card-kicker">${escapeHtml(dayName(weekId))}</span>
          <strong>${escapeHtml(weekCardLabel(weekId))}</strong>
          <span class="week-card-range">${escapeHtml(dateRangeLabel(weekId, weekEndFromStart(weekId)))}</span>
          <span class="week-card-status ${weekStatusTone(cached)}">${escapeHtml(status)}</span>
          <span class="week-card-detail">${escapeHtml(detail)}</span>
        </button>
      `;
    }).join("");
  }

  function applyWeek(week) {
    resetFilters();
    const normalized = normalizeWeek(week);
    const nextExpandedIds = new Set();
    normalized.events.forEach((event) => {
      if (state.expandedEventIds.has(event.id)) {
        nextExpandedIds.add(event.id);
      }
    });
    state.expandedEventIds = nextExpandedIds;
    state.week = normalized;
    state.weekId = normalized.week_id;
    state.dirty = false;
    cacheWeek(normalized);
    syncWeekQuery(normalized.week_id);
    render();
  }

  function markDirty(flag = true) {
    state.dirty = flag;
    renderMeta();
    renderStatus();
    renderActionState();
    renderWeekRail();
  }

  function renderMeta() {
    const week = state.week;
    if (!week) {
      els.weekSummary.textContent = "No draft loaded";
      els.stateBanner.className = "state-banner state-draft";
      els.stateTitle.textContent = "Draft";
      els.stateDetail.textContent = "Choose a week to review imported events, adjust scheduling, and prepare previews.";
      els.stateMeta.textContent = "Waiting for a weekly draft.";
      els.eventCount.textContent = "0 events";
      els.previewStatus.textContent = "Preview not generated";
      return;
    }

    const events = week.events || [];
    const hidden = events.filter((event) => event.status === "hidden").length;
    const visible = events.length - hidden;
    const custom = events.filter((event) => event.source === "custom").length;
    const pendingRequests = state.requests.filter((item) => item.status === "pending").length;
    const unsaved = state.dirty ? " · unsaved changes" : "";
    const approved = week.approval?.approved;
    const sent = Boolean(week.sent?.sent);
    const sending = Boolean(week.sent?.sending);
    const skipped = week.delivery?.mode === "skip";
    const postponed = week.delivery?.mode === "postpone";

    els.weekSummary.textContent = `${week.start_date} → ${week.end_date}`;
    els.eventCount.textContent = `${events.length} events (${visible} visible, ${custom} custom) · ${pendingRequests} pending requests`;

    if (skipped) {
      els.stateBanner.className = "state-banner state-skipped";
      els.stateTitle.textContent = "Skipped Week";
      els.stateDetail.textContent = "This week is marked “No email this week.” Review notifications and delivery are suppressed until the schedule is changed.";
      els.stateMeta.textContent = `${deliverySummaryText(week.delivery, week.week_id)}${unsaved}`;
    } else if (sent) {
      els.stateBanner.className = "state-banner state-sent";
      els.stateTitle.textContent = "Already sent";
      els.stateDetail.textContent = "This week has already been marked sent. Use “Mark Unsent” to reopen it for edits or resend prep.";
      els.stateMeta.textContent = `Sent by ${week.sent.sent_by || "sender"} at ${week.sent.sent_at || "an unknown time"}${unsaved}`;
    } else if (sending) {
      els.stateBanner.className = "state-banner state-sent";
      els.stateTitle.textContent = "Send in progress";
      els.stateDetail.textContent = "This week is currently marked sending. Use “Mark Unsent” to clear the send lock before editing or retrying.";
      els.stateMeta.textContent = `Claimed by ${week.sent.sending_by || "sender"} at ${week.sent.sending_at || "an unknown time"}${unsaved}`;
    } else if (approved) {
      els.stateBanner.className = "state-banner state-approved";
      els.stateTitle.textContent = postponed ? "Approved · postponed" : "Approved";
      els.stateDetail.textContent = postponed
        ? "This week is approved and queued for a delayed weekday send."
        : "This week is approved and ready for sender output.";
      els.stateMeta.textContent = `Approved by ${week.approval.approved_by || "admin"} at ${week.approval.approved_at || "an unknown time"}${unsaved}`;
    } else {
      els.stateBanner.className = `state-banner ${postponed ? "state-postponed" : "state-draft"}`;
      els.stateTitle.textContent = state.dirty ? "Draft · unsaved changes" : (postponed ? "Draft · postponed" : "Draft");
      els.stateDetail.textContent = hidden
        ? "Hidden events stay in the draft but are omitted from preview and sender output."
        : "Draft changes can be previewed and approved when ready.";
      els.stateMeta.textContent = `${visible} visible event${visible === 1 ? "" : "s"} · ${hidden} hidden${unsaved}`;
    }

    els.previewStatus.textContent = state.outputs ? "Preview ready" : "Preview not generated";
  }

  function renderEditorialFields() {
    els.heading.value = state.week?.heading || "This Week at Kent Denver";
    els.notes.value = state.week?.notes || "";
    writeCopyFields(copyOverridesForAudience(state.editorialAudience));
    els.copyAudienceButtons.forEach((button) => {
      const active = button.dataset.copyAudience === state.editorialAudience;
      button.classList.toggle("copy-audience-tab-active", active);
      button.setAttribute("aria-selected", String(active));
    });
    els.msSubjectInput.value = resolveSubjectInputValue("middle-school");
    els.usSubjectInput.value = resolveSubjectInputValue("upper-school");
  }

  function renderDelivery() {
    const weekId = state.week?.week_id || state.weekId;
    const delivery = normalizeDelivery(state.week?.delivery, weekId);
    const selected = deliveryChoiceFromState(delivery, weekId);
    els.deliverySummary.textContent = deliverySummaryText(delivery, weekId);
    els.deliveryOptions.forEach((input) => {
      input.checked = input.value === selected;
    });
  }

  function renderPreviewAudience(output, subjectEl, countEl, frameEl) {
    if (!output) {
      subjectEl.textContent = "No preview yet";
      countEl.textContent = "0 events";
      frameEl.srcdoc = EMPTY_PREVIEW;
      return;
    }
    subjectEl.textContent = output.subject || "No subject";
    countEl.textContent = `${output.source_event_count || 0} events`;
    frameEl.srcdoc = output.html || EMPTY_PREVIEW;
  }

  function renderPreview() {
    renderPreviewAudience(state.outputs?.["middle-school"], els.msSubject, els.msCount, els.msFrame);
    renderPreviewAudience(state.outputs?.["upper-school"], els.usSubject, els.usCount, els.usFrame);
  }

  function renderStatus() {
    const setStepState = (element, stepState) => {
      if (element) element.dataset.stepState = stepState;
    };

    const week = state.week;
    if (!week) {
      els.statusIngest.textContent = "No week loaded yet.";
      els.statusRefresh.textContent = "No week loaded yet.";
      els.statusReviewEmail.textContent = "No week loaded yet.";
      els.statusDelivery.textContent = "No week loaded yet.";
      els.statusApproval.textContent = "No week loaded yet.";
      els.statusSend.textContent = "No week loaded yet.";
      setStepState(els.statusStepIngest, "muted");
      setStepState(els.statusStepRefresh, "muted");
      setStepState(els.statusStepReviewEmail, "muted");
      setStepState(els.statusStepDelivery, "muted");
      setStepState(els.statusStepApproval, "muted");
      setStepState(els.statusStepSend, "muted");
      return;
    }

    const metadata = week.metadata || {};
    const isSkipped = week.delivery?.mode === "skip";
    const isApproved = Boolean(week.approval?.approved);
    const isSent = Boolean(week.sent?.sent);
    const isSending = Boolean(week.sent?.sending);
    const isPostponed = week.delivery?.mode === "postpone";
    const hasScheduledIngest = Boolean(metadata.scheduled_ingest);
    const hasManualRefresh = Boolean(metadata.manual_refresh);
    const hasReviewNotification = Boolean(metadata.review_notification);
    const hasWorkflowProgress = hasScheduledIngest
      || hasManualRefresh
      || hasReviewNotification
      || isPostponed
      || isSkipped
      || isApproved
      || isSending
      || isSent;
    els.statusIngest.textContent = formatActivity(metadata.scheduled_ingest, "No automation run recorded yet.");
    els.statusRefresh.textContent = formatActivity(metadata.manual_refresh, "No manual refresh recorded yet.");
    els.statusReviewEmail.textContent = formatActivity(metadata.review_notification, "No review notification recorded yet.");
    els.statusDelivery.textContent = deliveryStatusText(week.delivery, week.week_id);
    els.statusApproval.textContent = isApproved
      ? `approved by ${week.approval.approved_by || "admin"} at ${week.approval.approved_at || "unknown time"}`
      : (isSkipped ? "Approval disabled while the week is marked “No email this week.”" : "Week has not been approved yet.");
    if (isSent) {
      els.statusSend.textContent = `sent by ${week.sent.sent_by || "automation"} at ${week.sent.sent_at || "unknown time"}`;
    } else if (isSending) {
      els.statusSend.textContent = `claimed for sending by ${week.sent.sending_by || "automation"} at ${week.sent.sending_at || "unknown time"}`;
    } else {
      els.statusSend.textContent = formatActivity(metadata.send, "No send claim or completion recorded yet.");
    }

    if (!hasWorkflowProgress) {
      setStepState(els.statusStepIngest, "muted");
      setStepState(els.statusStepRefresh, "muted");
      setStepState(els.statusStepReviewEmail, "muted");
      setStepState(els.statusStepDelivery, "muted");
      setStepState(els.statusStepApproval, "muted");
      setStepState(els.statusStepSend, "muted");
      return;
    }

    setStepState(els.statusStepIngest, hasScheduledIngest ? "complete" : "pending");
    setStepState(els.statusStepRefresh, hasManualRefresh ? "complete" : "pending");
    setStepState(els.statusStepReviewEmail, hasReviewNotification ? "complete" : (isSkipped ? "warning" : "pending"));
    setStepState(els.statusStepDelivery, isSkipped ? "warning" : (isPostponed || isApproved || isSending || isSent ? "current" : "pending"));
    setStepState(els.statusStepApproval, isApproved ? "complete" : (isSkipped ? "warning" : (isSending || isSent ? "complete" : "pending")));
    setStepState(els.statusStepSend, isSent ? "complete" : (isSending ? "current" : "pending"));
  }

  function renderActivity() {
    if (!state.week) {
      els.activityList.innerHTML = "<div class=\"empty-activity-state\">Load a week to inspect recent activity.</div>";
      return;
    }
    if (!state.activity.length) {
      els.activityList.innerHTML = "<div class=\"empty-activity-state\">No recent activity recorded for this week yet.</div>";
      return;
    }

    els.activityList.innerHTML = state.activity.map((record) => {
      const eventType = String(record.event_type || "activity").replaceAll("_", " ");
      const status = String(record.status || "").trim().toLowerCase();
      const message = String(record.message || "").trim() || "No message recorded.";
      const meta = [
        record.actor ? `by ${record.actor}` : "",
        record.occurred_at ? `at ${record.occurred_at}` : "",
      ].filter(Boolean).join(" · ");
      const details = activityDetailsText(record);
      return `
        <article class="activity-item">
          <div class="activity-item-header">
            <span class="activity-item-type">${escapeHtml(eventType)}</span>
            <span class="activity-item-status activity-status-${escapeHtml(status || "unknown")}">${escapeHtml(status || "unknown")}</span>
          </div>
          <p class="activity-item-message">${escapeHtml(message)}</p>
          ${meta ? `<p class="activity-item-meta">${escapeHtml(meta)}</p>` : ""}
          ${details ? `<p class="activity-item-details">${escapeHtml(details)}</p>` : ""}
        </article>
      `;
    }).join("");
  }

  function requestCounts() {
    const pending = state.requests.filter((item) => item.status === "pending").length;
    const approved = state.requests.filter((item) => item.status === "approved").length;
    const denied = state.requests.filter((item) => item.status === "denied").length;
    return { pending, approved, denied, total: state.requests.length };
  }

  function requestStatusLabel(status) {
    if (status === "approved") return "Approved";
    if (status === "denied") return "Denied";
    return "Pending Review";
  }

  function requestDateLabel(item) {
    if (!item.start_date) return "Date not provided";
    if (item.end_date && item.end_date !== item.start_date) {
      return `${item.start_date} \u2192 ${item.end_date}`;
    }
    return item.start_date;
  }

  function formatAudiences(audiences) {
    if (!audiences || !audiences.length) return "Both";
    return audiences.map((value) => (
      value === "middle-school" ? "Middle School" : value === "upper-school" ? "Upper School" : value
    )).join(", ");
  }

  function requestCardMarkup(item, index) {
    const status = item.status || "pending";
    const reviewerNotes = item.review?.reviewer_notes || "";
    const detailParts = [
      item.time_text || "TBA",
      item.location || "On Campus",
      formatAudiences(item.audiences),
      item.category || "School Event",
    ].filter(Boolean);
    const requesterLabel = [item.requester_name, item.requester_email].filter(Boolean).join(" · ");
    const reviewSummary = item.review?.reviewed_at || item.review?.reviewed_by
      ? `${requestStatusLabel(status)} by ${item.review.reviewed_by || "admin"}${item.review.reviewed_at ? ` at ${item.review.reviewed_at}` : ""}`
      : "";

    return `
      <article class="request-card request-${escapeHtml(status)}" data-request-index="${index}">
        <div class="request-card-head">
          <div class="request-head-main">
            <span class="request-status request-status-${escapeHtml(status)}">${escapeHtml(requestStatusLabel(status))}</span>
            <h3>${escapeHtml(item.title)}</h3>
            <p class="request-meta">${escapeHtml(requestDateLabel(item))} · ${escapeHtml(detailParts.join(" · "))}</p>
          </div>
          <div class="request-contact">
            <strong>${escapeHtml(item.requester_name || "Unknown requester")}</strong>
            <span>${escapeHtml(item.requester_email || "No email provided")}</span>
          </div>
        </div>
        ${item.subtitle ? `<p class="request-block"><strong>Subtitle</strong><span>${escapeHtml(item.subtitle)}</span></p>` : ""}
        ${item.description ? `<p class="request-block"><strong>Requested event details</strong><span>${escapeHtml(item.description)}</span></p>` : ""}
        ${item.requester_notes ? `<p class="request-block"><strong>Requester notes</strong><span>${escapeHtml(item.requester_notes)}</span></p>` : ""}
        ${item.link ? `<p class="request-block"><strong>Link</strong><a href="${escapeHtml(item.link)}" target="_blank" rel="noreferrer">${escapeHtml(item.link)}</a></p>` : ""}
        ${status === "pending" ? `
          <label class="request-review-field">
            Reviewer Note
            <textarea data-request-field="reviewer_notes" rows="3" placeholder="Optional note to keep with the review decision.">${escapeHtml(reviewerNotes)}</textarea>
          </label>
          <div class="request-actions">
            <button class="btn btn-approve" data-request-action="approve" type="button">Approve &amp; Add to Draft</button>
            <button class="btn btn-ghost" data-request-action="deny" type="button">Deny Request</button>
          </div>
        ` : `
          <div class="request-review-summary">
            <strong>${escapeHtml(reviewSummary || requestStatusLabel(status))}</strong>
            ${reviewerNotes ? `<span>${escapeHtml(reviewerNotes)}</span>` : ""}
          </div>
        `}
        <p class="request-submitted">Submitted ${escapeHtml(item.submitted_at || "recently")} · ${escapeHtml(requesterLabel)}</p>
      </article>
    `;
  }

  function renderRequests() {
    if (!state.week) {
      els.requestSummary.textContent = "No requests loaded";
      els.requestList.innerHTML = "<div class=\"empty-request-state\">Load a week to review submitted requests.</div>";
      return;
    }

    const counts = requestCounts();
    if (!counts.total) {
      els.requestSummary.textContent = "0 requests";
      els.requestList.innerHTML = "<div class=\"empty-request-state\">No public requests have been submitted for this week yet.</div>";
      return;
    }

    els.requestSummary.textContent = `${counts.pending} pending · ${counts.approved} approved · ${counts.denied} denied`;
    els.requestList.innerHTML = state.requests.map((item, index) => requestCardMarkup(item, index)).join("");
  }

  function renderFilters() {
    els.eventSearch.value = state.filters.query;
    els.sourceFilter.value = state.filters.source;
    els.visibilityFilter.value = state.filters.visibility;

    if (!state.week) {
      els.filteredCount.textContent = "No events loaded";
      els.clearFiltersBtn.disabled = true;
      return;
    }

    const total = state.week.events.length;
    const shown = filteredEventRows().length;
    els.filteredCount.textContent = filtersAreActive() ? `Showing ${shown} of ${total}` : `All ${total} events shown`;
    els.clearFiltersBtn.disabled = !filtersAreActive();
  }

  function rowMarkup(event, index) {
    const isHidden = event.status === "hidden";
    const audienceChoice = audienceChoiceForEvent(event);
    const summarySubtitle = [formatEventDate(event), event.time_text || "TBA", event.location || "On Campus"].filter(Boolean).join(" · ");
    const isExpanded = state.expandedEventIds.has(event.id);
    return `
      <details data-index="${index}" class="event-card ${isHidden ? "row-hidden" : ""}" ${isExpanded ? "open" : ""}>
        <summary class="event-card-summary">
          <div class="event-card-head">
            <div class="event-card-meta">
              <div class="event-card-pills">
                <span class="source-pill ${sourceClass(event.source)}">${escapeHtml(event.source)}</span>
                <span class="kind-pill">${escapeHtml(event.kind)}</span>
                <span class="visibility-pill ${isHidden ? "visibility-pill-hidden" : ""}">${isHidden ? "Hidden" : "Visible"}</span>
              </div>
              <p class="event-summary-line"><strong>${escapeHtml(event.title || "Untitled")}</strong>${escapeHtml(event.subtitle || event.category || "")}</p>
              <p class="event-summary-subline">${escapeHtml(summarySubtitle)}</p>
            </div>
            <div class="event-card-summary-side">
              <p class="event-summary-audience">${escapeHtml(formatAudiences(event.audiences))}</p>
              <span class="event-expand-label">${isExpanded ? "Collapse" : "Expand"}</span>
            </div>
          </div>
        </summary>

        <div class="event-card-body">
          <div class="event-card-toolbar row-actions">
            <button class="row-action" data-action="duplicate" type="button">Duplicate</button>
            <button class="row-remove row-action-danger" data-action="remove" type="button">Delete</button>
          </div>

          <div class="event-card-grid">
            <section class="event-card-section event-card-section-wide">
              <p class="field-group-label">Basics</p>
              <div class="cell-stack">
                <select class="mini-select" data-field="kind">
                  <option value="event" ${event.kind === "event" ? "selected" : ""}>Event</option>
                  <option value="game" ${event.kind === "game" ? "selected" : ""}>Game</option>
                </select>
                <input class="mini-input" type="text" data-field="title" value="${escapeHtml(event.title)}" placeholder="${event.kind === "game" ? "Team name" : "Event title"}" />
                <input class="mini-input" type="text" data-field="subtitle" value="${escapeHtml(event.subtitle)}" placeholder="${event.kind === "game" ? "Opponent or matchup line" : "Subtitle"}" />
                <input class="mini-input" type="text" data-field="category" value="${escapeHtml(event.category)}" placeholder="${event.kind === "game" ? "Sport" : "Category"}" />
                ${buildIconOptionsMarkup(event.icon)}
              </div>
            </section>

            <section class="event-card-section">
              <p class="field-group-label">Schedule</p>
              <div class="inline-pair">
                <label class="inline-field">Start
                  <input class="mini-input" type="date" data-field="start_date" value="${escapeHtml(event.start_date)}" />
                </label>
                <label class="inline-field">End
                  <input class="mini-input" type="date" data-field="end_date" value="${escapeHtml(event.end_date)}" />
                </label>
              </div>
              <input class="mini-input" type="text" data-field="time_text" value="${escapeHtml(event.time_text)}" placeholder="Time" />
              <input class="mini-input" type="text" data-field="location" value="${escapeHtml(event.location)}" placeholder="Location" />
            </section>

            <section class="event-card-section">
              <p class="field-group-label">Audience &amp; Status</p>
              <div class="cell-stack">
                <select class="mini-select" data-field="audience_choice">
                  <option value="middle-school" ${audienceChoice === "middle-school" ? "selected" : ""}>Middle School</option>
                  <option value="upper-school" ${audienceChoice === "upper-school" ? "selected" : ""}>Upper School</option>
                  <option value="both" ${audienceChoice === "both" ? "selected" : ""}>Both Audiences</option>
                </select>
                <p class="field-note">Controls which preview and sender output includes this row.</p>
                <select class="mini-select" data-field="status">
                  <option value="active" ${event.status !== "hidden" ? "selected" : ""}>Visible</option>
                  <option value="hidden" ${event.status === "hidden" ? "selected" : ""}>Hidden</option>
                </select>
                <p class="field-note">${isHidden ? "Hidden rows are omitted from preview and sender output." : "Visible rows appear in preview and sender output."}</p>
              </div>
            </section>

            <section class="event-card-section event-card-section-wide">
              <p class="field-group-label">Links &amp; Notes</p>
              <div class="cell-stack">
                <input class="mini-input" type="url" data-field="link" value="${escapeHtml(event.link)}" placeholder="Optional link URL" />
                <textarea class="mini-textarea" data-field="description" placeholder="Optional notes or details">${escapeHtml(event.description)}</textarea>
              </div>
            </section>
          </div>
        </div>
      </details>
    `;
  }

  function renderRows() {
    if (!state.week) {
      els.tbody.innerHTML = "<div class=\"empty-row\">Choose a week to begin reviewing events.</div>";
      return;
    }

    if (!state.week.events.length) {
      els.tbody.innerHTML = "<div class=\"empty-row\">No events yet. Refresh from sources, add a custom announcement, or clear filters and start a fresh draft.</div>";
      return;
    }

    const rows = filteredEventRows();
    if (!rows.length) {
      els.tbody.innerHTML = "<div class=\"empty-row\">No events match the current filters. Clear filters to review the full draft.</div>";
      return;
    }

    els.tbody.innerHTML = rows.map(({ event, index }) => rowMarkup(event, index)).join("");
  }

  function renderActionState() {
    const week = state.week;
    const isSent = Boolean(week?.sent?.sent);
    const isSending = Boolean(week?.sent?.sending);
    const isSendLocked = isSent || isSending;
    const isSkipped = week?.delivery?.mode === "skip";
    const isApproved = Boolean(week?.approval?.approved);
    els.exportBtn.disabled = !week || !(week.events || []).length;
    els.createBtn.disabled = !state.week || isSendLocked;
    els.addBtn.disabled = !state.week || isSendLocked;
    els.generateAiBtn.disabled = !state.week || isSendLocked;
    els.clearWeekBtn.disabled = !state.week || isSendLocked;
    els.saveBtn.disabled = !state.week || isSendLocked;
    els.previewBtn.disabled = !state.week;
    els.approveBtn.disabled = !state.week || isSendLocked || isSkipped;
    els.sendNowBtn.disabled = !state.week || state.dirty || isSendLocked || isSkipped;
    els.sendNowBtn.textContent = !state.week || isApproved ? "Send Now" : "Approve & Send";
    els.markUnsentBtn.hidden = !isSendLocked;
    els.markUnsentBtn.disabled = !state.week || !isSendLocked;
    els.deliveryOptions.forEach((input) => {
      input.disabled = !state.week || isSendLocked;
    });
  }

  function render() {
    els.weekId.value = state.weekId;
    renderWeekRail();
    renderEditorialFields();
    renderDelivery();
    renderMeta();
    renderFilters();
    renderRows();
    renderPreview();
    renderStatus();
    renderRequests();
    renderActivity();
    renderActionState();
  }

  function currentWeekId() {
    const value = normalizeWeekId(String(els.weekId.value || state.weekId || "").trim());
    if (!value) throw new Error("Choose a Monday week start first.");
    return value;
  }

  function selectedDeliveryChoice() {
    const input = els.deliveryOptions.find((option) => option.checked);
    return input ? input.value : "default";
  }

  function syncWeekFields() {
    if (!state.week) return;
    state.week.heading = els.heading.value.trim() || "This Week at Kent Denver";
    state.week.notes = els.notes.value.trim();
    syncCurrentCopyFields();

    const nextSubjects = {};
    const middleValue = els.msSubjectInput.value.trim();
    const upperValue = els.usSubjectInput.value.trim();
    const middleDefault = defaultSubjectForAudience("middle-school");
    const upperDefault = defaultSubjectForAudience("upper-school");
    if (middleValue && middleValue !== middleDefault) nextSubjects["middle-school"] = middleValue;
    if (upperValue && upperValue !== upperDefault) nextSubjects["upper-school"] = upperValue;
    state.week.subject_overrides = nextSubjects;
    state.week.delivery = deliveryFromChoice(selectedDeliveryChoice(), state.week.week_id, state.week.delivery);
  }

  function syncWeekQuery(weekId) {
    const url = new URL(window.location.href);
    url.searchParams.set("week", weekId);
    window.history.replaceState({}, "", url.toString());
  }

  function mapFetchedEvent(event) {
    return normalizeEvent({
      source: event.source,
      kind: event.kind || (event.source === "athletics" ? "game" : "event"),
      title: event.title,
      subtitle: event.subtitle,
      start_date: event.date,
      end_date: event.date,
      time_text: event.time,
      location: event.location,
      category: event.category,
      audiences: event.audiences,
      badge: event.badge,
      icon: event.icon,
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
      icon: event.icon,
      badge: event.badge,
      priority: event.priority,
      accent: event.accent,
      source_id: event.source_id,
      metadata: event.metadata,
      created_at: event.created_at,
      updated_at: event.updated_at,
      team: event.team || event.title,
      opponent: event.kind === "game" ? opponent : event.opponent,
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
      subject_overrides: state.week.subject_overrides,
      delivery: state.week.delivery,
      copy_overrides: state.week.copy_overrides,
      copy_overrides_by_audience: state.week.copy_overrides_by_audience,
      events: state.week.events.map(serializeEvent),
    };
  }

  function upsertRequest(request) {
    const normalized = normalizeRequest(request);
    const index = state.requests.findIndex((item) => item.request_id === normalized.request_id);
    if (index === -1) {
      state.requests.push(normalized);
    } else {
      state.requests[index] = normalized;
    }
    state.requests.sort((left, right) => {
      const order = { pending: 0, approved: 1, denied: 2 };
      return (order[left.status] ?? 99) - (order[right.status] ?? 99)
        || left.start_date.localeCompare(right.start_date)
        || left.title.localeCompare(right.title);
    });
  }

  async function fetchWeekRequests(weekId) {
    const data = await fetchJson(`/api/emails/weeks/${weekId}/requests`);
    state.requests = (data.requests || []).map(normalizeRequest);
    renderRequests();
    renderMeta();
  }

  async function fetchWeekActivity(weekId) {
    const data = await fetchJson(`/api/emails/weeks/${weekId}/activity?limit=20`);
    state.activity = Array.isArray(data.activity) ? data.activity : [];
    renderActivity();
  }

  async function loadWeek(requestedWeekId = currentWeekId(), { silent = false } = {}) {
    const weekId = normalizeWeekId(requestedWeekId);
    state.weekId = weekId;
    state.requests = [];
    if (!silent) setFlash(`Loading week ${weekId}...`);

    try {
      const data = await fetchJson(`/api/emails/weeks/${weekId}`);
      state.outputs = null;
      applyWeek(data.week);
      await Promise.all([fetchWeekRequests(weekId), fetchWeekActivity(weekId)]);
      if (!silent) setFlash(`Loaded weekly draft for ${weekId}.`);
      await previewWeek({ silent: true, autoSave: false });
    } catch (error) {
      if (/No weekly draft found/i.test(error.message)) {
        state.outputs = null;
        applyWeek(blankWeek(weekId));
        await Promise.all([fetchWeekRequests(weekId), fetchWeekActivity(weekId)]);
        if (!silent) setFlash("No saved draft found for this week yet. Refresh from sources or start a blank draft.");
      } else {
        setFlash(error.message || "Unable to load week.", true);
      }
    }
  }

  async function selectWeek(weekId) {
    const normalized = normalizeWeekId(weekId);
    if (!normalized || normalized === state.weekId && state.week && !state.dirty) return;
    if (state.dirty && typeof window.confirm === "function") {
      const confirmed = window.confirm("You have unsaved changes. Switch weeks and discard those edits?");
      if (!confirmed) return;
    }
    await loadWeek(normalized, { silent: true });
  }

  async function createDraftFromSource() {
    const weekId = currentWeekId();
    if (!state.week) {
      setFlash("Load a week first.", true);
      return;
    }

    const hasExistingDraft = Boolean(state.week.events?.length);
    const isApproved = Boolean(state.week.approval?.approved);
    const confirmationMessage = hasExistingDraft
      ? "Refresh imported source events for this week? Custom events, editorial copy, delivery timing, and subject lines will be kept, but imported rows and their direct edits will be replaced and approval will reset."
      : "Fetch source events and create the weekly draft for this week?";
    if (hasExistingDraft && typeof window.confirm === "function" && !window.confirm(confirmationMessage)) {
      return;
    }

    setButtonBusy(els.createBtn, true);
    setFlash(`Refreshing source events for ${weekId}...`);

    try {
      const saved = await fetchJson(`/api/emails/weeks/${weekId}/source-refresh`, { method: "POST" });
      state.outputs = null;
      applyWeek(saved.week);
      const summary = saved.source_summary || {};
      const importedCount = Number(summary.total_events || 0);
      if (saved.action === "refreshed") {
        setFlash(
          isApproved
            ? `Source events refreshed. ${importedCount} imported events reloaded and approval reset.`
            : `Source events refreshed. ${importedCount} imported events reloaded; custom events and editorial content were kept.`,
        );
      } else {
        setFlash(`Created weekly draft with ${importedCount} imported events.`);
      }
      await fetchWeekActivity(weekId);
      await previewWeek({ silent: true, autoSave: false });
    } catch (error) {
      setFlash(error.message || "Unable to refresh source events.", true);
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
        method: "PUT",
        body: JSON.stringify(serializeWeek()),
      });
      state.outputs = null;
      applyWeek(data.week);
      await fetchWeekActivity(data.week.week_id);
      if (!silent) setFlash("Draft saved. Refresh preview to verify the updated email output.");
      return data.week;
    } catch (error) {
      setFlash(error.message || "Unable to save the draft.", true);
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
      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/preview`, { method: "POST" });
      state.outputs = data.outputs || null;
      applyWeek(data.week);
      if (!silent) setFlash("Preview refreshed for both audiences.");
    } catch (error) {
      setFlash(error.message || "Unable to build preview output.", true);
    } finally {
      setButtonBusy(els.previewBtn, false);
    }
  }

  async function approveWeek() {
    if (!state.week) return;
    if (state.week.delivery?.mode === "skip") {
      setFlash("Weeks marked “No email this week” cannot be approved until delivery is changed.", true);
      return;
    }
    setButtonBusy(els.approveBtn, true);

    try {
      if (state.dirty) {
        await saveWeek({ silent: true });
      }

      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/approve`, {
        method: "POST",
        headers: { "X-Email-Actor": "admin-ui" },
      });

      state.outputs = data.outputs || null;
      applyWeek(data.week);
      await fetchWeekActivity(data.week.week_id);
      setFlash("Week approved. Sender output can now fetch the reviewed content.");
    } catch (error) {
      setFlash(error.message || "Unable to approve the week.", true);
    } finally {
      setButtonBusy(els.approveBtn, false);
    }
  }

  async function sendWeekNow() {
    if (!state.week) return;
    if (state.dirty) {
      setFlash("Save or discard draft changes before sending now.", true);
      return;
    }
    if (state.week.delivery?.mode === "skip") {
      setFlash("Weeks marked “No email this week” cannot be sent until delivery is changed.", true);
      return;
    }
    const weekId = state.week.week_id;
    const isApproved = Boolean(state.week.approval?.approved);
    const confirmationMessage = isApproved
      ? "Send this approved week now? This will deliver both audience emails and mark the week sent."
      : "This week is not approved yet. Approve it and send both audience emails now?";
    const confirmed = typeof window.confirm !== "function"
      || window.confirm(confirmationMessage);
    if (!confirmed) return;

    setButtonBusy(els.sendNowBtn, true);
    setFlash(isApproved ? `Sending ${weekId} now...` : `Approving and sending ${weekId} now...`);

    try {
      if (!isApproved) {
        const approvalData = await fetchJson(`/api/emails/weeks/${weekId}/approve`, {
          method: "POST",
          headers: { "X-Email-Actor": "admin-ui" },
        });
        state.outputs = approvalData.outputs || null;
        applyWeek(approvalData.week);
        setButtonBusy(els.sendNowBtn, true);
      }

      const data = await fetchJson(`/api/emails/weeks/${weekId}/manual-send`, {
        method: "POST",
        headers: { "X-Email-Actor": "admin-ui" },
      });
      state.outputs = null;
      applyWeek(data.week);
      await fetchWeekActivity(data.week.week_id);
      setFlash("Manual send completed and the week is marked sent.");
    } catch (error) {
      setFlash(error.message || "Unable to send the week now.", true);
    } finally {
      setButtonBusy(els.sendNowBtn, false);
      renderActionState();
    }
  }

  async function generateAiCopy() {
    if (!state.week) return;
    setButtonBusy(els.generateAiBtn, true);
    setFlash("Generating editorial copy with Gemini...");

    try {
      if (state.dirty) {
        await saveWeek({ silent: true });
      }
      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/ai-copy`, {
        method: "POST",
        headers: { "X-Email-Actor": "admin-ui" },
      });
      state.outputs = data.outputs || null;
      applyWeek(data.week);
      await fetchWeekActivity(data.week.week_id);
      setFlash("AI copy generated. Review the text fields before approving.");
    } catch (error) {
      setFlash(error.message || "Unable to generate AI copy.", true);
    } finally {
      setButtonBusy(els.generateAiBtn, false);
    }
  }

  async function clearWeek() {
    if (!state.week) return;
    const confirmed = typeof window.confirm !== "function"
      || window.confirm("Clear this draft completely? This removes all events, custom copy, subject overrides, and resets delivery back to the Sunday default.");
    if (!confirmed) return;

    setButtonBusy(els.clearWeekBtn, true);
    try {
      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/clear`, {
        method: "POST",
        headers: { "X-Email-Actor": "admin-ui" },
      });
      state.outputs = null;
      applyWeek(data.week);
      await fetchWeekActivity(data.week.week_id);
      await previewWeek({ silent: true, autoSave: false });
      setFlash("Draft cleared. You can rebuild from sources or start again from a blank week.");
    } catch (error) {
      setFlash(error.message || "Unable to clear the draft.", true);
    } finally {
      setButtonBusy(els.clearWeekBtn, false);
    }
  }

  async function markWeekUnsent() {
    if (!state.week) return;
    const isSending = Boolean(state.week.sent?.sending);
    const confirmed = typeof window.confirm !== "function"
      || window.confirm(
        isSending
          ? "Clear the current sending lock and mark this week unsent? This will make the draft editable again."
          : "Mark this week unsent so it can be edited or resent again?",
      );
    if (!confirmed) return;

    setButtonBusy(els.markUnsentBtn, true);

    try {
      const data = await fetchJson(`/api/emails/weeks/${state.week.week_id}/sent`, {
        method: "POST",
        headers: { "X-Email-Actor": "admin-ui" },
        body: JSON.stringify({ state: "unsent" }),
      });

      applyWeek(data.week);
      await fetchWeekActivity(data.week.week_id);
      setFlash(isSending ? "Sending lock cleared. The week can be edited or resent again." : "Week marked unsent. The normal review workflow is available again.");
    } catch (error) {
      setFlash(error.message || "Unable to clear the send state.", true);
    } finally {
      setButtonBusy(els.markUnsentBtn, false);
    }
  }

  async function reviewRequest(index, decision) {
    const item = state.requests[index];
    if (!item || !state.week) return;

    const isDenial = decision === "deny";
    const confirmed = typeof window.confirm !== "function"
      || window.confirm(
        isDenial
          ? `Deny the request for “${item.title}”?`
          : `Approve the request for “${item.title}” and add it to this week's draft?`,
      );
    if (!confirmed) return;

    const endpoint = `/api/emails/weeks/${state.week.week_id}/requests/${item.request_id}/${isDenial ? "deny" : "approve"}`;
    try {
      const data = await fetchJson(endpoint, {
        method: "POST",
        headers: { "X-Email-Actor": "admin-ui" },
        body: JSON.stringify({ reviewer_notes: item.review?.reviewer_notes || "" }),
      });

      if (data.week) {
        state.outputs = null;
        applyWeek(data.week);
      }
      if (data.request) {
        upsertRequest(data.request);
      }
      await fetchWeekActivity(state.week.week_id);
      render();
      setFlash(
        isDenial
          ? `Denied request for ${item.title}.`
          : `Approved request for ${item.title} and added it to the draft.`,
      );
    } catch (error) {
      setFlash(error.message || "Unable to review the request.", true);
    }
  }

  function csvCell(value) {
    const text = String(value ?? "");
    if (text.includes(",") || text.includes("\"") || text.includes("\n")) {
      return `"${text.replaceAll("\"", "\"\"")}"`;
    }
    return text;
  }

  function exportEvents() {
    if (!state.week || !state.week.events.length) return;

    const week = state.week;
    const headers = ["Date", "Day", "End Date", "Time", "Title", "Subtitle", "Category", "Source", "Location", "Audience", "Status", "Link", "Description", "Icon"];
    const rows = week.events.map((event) => [
      csvCell(event.start_date),
      csvCell(dayName(event.start_date)),
      csvCell(event.end_date !== event.start_date ? event.end_date : ""),
      csvCell(event.time_text),
      csvCell(event.title),
      csvCell(event.subtitle),
      csvCell(event.category),
      csvCell(event.source),
      csvCell(event.location),
      csvCell(formatAudiences(event.audiences)),
      csvCell(event.status === "hidden" ? "Hidden" : "Visible"),
      csvCell(event.link),
      csvCell(event.description),
      csvCell(event.icon),
    ]);

    const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `kd-events-${week.week_id || "export"}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setFlash(`Exported ${week.events.length} events to CSV.`);
  }

  function addCustomEvent() {
    if (!state.week) {
      setFlash("Load or create a week first.", true);
      return;
    }

    resetFilters();
    const newEvent = createCustomEventTemplate();
    state.week.events.push(newEvent);
    state.expandedEventIds.add(newEvent.id);
    renderFilters();
    renderRows();
    markDirty();
    setFlash("Custom event added. Save the draft when you are ready.");
  }

  function onEditorialInput() {
    if (!state.week) return;
    syncWeekFields();
    markDirty();
  }

  function onCopyAudienceClick(event) {
    if (!state.week) return;
    const audience = event.currentTarget.dataset.copyAudience;
    if (!AUDIENCES.includes(audience) || audience === state.editorialAudience) return;
    syncCurrentCopyFields();
    state.editorialAudience = audience;
    renderEditorialFields();
  }

  function onDeliveryChange() {
    if (!state.week) return;
    syncWeekFields();
    renderDelivery();
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

  function onRequestInput(event) {
    const card = event.target.closest("[data-request-index]");
    if (!card) return;
    const index = Number(card.dataset.requestIndex);
    const item = state.requests[index];
    if (!item) return;

    const field = event.target.dataset.requestField;
    if (field === "reviewer_notes") {
      item.review.reviewer_notes = event.target.value;
    }
  }

  function onRequestClick(event) {
    const button = event.target.closest("[data-request-action]");
    if (!button) return;
    const card = button.closest("[data-request-index]");
    if (!card) return;
    const index = Number(card.dataset.requestIndex);
    if (!Number.isFinite(index)) return;
    reviewRequest(index, button.dataset.requestAction);
  }

  function onTableInput(event) {
    const row = event.target.closest(".event-card[data-index]");
    if (!row || !state.week) return;

    const index = Number(row.dataset.index);
    const item = state.week.events[index];
    if (!item) return;

    const field = event.target.dataset.field;

    if (field === "audience_choice") {
      item.audiences = audiencesFromChoice(event.target.value);
      markDirty();
      renderRows();
      return;
    }

    if (!field) return;

    item[field] = event.target.value;
    if (field === "kind" && event.target.value === "event") {
      item.opponent = "";
    }
    if (field === "title") {
      item.team = item.title;
    }
    if (field === "subtitle" && item.kind === "game") {
      item.opponent = deriveOpponent(item.subtitle);
    }
    if (field === "kind" || field === "status") {
      renderRows();
    }
    markDirty();
  }

  function onTableClick(event) {
    const button = event.target.closest("[data-action]");
    if (!button || !state.week) return;

    const row = button.closest(".event-card[data-index]");
    if (!row) return;

    const index = Number(row.dataset.index);
    if (!Number.isFinite(index)) return;

    const action = button.dataset.action;
    const item = state.week.events[index];
    if (!item) return;

    if (action === "set-icon") {
      item.icon = String(button.dataset.iconValue || "").trim();
      renderRows();
      markDirty();
      return;
    }

    if (action === "duplicate") {
      resetFilters();
      const duplicatedEvent = normalizeEvent({
        ...item,
        id: crypto.randomUUID(),
        created_at: "",
        updated_at: "",
      });
      state.week.events.splice(index + 1, 0, duplicatedEvent);
      state.expandedEventIds.add(duplicatedEvent.id);
      renderFilters();
      renderRows();
      markDirty();
      setFlash(`Duplicated ${item.title || "event"}. Save to keep both rows.`);
      return;
    }

    if (action !== "remove") return;

    const confirmed = typeof window.confirm !== "function"
      || window.confirm(`Delete “${item.title || "this event"}” from this draft? Reload the week to undo an unsaved deletion.`);
    if (!confirmed) return;

    state.expandedEventIds.delete(item.id);
    state.week.events.splice(index, 1);
    renderFilters();
    renderRows();
    markDirty();
    setFlash("Event removed from the draft. Save to persist the change.");
  }

  function onTableToggle(event) {
    const card = event.target.closest(".event-card[data-index]");
    if (!card || !state.week) return;
    const index = Number(card.dataset.index);
    const item = state.week.events[index];
    if (!item) return;

    if (card.open) {
      state.expandedEventIds.add(item.id);
    } else {
      state.expandedEventIds.delete(item.id);
    }
    const expandLabel = card.querySelector(".event-expand-label");
    if (expandLabel) {
      expandLabel.textContent = card.open ? "Collapse" : "Expand";
    }
  }

  function onWeekRailClick(event) {
    const button = event.target.closest("[data-week-id]");
    if (!button) return;
    selectWeek(button.dataset.weekId);
  }

  function initPreviewTabs() {
    document.querySelectorAll(".tab-btn").forEach((button) => {
      button.addEventListener("click", () => {
        const tab = button.dataset.tab;
        document.querySelectorAll(".tab-btn").forEach((item) => {
          item.classList.toggle("tab-active", item.dataset.tab === tab);
          item.setAttribute("aria-selected", String(item.dataset.tab === tab));
        });
        document.querySelectorAll(".tab-panel").forEach((panel) => {
          panel.classList.toggle("tab-active", panel.id === `tab-${tab}`);
        });
      });
    });
  }

  function bind() {
    els.weekRail.addEventListener("click", onWeekRailClick);
    els.loadPastWeeks.addEventListener("click", () => selectWeek(isoDate(addDays(parseIsoDate(state.weekId), -7))));
    els.loadFutureWeeks.addEventListener("click", () => selectWeek(isoDate(addDays(parseIsoDate(state.weekId), 7))));
    els.createBtn.addEventListener("click", createDraftFromSource);
    els.saveBtn.addEventListener("click", () => saveWeek());
    els.previewBtn.addEventListener("click", () => previewWeek());
    els.approveBtn.addEventListener("click", approveWeek);
    els.sendNowBtn.addEventListener("click", sendWeekNow);
    els.markUnsentBtn.addEventListener("click", markWeekUnsent);
    els.exportBtn.addEventListener("click", exportEvents);
    els.addBtn.addEventListener("click", addCustomEvent);
    els.generateAiBtn.addEventListener("click", generateAiCopy);
    els.clearWeekBtn.addEventListener("click", clearWeek);
    els.copyAudienceButtons.forEach((button) => button.addEventListener("click", onCopyAudienceClick));
    [
      els.heading,
      els.notes,
      els.heroText,
      els.introTitle,
      els.introText,
      els.spotlightLabel,
      els.scheduleLabel,
      els.alsoLabel,
      els.emptyDayTemplate,
      els.ctaEyebrow,
      els.ctaTitle,
      els.ctaText,
      els.msSubjectInput,
      els.usSubjectInput,
    ].forEach((field) => field.addEventListener("input", onEditorialInput));
    els.deliveryOptions.forEach((input) => input.addEventListener("change", onDeliveryChange));
    els.eventSearch.addEventListener("input", onFilterInput);
    els.sourceFilter.addEventListener("change", onFilterInput);
    els.visibilityFilter.addEventListener("change", onFilterInput);
    els.clearFiltersBtn.addEventListener("click", clearEventFilters);
    els.requestList.addEventListener("input", onRequestInput);
    els.requestList.addEventListener("click", onRequestClick);
    els.tbody.addEventListener("input", onTableInput);
    els.tbody.addEventListener("change", onTableInput);
    els.tbody.addEventListener("click", onTableClick);
    els.tbody.addEventListener("toggle", onTableToggle, true);
  }

  async function init() {
    els.msFrame.srcdoc = EMPTY_PREVIEW;
    els.usFrame.srcdoc = EMPTY_PREVIEW;
    render();
    bind();
    initPreviewTabs();
    await loadWeek(state.weekId || defaults.weekId || "", { silent: true });
  }

  init();
})();
