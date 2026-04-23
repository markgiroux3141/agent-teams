# Brief: Monoliths vs Microservices

## Bottom Line

Start with a monolith unless your organization is operationally mature (can run Kubernetes reliably). Nearly all successful companies—Netflix, Twitter, Shopify, Airbnb—began monolithic, then extracted services as boundaries became clear and teams grew. The critical variable is organizational readiness, not technical superiority. Microservices buy independent team scaling at the cost of deployment complexity; most startups overshoot and pay the tax without the benefit.

## Key Tradeoffs (Ranked by Actual Impact)

### 1. **Organizational Maturity as the Gate**
**The decisive factor, not team size or domain complexity.**

| Monolith | Microservices |
|----------|---------------|
| Runs on simple infrastructure; one deploy pipeline | Requires robust CI/CD, monitoring, orchestration (Kubernetes or equivalent) |
| Operational cost: low (grows linearly with team size) | Operational cost: high fixed overhead (~2–3 engineers per 10–20 services for platform) |
| Scales to 50+ engineers if discipline enforced | Scales efficiently to 100+ engineers; enables independent teams |

**Gate criterion:** Can your organization confidently operate and debug production systems across 20+ running services? No? Start monolithic.

---

### 2. **Development Velocity vs. Long-term Scalability**
**The time-to-value tradeoff.**

| Phase | Monolith | Microservices |
|-------|----------|---------------|
| **0–2 years** | 3–5x faster; minimal setup overhead | 50–100% slower due to distributed system tax; infrastructure investment burns runway |
| **2–5 years** | Velocity declines (merge conflicts, deployment risk, bottlenecks) | Pays off as teams work independently; deployment remains fast |
| **5+ years** | Often unmaintainable; refactoring risky; hard to scale components | Enables parallel velocity; remains deployable |

**Decision rule:** If you may not survive 5 years, monolith. If survival is not the bottleneck, and you have >20 independent engineers, microservices unlocks velocity later.

---

### 3. **Granular Scaling vs. Operational Simplicity**
**Applies when one component has wildly different load than others.**

Monolith scales everything equally; if recommendations service is the bottleneck, you scale the entire app (database, auth, inventory along with it). Microservices scale only what needs it.

**Reality check:** Most bottlenecks (database, search index) require optimization regardless of architecture. Granular scaling is valuable when: payment processing needs 10x capacity of admin panel, *and* that difference is predictable and persistent. Few applications actually need this.

---

### 4. **Data Consistency vs. Operational Simplicity**

Monolith: ACID transactions, strong consistency, simple semantics.  
Microservices: Eventual consistency, sagas, compensating transactions.

**When it matters:**
- *Low impact:* Recommendations, reviews, search (users tolerate staleness)
- *High impact:* Payments, inventory (sagas are error-prone and slow)
- **Hybrid works:** Core transactional data (strong consistency) + auxiliary services (eventual)—as Airbnb does

---

## When to Pick Which

### **Start Monolithic If:**
1. You are <2 years old or exploring the problem space  
2. Your team has <15 engineers  
3. You cannot confidently run 20+ production services  
4. Latency-sensitive (in-process calls beat network RPC)  
5. You lack DevOps/platform engineering expertise  

**Example:** Early-stage SaaS, startup MVP, internal tools.

---

### **Use Microservices If:**
1. You have >20 engineers in *independent squads* (not just headcount)  
2. You have operational maturity: strong CI/CD, monitoring, incident response  
3. You can identify clear, stable business boundaries (payments, recommendations, identity)  
4. You need independent deployment cycles (different teams move at different speeds)  
5. High availability matters more than simplicity (fault isolation is critical)  

**Example:** Mature scale-ups (Uber, Netflix post-2010), fintech (Monzo), high-reliability platforms.

---

### **Use Modular Monolith If:**
1. A monolith is growing but full microservices feels premature  
2. You want to enforce clear module boundaries *before* extracting services  
3. You have strong enough code discipline to prevent tight coupling over time  

**Benefit:** Preparation for extraction (clear boundaries) without current operational tax.

---

## The Actual Decision Tree

1. **Can you operate Kubernetes-scale infrastructure reliably?**  
   NO → Monolith.  
   YES → Next question.

2. **Can you identify clear, stable service boundaries today?**  
   NO → Monolith (or modular monolith); extract once boundaries emerge through experience.  
   YES → Next question.

3. **Do you have >20 engineers structured in independent teams?**  
   NO → Monolith.  
   YES → Next question.

4. **Do you have wildly different scaling profiles across components?**  
   NO → Monolith handles uniform load fine.  
   YES → Microservices unlocks granular scaling.

---

## What the Research Hides

- **Quantitative costs are absent.** How much slower is development with distributed tracing overhead? The research never says.
- **Failure cases vanish.** "Most microservices projects fail" is cited nowhere. No case studies of regret exist in the research.
- **Monzo breaks the rules.** 1,500+ microservices for ~500 engineers suggests operational maturity matters more than team size—but why Monzo works and others fail is unexplained.
- **The middle tier is invisible.** Guidance works for 10-person startups and 5,000-person tech giants. What about the 50–500 person organization with a half-million–line monolith? The research is weak here.

---

## Bottom Line (Restated)

**Monolith-first is almost always the right move.** Microservices is not a scaling panacea; it's a *specific tool* for organizations large enough to sustain the operational overhead and with team structures that can exploit independent deployment. The universal pattern (monolith → microservices) suggests this tradeoff is rarely reversed—once paid, microservices costs are rarely unwound. Choose based on organizational readiness, not ambition.