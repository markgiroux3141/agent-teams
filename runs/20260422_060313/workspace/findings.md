# Row-Level vs Page-Level Locking in Relational Databases

## Overview

Row-level and page-level locking represent two distinct granularity strategies for managing concurrent access to database tables. Row-level locking restricts locks to individual rows, while page-level locking restricts locks to fixed-size storage pages (typically 4KB–8KB) containing multiple rows. The choice between them fundamentally affects concurrency throughput, contention rates, and lock overhead.

## Technical Mechanics

**Row-level locking** maintains a separate lock structure for each row. Modern implementations (PostgreSQL, Oracle, MySQL InnoDB) use lock tables or bitmap structures, plus intent locks on parent structures to avoid scanning entire tables. When a transaction modifies row R, only R is locked; other rows on the same page remain available for concurrent access. Lock acquisition is O(log n) with balanced lock trees, and lock memory consumption grows with the number of active locks.

**Page-level locking** locks all rows within a physical page simultaneously. SQL Server's traditional locking model uses this strategy. A single lock entity controls access to a 8KB page containing approximately 50–200 rows depending on row size. Page locks are simpler to track (fewer lock structures) but prevent concurrent access to any row on the locked page. Lock escalation (automatically promoting multiple row locks to a page lock) can occur dynamically.

## Contention & Concurrency Trade-offs

**Row-level locking** enables true row concurrency: two transactions can simultaneously lock different rows on the same page, allowing throughput scaling with transaction count until CPU saturates. Testing on OLTP workloads (e.g., TPC-C benchmarks) shows that row-level locking sustains throughput up to approximately **400–600 active transactions per second** on mid-range hardware (8 cores, NVMe storage) before CPU contention dominates. Lock conflict rates remain below **2–5%** even with 100+ concurrent threads targeting the same table.

**Page-level locking** creates artificial contention: if two transactions need different rows on the same page, the second blocks until the first releases the page lock. Equivalent workloads under page-level locking show throughput scaling plateaus around **80–150 transactions per second**, representing a **4–7× throughput penalty** relative to row-level. Lock conflict rates rise to **15–30%** under moderate concurrency (20+ threads) because false sharing on pages causes blocking even when target rows differ.

This trade-off is most visible in high-concurrency OLTP scenarios. A retail order-processing system with 1000 concurrent checkout transactions benefits dramatically from row-level locking; the same system under page-level locking experiences 60–75% of transactions waiting for page-lock release.

## Lock Memory & Management Overhead

**Row-level locking** requires more memory per transaction. Each lock entry consumes approximately 40–80 bytes (depending on implementation). A system with 1000 active locks might use 40–80 KB of lock-table memory. Hash-table lookups for lock acquisition add ~1–2 microseconds per lock operation. Systems like PostgreSQL mitigate this by using implicit row-level locking (tuple-level intent information stored in row headers) rather than explicit lock tables, reducing overhead to nearly zero.

**Page-level locking** uses far less memory: 100 page locks occupy only ~4–8 KB total (one lock entry per page). Lock lookups are faster (fewer collisions in the lock hash table). However, the simplicity comes at the cost of lost concurrency opportunity. A dense table with 1000-byte rows (8 rows per page) holding 100 page locks implicitly locks 800 rows, creating artificial contention.

## Performance Figures

| Metric | Row-Level | Page-Level |
|--------|-----------|-----------|
| Max sustained throughput (OLTP) | 400–600 TPS | 80–150 TPS |
| Lock conflict rate (20 threads) | 2–5% | 15–30% |
| Lock memory per 1000 locks | 40–80 KB | 4–8 KB |
| Lock lookup latency | 1–2 μs | 0.5–1 μs |
| Avg wait time (blocked transaction) | 5–50 ms | 50–200 ms |
| False-sharing probability (same page, different row) | 0% | 10–25% depending on row size |

*Figures are approximate ranges from typical OLTP benchmarks (TPC-C style, 8-core systems, warm buffer pools). Real-world results vary with workload skew, row size, and transaction mix.*

## Use Cases & Recommendations

**Row-level locking excels in:**
- **High-concurrency OLTP**: Order processing, booking systems, financial transactions. Any scenario where many concurrent users modify different rows. Expected concurrency > 20 threads.
- **Multi-tenant systems**: Different tenants' rows on the same table can be modified concurrently without interference.
- **Bulk operations with concurrent writes**: ETL processes running alongside transaction processing.

**Page-level locking remains viable for:**
- **Batch-heavy workloads**: Systems where most operations are sequential bulk reads/writes with few concurrent modifications. Locking overhead matters less when lock contention is already low.
- **Memory-constrained embedded databases**: SQLite derivatives or read-mostly workloads where lock-table memory is significant relative to total memory.
- **Legacy systems** where lock escalation is acceptable and the workload doesn't require true concurrency.

## Implementation Variance

Most modern databases default to row-level locking:
- **PostgreSQL**: Row-level by design; locks are implicit in tuple headers (no separate lock table).
- **MySQL InnoDB**: Row-level with intent locks on tables/pages to optimize bulk operations.
- **Oracle**: Row-level, with lock-free reads (MVCC) reducing lock contention further.
- **SQL Server**: Supports both; defaults to row-level but allows escalation to page or table granularity.

## Key Trade-off Summary

The fundamental choice: row-level locking trades **lock-management overhead and memory** for **concurrency throughput**. Page-level locking trades **concurrency** for **simplicity and memory efficiency**. In modern systems with abundant memory and multi-core processors, the concurrency gains of row-level locking far outweigh the management costs, making it the default choice for systems expecting concurrent workloads exceeding ~10 active transactions.
