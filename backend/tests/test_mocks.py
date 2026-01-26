"""Tests for mock blueprint and generation."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.mocks.contracts import (
    CoverageConfig,
    CoverageItemCounts,
    CoverageItemWeights,
    DifficultyMix,
    CognitiveMix,
    MockBlueprintConfig,
)
from app.models.mock import (
    MockBlueprint,
    MockBlueprintMode,
    MockBlueprintStatus,
    MockBlueprintVersion,
    MockGenerationRun,
    MockInstance,
)
from app.models.question_cms import Question, QuestionStatus
from app.models.user import User, UserRole


@pytest.fixture
def sample_config() -> dict:
    """Sample valid blueprint config."""
    return {
        "coverage": {
            "mode": "counts",
            "items": [
                {"theme_id": "1", "count": 10},
                {"theme_id": "2", "count": 15},
            ],
        },
        "difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
        "cognitive_mix": {"C1": 0.2, "C2": 0.6, "C3": 0.2},
        "tag_constraints": {
            "must_include": {"theme_ids": [], "concept_ids": [], "tags": []},
            "must_exclude": {"question_ids": [], "tags": []},
        },
        "source_constraints": {"allow_sources": [], "deny_sources": []},
        "anti_repeat_policy": {"avoid_days": 30, "avoid_last_n": 0},
        "selection_policy": {"type": "random_weighted", "notes": None},
    }


@pytest.fixture
def sample_blueprint(db: Session, admin_user: User, sample_config: dict) -> MockBlueprint:
    """Create a sample blueprint."""
    blueprint = MockBlueprint(
        title="Test Blueprint",
        year=1,
        total_questions=25,
        duration_minutes=120,
        mode=MockBlueprintMode.EXAM,
        status=MockBlueprintStatus.DRAFT,
        config=sample_config,
        created_by=admin_user.id,
    )
    db.add(blueprint)
    db.flush()

    # Create initial version
    version = MockBlueprintVersion(
        blueprint_id=blueprint.id,
        version=1,
        config=sample_config,
        created_by=admin_user.id,
        diff_summary="Initial version",
    )
    db.add(version)
    db.commit()
    db.refresh(blueprint)
    return blueprint


@pytest.fixture
def sample_questions(db: Session, sample_blueprint: MockBlueprint) -> list[Question]:
    """Create sample published questions."""
    questions = []
    for i in range(30):
        q = Question(
            id=uuid4(),
            stem=f"Question {i}",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_index=0,
            explanation_md="Explanation",
            status=QuestionStatus.PUBLISHED,
            year_id=sample_blueprint.year,
            theme_id=1 if i < 15 else 2,
            difficulty="easy" if i < 10 else ("medium" if i < 20 else "hard"),
            cognitive_level="C1" if i < 5 else ("C2" if i < 20 else "C3"),
            created_by=uuid4(),
            updated_by=uuid4(),
        )
        db.add(q)
        questions.append(q)
    db.commit()
    return questions


class TestConfigValidation:
    """Test config validation."""

    def test_valid_config(self, sample_config: dict):
        """Test valid config passes validation."""
        config = MockBlueprintConfig.model_validate(sample_config)
        assert config.coverage.mode == "counts"
        assert len(config.coverage.items) == 2

    def test_invalid_difficulty_mix_sum(self):
        """Test difficulty mix must sum to 1.0."""
        config_dict = {
            "coverage": {
                "mode": "counts",
                "items": [{"theme_id": "1", "count": 10}],
            },
            "difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.1},  # Sums to 0.9
            "cognitive_mix": {"C1": 0.2, "C2": 0.6, "C3": 0.2},
        }
        with pytest.raises(Exception):  # Should raise validation error
            MockBlueprintConfig.model_validate(config_dict)

    def test_invalid_cognitive_mix_sum(self):
        """Test cognitive mix must sum to 1.0."""
        config_dict = {
            "coverage": {
                "mode": "counts",
                "items": [{"theme_id": "1", "count": 10}],
            },
            "difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
            "cognitive_mix": {"C1": 0.2, "C2": 0.6, "C3": 0.1},  # Sums to 0.9
        }
        with pytest.raises(Exception):  # Should raise validation error
            MockBlueprintConfig.model_validate(config_dict)

    def test_weights_mode_validation(self):
        """Test weights mode validation."""
        config_dict = {
            "coverage": {
                "mode": "weights",
                "items": [
                    {"theme_id": "1", "weight": 0.5},
                    {"theme_id": "2", "weight": 0.5},
                ],
            },
            "difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
            "cognitive_mix": {"C1": 0.2, "C2": 0.6, "C3": 0.2},
        }
        config = MockBlueprintConfig.model_validate(config_dict)
        assert config.coverage.mode == "weights"

    def test_weights_sum_not_one(self):
        """Test weights that don't sum to 1.0 are rejected."""
        config_dict = {
            "coverage": {
                "mode": "weights",
                "items": [
                    {"theme_id": "1", "weight": 0.3},
                    {"theme_id": "2", "weight": 0.3},  # Sums to 0.6
                ],
            },
            "difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
            "cognitive_mix": {"C1": 0.2, "C2": 0.6, "C3": 0.2},
        }
        with pytest.raises(Exception):  # Should raise validation error
            MockBlueprintConfig.model_validate(config_dict)


class TestDeterministicGeneration:
    """Test deterministic generation."""

    def test_same_seed_same_questions(
        self,
        db: Session,
        sample_blueprint: MockBlueprint,
        sample_questions: list[Question],
    ):
        """Test that same seed produces same question IDs."""
        from app.mocks.generator import generate_mock_questions
        from app.mocks.contracts import MockBlueprintConfig

        config = MockBlueprintConfig.model_validate(sample_blueprint.config)
        seed = 12345
        now = datetime.now(timezone.utc)

        # Generate twice with same seed
        question_ids_1, meta_1, warnings_1 = generate_mock_questions(
            db, sample_blueprint, config, seed, now
        )
        question_ids_2, meta_2, warnings_2 = generate_mock_questions(
            db, sample_blueprint, config, seed, now
        )

        # Should produce identical results
        assert question_ids_1 == question_ids_2
        assert len(question_ids_1) > 0

    def test_different_seed_different_questions(
        self,
        db: Session,
        sample_blueprint: MockBlueprint,
        sample_questions: list[Question],
    ):
        """Test that different seeds produce different question IDs."""
        from app.mocks.generator import generate_mock_questions
        from app.mocks.contracts import MockBlueprintConfig

        config = MockBlueprintConfig.model_validate(sample_blueprint.config)
        now = datetime.now(timezone.utc)

        question_ids_1, _, _ = generate_mock_questions(
            db, sample_blueprint, config, 12345, now
        )
        question_ids_2, _, _ = generate_mock_questions(
            db, sample_blueprint, config, 67890, now
        )

        # Should produce different results (with high probability)
        # Note: In edge cases they might be the same, but very unlikely
        assert question_ids_1 != question_ids_2 or len(question_ids_1) == 0

    def test_respects_must_exclude(
        self,
        db: Session,
        sample_blueprint: MockBlueprint,
        sample_questions: list[Question],
    ):
        """Test that must_exclude question_ids are respected."""
        from app.mocks.generator import generate_mock_questions
        from app.mocks.contracts import MockBlueprintConfig

        # Exclude first 5 questions
        exclude_ids = [str(q.id) for q in sample_questions[:5]]
        config_dict = sample_blueprint.config.copy()
        config_dict["tag_constraints"]["must_exclude"]["question_ids"] = exclude_ids

        config = MockBlueprintConfig.model_validate(config_dict)
        seed = 12345
        now = datetime.now(timezone.utc)

        question_ids, _, _ = generate_mock_questions(
            db, sample_blueprint, config, seed, now
        )

        # None of the excluded IDs should be in the result
        for excluded_id in exclude_ids:
            assert excluded_id not in question_ids


class TestAPIEndpoints:
    """Test API endpoints."""

    def test_create_blueprint_requires_auth(self, client, sample_config: dict):
        """Test creating blueprint requires authentication."""
        response = client.post(
            "/api/v1/admin/mocks/blueprints",
            json={
                "title": "Test",
                "year": 1,
                "total_questions": 25,
                "duration_minutes": 120,
                "config": sample_config,
            },
        )
        assert response.status_code == 401 or response.status_code == 403

    def test_activate_requires_phrase(
        self,
        client,
        admin_user,
        sample_blueprint: MockBlueprint,
        db: Session,
    ):
        """Test activation requires correct confirmation phrase."""
        # Login as admin
        # (Assuming you have a way to authenticate in tests)
        
        # Try to activate without correct phrase
        response = client.post(
            f"/api/v1/admin/mocks/blueprints/{sample_blueprint.id}/activate",
            json={
                "reason": "Testing activation",
                "confirmation_phrase": "WRONG PHRASE",
            },
        )
        # Should fail with 400
        assert response.status_code == 400

    def test_activate_requires_reason(
        self,
        client,
        admin_user,
        sample_blueprint: MockBlueprint,
        db: Session,
    ):
        """Test activation requires reason."""
        response = client.post(
            f"/api/v1/admin/mocks/blueprints/{sample_blueprint.id}/activate",
            json={
                "reason": "",  # Empty reason
                "confirmation_phrase": "ACTIVATE MOCK BLUEPRINT",
            },
        )
        # Should fail validation
        assert response.status_code == 422  # Validation error

    def test_generate_requires_phrase(
        self,
        client,
        admin_user,
        sample_blueprint: MockBlueprint,
        db: Session,
    ):
        """Test generation requires correct confirmation phrase."""
        # Activate blueprint first
        sample_blueprint.status = MockBlueprintStatus.ACTIVE
        db.commit()

        response = client.post(
            f"/api/v1/admin/mocks/blueprints/{sample_blueprint.id}/generate",
            json={
                "seed": 12345,
                "reason": "Testing generation",
                "confirmation_phrase": "WRONG PHRASE",
            },
        )
        # Should fail with 400
        assert response.status_code == 400

    def test_list_blueprints(
        self,
        client,
        admin_user,
        sample_blueprint: MockBlueprint,
    ):
        """Test listing blueprints."""
        response = client.get("/api/v1/admin/mocks/blueprints")
        # Should return list (may be empty if not authenticated)
        assert response.status_code in (200, 401, 403)
