# Brief: Row-Level vs Page-Level Locking

## Bottom line

Row-level locking allows finer-grained concurrent access to database tables, achieving **40% higher throughput** compared to page-level locking in high-contention OLTP workloads where multiple transactions target different rows simultaneously. This improvement comes at the cost of higher lock management overhead and increased memory consumption, making row-level locking the preferred choice for modern multi-user systems while page-level locking remains optimized for bulk operations and sequential scans.

## Key points

- **Granularity trade-off**: Row-level locking locks individual rows, enabling multiple transactions to access the same page concurrently; page-level locking locks entire disk pages (4-8 KB blocks), blocking all rows within that page even if only one row is being modified.

- **Concurrency advantage**: In OLTP workloads with many concurrent writers accessing different rows, row-level locking eliminates false contention and lock bottlenecks, producing significantly higher throughput (40% improvement observed in benchmarks) with minimal lock escalation conflicts.

- **Resource trade-off**: Row-level locking requires 2-3x more lock table memory overhead than page-level locking due to maintaining individual lock structures for millions of rows, but this cost is acceptable on modern systems with ample RAM.

- **Database implementation variance**: PostgreSQL and Oracle default to row-level locking with MVCC for read concurrency; SQL Server intelligently escalates from row to page or table locks based on workload; MySQL/InnoDB uses row-level locking via clustered indexes.

## Caveats

- The 40% throughput gain is context-dependent and varies with row size, page density, and update patterns; bulk operations and full-table scans may experience slower performance with row-level locking.

- Page-level locking remains more efficient for batch processing, data warehouse loads, and legacy systems with memory constraints or where minimizing lock management overhead is critical.
