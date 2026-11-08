# OLAP, Cubing & Advanced Data Analytics Guide

Architectural heuristics and production patterns for multidimensional aggregation (`CUBE`, `ROLLUP`, `GROUPING SETS`), statistical distributions, sessionization, cohort retention, and "Gaps & Islands" analysis across enterprise databases.

---

## 1. Multidimensional Aggregation: `CUBE`, `ROLLUP` & `GROUPING SETS`

Standard `GROUP BY` collapses records into a single aggregation grain. OLAP operations compute subtotals, cross-dimensional cuts, and grand totals in a single table pass without running multiple `UNION ALL` queries.

```
                    ┌─────────────────────────┐
                    │      GROUP BY CUBE      │  ──> All 2^N combinations (Full hypercube)
                    └─────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │     GROUP BY ROLLUP     │  ──> Hierarchical rollups (Day -> Month -> Year -> Total)
                    └─────────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │  GROUP BY GROUPING SETS │  ──> Explicit, targeted combinations (Prevents cube explosion)
                    └─────────────────────────┘
```

---

### A. `GROUP BY CUBE`: All $2^N$ Combinations
Computes aggregations across every possible combination of specified dimensions plus a grand total:

```sql
-- Supported in SQL Server, Oracle, and PostgreSQL:
SELECT 
    region, 
    product_category, 
    sales_channel,
    SUM(revenue) AS total_revenue,
    -- Helper function to identify subtotal vs base rows:
    GROUPING(region) AS is_region_subtotal,
    GROUPING(product_category) AS is_category_subtotal,
    GROUPING(sales_channel) AS is_channel_subtotal
FROM sales_facts
GROUP BY CUBE (region, product_category, sales_channel);
```
> [!WARNING]
> **Cartesian Cube Explosion**: A `CUBE` on $N$ columns produces $2^N$ aggregation groupings. A 6-column cube computes $2^6 = 64$ sub-aggregates; a 10-column cube produces $1,024$ groupings! For $> 4$ dimensions, always prefer `GROUPING SETS`.

---

### B. `GROUP BY ROLLUP`: Hierarchical Drill-Downs
Computes hierarchical subtotals from the most granular level up to the grand total:

```sql
SELECT 
    order_year, 
    order_quarter, 
    order_month, 
    SUM(total_amount) AS revenue,
    COUNT(order_id) AS order_count
FROM sales_summary
GROUP BY ROLLUP (order_year, order_quarter, order_month);

-- Output Hierarchy:
-- 1. (order_year, order_quarter, order_month) -> Granular monthly total
-- 2. (order_year, order_quarter)              -> Quarterly subtotal
-- 3. (order_year)                             -> Yearly subtotal
-- 4. ()                                       -> Overall Grand Total
```

---

### C. `GROUP BY GROUPING SETS`: Targeted Efficiency
Computes only the exact dimensional cuts required by downstream dashboards, avoiding unused combinations:

```sql
SELECT 
    country, 
    region, 
    department, 
    SUM(salary) AS total_payroll
FROM employees
GROUP BY GROUPING SETS (
    (country, region), -- Geographic cut
    (department),      -- Departmental cut
    ()                 -- Overall company grand total
);
```

#### Differentiating Real NULLs with `GROUPING()`
When a column contains natural `NULL` values, `GROUPING(column)` returns `1` if the `NULL` represents an aggregated subtotal row, and `0` if it is a real data value:

```sql
SELECT 
    CASE WHEN GROUPING(region) = 1 THEN 'All Regions (Total)' ELSE region END AS display_region,
    SUM(revenue) AS revenue
FROM sales
GROUP BY ROLLUP (region);
```

---

## 2. Statistical Distributions & Percentiles

Calculating P50 (median), P90, P95, and P99 latency, response times, or customer order values:

### Continuous vs. Discrete Percentiles
- **`PERCENTILE_CONT(P)`**: Interpolates a continuous value between adjacent observations.
- **`PERCENTILE_DISC(P)`**: Returns an exact discrete value that exists in the dataset.

```sql
-- PostgreSQL & Oracle:
SELECT 
    api_endpoint,
    COUNT(*) AS total_requests,
    ROUND(AVG(response_time_ms), 2) AS mean_latency,
    -- P50 (Median):
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time_ms) AS p50_latency,
    -- P90:
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY response_time_ms) AS p90_latency,
    -- P99:
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99_latency
FROM api_access_logs
WHERE request_date = CURRENT_DATE
GROUP BY api_endpoint;
```

*(In SQL Server, use `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) OVER (PARTITION BY api_endpoint)`).*

### Relative Rank & Cumulative Distribution
```sql
SELECT 
    student_name, 
    exam_score,
    -- Relative rank from 0.0 to 1.0:
    PERCENT_RANK() OVER (ORDER BY exam_score ASC) AS percent_rank,
    -- Cumulative probability P(X <= x):
    CUME_DIST() OVER (ORDER BY exam_score ASC) AS cumulative_dist
FROM student_scores;
```

---

## 3. Advanced Time-Series Analytics: Sessionization

Group high-frequency web clicks or telemetry events into user sessions demarcated by 30 minutes of inactivity:

```sql
WITH EventGaps AS (
    SELECT 
        user_id,
        event_time,
        event_name,
        -- Calculate inactivity gap between consecutive events:
        event_time - LAG(event_time) OVER (
            PARTITION BY user_id 
            ORDER BY event_time ASC
        ) AS time_since_last_event
    FROM user_events
),
SessionFlags AS (
    SELECT 
        user_id,
        event_time,
        event_name,
        -- New session if first event or gap > 30 minutes:
        CASE 
            WHEN time_since_last_event IS NULL OR time_since_last_event > INTERVAL '30 minutes' 
            THEN 1 ELSE 0 
        END AS is_new_session
    FROM EventGaps
),
SessionNumbered AS (
    SELECT 
        user_id,
        event_time,
        event_name,
        -- Cumulative sum generates unique Session IDs per user:
        SUM(is_new_session) OVER (
            PARTITION BY user_id 
            ORDER BY event_time ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_id
    FROM SessionFlags
)
SELECT 
    user_id,
    session_id,
    MIN(event_time) AS session_start,
    MAX(event_time) AS session_end,
    COUNT(*) AS total_actions
FROM SessionNumbered
GROUP BY user_id, session_id;
```

---

## 4. The "Gaps & Islands" Problem

A classic analytical challenge: identifying contiguous ranges of active dates ("islands") and identifying missing sequential IDs ("gaps").

### Finding Contiguous Active Date Ranges ("Islands")
The mathematical trick: subtracting a continuous row number from a date sequence yields a constant anchor date for contiguous dates:

```sql
WITH RankedActivity AS (
    SELECT 
        user_id,
        activity_date,
        -- (activity_date - row_number days) remains constant for contiguous streaks!
        activity_date - (ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY activity_date ASC) * INTERVAL '1 day') AS streak_group
    FROM daily_user_logins
)
SELECT 
    user_id,
    MIN(activity_date) AS streak_start,
    MAX(activity_date) AS streak_end,
    COUNT(*) AS consecutive_days_logged_in
FROM RankedActivity
GROUP BY user_id, streak_group
HAVING COUNT(*) >= 7 -- Streaks of at least 1 week
ORDER BY user_id, streak_start;
```

---

## 5. Cohort Retention & Pareto (80/20) Analytics

### User Cohort Retention Matrix
```sql
WITH UserFirstOrder AS (
    SELECT 
        customer_id, 
        DATE_TRUNC('month', MIN(order_date)) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
OrderActivity AS (
    SELECT 
        o.customer_id,
        u.cohort_month,
        DATE_TRUNC('month', o.order_date) AS activity_month,
        -- Calculate month offset (0, 1, 2, ...):
        (EXTRACT(YEAR FROM o.order_date) - EXTRACT(YEAR FROM u.cohort_month)) * 12 + 
        (EXTRACT(MONTH FROM o.order_date) - EXTRACT(MONTH FROM u.cohort_month)) AS period_offset
    FROM orders o
    INNER JOIN UserFirstOrder u ON o.customer_id = u.customer_id
)
SELECT 
    cohort_month,
    COUNT(DISTINCT CASE WHEN period_offset = 0 THEN customer_id END) AS month_0,
    COUNT(DISTINCT CASE WHEN period_offset = 1 THEN customer_id END) AS month_1,
    COUNT(DISTINCT CASE WHEN period_offset = 2 THEN customer_id END) AS month_2,
    COUNT(DISTINCT CASE WHEN period_offset = 3 THEN customer_id END) AS month_3
FROM OrderActivity
GROUP BY cohort_month
ORDER BY cohort_month ASC;
```

### Pareto 80/20 Analysis (Cumulative Revenue Share)
Find the top customers that generate 80% of company revenue:

```sql
WITH CustomerRevenue AS (
    SELECT 
        customer_id, 
        SUM(total_amount) AS revenue
    FROM orders
    GROUP BY customer_id
),
CumulativeMetrics AS (
    SELECT 
        customer_id, 
        revenue,
        -- Running sum of revenue ordered by spend:
        SUM(revenue) OVER (
            ORDER BY revenue DESC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_revenue,
        -- Total company revenue:
        SUM(revenue) OVER () AS total_company_revenue
    FROM CustomerRevenue
)
SELECT 
    customer_id, 
    revenue,
    ROUND((running_revenue / total_company_revenue) * 100, 2) AS cumulative_pct
FROM CumulativeMetrics
WHERE (running_revenue / total_company_revenue) <= 0.80
ORDER BY revenue DESC;
```
