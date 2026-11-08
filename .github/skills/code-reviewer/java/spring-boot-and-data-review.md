# Spring Boot & Data Access Review Guide

Audit guide for Spring Boot 3+, Spring Data JPA, Hibernate, and Transaction management.

---

## 1. Spring Data JPA & Hibernate N+1 Prevention

- [ ] **Lazy Loading & N+1 Cascades**:
  - Are `@ManyToOne` or `@OneToMany` relationships accessed in loops without join fetch?
  - **Resolution**: Use `@EntityGraph(attributePaths = {"..."})` or explicit JPQL `JOIN FETCH` queries.
- [ ] **Default Fetch Types**:
  - Are `@OneToMany` associations set to `FetchType.LAZY`? (EAGER fetching on collections causes cartesian explosions).
  - Are `@ManyToOne` associations explicitly configured with `FetchType.LAZY`? (Hibernate defaults to EAGER for `@ManyToOne`).
- [ ] **DTO Projections**:
  - For read-only operations, are JPA entities avoided in favor of interface or record projections (`record UserSummary(...)`)?

---

## 2. Transaction Management (`@Transactional`)

- [ ] **Self-Invocation Trap**:
  - Is a `@Transactional` method called from within the same class (`this.method()`)?
  - In Spring proxy-based AOP, internal self-invocation bypasses the transaction interceptor completely! Flag as `[P0 - Blocker]`.
- [ ] **Visibility**:
  - Are `@Transactional` methods strictly `public`?
- [ ] **Read-Only Optimization**:
  - Are queries marked with `@Transactional(readOnly = true)` to disable Hibernate dirty checking and optimize DB snapshot memory?
- [ ] **Rollback Exceptions**:
  - Does `@Transactional` declare `rollbackFor = Exception.class` if checked exceptions must trigger rollback? (Spring only rolls back on `RuntimeException` by default).

---

## 3. Spring Boot Architecture & Dependency Injection

- [ ] **Constructor Injection**:
  - Is constructor injection used with `final` fields rather than `@Autowired` field injection?
- [ ] **Configuration Properties**:
  - Are properties validated using `@ConfigurationProperties` and Jakarta Validation annotations rather than loose `@Value` strings?
- [ ] **Validation Layer**:
  - Are controller requests validated using `@Valid` with Jakarta annotations (`@NotNull`, `@Size`, `@Email`)?

