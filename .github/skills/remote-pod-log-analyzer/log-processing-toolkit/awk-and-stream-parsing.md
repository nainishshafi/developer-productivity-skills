# Stream Parsing & Statistical Analysis with Awk

Staff-level guide to extracting fields, aggregating error distributions, and computing latency percentiles with `awk`.

---

## 1. Essential `awk` Field Extraction

`awk` splits lines into whitespace-delimited fields: `$1, $2, \dots, $NF` (last field).

```bash
# Print timestamp ($1), log level ($2), and message ($4 to end of line)
awk '{
    printf "%-25s %-7s ", $1, $2;
    for (i=4; i<=NF; i++) printf "%s ", $i;
    print "";
}' /var/log/app.log | head -n 20

# Filter lines where HTTP status code ($9) >= 500
awk '$9 >= 500 { print $1, $7, $9, $NF }' /var/log/nginx/access.log | head -n 50
```

---

## 2. HTTP Status & Error Code Aggregation

Analyze error distributions in real time:

```bash
# Count requests grouped by HTTP status code
awk '{ print $9 }' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Top 10 client IP addresses generating 4xx/5xx errors
awk '$9 >= 400 { print $1 }' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -n 10

# Top 10 slowest API endpoints (assuming response time is in field $NF in seconds)
awk '$NF > 1.0 { print $7 }' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -n 10
```

---

## 3. Computing Response Time Percentiles (P50, P95, P99)

Given a column of response durations (e.g. column 10 in milliseconds):

```bash
awk '{ print $10 }' /var/log/nginx/access.log | sort -n | awk '
BEGIN { count = 0 }
{
    values[count++] = $1;
    sum += $1;
}
END {
    if (count == 0) { print "No records found"; exit }
    p50_idx = int(count * 0.50);
    p95_idx = int(count * 0.95);
    p99_idx = int(count * 0.99);
    printf "Count: %d | Avg: %.2f ms | P50: %.2f ms | P95: %.2f ms | P99: %.2f ms | Max: %.2f ms\n",
           count, (sum/count), values[p50_idx], values[p95_idx], values[p99_idx], values[count-1];
}'
```

---

## 4. Multiline Stack Trace Consolidation

Application stack traces span multiple lines (starting with a timestamp line, followed by `\tat com.example...` lines).

```bash
# Group multi-line Java / Python stack traces into single-line records for grep/sort
awk '
/^[0-9]{4}-[0-9]{2}-[0-9]{2}/ {
    if (line != "") print line;
    line = $0;
    next;
}
{
    line = line " -> " $0;
}
END {
    if (line != "") print line;
}' /var/log/app.log | grep 'Exception' | head -n 20
```

