"""Mock blueprint configuration contracts and validation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CoverageItemCounts(BaseModel):
    """Coverage item with count (for counts mode)."""

    theme_id: str = Field(..., description="Theme ID")
    count: int = Field(..., ge=0, description="Number of questions from this theme")


class CoverageItemWeights(BaseModel):
    """Coverage item with weight (for weights mode)."""

    theme_id: str = Field(..., description="Theme ID")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight for this theme (0.0-1.0)")


class CoverageConfig(BaseModel):
    """Coverage configuration."""

    mode: Literal["counts", "weights"] = Field(..., description="Coverage mode")
    items: list[CoverageItemCounts | CoverageItemWeights] = Field(..., min_length=1, description="Coverage items")

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list, info) -> list:
        """Validate items match mode."""
        if not v:
            raise ValueError("coverage.items cannot be empty")
        mode = info.data.get("mode")
        if mode == "counts":
            if not all(isinstance(item, CoverageItemCounts) for item in v):
                raise ValueError("coverage.items must be CoverageItemCounts when mode=counts")
        elif mode == "weights":
            if not all(isinstance(item, CoverageItemWeights) for item in v):
                raise ValueError("coverage.items must be CoverageItemWeights when mode=weights")
        return v


class DifficultyMix(BaseModel):
    """Difficulty distribution mix."""

    easy: float = Field(..., ge=0.0, le=1.0, description="Proportion of easy questions")
    medium: float = Field(..., ge=0.0, le=1.0, description="Proportion of medium questions")
    hard: float = Field(..., ge=0.0, le=1.0, description="Proportion of hard questions")

    @model_validator(mode="after")
    def validate_sum(self) -> "DifficultyMix":
        """Validate difficulty mix sums to 1.0."""
        total = self.easy + self.medium + self.hard
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"difficulty_mix must sum to 1.0, got {total}")
        return self


class CognitiveMix(BaseModel):
    """Cognitive level distribution mix."""

    C1: float = Field(..., ge=0.0, le=1.0, description="Proportion of C1 questions")
    C2: float = Field(..., ge=0.0, le=1.0, description="Proportion of C2 questions")
    C3: float = Field(..., ge=0.0, le=1.0, description="Proportion of C3 questions")

    @model_validator(mode="after")
    def validate_sum(self) -> "CognitiveMix":
        """Validate cognitive mix sums to 1.0."""
        total = self.C1 + self.C2 + self.C3
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"cognitive_mix must sum to 1.0, got {total}")
        return self


class TagConstraints(BaseModel):
    """Tag-based inclusion/exclusion constraints."""

    must_include: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Must include items (theme_ids, concept_ids, tags)",
    )
    must_exclude: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Must exclude items (question_ids, tags)",
    )


class SourceConstraints(BaseModel):
    """Source-based constraints."""

    allow_sources: list[str] = Field(default_factory=list, description="Allowed source books")
    deny_sources: list[str] = Field(default_factory=list, description="Denied source books")


class AntiRepeatPolicy(BaseModel):
    """Anti-repeat policy for question selection."""

    avoid_days: int = Field(default=30, ge=0, description="Avoid questions used in last N days")
    avoid_last_n: int = Field(default=0, ge=0, description="Avoid last N used questions for cohort")


class SelectionPolicy(BaseModel):
    """Question selection policy."""

    type: Literal["random_weighted"] = Field(default="random_weighted", description="Selection type")
    notes: str | None = Field(default=None, description="Optional notes")


class MockBlueprintConfig(BaseModel):
    """Mock blueprint configuration schema (STRICT)."""

    coverage: CoverageConfig = Field(..., description="Theme coverage configuration")
    difficulty_mix: DifficultyMix = Field(..., description="Difficulty distribution")
    cognitive_mix: CognitiveMix = Field(..., description="Cognitive level distribution")
    tag_constraints: TagConstraints = Field(default_factory=TagConstraints, description="Tag constraints")
    source_constraints: SourceConstraints = Field(default_factory=SourceConstraints, description="Source constraints")
    anti_repeat_policy: AntiRepeatPolicy = Field(default_factory=AntiRepeatPolicy, description="Anti-repeat policy")
    selection_policy: SelectionPolicy = Field(default_factory=SelectionPolicy, description="Selection policy")

    @model_validator(mode="after")
    def validate_coverage_counts(self) -> "MockBlueprintConfig":
        """Validate coverage counts sum to total_questions if mode=counts."""
        if self.coverage.mode == "counts":
            # Note: total_questions is not in config, it's in blueprint
            # This validation will be done at blueprint creation/update time
            pass
        elif self.coverage.mode == "weights":
            # Validate weights sum to approximately 1.0
            total_weight = sum(item.weight for item in self.coverage.items if isinstance(item, CoverageItemWeights))
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f"coverage.items weights must sum to 1.0, got {total_weight}")
        return self

    def validate_against_total_questions(self, total_questions: int) -> list[str]:
        """
        Validate config against total_questions and return warnings.

        Returns:
            List of warning messages (empty if no warnings)
        """
        warnings: list[str] = []

        if total_questions > 300:
            warnings.append(f"total_questions ({total_questions}) exceeds hard cap of 300")

        if self.coverage.mode == "counts":
            total_count = sum(item.count for item in self.coverage.items if isinstance(item, CoverageItemCounts))
            if total_count < total_questions:
                warnings.append(f"coverage.items counts sum ({total_count}) < total_questions ({total_questions}), will underfill")
            elif total_count > total_questions:
                warnings.append(f"coverage.items counts sum ({total_count}) > total_questions ({total_questions}), will overfill")

        return warnings
