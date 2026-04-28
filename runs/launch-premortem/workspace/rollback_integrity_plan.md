# Rollback Integrity Plan — Data Reconciliation & Schema Compatibility

**Objective:** Ensure that if the feature flag is flipped OFF (rollback), v1 code can run successfully against the v2-migrated database schema, and post-rollback ledger integrity can be verified.

**Critical blocker:** The v2 migration has already run in production. If rollback becomes necessary and v1 encounters schema errors, we are stuck. This plan must be **tested in staging by Thursday EOD**.

---

## 1. Rollback Test Plan in Staging (Complete by Thursday EOD)

### Timeline

- **Wednesday 2026-04-23, afternoon:** Set up staging environment with v2 migration applied
- **Wednesday evening:** Ramp synthetic v2 traffic to staging (10–20 transactions) to populate ledger
- **Thursday 2026-04-24, morning:** Execute rollback test (flip flag OFF, verify v1 transactions)
- **Thursday 2:00 PM:** Complete test report, share with ops and compliance

### Test Environment Setup

#### Step 1: Prepare Staging Database (Wednesday afternoon)

1. **Snapshot production database schema** (schema only, no data)
   - Or: Take current staging schema and apply the v2 migration to it (same migration that already ran in prod)
   - Confirm that all schema changes from the v2 migration are present:
     - New columns added to transaction table (e.g., `idempotency_key`, `code_path`)
     - New indexes created for v2 optimization
     - Any schema constraints or triggers added for v2
     - Verify: `DESCRIBE transactions` shows all v2 columns

2. **Enable v2 code path** (feature flag ON)
   - Set feature flag to v2 in staging Redis
   - Verify: GET flag-key returns "v2"

3. **Confirm v1 code is still available** (not deleted)
   - v1 code path must still exist in the deployed version (feature flag controls routing, not code presence)
   - Verify: git history shows v1 code is in the branch

#### Step 2: Ramp Synthetic v2 Traffic (Wednesday evening, 1–2 hours)

Run 10–20 synthetic transaction requests through the v2 checkout flow in staging:

1. **Transaction workload**
   - 5 successful v2 transactions (valid coupons, valid amounts)
   - 3 failed v2 transactions (invalid coupon, expired, cart too small) — these should be rejected by v2
   - 2 duplicate attempt transactions (same user, same idempotency key) — should be rejected on second attempt
   - Generate requests with realistic request timestamps, valid idempotency keys, user IDs

2. **Capture the audit log state pre-rollback**
   - Query: `SELECT COUNT(*) as tx_count, code_path FROM transactions WHERE created_at >= NOW() - INTERVAL 2 HOURS GROUP BY code_path;`
   - Expected result: `tx_count=10, code_path=v2` (only v2 transactions should exist)
   - Save baseline counts for comparison post-rollback

3. **Verify v2 transactions are in ledger**
   - Query: `SELECT transaction_id, user_id, idempotency_key, code_path, status FROM transactions WHERE code_path = 'v2' ORDER BY created_at DESC LIMIT 20;`
   - Confirm all 10 transactions are present with correct status (5 successful, 3 rejected, 2 rejected due to idempotency duplicate)
   - Confirm each successful v2 transaction has a non-NULL idempotency_key

#### Step 3: Execute Rollback (Thursday morning, 9:00 AM)

**Step 3a: Flip the feature flag**

1. Set feature flag to v1 in staging Redis
   - Verify: `GET checkout-flag` returns "v1"
   - Record timestamp: `2026-04-24 09:00:00 UTC` (this is the rollback boundary)

2. Log rollback event
   - Insert into `rollback_events`: `{timestamp: 09:00:00, reason: 'STAGING_TEST', flag_state: 'v1', user_count_v2: 10}`

**Step 3b: Run v1 transactions through the migrated schema (Thursday morning, 9:05 AM)**

Attempt 10 new v1 transactions against the v2-migrated schema:

1. **Transaction workload (same pattern as v2 above)**
   - 5 successful v1 transactions (valid data)
   - 3 failed v1 transactions (invalid coupon, expired, invalid amount) — v1 should reject these gracefully
   - 2 transactions that were already processed in v2 (same user, same idempotency key) — v1 should recognize as already-processed and not re-process

2. **Run transactions and capture results**
   ```
   For each transaction:
     - Execute v1 request
     - Capture response status code (2xx success, 4xx client error, 5xx server error)
     - Capture response body / error message
     - Record whether transaction succeeded or failed
     - Look for any database constraint violations, column not found, type mismatches
   ```

3. **Expected outcomes:**
   - 5 successful v1 transactions: HTTP 200, transaction recorded in ledger with `code_path = 'v1'`
   - 3 invalid v1 transactions: HTTP 400, transaction NOT recorded in ledger (validation fails before write)
   - 2 duplicate idempotency keys: HTTP 409 (already processed), transaction NOT recorded again (idempotency guard works)

4. **Failure detection:**
   - **RED FLAG:** Any HTTP 5xx error from v1 transactions → schema incompatibility detected
   - **RED FLAG:** "Column not found" error → v1 expects a column that doesn't exist in v2-migrated schema
   - **RED FLAG:** "Constraint violation" error → v2 migration added a constraint that v1 can't satisfy
   - **RED FLAG:** Transaction count mismatch (see below)

#### Step 4: Verify Ledger State Post-Rollback (Thursday morning, 9:30 AM)

1. **Transaction count verification**
   ```sql
   SELECT COUNT(*) as v2_tx_count FROM transactions WHERE code_path = 'v2';
   SELECT COUNT(*) as v1_tx_count FROM transactions WHERE code_path = 'v1';
   ```
   - Expected: v2_tx_count = 10 (unchanged from pre-rollback)
   - Expected: v1_tx_count = 5 (only the 5 successful new v1 transactions)
   - **PASS:** Total = 15. **FAIL:** Any other count indicates lost or duplicate transactions.

2. **Idempotency verification post-rollback**
   ```sql
   SELECT user_id, idempotency_key, COUNT(*) as dup_count 
   FROM transactions 
   WHERE idempotency_key IS NOT NULL 
   GROUP BY user_id, idempotency_key 
   HAVING dup_count > 1;
   ```
   - Expected: No results (no duplicates)
   - **PASS:** Empty result set. **FAIL:** Any row indicates a duplicate transaction ID.

3. **Code path assignment verification**
   ```sql
   SELECT code_path, COUNT(*) as count FROM transactions GROUP BY code_path;
   ```
   - Expected: Results show clean separation (10 v2, 5 v1)
   - **PASS:** Clear split by code_path. **FAIL:** Mixed code paths or NULL code_path values.

4. **Timestamp monotonicity check**
   ```sql
   SELECT 
     user_id, 
     transaction_id, 
     created_at,
     LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at) as prev_timestamp
   FROM transactions
   WHERE user_id IN (
     SELECT user_id FROM transactions 
     GROUP BY user_id 
     HAVING COUNT(*) >= 2
   )
   ORDER BY user_id, created_at;
   ```
   - For any user with 2+ transactions, verify `created_at >= prev_timestamp` (monotonically increasing)
   - **PASS:** All timestamps in order. **FAIL:** Any timestamp decreases (data corruption).

#### Step 5: Test Data Repair Mechanism (Thursday morning, 10:00 AM)

If any failures are detected, test the remediation:

1. **Scenario: Schema incompatibility found**
   - For each schema error found, document:
     - The specific error message
     - The v1 code that triggered it
     - The v2 schema change that caused it
     - Proposed fix (e.g., add a default column value, update v1 code, modify constraint)

2. **Scenario: Duplicate transaction found**
   - Test the cleanup process (see Section 3)
   - Delete the duplicate record from ledger
   - Verify count is corrected

3. **Scenario: Orphaned transaction found**
   - Identify which code path owns it (v1 or v2)
   - Document the root cause
   - If it's a legitimate transaction, correct the code_path or owner; if orphaned, mark for removal

#### Step 6: Report & Sign-Off (Thursday 2:00 PM)

1. **Rollback Test Report**
   ```
   Test Name: Staging Rollback Integrity Test (2026-04-24)
   Test Owner: [Engineer Name]
   
   Pre-Rollback State:
   - v2 transactions: 10
   - v1 transactions: 0
   - Total: 10
   
   Rollback Action: Flipped flag OFF at 09:00 UTC
   
   Post-Rollback State (after v1 transactions):
   - v2 transactions: 10 (unchanged)
   - v1 transactions: 5 (new)
   - Total: 15
   
   Test Results:
   - v1 transaction success rate: 5/10 (5 succeeded, 5 rejected for validation)
   - Schema compatibility: PASS / FAIL
   - Idempotency guard: PASS / FAIL
   - Timestamp monotonicity: PASS / FAIL
   - Code path assignment: PASS / FAIL
   
   Issues Found:
   - [List any schema errors, constraint violations, or data anomalies]
   
   Remediation (if needed):
   - [Specific fix for each issue]
   - [Estimated effort and risk]
   
   Go/No-Go for Friday Launch: GO / NO-GO
   
   Sign-off:
   - Test Engineer: _________________ (Date/Time)
   - Ops Lead: _________________ (Date/Time)
   - DBA: _________________ (Date/Time)
   ```

2. **Sign-off criteria for GO:**
   - All v1 transactions succeed without schema errors
   - Idempotency guard works (duplicates rejected)
   - Timestamp monotonicity maintained
   - Code path assignment clean
   - Total transaction count correct
   - No orphaned or partial transactions

3. **Sign-off criteria for NO-GO:**
   - Any schema incompatibility found and no quick fix available
   - Idempotency guard fails to prevent duplicates
   - Data corruption detected (timestamp inversion, orphaned transactions)
   - Duplicate transactions appear that shouldn't

---

## 2. Data Reconciliation Procedure (Post-Rollback)

**Applies if:** Rollback occurs (flag OFF at any point)

**Timing:** Execute immediately post-rollback (within 1 hour) if rollback was unplanned

### Reconciliation Owner

- **Data engineer / DBA:** Executes queries, compares counts, identifies discrepancies
- **Ops:** Monitors query runtime, alerts if anything takes too long
- **Compliance:** Reviews results for any data integrity gaps

### Reconciliation Steps

#### Step 1: Extract Transaction Snapshots (Immediate, within 1 hour of rollback)

1. **Snapshot v2 transactions**
   ```sql
   SELECT 
     transaction_id,
     user_id,
     idempotency_key,
     amount_cents,
     code_path,
     status,
     created_at,
     updated_at
   INTO OUTFILE 'v2_transactions_snapshot.csv'
   FROM transactions
   WHERE code_path = 'v2'
   ORDER BY created_at;
   ```
   - File: `v2_transactions_snapshot.csv` (saved to secure location)
   - Count total: `SELECT COUNT(*) FROM transactions WHERE code_path = 'v2';`

2. **Snapshot v1 transactions**
   ```sql
   SELECT 
     transaction_id,
     user_id,
     idempotency_key,
     amount_cents,
     code_path,
     status,
     created_at,
     updated_at
   INTO OUTFILE 'v1_transactions_snapshot.csv'
   FROM transactions
   WHERE code_path = 'v1'
   ORDER BY created_at;
   ```
   - File: `v1_transactions_snapshot.csv`
   - Count total: `SELECT COUNT(*) FROM transactions WHERE code_path = 'v1';`

3. **Snapshot rollback_events**
   ```sql
   SELECT * FROM rollback_events ORDER BY timestamp DESC;
   ```
   - File: `rollback_events_snapshot.csv`
   - Confirms flag flip timestamp and reasoning

#### Step 2: Compare Transaction Counts

1. **Total transaction count comparison**
   ```sql
   SELECT 
     'v2' as code_path,
     COUNT(*) as transaction_count,
     SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
     SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
   FROM transactions
   WHERE code_path = 'v2'
   
   UNION ALL
   
   SELECT 
     'v1' as code_path,
     COUNT(*) as transaction_count,
     SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
     SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
   FROM transactions
   WHERE code_path = 'v1';
   ```
   - Expected: v2 count = baseline from pre-rollback test; v1 count = new transactions since rollback
   - **PASS:** Counts match expected. **WARN:** Off-by-one acceptable (in-flight request). **FAIL:** Discrepancy > 5.

2. **Identify missing transactions (not in either ledger)**
   ```sql
   SELECT COUNT(*) as orphaned_count
   FROM transactions
   WHERE code_path IS NULL OR code_path NOT IN ('v1', 'v2');
   ```
   - Expected: 0
   - **FAIL:** Any NULL or unknown code_path.

#### Step 3: Detect Duplicate Transactions (by Idempotency Key)

1. **Find duplicates across v1 and v2**
   ```sql
   SELECT 
     user_id,
     idempotency_key,
     code_path,
     COUNT(*) as occurrence_count,
     GROUP_CONCAT(transaction_id) as transaction_ids
   FROM transactions
   WHERE idempotency_key IS NOT NULL
   GROUP BY user_id, idempotency_key, code_path
   HAVING occurrence_count > 1;
   ```
   - Expected: Empty result (no duplicates within same code path)
   - **FAIL:** Any result indicates duplicates.

2. **Find duplicates across v1 and v2 (same idempotency key, different code path)**
   ```sql
   SELECT 
     user_id,
     idempotency_key,
     COUNT(DISTINCT code_path) as code_path_count,
     GROUP_CONCAT(DISTINCT code_path) as code_paths,
     GROUP_CONCAT(transaction_id) as transaction_ids
   FROM transactions
   WHERE idempotency_key IS NOT NULL
   GROUP BY user_id, idempotency_key
   HAVING code_path_count > 1;
   ```
   - Expected: Empty result (same idempotency key should not be processed by both v1 and v2)
   - **WARN:** If results exist, check if they are valid (e.g., v2 transaction before rollback, v1 transaction after). If the same idempotency key exists in both, it's a data integrity issue (see Section 3).

#### Step 4: Verify Amount Reconciliation (Financial)

1. **Total amount processed per code path**
   ```sql
   SELECT 
     code_path,
     COUNT(*) as transaction_count,
     SUM(amount_cents) as total_cents,
     SUM(amount_cents) / 100.0 as total_dollars,
     AVG(amount_cents) as avg_cents
   FROM transactions
   WHERE status = 'success'
   GROUP BY code_path;
   ```
   - Expected: v2 and v1 should each show the total amount processed through that path
   - **PASS:** Amounts are positive and reasonable. **FAIL:** Negative amounts or zero when expecting positive.

2. **Compare against external ledger (if available)**
   - If there's an external payments ledger or bank settlement file, cross-check:
     - Sum of v1 successful transactions should match v1 ledger
     - Sum of v2 successful transactions should match v2 ledger
     - **WARN:** Small discrepancies (< 0.01%) acceptable due to timing; investigate anything larger.

#### Step 5: Verify Timestamp Integrity

1. **Check for timestamp inversions**
   ```sql
   SELECT 
     user_id,
     transaction_id,
     created_at,
     LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at) as prev_timestamp,
     CASE WHEN created_at < LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at) THEN 'INVERSION' ELSE 'OK' END as time_check
   FROM transactions
   ORDER BY user_id, created_at;
   ```
   - Expected: All rows show 'OK'
   - **FAIL:** Any 'INVERSION' indicates time went backwards (data corruption).

2. **Check for timestamps outside expected window**
   ```sql
   SELECT 
     code_path,
     COUNT(*) as count,
     MIN(created_at) as earliest_tx,
     MAX(created_at) as latest_tx
   FROM transactions
   GROUP BY code_path;
   ```
   - v2 transactions should all be before rollback timestamp
   - v1 transactions should mostly be after rollback timestamp (with overlap during partial rollback window)
   - **FAIL:** v1 transactions with timestamps before rollback (indicates clock skew or data movement).

#### Step 6: Generate Reconciliation Report

1. **Report format**
   ```
   Data Reconciliation Report (Post-Rollback)
   ==========================================
   
   Rollback Timestamp: 2026-04-27 15:30:00 UTC
   Report Generated: 2026-04-27 16:00:00 UTC (30 minutes post-rollback)
   Owner: [DBA Name]
   
   Transaction Counts:
   - v2 transactions: [count]
   - v1 transactions: [count]
   - Total: [count]
   - Orphaned: [count]
   
   Duplicate Transactions:
   - Same idempotency key within v1: [count]
   - Same idempotency key within v2: [count]
   - Same idempotency key across v1 and v2: [count]
   
   Amount Reconciliation:
   - v2 total: [amount]
   - v1 total: [amount]
   - Discrepancy vs external ledger: [amount or ✓ matches]
   
   Timestamp Integrity:
   - Inversions detected: [count] ✓ PASS / ✗ FAIL
   - Timestamps outside expected window: [count]
   
   Data Quality Issues:
   - [List each issue with severity and remediation needed]
   
   Recommendation:
   - Proceed with cleanup (Section 3) / Escalate to DRI / Investigate further
   
   Sign-off:
   - Data Engineer: _________________ (Date/Time)
   - Compliance: _________________ (Date/Time)
   ```

2. **Sign-off criteria:**
   - Counts reconcile (v2 + v1 = total, no orphans)
   - No duplicate transactions (or duplicates within acceptable threshold)
   - Amounts reconcile (or discrepancy explained)
   - Timestamps integrity verified
   - All critical issues have documented remediation

---

## 3. Audit Log Correction & Cleanup (if Duplicates Found)

**Applies if:** Data reconciliation finds duplicates

**Owner:** Data engineer (execution), Compliance officer (approval), Backend engineer (investigation)

### Cleanup Steps

#### Step 1: Identify Root Cause of Duplicates

For each duplicate found:

1. **Classify the duplicate**
   - **Type A:** Same idempotency key appears twice within v1 or v2 (genuine duplicate)
   - **Type B:** Same idempotency key appears in both v1 and v2 (indicates failed idempotency guard during rollback)
   - **Type C:** Same idempotency key appears in v2 post-rollback (indicates transaction was re-submitted after rollback and idempotency guard failed)

2. **Investigate root cause**
   - **For Type A:** v1 or v2 code path allowed a duplicate through despite idempotency-key check. Likely a race condition or bug in idempotency enforcement.
   - **For Type B:** The idempotency guard that checks audit log for existing v2 transactions (before processing in v1) failed. Likely a timing issue or the audit log wasn't accessible.
   - **For Type C:** User re-submitted the same request post-rollback, and v1 didn't recognize it as already-processed. Indicates idempotency-key wasn't preserved across v2→v1 handoff.

3. **Document findings**
   ```
   Duplicate Investigation Report
   ===============================
   Idempotency Key: [key]
   User ID: [id]
   Type: A / B / C
   Occurrences: [count]
   
   Transactions Involved:
   - Transaction ID: [id], Code Path: [v1/v2], Amount: [cents], Status: [success/failed], Timestamp: [ts]
   - Transaction ID: [id], Code Path: [v1/v2], Amount: [cents], Status: [success/failed], Timestamp: [ts]
   
   Root Cause Hypothesis:
   - [Describe what likely caused the duplicate]
   
   Evidence:
   - [Logs, timestamps, state that supports the hypothesis]
   
   Recommended Action:
   - Delete duplicate (which one?)
   - Issue refund (if both succeeded, refund one)
   - Leave as-is (if both are legitimate but code path is wrong, fix code path)
   ```

#### Step 2: Decide Action Per Duplicate

For each classified duplicate:

1. **If Type A (genuine duplicate within one code path)**
   - One record is the "canonical" transaction; the other is a duplicate
   - Determine which one to keep:
     - Keep the first occurrence (original request)
     - Mark the second occurrence with `audit_status = 'duplicate_suppressed'`
   - If both transactions succeeded and amount charged twice:
     - Issue a refund credit for one transaction
     - Mark the refunded transaction with `audit_status = 'duplicate_refunded'`

2. **If Type B (same key in both v1 and v2)**
   - One transaction is illegitimate (the v1 re-processing)
   - Keep the v2 transaction (it was processed before rollback)
   - Delete or suppress the v1 transaction
   - If v1 transaction succeeded and charged: issue refund
   - Mark suppressed transaction: `audit_status = 'duplicate_suppressed_v1_reprocessing'`

3. **If Type C (post-rollback duplicate)**
   - User re-submitted the same request in v1, and idempotency guard failed
   - One transaction is the original (in v2); one is the duplicate (in v1)
   - Keep the v2 transaction; suppress the v1 transaction
   - If v1 transaction succeeded and charged: issue refund
   - Mark suppressed: `audit_status = 'duplicate_suppressed_post_rollback_resubmit'`

#### Step 3: Execute Cleanup (DBA Only, with Audit Trail)

1. **For each duplicate to suppress:**
   ```sql
   UPDATE transactions 
   SET audit_status = 'duplicate_suppressed',
       suppression_reason = '[Type A/B/C and reason]',
       suppressed_timestamp = NOW(),
       suppressed_by = '[DBA Name]'
   WHERE transaction_id = '[duplicate_transaction_id]';
   ```

2. **For each transaction requiring refund:**
   ```sql
   INSERT INTO refunds (
     original_transaction_id,
     refund_amount_cents,
     reason,
     refund_status,
     created_at
   ) VALUES (
     '[transaction_id]',
     '[amount_cents]',
     'Duplicate transaction — duplicate suppressed; refund issued',
     'pending',
     NOW()
   );
   
   -- Update transaction to mark it refunded
   UPDATE transactions 
   SET audit_status = 'duplicate_refunded',
       refund_transaction_id = LAST_INSERT_ID()
   WHERE transaction_id = '[duplicate_transaction_id]';
   ```

3. **Log cleanup event**
   ```sql
   INSERT INTO audit_corrections (
     correction_type,
     original_transaction_id,
     affected_count,
     reason,
     corrected_by,
     corrected_timestamp
   ) VALUES (
     'duplicate_suppression',
     '[transaction_id]',
     1,
     'Type B duplicate: same idempotency key in v1 and v2. Suppressed v1 transaction. User will be refunded if charged.',
     '[DBA Name]',
     NOW()
   );
   ```

4. **Verify cleanup**
   - Re-run duplicate detection query (Section 2, Step 3)
   - Confirm duplicate is no longer flagged (either deleted or marked suppressed)
   - Confirm refund is in `refunds` table with status 'pending'

#### Step 4: Refund Processing (Finance/Payments Team)

1. **Identify all pending refunds**
   ```sql
   SELECT * FROM refunds WHERE refund_status = 'pending';
   ```

2. **Process refunds**
   - For each pending refund, issue credit to user's original payment method or account balance
   - Update refund status to 'completed' with timestamp

3. **Notify users** (if needed)
   - Send email: "We detected a duplicate charge in our system and have automatically refunded the extra amount. You should see the refund in 3–5 business days. Details: [transaction IDs, amounts]."

#### Step 5: Audit Report

1. **Compile cleanup report**
   ```
   Audit Log Correction Report (Post-Rollback)
   ============================================
   
   Corrections Executed: [Date/Time]
   Owner: [DBA Name]
   
   Duplicates Found: [count]
   
   Per Type:
   - Type A (within code path): [count], all suppressed
   - Type B (across v1 and v2): [count], all suppressed
   - Type C (post-rollback resubmit): [count], all suppressed
   
   Actions Taken:
   - Duplicates suppressed: [count]
   - Refunds issued: [count]
   - Total affected users: [count]
   - Total refund amount: [dollars]
   
   Verification:
   - Duplicate query result: Empty ✓
   - Refunds in system: [count] with status 'pending'
   
   Sign-off:
   - DBA: _________________ (Date/Time)
   - Compliance: _________________ (Date/Time)
   ```

---

## 4. Rollback Success Criteria & Verification Queries

**Applies if:** Rollback is executed in production

**Owner:** Ops (monitoring), Data engineer (verification), Compliance (sign-off)

**Timing:** Run within 1 hour of rollback flag OFF

### Go/No-Go Queries

#### Query 1: Transaction Count Integrity

```sql
SELECT 
  code_path,
  COUNT(*) as total_count,
  SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
  COUNT(DISTINCT user_id) as unique_users,
  MIN(created_at) as earliest_tx,
  MAX(created_at) as latest_tx
FROM transactions
GROUP BY code_path
ORDER BY code_path;
```

**PASS Criteria:**
- v2 count is stable (same as pre-rollback) ± 1 (in-flight request)
- v1 count is > 0 (new transactions post-rollback)
- v1 success rate is > 95% (transactions succeeding)
- No NULL code_path values

**FAIL Criteria:**
- v2 count changes significantly (lost transactions)
- v1 success rate < 85% (indicates systematic error)
- NULL code_path detected

#### Query 2: Idempotency Key Validation

```sql
SELECT 
  COUNT(*) as null_key_count
FROM transactions
WHERE code_path = 'v2' AND idempotency_key IS NULL;

-- Also check duplicates
SELECT 
  user_id,
  idempotency_key,
  COUNT(*) as occurrence_count
FROM transactions
WHERE idempotency_key IS NOT NULL
GROUP BY user_id, idempotency_key
HAVING occurrence_count > 1;
```

**PASS Criteria:**
- NULL key count = 0 (all v2 transactions have idempotency keys)
- Duplicate check returns empty result (no duplicates)

**FAIL Criteria:**
- Any NULL keys in v2 transactions
- Any idempotency-key duplicates exist

#### Query 3: Timestamp Monotonicity

```sql
SELECT 
  COUNT(*) as inversion_count
FROM (
  SELECT 
    user_id,
    created_at,
    LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at) as prev_ts
  FROM transactions
  WHERE prev_ts > created_at
) inversions;
```

**PASS Criteria:**
- Inversion count = 0 (all timestamps are in order)

**FAIL Criteria:**
- Inversion count > 0 (timestamp went backwards — data corruption)

#### Query 4: Amount Reconciliation

```sql
SELECT 
  code_path,
  COUNT(*) as tx_count,
  SUM(amount_cents) as total_cents,
  SUM(amount_cents) / 100.0 as total_dollars,
  SUM(CASE WHEN status = 'success' THEN amount_cents ELSE 0 END) / 100.0 as successful_dollars
FROM transactions
GROUP BY code_path;
```

**PASS Criteria:**
- v1 and v2 amounts are both positive
- v2 amount matches baseline (pre-rollback)
- v1 amount is reasonable for the time window

**FAIL Criteria:**
- Negative amounts detected
- v2 amount changed significantly
- Amounts don't reconcile with external ledger (coordinate with Finance)

#### Query 5: Orphaned Transactions

```sql
SELECT 
  COUNT(*) as orphaned_count,
  GROUP_CONCAT(DISTINCT code_path) as code_paths
FROM transactions
WHERE code_path IS NULL 
   OR code_path NOT IN ('v1', 'v2')
   OR (idempotency_key IS NULL AND code_path = 'v2');
```

**PASS Criteria:**
- Orphaned count = 0

**FAIL Criteria:**
- Any orphaned transactions detected

### Rollback Success Decision Tree

```
Run all 5 queries above.

IF Query 1 PASS AND Query 2 PASS AND Query 3 PASS AND Query 4 PASS AND Query 5 PASS:
  → ROLLBACK SUCCESSFUL ✓
  → Resume normal operations
  → Schedule post-mortem for root cause analysis
  → No additional actions required

IF Query 1 FAIL OR Query 3 FAIL OR Query 5 FAIL:
  → CRITICAL FAILURE — DATA CORRUPTION DETECTED
  → STOP all operations
  → Escalate to DRI (Data Recovery / Infrastructure)
  → Consider database rollback to pre-rollback snapshot
  → Page VP Engineering + Compliance Officer immediately

IF Query 2 FAIL:
  → IDEMPOTENCY FAILURE — DUPLICATES DETECTED
  → Execute cleanup procedure (Section 3)
  → Issue refunds for duplicates
  → Sign-off before resuming operations

IF Query 4 FAIL:
  → FINANCIAL INTEGRITY ISSUE
  → Escalate to Finance + Compliance
  → Do not resume operations until amounts reconcile
  → May require manual audit of transactions
```

### Rollback Success Checklist

After executing rollback in production:

- [ ] Feature flag flipped OFF: confirm `GET checkout-flag` returns 'v1'
- [ ] Timestamp recorded: rollback event in `rollback_events` table
- [ ] Wait 5 minutes for in-flight v2 transactions to complete
- [ ] Run Query 1 (Transaction counts) → PASS?
- [ ] Run Query 2 (Idempotency) → PASS?
- [ ] Run Query 3 (Timestamp monotonicity) → PASS?
- [ ] Run Query 4 (Amount reconciliation) → PASS?
- [ ] Run Query 5 (Orphaned transactions) → PASS?
- [ ] All queries pass → Rollback SUCCESSFUL
- [ ] Data reconciliation report signed off by DBA + Compliance
- [ ] Any duplicates found → Cleanup executed (Section 3)
- [ ] Finance confirms refunds processed (if any)
- [ ] Incident commander notifies team: "Rollback complete, v1 live, all systems stable"

---

## 5. Pre-Launch Checklist (for Thursday EOD)

To ensure rollback integrity is verified before Friday ship:

**Staging Test (Must Complete by Thursday EOD):**
- [ ] Staging database has v2 migration applied
- [ ] Synthetic v2 traffic ramped (10–20 transactions)
- [ ] Feature flag flipped OFF in staging
- [ ] 5 successful v1 transactions executed against v2 schema
- [ ] 5 v1 validation failures (expected)
- [ ] 2 v1 idempotency duplicates (expected to be rejected)
- [ ] All 5 verification queries (Section 4) executed and PASS
- [ ] Rollback test report completed and signed off

**Data Reconciliation Scripts Ready:**
- [ ] v2 transaction snapshot query ready (Section 2, Step 1)
- [ ] v1 transaction snapshot query ready
- [ ] Duplicate detection queries ready (Section 2, Step 3)
- [ ] Amount reconciliation queries ready (Section 2, Step 4)
- [ ] Timestamp integrity queries ready (Section 2, Step 5)
- [ ] All queries validated in staging

**Cleanup Procedures Ready:**
- [ ] Duplicate classification process documented (Section 3, Step 1)
- [ ] Cleanup SQL templates prepared (Section 3, Step 3)
- [ ] Refund processing workflow documented (Section 3, Step 4)
- [ ] DBA trained on cleanup execution
- [ ] Compliance approved cleanup criteria

**Rollback Success Criteria Documented:**
- [ ] All 5 verification queries identified (Section 4)
- [ ] PASS/FAIL thresholds defined
- [ ] Decision tree documented
- [ ] Rollback checklist prepared for on-call use

**Owners & Escalation Path Confirmed:**
- [ ] Data Engineer (owner): name and on-call contact
- [ ] Ops Lead (monitoring): name and on-call contact
- [ ] DBA (schema/cleanup): name and on-call contact
- [ ] Compliance Officer (sign-off): name and on-call contact
- [ ] Page routing verified in PagerDuty (escalation paths)

**Sign-Off for Friday Ship:**
- [ ] Test Engineer: Staging rollback test PASS
- [ ] DBA: Schema compatibility confirmed
- [ ] Ops: Reconciliation queries ready
- [ ] Compliance: Cleanup procedures approved
- [ ] PM/Leadership: GO for Friday ship

---

## Summary

**Rollback Integrity Plan ensures:**

1. **Schema compatibility verified** — v1 runs successfully against v2 schema (tested in staging, Thursday EOD)
2. **Data reconciliation procedure documented** — post-rollback audit queries ready, owner assigned
3. **Duplicate cleanup process defined** — if duplicates found, root cause identified, data repaired, users refunded
4. **Rollback success criteria specified** — 5 verification queries with go/no-go thresholds; decision tree for escalation

**Timeline:**
- Wednesday: Set up staging, ramp v2 traffic
- Thursday morning: Execute rollback test, verify all queries pass
- Thursday 2 PM: Sign-off report, confirm GO for Friday ship
- Friday: Monitor; if rollback needed, execute with pre-tested procedures
- Post-rollback: Run reconciliation queries (within 1 hour), execute cleanup if needed

**Key owners:**
- **Data Engineer / DBA:** Staging test execution, reconciliation queries, cleanup
- **Ops:** Monitoring, alerting, decision tree execution
- **Compliance:** Cleanup approval, sign-off
- **Backend Engineer:** Investigation of root causes, schema verification

This plan is a compliance and operational blocker for Friday launch. **Must be complete and signed off by Thursday EOD.**
