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
  const backendState = {
    sent: { sent: false, sent_at: '', sent_by: '', sending: false, sending_at: '', sending_by: '' },
    finalizeAttempts: 0,
    ingestCalls: 0,
    failIngest: Boolean(options.failIngest),
    ingestAction: options.ingestAction || 'created',
  };
  const deliveries = [];
  const adminEmails = [];
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
    MailApp: {
      sendEmail(options) {
        if (options.to === 'admin@example.test') {
          adminEmails.push(options);
          return;
        }
        deliveries.push(options);
      },
    },
    UrlFetchApp: {
      fetch(url, options = {}) {
        if (url.includes('/api/emails/automation/weeks/')) {
          backendState.ingestCalls += 1;
          if (backendState.failIngest) {
            return makeResponse(503, { ok: false, error: 'scheduled ingest failed' });
          }

          return makeResponse(200, {
            ok: true,
            week_id: '2026-03-09',
            action: backendState.ingestAction,
            reason: backendState.ingestAction === 'created' ? 'created_from_sources' : 'existing_draft',
            source_summary: {
              athletics_events: backendState.ingestAction === 'created' ? 2 : 0,
              arts_events: backendState.ingestAction === 'created' ? 1 : 0,
              total_events: backendState.ingestAction === 'created' ? 3 : 0,
            },
            week: { week_id: '2026-03-09' },
          });
        }

        if (url.endsWith('/sender-output')) {
          return makeResponse(200, {
            ok: true,
            approved: true,
            week_id: '2026-03-09',
            outputs: {
              'middle-school': { audience: 'middle-school', subject: 'MS Sports', html: '<p>MS</p>' },
              'upper-school': { audience: 'upper-school', subject: 'US Sports', html: '<p>US</p>' },
            },
            sent: { ...backendState.sent },
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
      formatDate(_date, _timezone, format) {
        if (format === 'yyyy-MM-dd') return '2026-03-09';
        if (format === 'MMMdd') return 'mar09';
        if (format === 'EEEE, MMMM dd, yyyy') return 'Monday, March 09, 2026';
        return '2026-03-09';
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
    `${senderSource}\nthis.__exports = { runSundayDraftCycle, sendSportsEmails, setupTriggers, removeTriggers, CONFIG };`,
    sandbox
  );
  sandbox.__exports.CONFIG.API_BASE_URL = 'https://example.test';
  sandbox.__exports.CONFIG.AUTOMATION_API_KEY = 'secret-key';
  sandbox.__exports.CONFIG.ADMIN_EMAIL = 'admin@example.test';
  sandbox.__exports.CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL.to = 'middle@example.test';
  sandbox.__exports.CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL.to = 'upper@example.test';

  return { exports: sandbox.__exports, backendState, deliveries, adminEmails, triggers };
}

test('rerun does not resend when sent finalization fails after delivery', () => {
  const harness = buildHarness();

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

test('sunday draft cycle emails review link when a draft is created', () => {
  const harness = buildHarness({ ingestAction: 'created' });

  harness.exports.runSundayDraftCycle();

  assert.equal(harness.backendState.ingestCalls, 1);
  assert.equal(harness.adminEmails.length, 1);
  assert.match(harness.adminEmails[0].subject, /Review sports email draft/i);
  assert.match(harness.adminEmails[0].body, /2026-03-09/);
  assert.match(harness.adminEmails[0].body, /3 imported events/i);
  assert.match(harness.adminEmails[0].htmlBody, /emails\?week=2026-03-09/i);
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

test('sunday draft cycle sends admin error email on backend failure', () => {
  const harness = buildHarness({ failIngest: true });

  harness.exports.runSundayDraftCycle();

  assert.equal(harness.backendState.ingestCalls, 1);
  assert.equal(harness.adminEmails.length, 1);
  assert.match(harness.adminEmails[0].subject, /Automation Error/i);
  assert.match(harness.adminEmails[0].body, /draft cycle/i);
});

test('setupTriggers creates both sunday triggers and removes existing managed ones', () => {
  const harness = buildHarness({ triggers: ['sendSportsEmails', 'runSundayDraftCycle', 'otherHandler'] });

  harness.exports.setupTriggers();

  const handlers = harness.triggers.map((trigger) => trigger.getHandlerFunction()).sort();
  assert.deepEqual(handlers, ['otherHandler', 'runSundayDraftCycle', 'sendSportsEmails']);
});

test('apps script sources use app-owned ingest and approved sender flow', () => {
  assert.doesNotMatch(senderSource, /raw\.githubusercontent/);
  assert.doesNotMatch(troubleshootingSource, /raw\.githubusercontent/);
  assert.match(senderSource, /scheduled-ingest/);
  assert.match(senderSource, /sender-output/);
  assert.match(troubleshootingSource, /debugScheduledIngestAccess/);
});
