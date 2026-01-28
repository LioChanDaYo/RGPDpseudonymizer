# Audit Logging

## Overview

The GDPR Pseudonymizer includes comprehensive audit logging to track all pseudonymization operations. This audit trail is essential for GDPR Article 30 compliance (Records of Processing Activities) and enables troubleshooting, performance analysis, and accountability.

**Key Features:**
- Automatic logging of all operations (process, batch, validate, etc.)
- Query operations with flexible filters (type, success status, date range)
- Export audit logs to JSON or CSV for compliance reporting
- Performance analytics (average processing time, failure rates, entity counts)
- No sensitive data stored in audit logs (metadata only)

---

## Operations Table Schema

The `operations` table stores audit trail records with the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | TEXT (UUID) | Yes | Unique operation identifier (auto-generated) |
| `timestamp` | TIMESTAMP | Yes | Operation timestamp in UTC (auto-generated if not provided) |
| `operation_type` | TEXT | Yes | Type of operation: `PROCESS`, `BATCH`, `VALIDATE`, `IMPORT`, `EXPORT`, `DESTROY` |
| `files_processed` | JSON (list[str]) | Yes | List of file paths processed in this operation |
| `model_name` | TEXT | Yes | NLP model used (e.g., `spacy`, `stanza`) |
| `model_version` | TEXT | Yes | NLP model version (e.g., `fr_core_news_lg-3.8.0`) |
| `theme_selected` | TEXT | Yes | Pseudonym theme used (`neutral`, `star_wars`, `lotr`) |
| `user_modifications` | JSON (dict) | No | User corrections in validation mode (Epic 3 feature, optional) |
| `entity_count` | INTEGER | Yes | Number of entities detected/processed |
| `processing_time_seconds` | FLOAT | Yes | Total processing time in seconds |
| `success` | BOOLEAN | Yes | Operation success status (`True` = success, `False` = failed) |
| `error_message` | TEXT | No | Error message if operation failed (optional) |

**Indexes:**
- `idx_operations_timestamp` - Fast date range queries
- `idx_operations_type` - Fast operation type filtering

**Important:** The operations table does NOT contain sensitive entity data (no names, addresses, etc.). It contains only metadata about processing operations. Sensitive data is stored encrypted in the `entities` table.

---

## AuditRepository Usage

### Initialization

```python
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository

# Open database connection
with open_database("path/to/database.db", passphrase) as db_session:
    repo = AuditRepository(db_session.session)
    # Use repository methods...
```

### Logging Operations

```python
from gdpr_pseudonymizer.data.models import Operation

# Create operation record
operation = Operation(
    operation_type="PROCESS",
    files_processed=["document.md"],
    model_name="spacy",
    model_version="fr_core_news_lg-3.8.0",
    theme_selected="star_wars",
    entity_count=10,
    processing_time_seconds=5.2,
    success=True
)

# Log to audit trail
logged_operation = repo.log_operation(operation)
print(f"Operation logged with ID: {logged_operation.id}")
```

**Note:** ID and timestamp are auto-generated if not provided.

### Querying Operations

#### Get All Operations

```python
# Retrieve all operations (newest first)
all_operations = repo.find_operations()

for op in all_operations:
    print(f"{op.timestamp}: {op.operation_type} - {op.entity_count} entities")
```

#### Filter by Operation Type

```python
# Get only BATCH operations
batch_operations = repo.find_operations(operation_type="BATCH")

for op in batch_operations:
    print(f"Batch job: {len(op.files_processed)} files, {op.entity_count} entities")
```

#### Filter by Success Status

```python
# Find all failed operations in last 7 days
from datetime import datetime, timedelta

start_date = datetime.utcnow() - timedelta(days=7)
failed_ops = repo.find_operations(
    success=False,
    start_date=start_date
)

for op in failed_ops:
    print(f"Failed: {op.operation_type} - Error: {op.error_message}")
```

#### Filter by Date Range

```python
# Get operations from specific date range
from datetime import datetime

start = datetime(2026, 1, 1)
end = datetime(2026, 1, 31)

january_ops = repo.find_operations(
    start_date=start,
    end_date=end
)

print(f"Operations in January: {len(january_ops)}")
```

#### Limit Results

```python
# Get 10 most recent operations
recent_ops = repo.find_operations(limit=10)
```

#### Combine Filters

```python
# Get recent successful PROCESS operations
ops = repo.find_operations(
    operation_type="PROCESS",
    success=True,
    start_date=datetime.utcnow() - timedelta(days=7),
    limit=20
)
```

### Retrieve Specific Operation

```python
# Get operation by ID
operation_id = "abc-123-def-456"
operation = repo.get_operation_by_id(operation_id)

if operation:
    print(f"Found: {operation.operation_type}")
else:
    print("Operation not found")
```

---

## Analytics Methods

### Total Entity Count

```python
# Get total entities processed (successful operations only)
total_entities = repo.get_total_entity_count()
print(f"Total entities processed: {total_entities}")

# Get total for specific operation type
batch_entities = repo.get_total_entity_count(operation_type="BATCH")
print(f"Entities in batch operations: {batch_entities}")

# Include failed operations
all_entities = repo.get_total_entity_count(success=None)
```

### Average Processing Time

```python
# Get average processing time (successful operations only)
avg_time = repo.get_average_processing_time()
print(f"Average processing time: {avg_time:.2f} seconds")

# Get average for BATCH operations
batch_avg = repo.get_average_processing_time(operation_type="BATCH")
print(f"Average batch time: {batch_avg:.2f} seconds")
```

**Note:** Returns `0.0` if no operations found.

### Failure Rate

```python
# Get overall failure rate
failure_rate = repo.get_failure_rate()
print(f"Failure rate: {failure_rate * 100:.2f}%")

# Get failure rate for PROCESS operations
process_failure = repo.get_failure_rate(operation_type="PROCESS")
print(f"Process failure rate: {process_failure * 100:.2f}%")
```

**Note:** Returns `0.0` if no operations found. Result is decimal (0.0 to 1.0).

---

## Export Functionality

### Export to JSON

Export operations to JSON format with metadata and ISO 8601 timestamps.

```python
# Export all operations
repo.export_to_json("audit_export.json")

# Export with filters
repo.export_to_json(
    "failed_operations.json",
    success=False,
    start_date=datetime.utcnow() - timedelta(days=30)
)

# Export specific operation type
repo.export_to_json(
    "batch_operations.json",
    operation_type="BATCH",
    limit=100
)
```

**JSON Export Format:**
```json
{
  "export_metadata": {
    "schema_version": "1.0.0",
    "export_timestamp": "2026-01-28T14:30:00",
    "filters_applied": {
      "operation_type": "PROCESS",
      "success": true,
      "limit": 100
    },
    "total_results": 15
  },
  "operations": [
    {
      "id": "abc-123-def-456",
      "timestamp": "2026-01-28T14:25:30",
      "operation_type": "PROCESS",
      "files_processed": ["input.txt"],
      "model_name": "spacy",
      "model_version": "fr_core_news_lg-3.8.0",
      "theme_selected": "star_wars",
      "user_modifications": null,
      "entity_count": 10,
      "processing_time_seconds": 5.2,
      "success": true,
      "error_message": null
    }
  ]
}
```

### Export to CSV

Export operations to CSV format with flattened JSON fields.

```python
# Export all operations
repo.export_to_csv("audit_export.csv")

# Export with filters
repo.export_to_csv(
    "january_operations.csv",
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 1, 31)
)
```

**CSV Format:**
- Header row with all field names
- `files_processed`: comma-separated list (e.g., `"doc1.txt,doc2.txt"`)
- `user_modifications`: JSON string (e.g., `"{\"entity_123\": \"corrected\"}"`)
- `timestamp`: ISO 8601 format (e.g., `"2026-01-28T14:30:00"`)

**Error Handling:**
Both export methods raise `OSError` if file cannot be written (permission errors, invalid paths). Parent directories are created automatically if they don't exist.

```python
try:
    repo.export_to_json("exports/audit.json")
except OSError as e:
    print(f"Export failed: {e}")
```

---

## Common Use Cases

### Find Failed Operations in Last 7 Days

```python
from datetime import datetime, timedelta

start_date = datetime.utcnow() - timedelta(days=7)
failed_ops = repo.find_operations(
    success=False,
    start_date=start_date
)

print(f"Failed operations: {len(failed_ops)}")
for op in failed_ops:
    print(f"  - {op.timestamp}: {op.operation_type}")
    print(f"    Error: {op.error_message}")
    print(f"    Files: {', '.join(op.files_processed)}")
```

### Get Operations by Type (PROCESS vs BATCH)

```python
# Compare single-document vs batch processing
process_ops = repo.find_operations(operation_type="PROCESS")
batch_ops = repo.find_operations(operation_type="BATCH")

print(f"Single documents processed: {len(process_ops)}")
print(f"Batch jobs processed: {len(batch_ops)}")
```

### Calculate Average Processing Time per Operation Type

```python
# Performance comparison
process_avg = repo.get_average_processing_time(operation_type="PROCESS")
batch_avg = repo.get_average_processing_time(operation_type="BATCH")

print(f"Average PROCESS time: {process_avg:.2f}s")
print(f"Average BATCH time: {batch_avg:.2f}s")
```

### Get Failure Rate for Troubleshooting

```python
# Overall reliability metrics
total_failure_rate = repo.get_failure_rate()
process_failure_rate = repo.get_failure_rate(operation_type="PROCESS")
batch_failure_rate = repo.get_failure_rate(operation_type="BATCH")

print(f"Overall failure rate: {total_failure_rate * 100:.2f}%")
print(f"PROCESS failure rate: {process_failure_rate * 100:.2f}%")
print(f"BATCH failure rate: {batch_failure_rate * 100:.2f}%")
```

### Export Monthly Report for Compliance

```python
from datetime import datetime

# Export January 2026 operations for GDPR audit
start = datetime(2026, 1, 1)
end = datetime(2026, 1, 31, 23, 59, 59)

repo.export_to_json(
    "reports/gdpr_audit_2026_01.json",
    start_date=start,
    end_date=end
)

# Also export CSV for spreadsheet analysis
repo.export_to_csv(
    "reports/gdpr_audit_2026_01.csv",
    start_date=start,
    end_date=end
)

print("Monthly report generated for compliance officer")
```

---

## Integration Points

The `AuditRepository.log_operation()` method should be called by workflow components after each operation completes. Integration will be implemented in Story 2.6 (Single-Document Workflow).

**When to Log Operations:**

1. **Single-Document Processing (PROCESS):**
   - After `DocumentProcessor.process()` completes (success or failure)
   - Capture: file path, entity count, processing time, error message (if failed)

2. **Batch Processing (BATCH):**
   - After `BatchProcessor.process_batch()` completes
   - Capture: list of file paths, total entity count, total processing time

3. **Validation Mode (VALIDATE):**
   - After user validation session completes (Epic 3 feature)
   - Capture: user modifications in `user_modifications` field

4. **Table Destruction (DESTROY):**
   - After `destroy-table` command executes (FR17)
   - Capture: records deleted count as entity_count

**Required Fields for Integration:**
- `operation_type`: Operation type constant
- `files_processed`: List of file paths (use absolute paths)
- `model_name`: NLP detector name (from config)
- `model_version`: NLP model version (from NLP library)
- `theme_selected`: Pseudonym theme (from config)
- `entity_count`: Count from entity detector output
- `processing_time_seconds`: Measured with timer (start/end timestamps)
- `success`: Boolean based on exception handling
- `error_message`: Exception message if caught (optional)

**Example Integration Pattern (Story 2.6):**

```python
import time
from datetime import datetime

def process_document(file_path: str, config: Config) -> ProcessingResult:
    """Process document with audit logging."""
    start_time = time.time()

    try:
        # Process document
        result = document_processor.process(file_path)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log successful operation
        repo.log_operation(Operation(
            operation_type="PROCESS",
            files_processed=[file_path],
            model_name=config.nlp_model,
            model_version=detector.get_version(),
            theme_selected=config.theme,
            entity_count=len(result.entities),
            processing_time_seconds=processing_time,
            success=True
        ))

        return result

    except Exception as e:
        # Calculate processing time
        processing_time = time.time() - start_time

        # Log failed operation
        repo.log_operation(Operation(
            operation_type="PROCESS",
            files_processed=[file_path],
            model_name=config.nlp_model,
            model_version=detector.get_version(),
            theme_selected=config.theme,
            entity_count=0,
            processing_time_seconds=processing_time,
            success=False,
            error_message=str(e)
        ))

        raise
```

---

## GDPR Article 30 Compliance

### Overview

GDPR Article 30 requires organizations to maintain **Records of Processing Activities**. The operations table audit logs directly support this requirement by tracking when, how, and why personal data was processed.

**Relevant GDPR Articles:**
- **Article 30:** Records of Processing Activities
- **Article 32:** Security of Processing (audit logs demonstrate technical measures)
- **Article 5(2):** Accountability Principle (audit logs prove compliance)

### Article 30 Requirements Mapping

| Article 30 Requirement | Operations Table Field | Notes |
|------------------------|------------------------|-------|
| **Name and contact details of controller** | N/A | Must be maintained externally by user (not stored in tool) |
| **Purposes of processing** | `operation_type` | Values: `PROCESS` (pseudonymization), `BATCH` (bulk processing), `VALIDATE` (user review), `DESTROY` (data deletion) |
| **Description of data subjects and data categories** | `entity_count`, `entities` table | Operations table tracks count; entities table tracks specific PERSON entities (names encrypted) |
| **Categories of recipients** | N/A | Not applicable - tool is local-only (NFR11), no data sharing or network transmission |
| **Transfers to third countries** | N/A | Not applicable - zero network operations (NFR11), all data stored locally in SQLite |
| **Time limits for erasure** | User-controlled via `destroy-table` command | No automatic deletion policy; user must manually destroy table when retention period ends (FR17) |
| **Technical and organizational security measures** | References to encryption (Story 2.4) | Audit logs demonstrate: (1) Encrypted entity storage, (2) Passphrase-protected database, (3) Audit trail for accountability |

### GDPR Rights Supported by Audit Logs

#### Right to Access (Article 15)
Audit logs show when a data subject's personal data was pseudonymized. Compliance officers can:
```python
# Find all operations on specific date
operations = repo.find_operations(
    start_date=datetime(2026, 1, 15),
    end_date=datetime(2026, 1, 15, 23, 59, 59)
)
```

#### Right to Erasure (Article 17)
The `destroy-table` command (FR17) destroys all pseudonymization mappings. This operation is logged:
```python
repo.log_operation(Operation(
    operation_type="DESTROY",
    files_processed=[],  # N/A for destroy operation
    entity_count=deleted_count,
    success=True
))
```

#### Data Breach Notification (Article 33)
Failed operations are logged with error messages, enabling breach detection:
```python
# Check for security-related failures
failed_ops = repo.find_operations(success=False)
for op in failed_ops:
    if "permission" in op.error_message.lower():
        # Potential security issue
        alert_security_team(op)
```

#### Accountability (Article 5.2)
Comprehensive audit trail demonstrates compliance with GDPR principles:
- **Lawfulness:** Operations logged with purpose (operation_type)
- **Transparency:** Export functionality provides reports for data subjects
- **Purpose limitation:** Only pseudonymization operations logged
- **Data minimization:** Only metadata logged (no sensitive data in operations table)
- **Accuracy:** User modifications tracked (validation mode, Epic 3)
- **Storage limitation:** Processing timestamps enable retention policy enforcement
- **Integrity and confidentiality:** Audit logs track security measures (encryption)

### Exporting Audit Logs for GDPR Audits

#### JSON Export for Detailed Analysis

```python
from datetime import datetime

# Export all operations from 2026 for annual audit
repo.export_to_json(
    "gdpr_audit_2026.json",
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 12, 31, 23, 59, 59)
)
```

Provide to auditors with explanation:
- **Purpose:** Demonstrate compliance with Article 30 (Records of Processing)
- **Contents:** Processing timestamps, operation types, file counts, success rates
- **Sensitive Data:** NO sensitive personal data included (metadata only)

#### CSV Export for Spreadsheet Analysis

```python
# Export for compliance officer review
repo.export_to_csv(
    "gdpr_article30_report.csv",
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 12, 31, 23, 59, 59)
)
```

Compliance officers can:
- Filter by operation type (e.g., show only DESTROY operations)
- Calculate retention statistics (time between processing and destruction)
- Identify processing patterns (peak usage times, batch vs single-document ratios)

### Sample Audit Log Export Report Format

**GDPR Article 30 Processing Activities Report**

```
Organization: [User Organization Name]
Report Period: January 1, 2026 - December 31, 2026
Generated: 2027-01-15
Tool: GDPR Pseudonymizer v1.0

Processing Activities Summary:
- Total Operations: 1,245
- Successful Operations: 1,198 (96.2%)
- Failed Operations: 47 (3.8%)
- Total Entities Processed: 15,678
- Operation Types:
  - PROCESS (single documents): 987
  - BATCH (bulk processing): 245
  - VALIDATE (user review): 10
  - DESTROY (data deletion): 3

Average Processing Time: 5.2 seconds per document

Failure Analysis:
- NLP model errors: 25 (53.2% of failures)
- File I/O errors: 15 (31.9% of failures)
- Configuration errors: 7 (14.9% of failures)

Data Retention Compliance:
- All entities destroyed via destroy-table command after processing completion
- Audit logs retained for [User Policy] years for compliance demonstration

Technical Security Measures (Article 32):
- Entity data encrypted at rest (AES-128 via Fernet)
- Passphrase-protected database (PBKDF2 key derivation, 100,000 iterations)
- Zero network transmission (NFR11 - local-only tool)
- Comprehensive audit trail maintained

For detailed operation-level data, see attached export: gdpr_audit_2026.csv
```

### Limitations and External Documentation Required

**What Audit Logs DO NOT Cover:**
1. **Controller/Processor Identity:** User must maintain organization name, contact details externally
2. **Legal Basis for Processing:** User must document lawful basis (consent, contract, legitimate interest, etc.)
3. **Data Subject Categories:** Audit logs track entity count, not specific categories (employees, customers, etc.)
4. **Retention Policy:** User must define and enforce retention periods (tool does not auto-delete)
5. **Data Subject Rights Procedures:** User must document processes for handling access/erasure requests

**Recommended External Documentation:**
- Data Protection Impact Assessment (DPIA) for pseudonymization tool usage
- Processing activity register (combines audit logs with legal basis, controller info)
- Data retention policy document (defines when to run `destroy-table` command)
- Security policy document (references encryption, passphrase management, access controls)

**Example Article 30 Record Entry:**

```
Processing Activity: Pseudonymization of Research Data
Controller: [Organization Name]
Contact: [DPO Email]
Purposes: Anonymization of personal data for research analysis (GDPR Article 6(1)(f) - Legitimate Interest)
Data Subjects: Research participants
Data Categories: Person names (pseudonymized using GDPR Pseudonymizer tool)
Recipients: Research team (internal only)
Third Country Transfers: None
Retention Period: Pseudonymization mappings destroyed immediately after processing; audit logs retained 5 years
Technical Measures: See audit logs exported from GDPR Pseudonymizer (file: gdpr_audit_2026.json)
```

---

## Performance Considerations

- **Query Performance:** Indexes on `timestamp` and `operation_type` enable fast filtering
- **Export Performance:** Large datasets (>10,000 operations) may take several seconds to export
- **Storage:** Operations table grows linearly with usage; typical operation record ≈ 500 bytes
- **Cleanup:** No automatic log rotation; users can manually query and delete old operations if needed

**Estimated Storage:**
- 1,000 operations ≈ 500 KB
- 10,000 operations ≈ 5 MB
- 100,000 operations ≈ 50 MB

**Cleanup Example (Manual):**
```python
# Delete operations older than 1 year (user must implement if needed)
from sqlalchemy import delete

cutoff_date = datetime.utcnow() - timedelta(days=365)
db_session.execute(
    delete(Operation).where(Operation.timestamp < cutoff_date)
)
db_session.commit()
```

---

## References

- **Story 2.4:** Encrypted Mapping Table (implemented AuditRepository core functionality)
- **Story 2.5:** Audit Logging (implemented export functionality, comprehensive tests, this documentation)
- **Story 2.6:** Single-Document Workflow (will integrate audit logging into processing workflow)
- **FR12:** Audit logging requirement specification (docs/prd/requirements.md)
- **GDPR Article 30:** Records of processing activities (EUR-Lex link)
- **Database Schema:** [docs/architecture/9-database-schema.md](9-database-schema.md)
- **Data Models:** [docs/architecture/4-data-models.md](4-data-models.md)
