# 18. Monitoring and Observability

**Context:** Local CLI tool, not a cloud service. Monitoring = **user-visible metrics and logs**.

### 18.1 Monitoring Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Application Logs** | structlog (JSON format) | Error tracking |
| **Audit Logs** | SQLite (operations table) | GDPR compliance |
| **Performance Metrics** | Audit logs | NFR validation |
| **User-Visible Stats** | `gdpr-pseudo stats` command | Self-service monitoring |

**No External Monitoring:** No telemetry or external services (NFR11)

---

### 18.2 Key Metrics

```bash
$ gdpr-pseudo stats

Performance Statistics:
  Average time (single doc):  12.3 seconds (NFR1: <30s ✓)
  Average time (batch):       18.5 minutes (NFR2: <30min ✓)
  Total documents:            127
  Total entities:             1,842

Library Usage:
  Theme: neutral
  Exhaustion: 3.7% (LOW ✓)
```

---
