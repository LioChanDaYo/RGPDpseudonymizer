"""Unit tests for SQLAlchemy data models."""

from __future__ import annotations

from datetime import datetime

from gdpr_pseudonymizer.data.models import Base, Entity, Metadata, Operation


def test_entity_model_creation() -> None:
    """Test Entity model creation with valid data."""
    entity = Entity(
        entity_type="PERSON",
        full_name="Marie Dubois",
        pseudonym_full="Aurora Nightshade",
        theme="neutral",
    )

    assert entity.entity_type == "PERSON"
    assert entity.full_name == "Marie Dubois"
    assert entity.pseudonym_full == "Aurora Nightshade"
    assert entity.theme == "neutral"
    assert entity.is_ambiguous is False
    assert entity.first_seen_timestamp is not None


def test_entity_model_with_split_names() -> None:
    """Test Entity model with first and last name components."""
    entity = Entity(
        entity_type="PERSON",
        first_name="Marie",
        last_name="Dubois",
        full_name="Marie Dubois",
        pseudonym_first="Aurora",
        pseudonym_last="Nightshade",
        pseudonym_full="Aurora Nightshade",
        theme="star_wars",
        gender="female",
    )

    assert entity.first_name == "Marie"
    assert entity.last_name == "Dubois"
    assert entity.pseudonym_first == "Aurora"
    assert entity.pseudonym_last == "Nightshade"
    assert entity.gender == "female"


def test_entity_model_optional_fields() -> None:
    """Test Entity model with optional fields set to None."""
    entity = Entity(
        entity_type="LOCATION",
        full_name="Paris",
        pseudonym_full="Coruscant",
        theme="star_wars",
    )

    assert entity.entity_type == "LOCATION"
    assert entity.first_name is None
    assert entity.last_name is None
    assert entity.gender is None
    assert entity.confidence_score is None


def test_entity_model_with_confidence_score() -> None:
    """Test Entity model with confidence score."""
    entity = Entity(
        entity_type="PERSON",
        full_name="Jean Martin",
        pseudonym_full="Luke Skywalker",
        theme="star_wars",
        confidence_score=0.92,
    )

    assert entity.confidence_score == 0.92


def test_entity_model_ambiguous_flag() -> None:
    """Test Entity model with ambiguous flag and reason."""
    entity = Entity(
        entity_type="PERSON",
        full_name="Martin",
        pseudonym_full="Skywalker",
        theme="neutral",
        is_ambiguous=True,
        ambiguity_reason="Could be first or last name",
    )

    assert entity.is_ambiguous is True
    assert entity.ambiguity_reason == "Could be first or last name"


def test_entity_model_timestamp_auto_generation() -> None:
    """Test that first_seen_timestamp is automatically generated."""
    before = datetime.utcnow()
    entity = Entity(
        entity_type="PERSON",
        full_name="Test Name",
        pseudonym_full="Test Pseudonym",
        theme="neutral",
    )
    after = datetime.utcnow()

    assert entity.first_seen_timestamp is not None
    assert before <= entity.first_seen_timestamp <= after


def test_operation_model_creation() -> None:
    """Test Operation model creation with valid data."""
    operation = Operation(
        operation_type="PROCESS",
        files_processed=["document1.txt", "document2.md"],
        model_name="fr_core_news_lg",
        model_version="3.8.0",
        theme_selected="neutral",
        entity_count=15,
        processing_time_seconds=2.5,
        success=True,
    )

    assert operation.operation_type == "PROCESS"
    assert operation.files_processed == ["document1.txt", "document2.md"]
    assert operation.model_name == "fr_core_news_lg"
    assert operation.model_version == "3.8.0"
    assert operation.theme_selected == "neutral"
    assert operation.entity_count == 15
    assert operation.processing_time_seconds == 2.5
    assert operation.success is True
    assert operation.timestamp is not None


def test_operation_model_with_error() -> None:
    """Test Operation model with error message."""
    operation = Operation(
        operation_type="BATCH",
        files_processed=["file1.txt"],
        model_name="fr_core_news_lg",
        model_version="3.8.0",
        theme_selected="star_wars",
        entity_count=0,
        processing_time_seconds=0.1,
        success=False,
        error_message="Model not found",
    )

    assert operation.success is False
    assert operation.error_message == "Model not found"


def test_operation_model_with_user_modifications() -> None:
    """Test Operation model with user modifications JSON field."""
    modifications = {
        "entity_1": {"action": "confirmed"},
        "entity_2": {"action": "modified", "new_text": "Corrected Name"},
        "entity_3": {"action": "rejected"},
    }

    operation = Operation(
        operation_type="VALIDATE",
        files_processed=["document.txt"],
        user_modifications=modifications,
        model_name="fr_core_news_lg",
        model_version="3.8.0",
        theme_selected="neutral",
        entity_count=3,
        processing_time_seconds=45.2,
        success=True,
    )

    assert operation.user_modifications == modifications
    assert operation.user_modifications["entity_2"]["new_text"] == "Corrected Name"


def test_operation_model_timestamp_auto_generation() -> None:
    """Test that timestamp is automatically generated."""
    before = datetime.utcnow()
    operation = Operation(
        operation_type="PROCESS",
        files_processed=["test.txt"],
        model_name="fr_core_news_lg",
        model_version="3.8.0",
        theme_selected="neutral",
        entity_count=1,
        processing_time_seconds=1.0,
        success=True,
    )
    after = datetime.utcnow()

    assert operation.timestamp is not None
    assert before <= operation.timestamp <= after


def test_metadata_model_creation() -> None:
    """Test Metadata model creation with valid data."""
    metadata = Metadata(key="passphrase_canary", value="encrypted_verification_string")

    assert metadata.key == "passphrase_canary"
    assert metadata.value == "encrypted_verification_string"
    assert metadata.updated_at is not None


def test_metadata_model_json_value() -> None:
    """Test Metadata model with JSON-serialized value."""
    import json

    config_data = {"iterations": 100000, "algorithm": "PBKDF2"}
    metadata = Metadata(key="kdf_config", value=json.dumps(config_data))

    assert metadata.key == "kdf_config"
    # Verify value can be deserialized
    assert json.loads(metadata.value) == config_data


def test_metadata_model_schema_version() -> None:
    """Test Metadata model for storing schema version."""
    metadata = Metadata(key="schema_version", value="1.0")

    assert metadata.key == "schema_version"
    assert metadata.value == "1.0"


def test_metadata_model_file_hash() -> None:
    """Test Metadata model for storing file hash."""
    metadata = Metadata(
        key="file:/path/to/document.txt:hash",
        value="sha256:abc123def456...",
    )

    assert metadata.key == "file:/path/to/document.txt:hash"
    assert metadata.value.startswith("sha256:")


def test_metadata_model_timestamp_auto_generation() -> None:
    """Test that updated_at is automatically generated."""
    before = datetime.utcnow()
    metadata = Metadata(key="test_key", value="test_value")
    after = datetime.utcnow()

    assert metadata.updated_at is not None
    assert before <= metadata.updated_at <= after


def test_base_declarative_base() -> None:
    """Test that all models inherit from Base."""
    assert issubclass(Entity, Base)
    assert issubclass(Operation, Base)
    assert issubclass(Metadata, Base)


def test_entity_table_name() -> None:
    """Test Entity model table name."""
    assert Entity.__tablename__ == "entities"


def test_operation_table_name() -> None:
    """Test Operation model table name."""
    assert Operation.__tablename__ == "operations"


def test_metadata_table_name() -> None:
    """Test Metadata model table name."""
    assert Metadata.__tablename__ == "metadata"
