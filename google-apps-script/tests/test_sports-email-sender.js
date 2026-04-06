const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const senderSource = fs.readFileSync(path.join(__dirname, '..', 'sports-email-sender.gs'), 'utf8');
const troubleshootingSource = fs.readFileSync(path.join(__dirname, '..', 'troubleshooting-functions.gs'), 'utf8');

function makeResponse(status, payload) {
  return {
    getResponseCode() {
      return status;
    },
    getContentText() {
      return JSON.stringify(payload);
    },
  };
}

function buildHarness(options = {}) {
  const weekId = options.weekId || '2026-03-09';
  const todayIso = options.todayIso || '2026-03-08';
  const signageDayId = options.signageDayId || todayIso;
  const isoWeekday = options.isoWeekday || 7;
  const senderDelivery = options.delivery || {
    mode: 'default',
    send_on: options.deliverySendOn || todayIso,
    send_time: '16:00',
  };
  const ingestWeekDelivery = options.ingestWeekDelivery || senderDelivery;
  const backendState = {
    sent: { sent: false, sent_at: '', sent_by: '', sending: false, sending_at: '', sending_by: '' },
    finalizeAttempts: 0,
    ingestCalls: 0,
    signageRefreshCalls: 0,
    activityCalls: [],
    failIngest: Boolean(options.failIngest),
    failSignageRefresh: Boolean(options.failSignageRefresh),
    ingestAction: options.ingestAction || 'created',
    weekId,
    todayIso,
    signageDayId,
    isoWeekday,
    approved: options.senderApproved !== false,
    delivery: senderDelivery,
  };
  const deliveries = [];
  const adminEmails = [];
  const properties = {
    API_BASE_URL: 'https://example.test',
    AUTOMATION_API_KEY: 'secret-key',
    ADMIN_NOTIFICATION_EMAILS: 'admin@example.test',
    MIDDLE_SCHOOL_TO: 'middle@example.test',
    MIDDLE_SCHOOL_BCC: 'middlebcc@example.test',
    UPPER_SCHOOL_TO: 'upper@example.test',
    UPPER_SCHOOL_BCC: 'upperbcc@example.test',
  };
  const triggers = (options.triggers || []).map((handlerFunction) => ({
    getHandlerFunction() {
      return handlerFunction;
    },
    getTriggerSource() {
      return 'CLOCK';
    },
  }));

  const sandbox = {
    console,
    Date: options.Date || Date,
    MailApp: {
      sendEmail(opts) {
        if ((opts.to || '').includes('admin@example.test')) {
          adminEmails.push(opts);
          return;
        }
        deliveries.push(opts);
      },
    },
    PropertiesService: {
      getScriptProperties() {
        return {
          getProperty(name) {
            return properties[name] || '';
          },
          setProperty(name, value) {
            properties[name] = value;
          },
        };
      },
    },
    Session: {
      getActiveUser() {
        return {
          getEmail() {
            return 'tester@example.test';
          },
        };
      },
    },
    UrlFetchApp: {
      fetch(url, options = {}) {
        if (url.includes('/api/emails/automation/weeks/') && url.endsWith('/activity')) {
          backendState.activityCalls.push(JSON.parse(options.payload || '{}'));
          return makeResponse(200, { ok: true });
        }

        if (url.includes('/api/signage/automation/days/')) {
          backendState.signageRefreshCalls += 1;
          if (backendState.failSignageRefresh) {
            return makeResponse(503, { ok: false, error: 'signage refresh failed' });
          }

          return makeResponse(200, {
            ok: true,
            day_id: backendState.signageDayId,
            action: backendState.signageRefreshCalls === 1 ? 'created' : 'refreshed',
            reason: backendState.signageRefreshCalls === 1 ? 'created_from_sources' : 'replaced_existing_snapshot',
            source_summary: {
              athletics_events: 1,
              arts_events: 1,
              total_events: 2,
            },
            day: { date: backendState.signageDayId },
          });
        }

        if (url.includes('/api/emails/automation/weeks/')) {
          backendState.ingestCalls += 1;
          if (backendState.failIngest) {
            return makeResponse(503, { ok: false, error: 'scheduled ingest failed' });
          }

          return makeResponse(200, {
            ok: true,
            week_id: backendState.weekId,
            action: backendState.ingestAction,
            reason: backendState.ingestAction === 'created' ? 'created_from_sources' : 'existing_draft',
            source_summary: {
              athletics_events: backendState.ingestAction === 'created' ? 2 : 0,
              arts_events: backendState.ingestAction === 'created' ? 1 : 0,
              total_events: backendState.ingestAction === 'created' ? 3 : 0,
            },
            week: { week_id: backendState.weekId, delivery: ingestWeekDelivery },
          });
        }

        if (url.endsWith('/sender-output')) {
          return makeResponse(200, {
            ok: true,
            approved: backendState.approved,
            week_id: backendState.weekId,
            outputs: {
              'middle-school': { audience: 'middle-school', subject: 'MS Sports', html: '<p>MS</p>' },
              'upper-school': { audience: 'upper-school', subject: 'US Sports', html: '<p>US</p>' },
            },
            sent: { ...backendState.sent },
            delivery: { ...backendState.delivery },
          });
        }

        if (!url.endsWith('/sent')) {
          throw new Error(`Unexpected fetch URL: ${url}`);
        }

        const payload = JSON.parse(options.payload || '{}');
        if (payload.state === 'sending') {
          if (backendState.sent.sent) {
            return makeResponse(200, { ok: true, sent: { ...backendState.sent } });
          }
          if (backendState.sent.sending) {
            return makeResponse(409, { ok: false, error: 'Week is already claimed for sending by google-apps-script at 2026-03-09T16:00:00Z' });
          }
          backendState.sent = {
            sent: false,
            sent_at: '',
            sent_by: '',
            sending: true,
            sending_at: '2026-03-09T16:00:00Z',
            sending_by: 'google-apps-script',
          };
          return makeResponse(200, { ok: true, sent: { ...backendState.sent } });
        }

        if (payload.state === 'sent') {
          backendState.finalizeAttempts += 1;
          return makeResponse(503, { ok: false, error: 'backend unavailable while recording sent-state' });
        }

        return makeResponse(400, { ok: false, error: 'unexpected state' });
      },
    },
    Utilities: {
      formatDate(date, _timezone, format) {
        const value = date instanceof Date ? date : new Date(date);
        const isoUtc = `${value.getUTCFullYear()}-${String(value.getUTCMonth() + 1).padStart(2, '0')}-${String(value.getUTCDate()).padStart(2, '0')}`;
        const weekdayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        const monthShort = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

        if (format === 'u') return String(backendState.isoWeekday);
        if (format === 'yyyy-MM-dd') {
          if (value.getUTCHours() || value.getUTCMinutes() || value.getUTCSeconds() || value.getUTCMilliseconds()) {
            return backendState.todayIso;
          }
          return isoUtc;
        }
        if (format === 'MMMdd') {
          return `${monthShort[value.getUTCMonth()]}${String(value.getUTCDate()).padStart(2, '0')}`;
        }
        if (format === 'EEEE, MMMM dd, yyyy') {
          return `${weekdayNames[value.getUTCDay()]}, ${monthNames[value.getUTCMonth()]} ${String(value.getUTCDate()).padStart(2, '0')}, ${value.getUTCFullYear()}`;
        }
        return isoUtc;
      },
    },
    ScriptApp: {
      WeekDay: { SUNDAY: 'SUNDAY' },
      getProjectTriggers() {
        return triggers;
      },
      deleteTrigger(trigger) {
        const index = triggers.indexOf(trigger);
        if (index >= 0) {
          triggers.splice(index, 1);
        }
      },
      newTrigger(handlerFunction) {
        const trigger = {
          handlerFunction,
          getHandlerFunction() {
            return handlerFunction;
          },
          getTriggerSource() {
            return 'CLOCK';
          },
        };
        return {
          timeBased() { return this; },
          everyDays() { return this; },
          everyWeeks() { return this; },
          onWeekDay() { return this; },
          atHour(hour) {
            trigger.hour = hour;
            return this;
          },
          create() {
            triggers.push(trigger);
            return trigger;
          },
        };
      },
    },
    Logger: { log() {} },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    `${senderSource}\nthis.__exports = { refreshDailySignage, runSundayDraftCycle, sendSportsEmails, setupTriggers, removeTriggers, validateConfiguration, getEffectiveConfig, getTargetMondayDate, getCurrentWeekId, getCurrentSignageDayId, CONFIG };`,
    sandbox
  );

  return { exports: sandbox.__exports, backendState, deliveries, adminEmails, triggers, properties };
}

test('configuration validation fails fast when script properties are missing', () => {
  const harness = buildHarness();
  delete harness.properties.AUTOMATION_API_KEY;

  const result = harness.exports.validateConfiguration();

  assert.equal(result.ok, false);
  assert.match(result.missing.join(','), /AUTOMATION_API_KEY/);
});

test('rerun does not resend when sent finalization fails after delivery', () => {
  const harness = buildHarness({
    todayIso: '2026-03-08',
    isoWeekday: 7,
    delivery: { mode: 'default', send_on: '2026-03-08', send_time: '16:00' },
  });

  harness.exports.sendSportsEmails();

  assert.equal(harness.deliveries.length, 2);
  assert.equal(harness.adminEmails.length, 1);
  assert.equal(harness.backendState.sent.sent, false);
  assert.equal(harness.backendState.sent.sending, true);
  assert.match(harness.adminEmails[0].body, /remains claimed as sending to prevent duplicate reruns/i);

  harness.exports.sendSportsEmails();

  assert.equal(harness.deliveries.length, 2);
  assert.equal(harness.adminEmails.length, 2);
  assert.equal(harness.backendState.finalizeAttempts, 1);
  assert.match(harness.adminEmails[1].body, /already claimed for sending/i);
});

test('dispatcher sends postponed weeks on the scheduled weekday', () => {
  const harness = buildHarness({
    todayIso: '2026-03-10',
    isoWeekday: 2,
    delivery: { mode: 'postpone', send_on: '2026-03-10', send_time: '16:00' },
  });

  harness.exports.sendSportsEmails();

  assert.equal(harness.deliveries.length, 2);
  assert.equal(harness.backendState.finalizeAttempts, 1);
});

test('dispatcher no-ops for skipped weeks', () => {
  const harness = buildHarness({
    todayIso: '2026-03-10',
    isoWeekday: 2,
    delivery: { mode: 'skip', send_on: '', send_time: '16:00' },
  });

  harness.exports.sendSportsEmails();

  assert.equal(harness.deliveries.length, 0);
  assert.equal(harness.backendState.activityCalls[0].status, 'skipped');
});

test('sunday draft cycle emails review link when a draft is created', () => {
  const harness = buildHarness({ ingestAction: 'created' });

  harness.exports.runSundayDraftCycle();

  assert.equal(harness.backendState.ingestCalls, 1);
  assert.equal(harness.adminEmails.length, 1);
  assert.match(harness.adminEmails[0].subject, /Review sports email draft/i);
  assert.match(harness.adminEmails[0].body, /2026-03-09/);
  assert.match(harness.adminEmails[0].body, /3 imported events/i);
  assert.match(harness.adminEmails[0].htmlBody, /emails\?week=2026-03-09/i);
  assert.equal(harness.backendState.activityCalls[0].event_type, 'review_notification');
  assert.equal(harness.backendState.activityCalls[0].status, 'success');
});

test('daily signage refresh hits the app-owned signage endpoint', () => {
  const harness = buildHarness();

  harness.exports.refreshDailySignage();

  assert.equal(harness.backendState.signageRefreshCalls, 1);
  assert.equal(harness.adminEmails.length, 0);
});

test('sunday draft cycle still emails review link when draft already exists', () => {
  const harness = buildHarness({ ingestAction: 'skipped' });

  harness.exports.runSundayDraftCycle();

  assert.equal(harness.backendState.ingestCalls, 1);
  assert.equal(harness.adminEmails.length, 1);
  assert.match(harness.adminEmails[0].subject, /existing sports email draft/i);
  assert.match(harness.adminEmails[0].body, /left it unchanged/i);
  assert.match(harness.adminEmails[0].htmlBody, /emails\?week=2026-03-09/i);
});

test('sunday draft cycle suppresses review email when skipped week already exists', () => {
  const harness = buildHarness({
    ingestAction: 'skipped',
    ingestWeekDelivery: { mode: 'skip', send_on: '', send_time: '16:00' },
  });

  harness.exports.runSundayDraftCycle();

  assert.equal(harness.adminEmails.length, 0);
  assert.equal(harness.backendState.activityCalls[0].event_type, 'review_notification');
  assert.equal(harness.backendState.activityCalls[0].status, 'suppressed');
});

test('sunday draft cycle sends admin error email on backend failure', () => {
  const harness = buildHarness({ failIngest: true });

  harness.exports.runSundayDraftCycle();

  assert.equal(harness.backendState.ingestCalls, 1);
  assert.equal(harness.adminEmails.length, 1);
  assert.match(harness.adminEmails[0].subject, /Automation Error/i);
  assert.match(harness.adminEmails[0].body, /draft cycle/i);
  assert.equal(harness.backendState.activityCalls[0].status, 'failed');
});

test('setupTriggers creates both sunday triggers and removes existing managed ones', () => {
  const harness = buildHarness({ triggers: ['refreshDailySignage', 'sendSportsEmails', 'runSundayDraftCycle', 'otherHandler'] });

  harness.exports.setupTriggers();

  const handlers = harness.triggers.map((trigger) => trigger.getHandlerFunction()).sort();
  assert.deepEqual(handlers, ['otherHandler', 'refreshDailySignage', 'runSundayDraftCycle', 'sendSportsEmails']);
});

test('timezone helpers derive monday and day ids from configured timezone dates', () => {
  class FixedDate extends Date {
    constructor(...args) {
      if (args.length) {
        super(...args);
        return;
      }
      super('2026-03-08T23:30:00Z');
    }
    static now() {
      return new Date('2026-03-08T23:30:00Z').getTime();
    }
  }

  const harness = buildHarness({ Date: FixedDate, todayIso: '2026-03-08', isoWeekday: 7 });
  harness.properties.TIMEZONE = 'America/Denver';

  const monday = harness.exports.getTargetMondayDate();

  assert.ok(monday instanceof Date);
  assert.equal(harness.exports.getCurrentWeekId(), '2026-03-09');
  assert.equal(harness.exports.getCurrentSignageDayId(), '2026-03-08');
});

test('apps script sources use app-owned ingest, approved sender flow, and script properties', () => {
  assert.doesNotMatch(senderSource, /raw\.githubusercontent/);
  assert.doesNotMatch(troubleshootingSource, /raw\.githubusercontent/);
  assert.match(senderSource, /scheduled-ingest/);
  assert.match(senderSource, /api\/signage\/automation\/days/);
  assert.match(senderSource, /sender-output/);
  assert.match(senderSource, /PropertiesService/);
  assert.match(troubleshootingSource, /validateConfiguration/);
});
