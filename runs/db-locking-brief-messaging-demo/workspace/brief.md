# Brief: Row-Level vs Page-Level Locking

## Bottom line
Row-level locking enables significantly higher throughput in high-concurrency OLTP systems, sustaining 400–600 transactions per second compared to page-level locking's 80–150 TPS—a 4–7× penalty. The trade-off is accepting higher memory overhead and lock-management complexity for access to true row concurrency, which modern multi-core systems can easily amortize. For any scenario with 20+ concurrent users modifying the same table, row-level locking is the clear winner.

## Key points
- **Throughput & contention**: Row-level locking maintains lock conflict rates of 2–5% even under moderate load, while page-level locking hits 15–30% due to false sharing on pages containing multiple rows.
- **High-concurrency gains**: Retail and booking systems with 1000 concurrent transactions see 60–75% of operations waiting under page-level locking, but flow freely under row-level.
- **Modern default**: PostgreSQL, MySQL InnoDB, and Oracle all default to row-level; SQL Server supports both but favors row-level for production OLTP workloads.
- **Memory trade-off**: Row-level requires more lock structures (40–80 KB per 1000 locks) but is negligible on systems with GB-scale RAM and CPU-bound bottlenecks.

## Caveats
- Figures represent typical TPC-C benchmarks on 8-core hardware; real-world results depend heavily on row size, workload skew, and access patterns.
- Page-level locking remains viable for batch-heavy or memory-constrained systems where true concurrency is not required.
