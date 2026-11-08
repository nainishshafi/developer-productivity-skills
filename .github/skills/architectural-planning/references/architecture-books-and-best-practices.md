# Software Architecture Best Practices & Foundational Literature

A curated compendium of seminal architectural literature, decision frameworks, and best-practice books that inform the heuristics, trade-off matrices, and patterns in the `architectural-planning` skill.

---

## 1. Data Systems & Distributed Architecture

### *Designing Data-Intensive Applications (DDIA)* — Martin Kleppmann (O'Reilly, 2017)
* **Core Philosophy**: There is no one-size-fits-all database; modern architectures are composite data systems integrating specialized stores (OLTP, search index, cache, analytical warehouse, event log).
* **Key Heuristics Applied in This Skill**:
  - **Storage Engine Selection**: Understand B-Trees (optimized for read-heavy transactional workloads like PostgreSQL/MySQL) vs. LSM-Trees (optimized for write-heavy workloads like Cassandra/RocksDB).
  - **Single-Leader vs. Multi-Leader vs. Leaderless**: Choose replication topologies based on network partition tolerance and cross-region write latency.
  - **Unbundled Databases & Stream Processing**: Treat the log (Kafka/Redpanda) as the single source of truth, deriving caches and search indexes as secondary materialized views.
  - **CAP & PACELC Theorems**: In the presence of network partitions ($P$), choose between Availability ($A$) and Consistency ($C$); else, choose between Latency ($L$) and Consistency ($C$).

### *Designing Distributed Systems* — Brendan Burns (O'Reilly, 2018)
* **Core Philosophy**: Distributed system design patterns replicate the reusable object-oriented design patterns of the 1990s at the container and pod scale.
* **Key Heuristics Applied in This Skill**:
  - **Single-Node Patterns**: Sidecar (logging/metrics proxy), Ambassador (routing to external services), and Adapter (standardizing monitoring interfaces).
  - **Serving Patterns**: Replicated load-balanced services, sharded caching layers, and scatter/gather query fan-out.
  - **Batch Computation**: Work queue workers and event-driven pipelined task distribution.

### *System Design Interview (Vols 1 & 2)* — Alex Xu & Sahn Lam (ByteByteGo, 2020–2022)
* **Core Philosophy**: Pragmatic, high-level capacity estimation, component layout, and back-of-the-envelope calculations for large-scale consumer and enterprise systems.
* **Key Heuristics Applied in This Skill**:
  - Capacity estimation: QPS, read-to-write ratios, bandwidth requirements, and 5-year storage growth calculations.
  - Standard reference topologies for rate limiters, distributed unique ID generators (Snowflake), notification services, and web crawlers.

---

## 2. Architecture Principles & Trade-off Arbitration

### *Fundamentals of Software Architecture* — Mark Richards & Neal Ford (O'Reilly, 2020)
* **Core Philosophy**: *"Everything in software architecture is a trade-off. If an architect thinks they came up with something that doesn't have trade-offs, they haven't identified them yet."*
* **Key Heuristics Applied in This Skill**:
  - **The First Law of Software Architecture**: Always articulate the disadvantages and costs of a chosen pattern alongside its advantages.
  - **Architectural Characteristics (the "-ilities")**: Explicitly rank operational traits (scalability, availability, elasticity), structural traits (maintainability, modularity, testability), and cross-cutting traits (security, compliance).
  - **Component Cohesion & Coupling**: Calculate afferent ($C_a$) and efferent ($C_e$) coupling to ensure modules do not form hidden cyclical dependencies.

### *Software Architecture: The Hard Parts* — Neal Ford, Mark Richards, Pramod Sadalage, Zhamak Dehghani (O'Reilly, 2021)
* **Core Philosophy**: Modern distributed architecture is dominated by difficult decisions: data decomposition, transactional sagas, distributed workflow orchestration, and contract management.
* **Key Heuristics Applied in This Skill**:
  - **Data Decomposition Dilemmas**: Slicing the database is 10x harder than slicing the code. Decompose data along transactional and bounded-context lines.
  - **Saga Orchestration vs. Choreography**: Prefer centralized orchestration (state machine / Temporal / Step Functions) for complex multi-step sagas needing auditability; prefer choreography for simple 2-step event notifications.
  - **Transactional Boundaries**: Avoid two-phase commits (2PC) across distributed networks; design for eventual consistency, compensating transactions, and idempotent consumers.

---

## 3. Microservices vs. Modular Monolith

### *Monolith to Microservices: Evolutionary Patterns to Transform Your Monolith* — Sam Newman (O'Reilly, 2019)
* **Core Philosophy**: *"If you do a big-bang rewrite, the only thing you are guaranteed is a big bang."*
* **Key Heuristics Applied in This Skill**:
  - **Modular Monolith as the Starting Point**: Build strong modular boundaries in a single deployment artifact first. If you cannot modularize a monolith, your microservices will become a distributed monolith.
  - **Strangler Fig Pattern**: Incrementally intercept and route traffic from the old monolith to new services via an API gateway, migrating one capability at a time.
  - **Database Splitting (Expand-and-Contract)**: Never split code and database simultaneously. Use view/trigger bridges and parallel writes before severing foreign key constraints.

### *Building Microservices (2nd Edition)* — Sam Newman (O'Reilly, 2021)
* **Core Philosophy**: Microservices model independently deployable units organized around business capabilities rather than technical layers.
* **Key Heuristics Applied in This Skill**:
  - **Independent Deployability**: If Service A must be deployed simultaneously with Service B, they are not microservices.
  - **BFF (Backend-for-Frontend)**: Tailor edge gateways specifically to client needs (mobile vs. desktop vs. third-party partners).
  - **Contract Testing**: Use consumer-driven contract tests (e.g., Pact) to verify cross-service compatibility in CI without spinning up the entire microservices constellation.

---

## 4. Production Resilience & Reliability

### *Release It! Design and Deploy Production-Ready Software (2nd Edition)* — Michael T. Nygard (Pragmatic Bookshelf, 2018)
* **Core Philosophy**: Software systems are complex, dynamic ecosystems where failures are inevitable; systems must be designed to survive catastrophic component failures with graceful degradation.
* **Key Heuristics Applied in This Skill**:
  - **Bulkhead Pattern**: Partition resources (thread pools, connection pools, CPU quotas) so a catastrophic failure in one domain does not exhaust resources system-wide.
  - **Circuit Breaker Pattern**: Fail fast when a remote dependency is unresponsive, giving it time to recover while serving fallbacks or cached state.
  - **Timeouts & Deadlines**: Every single network socket, RPC call, and database query must enforce an explicit timeout; unbounded waits are the #1 cause of cascading outages.
  - **Fail Fast & Handshake**: Check preconditions and authentication early; reject invalid requests before acquiring expensive database connection leases.

### *Site Reliability Engineering (SRE): How Google Runs Production Systems* — Betsy Beyer, Chris Jones, Jennifer Petoff, Niall Richard Murphy (O'Reilly, 2016)
* **Core Philosophy**: Hope is not a strategy. Reliability must be defined quantitatively using Service Level Objectives (SLOs) and Error Budgets.
* **Key Heuristics Applied in This Skill**:
  - **SLI / SLO / SLA Hierarchy**: Base architecture capacity on explicit availability targets (e.g., 99.9% uptime = 43 minutes of downtime/month).
  - **Eliminating Toil**: Automate schema migrations, environment provisioning, and deployment rollbacks.
  - **Graceful Load Shedding**: Drop non-critical background traffic during traffic spikes to protect core checkout and query operations.

### *Observability Engineering* — Charity Majors, Liz Fong-Jones, George Miranda (O'Reilly, 2022)
* **Core Philosophy**: Traditional monitoring answers *"is the system up?"*; observability answers *"why is the system broken in a way we have never seen before?"*
* **Key Heuristics Applied in This Skill**:
  - **Wide Structured Events**: Emit rich, context-dense JSON log payloads containing user IDs, tenant IDs, request IDs, and execution spans.
  - **OpenTelemetry Standard**: Decouple application tracing instrumentation from vendor collectors, allowing metrics and traces to route to Prometheus, Jaeger, Datadog, or Grafana without code rewrites.

---

## 5. Domain Modeling & Structural Boundaries

### *Domain-Driven Design: Tackling Complexity in the Heart of Software* — Eric Evans (Addison-Wesley, 2003)
* **Core Philosophy**: The structure and language of software code should match the real-world business domain.
* **Key Heuristics Applied in This Skill**:
  - **Ubiquitous Language**: Software models and database column names must strictly reflect business terminology, not technical implementation jargon.
  - **Bounded Contexts**: Draw explicit boundaries where domain terms have unambiguous meanings (e.g., `Account` in Billing vs. `Account` in Identity).
  - **Aggregate Roots**: Enforce transactional invariants within aggregate boundaries; cross-aggregate operations should rely on domain events and eventual consistency.

### *Implementing Domain-Driven Design* — Vaughn Vernon (Addison-Wesley, 2013)
* **Core Philosophy**: The practical, code-centric guide to implementing Evans' strategic and tactical DDD patterns.
* **Key Heuristics Applied in This Skill**:
  - **Hexagonal Architecture (Ports and Adapters)**: Keep domain entities completely pure and independent of frameworks, databases, and HTTP transports.
  - **Domain Events**: Publish immutable facts that have occurred in the domain to trigger side-effects asynchronously.

---

## 6. Software Simplicity & Anti-Bloat

### *Choose Boring Technology* — Dan McKinley (Etsy Tech, 2015)
* **Core Philosophy**: *"Boring technology is awesome. Boring means you know its failure modes."*
* **Key Heuristics Applied in This Skill**:
  - **Innovation Tokens**: An engineering team only has 2 to 3 "innovation tokens" to spend across an entire project. Spend them exclusively on core domain value; use battle-tested, standard technologies (PostgreSQL, Redis, Linux, HTTP/JSON) for everything else.
  - **Failure Mode Visibility**: Mature technologies have thousands of documented StackOverflow answers, runbooks, and known CVE patches; bleeding-edge tools make your production system the guinea pig.

### *A Philosophy of Software Design* — John Ousterhout (Yaknyam Press, 2018)
* **Core Philosophy**: The greatest challenge in software design is managing complexity; modules should be "deep" with simple interfaces and rich functionality.
* **Key Heuristics Applied in This Skill**:
  - **Deep Modules**: Strive for simple, small interfaces that conceal large internal implementation complexity.
  - **Shallow Module Anti-Pattern**: Avoid classes and interfaces that add layer indirection with negligible abstraction benefit (e.g., a service layer that simply forwards identical arguments to a repository).
  - **Define Errors Out of Existence**: Design APIs and data structures so edge cases are handled naturally rather than requiring defensive exceptions and fragmented handling.

---

## 7. Evolutionary Architecture & Decision Records

### *Building Evolutionary Architectures (2nd Edition)* — Neal Ford, Rebecca Parsons, Patrick Kua (O'Reilly, 2023)
* **Core Philosophy**: An evolutionary architecture supports guided, incremental change across multiple dimensions over time.
* **Key Heuristics Applied in This Skill**:
  - **Architectural Fitness Functions**: Implement automated CI tests that verify architectural constraints (e.g., ArchUnit in Java, dependency-cruiser in TS) to prevent architectural drift.
  - **Last Responsible Moment**: Defer irreversible technical choices until business requirements provide sufficient evidence.

### *Documenting Architecture Decisions* — Michael Nygard (2011)
* **Core Philosophy**: Architecture decisions must be recorded in lightweight, version-controlled markdown records alongside the source code.
* **Standard ADR Structure**:
  1. **Title**: Context and sequential number (e.g., `ADR-004: Use PostgreSQL as Primary Relational Store`).
  2. **Status**: Proposed, Accepted, Rejected, Deprecated, Superseded.
  3. **Context**: What business or technical forces prompted this decision?
  4. **Decision**: What option was chosen, and what are the detailed technical commitments?
  5. **Consequences**: What becomes easier, what becomes harder, and what trade-offs were accepted?

---

## 8. Integration: How This Literature Maps to Skill Steps

| Architectural Step | Primary Literature Reference | Key Heuristic Applied |
|---|---|---|
| **Step 1 (Scope & Scale)** | Kleppmann (*DDIA*), Alex Xu (*System Design*) | Back-of-the-envelope capacity planning & bounded context identification |
| **Step 2 (Backend)** | Dan McKinley (*Choose Boring Tech*), Ousterhout (*Philosophy of Software Design*) | Boring technology defaults & deep module abstractions |
| **Step 3 (Frontend)** | Sam Newman (*Building Microservices*) | BFF (Backend-for-Frontend) & client-tailored API contracts |
| **Step 4 (Database & ORM)** | Kleppmann (*DDIA*), Sam Newman (*Monolith to Microservices*) | Expand-and-contract migrations, ACID vs. BASE, and B-Tree vs. LSM storage |
| **Step 5 (Caching)** | Kleppmann (*DDIA*), Nygard (*Release It!*) | Cache stampede prevention, SingleFlight, multi-layer L1/L2 invalidation |
| **Step 6 (Auth & Identity)** | Neil Madden (*API Security*), Evans (*DDD*) | Zero-trust token defense, RS256 asymmetric signing, and identity boundaries |
| **Step 7 (Messaging)** | Kleppmann (*DDIA*), Hohpe & Woolf (*Enterprise Integration*) | Log-based streams vs. message brokers, idempotency, and DLQ routing |
| **Step 8 (Deployment)** | Brendan Burns (*Distributed Systems*), Beyer et al. (*Google SRE*) | Container topologies, sidecars, autoscaling, and SLA/SLO definitions |
| **Step 9 (CI/CD)** | Neal Ford et al. (*Evolutionary Architecture*) | Architectural fitness functions & automated delivery verification gates |
| **Step 10 (Observability)** | Charity Majors et al. (*Observability Engineering*) | OpenTelemetry standard, wide events, and distributed tracing |
| **Step 11 (Documentation)** | Michael Nygard (*ADRs*), Richards & Ford (*Architecture Hard Parts*) | Trade-off articulation, Mermaid diagrams, and version-controlled ADRs |

