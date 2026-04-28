# Audit Log Compliance Plan — Checkout Refactor Launch

## 1. Definition: What is a "Clean" Audit Log?

A clean audit log for this launch means:

- **No duplicate transactions:** Each idempotency key appears exactly once in the transaction ledger. No transaction is recorded twice, even if the same request was submitted multiple times (e.g., network retry, user double-click).

- **All transactions have valid idempotency keys:** Every transaction recorded Monday 2026-04-27 onward has a non-NULL `idempotency_key` header present in the audit log. Transactions from v1 (Saturday – Sunday, read-only period) do not require idempotency keys; v2 transactions (Friday–Monday ramp) must have them.

- **Consistent and monotonic timestamps:** Each transaction has a server-recorded `transaction_timestamp` (UTC). Timestamps are monotonically increasing per user (no backwards time travel). Request timestamp ≤ ledger timestamp ≤ response timestamp.

- **Reconcilable v1↔v2 transaction boundary:** Saturday 00:00 UTC, v1 goes read-only. Transactions from Saturday 00:00 onward are v2-only. Audit log clearly marks which code path (v1 vs v2) processed each transaction. No ambiguity about which system owns a transaction during handoff.

- **No orphaned or partial transactions:** A transaction is either fully recorded (request, processing, ledger entry, response) or not recorded at all. Partial writes (e.g., ledger entry present but idempotency key missing, or response sent but ledger entry absent) are treated as errors.

- **Audit trail is deterministic and reproducible:** Given a user ID, transaction date, and idempotency key, the audit log shows the exact same state whether queried once or 100 times. No cache eviction or lazy-write issues corrupt the historical record.

---

## 2. Post-Ramp Audit Procedure (Monday Night, April 28)

**Timeline:** Monday 2026-04-27 at 23:00 UTC (end of business, post-100% ramp).

**Owner:** Compliance + Engineering (joint responsibility; see below for role split).

### Pre-Audit Setup (by Friday EOD)

- **Compliance owner:** Define acceptable error threshold (e.g., < 0.1% duplicate rate is acceptable; >= 0.1% triggers rollback).
- **Engineering owner:** Build and stage the audit verification script (see "Verification Steps" below) in a read-only sandbox environment.
- **Ops owner:** Ensure audit log data is queriable via a read-only SQL interface or API; prepare off-line backups before the ramp begins.

### Verification Steps (Monday 23:00 UTC)

1. **Extract audit log snapshot**
   - Query: All transactions from `2026-04-25 00:00:00 UTC` (Saturday, v1 read-only begins) through `2026-04-27 23:59:59 UTC` (end of Monday).
   - Include: `transaction_id`, `idempotency_key`, `user_id`, `amount_cents`, `transaction_timestamp`, `code_path` (v1 vs v2), `request_timestamp`, `response_status`.
   - Output: CSV or Parquet file for downstream analysis.

2. **Validate idempotency key presence**
   - Count transactions with `idempotency_key IS NULL` in the v2 period (Friday onward).
   - **PASS:** Zero NULL keys in v2 period.
   - **FAIL:** Any NULL keys in v2 period. Action: Log critical alert; flag for investigation.

3. **Detect duplicates**
   - For each `(user_id, idempotency_key)` pair in v2 period, count occurrences in ledger.
   - **PASS:** All pairs appear exactly 1 time.
   - **FAIL:** Any pair appears 2+ times. Action: Log transaction IDs of duplicates; calculate impact (refund amount, user count).

4. **Verify timestamp monotonicity**
   - For each user, sort transactions by `transaction_timestamp`. Verify no timestamp decreases.
   - **PASS:** All user timelines are monotonic.
   - **FAIL:** Any user has out-of-order timestamps. Action: Log affected transactions and users.

5. **Reconcile v1 ↔ v2 boundary**
   - Count transactions before 2026-04-25 00:00:00 (v1 only): should match v1 system's ledger total.
   - Count transactions from 2026-04-25 00:00:00 onward (v2): cross-check against v2 system's ledger total.
   - **PASS:** Counts match within 1 transaction (accounting for edge-case timing).
   - **FAIL:** Discrepancy > 1. Action: Investigate missing or orphaned transactions.

6. **Validate code_path assignment**
   - Verify all v2-period transactions have `code_path = 'v2'`. No v1-path transactions in v2 period (except during partial rollback window, see Section 4).
   - **PASS:** Code path assignment is clean.
   - **FAIL:** Mixed code paths in v2 period without justification. Action: Investigate flag state changes during ramp.

### Pass/Fail Criteria

**PASS (Audit Complete, No Action Needed):**
- All 6 verification steps pass.
- Duplicate count: 0.
- NULL idempotency-key count: 0 (in v2 period).
- No timestamp inversions.
- v1 ↔ v2 boundary reconciles.

**FAIL (Minor Issues, Manual Review + Repair):**
- Duplicate count: 1–10 (< 0.1% of transaction volume). Action: Identify affected users, issue refunds, add duplicate records to "known issues" log for audit report. No rollback required.
- Timestamp inversion count: 1–5. Action: Correct timestamps in audit log (with audit trail of correction). Flag for manual review.

**CRITICAL FAIL (Immediate Rollback Required):**
- Duplicate count: > 10 or > 0.1% of transaction volume.
- NULL idempotency-key count: > 100 or > 0.1% of v2 transactions.
- v1 ↔ v2 reconciliation discrepancy: > 1 and cause unknown.
- Any evidence of code-path execution in wrong period (v1 processing v2-era transactions, or vice versa).
- Action: Initiate rollback (see Section 3).

### Ownership

- **Compliance officer:** Defines acceptable thresholds and signs off on PASS/FAIL determination.
- **Engineering lead:** Executes verification script; investigates root cause of any failures; provides remediation plan if FAIL (Minor).
- **Ops:** Provides data access, monitors script runtime, alerts if script hangs or times out.
- **Data engineer / DBA:** Executes data repair steps if FAIL (Minor); rolls back if CRITICAL FAIL.

---

## 3. Rollback Data Repair Steps

### Scenario A: Rollback During Ramp (Partial v2 Traffic, < 100%)

If we flip the feature flag OFF before reaching 100%, some transactions went through v2, some through v1.

**Steps:**

1. **Flip feature flag OFF:** Feature flag service sets the checkout flag to v1 for all users. Timestamp this action (this is the rollback boundary).

2. **Identify v2-era transactions:** Query audit log for all transactions between Friday 00:00 UTC and flag-flip timestamp with `code_path = 'v2'`.

3. **Validate idempotency compliance for v2 transactions:** For each v2 transaction, verify idempotency key is present and unique (already handled by post-ramp audit if applicable; if rollback happens pre-audit, run this check now).

4. **No data deletion:** Do NOT delete v2 transactions from the ledger. They are legally recorded; reversing them requires explicit refund requests. Leave v2 transactions in place with `code_path = 'v2'`.

5. **Prevent double-processing:** When traffic re-routes to v1, the v1 code path must not re-process any idempotency keys seen in the v2 period. Add a check: before v1 accepts a transaction, query the audit log for (user_id, idempotency_key, timestamp within last 24h). If found, reject with "Transaction already processed" (HTTP 409 Conflict) and return the original response.

6. **Audit trail:** Log the rollback event in a separate `rollback_events` table with timestamp, reason, user count affected, and data engineer owner.

**Ownership:**
- **Feature flag service owner:** Flip flag OFF.
- **Backend engineering:** Deploy v1 ↔ v2 idempotency check immediately after flag flip.
- **Data engineer:** Query and validate v2 transaction list; confirm no orphans.

**Data cleanup timeline:** None required immediately. Post-launch (week of 2026-05-01), audit team and compliance review the v2 transaction list and determine if refunds or corrections are needed. This is a separate compliance workflow, not critical path.

---

### Scenario B: Rollback Post-100% Ramp (All Traffic v2, Audit Completed)

If audit (Section 2) fails with CRITICAL FAIL, we must rollback after 100% traffic is live.

**Steps:**

1. **Alert compliance and exec:** Immediately notify compliance officer and engineering leadership that audit failed. Present failure type and estimated user/transaction impact.

2. **Decide: Rollback or Repair?**
   - If failure is < 5 duplicate transactions affecting < 10 users: Option to repair instead of rollback (see Scenario C below).
   - If failure is > 5 duplicates or > 10 users affected, or if root cause is unknown: Proceed to Rollback.

3. **Flip feature flag OFF:** Feature flag service sets checkout flag to v1. Timestamp this action.

4. **Verify v1 schema compatibility:** Before traffic re-routes, test that v1 code path runs successfully against the v2-migrated database schema (this should have been done in staging pre-launch, see Section 4; confirm it was). If any schema errors surface, abort rollback and escalate to data engineer for emergency schema repair.

5. **Re-route traffic to v1:** Monitor v1 error rate and checkout conversion rate for 30 minutes. If error rate spikes or conversion drops > 5%, investigate immediately. If investigation reveals schema issue or logic error, consider full database rollback (see below).

6. **Audit log handling:** All v2-period transactions remain in the audit log. They are immutable. Mark v2 transactions in audit log with `audit_status = 'rolled_back'` (adds a column to track this). Transactions from rollback-onward will be re-processed via v1 code path.

7. **Idempotency safeguard:** Same as Scenario A: v1 code path checks audit log before processing. If an idempotency key exists in v2 period, it is not re-processed.

**Ownership:**
- **Compliance officer + Exec sponsor:** Approve rollback decision.
- **Feature flag service owner:** Execute flag flip.
- **Backend engineering:** Verify schema compatibility; monitor v1 error rate; implement idempotency check.
- **Ops:** Monitor checkout metrics; alert if conversion drops.

---

### Scenario C: Rollback with Data Repair (Isolated Issues, < 5 Duplicates)

If audit fails but with a small, isolated issue (e.g., 3 duplicate transactions due to a known edge case), repair instead of full rollback.

**Steps:**

1. **Document the issue:** Capture which transactions are duplicates, which users are affected, root cause hypothesis.

2. **Identify remediation:** For each duplicate:
   - If one copy is clearly "correct" (matches request-to-response flow), mark the other as `audit_status = 'duplicate_suppressed'`.
   - If both copies are valid (both have request/response), issue a refund for one and mark it `audit_status = 'refund_issued'`.
   - If the duplicate was caused by a transient error (e.g., network timeout causing retry), investigate the retry logic and fix it for future transactions.

3. **Execute refunds:** For each suppressed/refund-marked transaction, automatically issue a refund credit to the user's account or original payment method. Log refund in a `refunds` table with reference to the original audit entry.

4. **Update audit log:** Add explanatory notes to the audit entry: "Duplicate detected post-audit. Refund issued on [date]. Reference: [refund ID]."

5. **Continue v2 (no rollback):** Leave the feature flag ON and continue forward with v2. Issue a post-mortem on what caused the duplicates to prevent recurrence.

**Ownership:**
- **Compliance officer:** Approves individual repair decisions.
- **Backend engineering:** Implements refund logic and audit log annotations.
- **Payments/Finance:** Validates refunds against ledger.

---

## 4. Incomplete Rollback: Audit Log Consistency

If the rollback process is interrupted (e.g., flag flip succeeds but v1 schema compatibility fails and we cannot proceed), the audit log is in a mixed state:
- v2-era transactions (Friday–rollback timestamp): code_path = 'v2'
- Post-rollback era: partially attempted v1, may have errors or incomplete transactions

**Handling:**

1. **Pause all checkout traffic:** Do not allow new transactions until the inconsistency is resolved.

2. **Audit log state:** Record a `rollback_event` with `status = 'incomplete'`, `pause_timestamp`, and `reason` (e.g., "v1 schema incompatible with v2 migration").

3. **Resolve the blocker:**
   - If v1 schema issue: Run emergency schema repair (e.g., add missing column v1 expects, or drop new constraint) to make v1 compatible.
   - If v1 logic error: Roll back the v1 deployment and re-deploy a hotfix, or skip the rollback entirely and proceed with v2-only repair (Scenario C).

4. **Update audit log after resolution:** Once the issue is resolved, record a follow-up event: `rollback_event` with `status = 'completed'` or `status = 'aborted_proceeding_with_v2'`.

5. **Audit log integrity:** The mixed-state audit log is valid and acceptable IF all transactions are fully recorded (complete request/processing/ledger/response). The presence of incomplete transactions is not acceptable and must be cleaned up before audit passes.

   **Criteria for acceptable mixed-state audit log:**
   - All transactions have either fully succeeded or fully failed (no half-written records).
   - Each transaction has a complete audit trail (request, code path executed, ledger entry, response status).
   - The rollback event is recorded with clear timestamp and reason.
   - No orphaned or partial writes.

**Ownership:**
- **Data engineer / DBA:** Executes schema repair or rollback.
- **Compliance officer:** Validates that mixed-state audit log is still compliant (i.e., no data integrity issues).
- **Incident commander:** Coordinates pause/resume of checkout traffic.

---

## 5. Pre-Launch Verification Checklist

To ensure this plan is executable by Friday EOD:

- [ ] Audit verification script is staged and tested in sandbox with synthetic v2 transactions.
- [ ] Audit log schema includes: `idempotency_key`, `transaction_timestamp`, `request_timestamp`, `code_path`, `audit_status` fields.
- [ ] v1 code path has been updated to check audit log before processing (idempotency guard in Scenario A/B).
- [ ] v1 has been tested against v2-migrated database schema in staging (Scenario B, step 4).
- [ ] Rollback event table (`rollback_events`) is created and queryable.
- [ ] Refund logic is implemented and tested (Scenario C).
- [ ] Compliance officer and engineering lead have reviewed and signed off on this plan.
- [ ] Ops has runbooks for flag flip, data export, and rollback monitoring.
- [ ] On-call roster for Monday night includes: data engineer, backend engineer, compliance officer, ops lead.

---

## Summary

**Clean audit log definition:** No duplicate transactions; all v2 transactions have idempotency keys; monotonic timestamps; reconcilable v1↔v2 boundary; no orphaned records.

**Post-ramp audit:** Monday 23:00 UTC, verify 6 conditions (idempotency, duplicates, timestamps, boundary, code path, orphans). PASS → ship. FAIL (Minor) → repair. FAIL (Critical) → rollback.

**Rollback steps:** Flip flag, idempotency guard v1, verify schema, re-route traffic, mark v2 transactions with audit status. If rollback is incomplete, pause traffic and resolve blocker.

**Ownership:** Compliance (thresholds, sign-off), Engineering (verification, repair, v1 compatibility), Ops (monitoring, runbooks), Data (schema, refunds).

This plan is a compliance blocker and must be signed off by Friday EOD.
