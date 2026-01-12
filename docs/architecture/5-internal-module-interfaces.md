# 5. Internal Module Interfaces

Since this is a CLI application rather than a web service, this section documents the **internal Python module interfaces** that define contracts between architectural layers. These interfaces enable clean separation of concerns, dependency injection for testing, and future extensibility.

### 5.1 EntityDetector Interface (NLP Engine)

**Purpose:** Abstract NLP library implementation (spaCy/Stanza) to enable benchmarking, testing, and future library swaps.

**Location:** `gdpr_pseudonymizer/nlp/entity_detector.py`

**Interface Definition:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DetectedEntity:
    """Result of entity detection."""
    text: str                    # Original entity text (e.g., "Marie Dubois")
    entity_type: str             # PERSON, LOCATION, or ORG
    start_pos: int               # Character offset in document
    end_pos: int                 # Character offset end
    confidence: Optional[float]  # NER confidence score (0.0-1.0)
    gender: Optional[str]        # male/female/neutral/unknown (if available)

class EntityDetector(ABC):
    """Abstract interface for NLP entity detection."""

    @abstractmethod
    def load_model(self, model_name: str) -> None:
        """Load NLP model into memory."""
        pass

    @abstractmethod
    def detect_entities(self, text: str) -> List[DetectedEntity]:
        """Detect named entities in text."""
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """Get model metadata for audit logging."""
        pass

    @property
    @abstractmethod
    def supports_gender_classification(self) -> bool:
        """Whether this NLP library provides gender info."""
        pass
```

**Usage Example:**

```python
# Core orchestrator uses interface, not concrete class
detector: EntityDetector = SpaCyDetector()  # or StanzaDetector()
detector.load_model("fr_core_news_lg")

entities = detector.detect_entities("Marie Dubois habite à Paris.")
# Returns: [
#   DetectedEntity(text="Marie Dubois", entity_type="PERSON", ...),
#   DetectedEntity(text="Paris", entity_type="LOCATION", ...)
# ]
```

---

### 5.2 MappingRepository Interface (Data Layer)

**Purpose:** Abstract database operations for entity↔pseudonym mappings. Implements Repository pattern to isolate SQLite details.

**Location:** `gdpr_pseudonymizer/data/repositories/mapping_repository.py`

**Interface Definition:**

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import Entity

class MappingRepository(ABC):
    """Abstract interface for entity mapping persistence."""

    @abstractmethod
    def find_by_full_name(self, full_name: str) -> Optional[Entity]:
        """Find existing entity by full name (for idempotency)."""
        pass

    @abstractmethod
    def find_by_component(
        self,
        component: str,
        component_type: str  # "first_name" or "last_name"
    ) -> List[Entity]:
        """Find entities with matching name component (compositional logic)."""
        pass

    @abstractmethod
    def save(self, entity: Entity) -> Entity:
        """Persist new entity or update existing."""
        pass

    @abstractmethod
    def save_batch(self, entities: List[Entity]) -> List[Entity]:
        """Persist multiple entities in single transaction."""
        pass

    @abstractmethod
    def find_all(
        self,
        entity_type: Optional[str] = None,
        is_ambiguous: Optional[bool] = None
    ) -> List[Entity]:
        """Query entities with optional filters."""
        pass
```

---

### 5.3 PseudonymManager Interface

**Purpose:** Assign pseudonyms from themed libraries with compositional logic and exhaustion tracking.

**Location:** `gdpr_pseudonymizer/pseudonym/assignment_engine.py`

**Interface Definition:**

```python
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class PseudonymAssignment:
    """Result of pseudonym assignment."""
    pseudonym_full: str          # Complete pseudonym
    pseudonym_first: Optional[str]   # First name component (PERSON only)
    pseudonym_last: Optional[str]    # Last name component (PERSON only)
    theme: str                   # Library used
    exhaustion_percentage: float # Library usage (0.0-1.0)

class PseudonymManager(ABC):
    """Abstract interface for pseudonym assignment."""

    @abstractmethod
    def load_library(self, theme: str) -> None:
        """Load pseudonym library from JSON file."""
        pass

    @abstractmethod
    def assign_pseudonym(
        self,
        entity_type: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        gender: Optional[str] = None,
        existing_first: Optional[str] = None,  # For compositional matching
        existing_last: Optional[str] = None
    ) -> PseudonymAssignment:
        """Assign pseudonym using compositional logic."""
        pass

    @abstractmethod
    def check_exhaustion(self) -> float:
        """Get library exhaustion percentage."""
        pass
```

---
