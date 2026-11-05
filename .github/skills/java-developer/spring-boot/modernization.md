# Modernization & Migration: Legacy JSP / Webflow to Spring Boot 3

A practical guide for refactoring legacy server-rendered Spring applications into stateless RESTful microservices and navigating Spring Boot 3 internals.

---

## 1. Migration Strategy: The Strangler Fig Pattern

Never attempt a "big bang" rewrite. Incrementally carve out bounded contexts using an API gateway or reverse proxy (Envoy, Nginx, Spring Cloud Gateway):

```text
Client Requests
      │
      ▼
[ API Gateway / Proxy ]
      ├── /api/v2/orders/*   ──► [ New Spring Boot 3 Microservice ] (Stateless REST)
      └── /* (all legacy)    ──► [ Legacy Monolith (JSP / Webflow) ] (Stateful)
```

1. **Identify Bounded Contexts**: Carve out domain boundaries by business capability (e.g., Billing, Inventory).
2. **Decouple Data Ownership First**: Isolate database tables; stop direct cross-domain table joins using APIs or event messaging.
3. **Route Traffic Incrementally**: Divert endpoints one by one. Once all routes are migrated, decommission the legacy monolith.

---

## 2. Refactoring Legacy JSP to Headless REST APIs

Legacy JSP controllers couple presentation, session state, and business logic into `ModelAndView` and server-rendered tags.

### Anti-Pattern: Stateful Form Controller (JSP)
```java
// Legacy Spring MVC (JSP)
@Controller
public class LegacyUserController {
    @RequestMapping(value = "/user.do", method = RequestMethod.POST)
    public ModelAndView submitForm(@ModelAttribute("user") UserForm form, HttpSession session) {
        session.setAttribute("currentUser", form);
        return new ModelAndView("userSummary", "data", form);
    }
}
```

### Modern Target: Stateless REST Controller (Spring Boot 3)
```java
// Spring Boot 3 RESTful Endpoint
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @PostMapping
    public ResponseEntity<UserResponse> createUser(@Valid @RequestBody CreateUserRequest request) {
        var user = userService.createUser(request.toCommand());
        return ResponseEntity.created(URI.create("/api/v1/users/" + user.id())).body(user);
    }
}
```

### Key Refactoring Directives
- **Replace `ModelAndView` with Records**: Return immutable DTO records serialized via Jackson.
- **Eliminate `HttpSession` Dependency**:
  - Replace server-side session attributes with client-managed tokens (JWT/OAuth2) or external distributed session caches (Spring Session + Redis) during transition.
- **Drop JSTL / Taglibs**: Move conditional UI rendering and loops to modern frontend frameworks (React, Angular, Vue) consuming pure JSON.

---

## 3. Refactoring Spring Webflow (SWF) to RESTful Workflows

Spring Webflow stores multi-step conversational state (`flow.xml`, `view-state`, `flowScope`, `conversationScope`) in memory across wizard screens.

### How to Decompose a Webflow Wizard
1. **Model the Workflow Resource**: Turn conversational state into an aggregate document in the database (e.g., `RegistrationDraft` or `Application`).
2. **Replace States with REST Resources**:
   - `view-state` / `action-state` $\rightarrow$ Step-based `PATCH` or `PUT` endpoints:
     - `POST /api/v1/applications` $\rightarrow$ initializes draft, returns `draftId`.
     - `PUT /api/v1/applications/{id}/personal-details` $\rightarrow$ completes Step 1.
     - `PUT /api/v1/applications/{id}/payment` $\rightarrow$ completes Step 2.
     - `POST /api/v1/applications/{id}/submit` $\rightarrow$ terminal transition.
3. **Replace `flowScope` / `transition` Logic**:
   - Model valid transitions using Java `sealed` interfaces or an explicit state machine:
     ```java
     public sealed interface ApplicationState permits Draft, Submitted, Approved, Rejected {}
     ```
   - For long-running, multi-day orchestrations, prefer workflow engines (Temporal, Camunda) over server-bound session flows.

---

## 4. Spring Boot 3 Internals & Migration Essentials

Spring Boot 3.x is built on **Spring Framework 6** and requires **Java 17 minimum**.

### 1. The `javax.*` $\rightarrow$ `jakarta.*` Namespace Shift
All Java EE specifications moved to Eclipse Jakarta EE 10:
| Old (`javax.*`) | New (`jakarta.*`) | Purpose |
| :--- | :--- | :--- |
| `javax.servlet.*` | `jakarta.servlet.*` | Web filters, servlets |
| `javax.persistence.*` | `jakarta.persistence.*` | JPA annotations (`@Entity`, `@Table`) |
| `javax.validation.*` | `jakarta.validation.*` | Bean validation (`@NotNull`, `@Valid`) |
| `javax.annotation.*` | `jakarta.annotation.*` | `@PostConstruct`, `@PreDestroy` |

*Trap*: Never leave mixed `javax` and `jakarta` dependencies on the classpath; annotations from `javax` are silently ignored by Spring Boot 3.

### 2. Spring Security 6 Architectural Changes
`WebSecurityConfigurerAdapter` is completely removed in favor of component-based filter chains:
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**", "/actuator/health").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .build();
    }
}
```
*Note*: `antMatchers()` and `authorizeRequests()` are removed. Use `requestMatchers()` and `authorizeHttpRequests()`.

### 3. Modern Synchronous HTTP: `RestClient`
Replace legacy `RestTemplate` with the fluent, synchronous `RestClient` (Spring Boot 3.2+):
```java
@Bean
public RestClient paymentRestClient(RestClient.Builder builder) {
    return builder
        .baseUrl("https://api.payment-gateway.com")
        .requestFactory(new JdkClientHttpRequestFactory())
        .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
        .build();
}
```

### 4. Ahead-of-Time (AOT) & GraalVM Native Image
Spring Boot 3 analyzes the application context at build time (`spring-boot:process-aot`), generating code to avoid runtime reflection and CGLIB proxies.
- **Benefit**: Sub-100ms startup times and tiny container memory footprints.
- **Migration Caution**: Dynamic reflection, classpath scanning, and unconfigured dynamic proxies require explicit reachability metadata (`@RegisterReflectionForBinding` or `reflect-config.json`).

### 5. RFC 7807 Standardized Errors
Use built-in `ProblemDetail` instead of custom error DTOs:
```java
@ExceptionHandler(OrderNotFoundException.class)
public ProblemDetail handleNotFound(OrderNotFoundException ex) {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
    problem.setTitle("Order Not Found");
    problem.setProperty("timestamp", Instant.now());
    return problem;
}
```

### 6. Breaking Behavior Changes in Spring Boot 3 / Hibernate 6
- **Trailing Slash Matching Removed**: `/api/users/` no longer matches `@GetMapping("/api/users")` by default in Spring 6. Fix client URLs rather than re-enabling deprecated matching.
- **Hibernate 6 Sequence Defaults**: `@GeneratedValue(strategy = AUTO)` now creates per-entity sequences (`<entity>_seq` with `allocationSize = 50`) instead of a single global `hibernate_sequence`. Explicitly specify `@SequenceGenerator` when migrating existing schemas.
- **Observability Migration**: Spring Cloud Sleuth is replaced by **Micrometer Tracing** (`micrometer-tracing-bridge-otel` or `micrometer-tracing-bridge-brave`).

---

## 5. Step-by-Step Modernization Checklist

- [ ] **Upgrade JDK to 17/21+**: Verify project compiles and tests pass on the target LTS JVM.
- [ ] **Run OpenRewrite**: Use automated recipes (`org.openrewrite.recipe:rewrite-spring:upgradeSpringBoot_3_2`) to bulk-migrate `javax` to `jakarta` imports and deprecated properties.
- [ ] **Remove Deprecated Starters**: Strip out `spring-boot-starter-tomcat` overrides, legacy XML application contexts (`applicationContext.xml`), and JSP view resolvers.
- [ ] **Convert Webflow Flows to REST Resources**: Audit all `flow.xml` definitions, document wizard steps as stateful domain entities, and expose REST endpoints.
- [ ] **Externalize Session State**: Replace in-memory session dependencies with stateless tokens or distributed caches before decomposing into microservices.
- [ ] **Enable Virtual Threads (Java 21+)**: Add `spring.threads.virtual.enabled=true` for high-throughput I/O pipelines.

