# Spring Boot Best Practices

## 1. Dependency Injection
- **Use Constructor Injection**: Avoid `@Autowired` on private fields. Constructor injection ensures immutability, facilitates unit testing without Spring context, and prevents circular dependencies.
  ```java
  @Service
  @RequiredArgsConstructor // Or explicit constructor
  public class OrderService {
      private final OrderRepository orderRepository;
      private final PaymentClient paymentClient;
  }
  ```

## 2. Validation & Error Handling
- **Bean Validation (Jakarta)**: Use annotations (`@NotNull`, `@Size`, `@Email`) on DTO fields. Add `@Valid` to controller arguments.
- **Global Exception Handling**: Use `@RestControllerAdvice` and RFC 7807 `ProblemDetail` (Spring 6 / Boot 3+) to return consistent error payloads:
  ```java
  @RestControllerAdvice
  public class GlobalExceptionHandler {
      @ExceptionHandler(ResourceNotFoundException.class)
      public ProblemDetail handleNotFound(ResourceNotFoundException ex) {
          return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
      }
  }
  ```

## 3. Configuration Management
- Use `@ConfigurationProperties` with records or typed classes instead of scattered `@Value` annotations. Add `@Validated` to fail fast on bad config.
- Keep profiles explicit (`application-dev.yml`, `application-prod.yml`).
- Never commit secrets; inject via environment variables or a secret store.

## 4. HTTP Clients & Runtime
- Use `RestClient` (Boot 3.2+) for synchronous calls, `WebClient` only in reactive apps. Avoid `RestTemplate` in new code.
- Always configure connect/read timeouts on outbound clients.
- On Java 21+, enable virtual threads with `spring.threads.virtual.enabled=true` instead of tuning Tomcat thread pools.
- Boot 3 uses `jakarta.*` packages — never mix in `javax.persistence` / `javax.validation`.

## 5. Observability
- Include Spring Boot Actuator; expose only `health`, `info`, `metrics`/`prometheus` publicly.
- Use Micrometer for metrics and tracing; propagate a correlation/trace ID in logs.

## 6. Testing Strategy
- **Unit Tests**: Test service logic in isolation using JUnit 5 and Mockito (`@ExtendWith(MockitoExtension.class)`). Fast, no Spring context.
- **Slice Tests**: Use `@WebMvcTest` for controllers and `@DataJpaTest` for database queries. Use `@MockitoBean` (Boot 3.4+; `@MockBean` on older versions).
- **Integration Tests**: Use `@SpringBootTest` with Testcontainers (`@ServiceConnection`) against the real database engine — not H2 — sparingly for full end-to-end verification.

