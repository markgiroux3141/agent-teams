# Row-Level vs Page-Level Locking in Relational Databases

## Core Mechanics

**Row-level locking** grants exclusive or shared access to individual table rows, ensuring that only one transaction can modify a specific row at a time. The lock is held until the transaction commits or rolls back. **Page-level locking** operates at a coarser granularity, locking entire disk pages (typically 4-8 KB blocks) containing multiple rows. When a transaction needs to modify a row, it locks the entire page holding that row.

The fundamental trade-off stems from lock granularity: finer locks (row-level) allow more concurrent transactions to proceed in parallel, while coarser locks (page-level) reduce lock management overhead.

## Advantages and Disadvantages

### Row-Level Locking

**Advantages:**
- Enables higher concurrency: multiple transactions can operate on different rows in the same table or page simultaneously
- Reduces lock contention in high-concurrency workloads with many simultaneous transactions targeting different data
- Better for OLTP systems where many users access overlapping but distinct subsets of data
- Minimizes cascade lock escalation problems (deadlocks between waiting transactions)

**Disadvantages:**
- Higher memory overhead: maintaining individual locks for millions of rows consumes significant lock table memory
- Increased CPU cost for lock acquisition, release, and conflict detection
- Higher latency in lock operations due to more frequent locking/unlocking cycles
- Complex deadlock detection and resolution becomes necessary at finer granularity
- Slower full-table scans and sequential operations that naturally lock contiguous rows

### Page-Level Locking

**Advantages:**
- Lower memory footprint: fewer lock structures needed in the lock table
- Reduced CPU overhead per lock operation; operations naturally align with storage structure
- Simpler deadlock handling for sequential operations
- Better for bulk operations (full table scans, batch updates) where multiple adjacent rows need locking anyway
- Faster lock acquisitions due to fewer lock structures to manage

**Disadvantages:**
- False contention: transactions targeting different rows in the same page block each other unnecessarily
- Reduced concurrency in workloads with multiple concurrent writers
- Lock escalation risk: when many rows on a page are locked, the system may escalate to page-level or table-level locks, temporarily stalling other transactions
- Performance degradation under contention; "hot pages" become bottlenecks

## Real-World Database Implementations

**PostgreSQL**: Uses row-level locking with a sophisticated MVCC (Multi-Version Concurrency Control) system. Locks are stored in a centralized lock manager and coexist with row versions. This design favors read concurrency and OLTP workloads.

**SQL Server**: Supports multiple locking granularities and intelligent lock escalation. It starts with row-level locks but escalates to page or table locks if the number of locks exceeds a threshold, balancing concurrency with overhead.

**MySQL/InnoDB**: Implements row-level locking through clustered index structures. Each row lock is tracked by the lock manager, enabling high concurrency for row updates but increasing overhead during full-table operations.

**Oracle Database**: Employs row-level locking natively, though it uses lock-free read consistency through undo logs and MVCC variants, reducing lock contention on reads.

## Trade-Offs and Use Cases

**Row-level locking is optimal for:**
- OLTP systems with many short transactions targeting distinct rows
- Workloads where concurrent writers frequently modify different data
- Systems where memory and CPU for lock management are plentiful
- Applications requiring minimal lock contention and maximum parallelism

**Page-level locking is optimal for:**
- Batch processing and bulk operations (ETL, data warehouse loads)
- Workloads dominated by sequential or full-table scans
- Systems with severe memory constraints
- Legacy systems where lock management overhead must be minimized
- Scenarios where hot pages are unavoidable (e.g., identity sequences, monotonically increasing keys)

## Modern Context

Most modern relational databases default to row-level locking because contemporary systems typically prioritize OLTP performance and multi-user concurrency. However, the trade-off resurfaces in special cases: systems like PostgreSQL automatically handle full-table scans efficiently despite row locking, while databases like SQL Server provide dynamic escalation to avoid lock memory exhaustion during large operations. The choice between row and page locking is increasingly a tuning parameter rather than a hard architectural constraint.
