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

function buildHarness() {
  const backendState = {
    sent: { sent: false, sent_at: '', sent_by: '', sending: false, sending_at: '', sending_by: '' },
    finalizeAttempts: 0,
  };
  const deliveries = [];
  const notifications = [];

  const sandbox = {
    console,
    MailApp: {
      sendEmail(options) {
        if (options && options.htmlBody) {
          deliveries.push(options);
          return;
        }
        notifications.push(options);
      },
    },
    UrlFetchApp: {
      fetch(url, options = {}) {
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
      newTrigger() {
        return {
          timeBased() { return this; },
          onWeekDay() { return this; },
          atHour() { return this; },
          create() { return this; },
        };
      },
      getProjectTriggers() {
        return [];
      },
      deleteTrigger() {},
    },
    Logger: { log() {} },
  };

  vm.createContext(sandbox);
  vm.runInContext(`${senderSource}\nthis.__exports = { sendSportsEmails, CONFIG };`, sandbox);
  sandbox.__exports.CONFIG.API_BASE_URL = 'https://example.test';
  sandbox.__exports.CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL.to = 'middle@example.test';
  sandbox.__exports.CONFIG.EMAIL_RECIPIENTS.UPPER_SCHOOL.to = 'upper@example.test';

  return { exports: sandbox.__exports, backendState, deliveries, notifications };
}

test('rerun does not resend when sent finalization fails after delivery', () => {
  const harness = buildHarness();

  harness.exports.sendSportsEmails();

  assert.equal(harness.deliveries.length, 2);
  assert.equal(harness.notifications.length, 1);
  assert.equal(harness.backendState.sent.sent, false);
  assert.equal(harness.backendState.sent.sending, true);
  assert.match(harness.notifications[0].body, /remains claimed as sending to prevent duplicate reruns/i);

  harness.exports.sendSportsEmails();

  assert.equal(harness.deliveries.length, 2);
  assert.equal(harness.notifications.length, 2);
  assert.equal(harness.backendState.finalizeAttempts, 1);
  assert.match(harness.notifications[1].body, /already claimed for sending/i);
});

test('apps script sources use approved API flow and omit legacy GitHub aliases', () => {
  assert.doesNotMatch(senderSource, /testGitHubAccess/);
  assert.doesNotMatch(senderSource, /raw\.githubusercontent/);
  assert.doesNotMatch(troubleshootingSource, /raw\.githubusercontent/);
  assert.doesNotMatch(troubleshootingSource, /debugGitHubAccess/);
  assert.match(troubleshootingSource, /fetchApprovedEmailPayloads/);
});