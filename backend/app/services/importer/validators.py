"""Validators for import engine."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.import_schema import ImportSchema
from app.models.syllabus import Block, Theme, Year


class ValidationError:
    """Validation error for a specific field."""

    def __init__(self, code: str, message: str, field: str | None = None):
        """
        Initialize validation error.

        Args:
            code: Error code (stable identifier)
            message: Human-readable message
            field: Field name that failed validation
        """
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON storage."""
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


class QuestionValidator:
    """Validate mapped question data before insertion."""

    # Error codes (stable)
    MISSING_REQUIRED = "MISSING_REQUIRED"
    INVALID_YEAR = "INVALID_YEAR"
    INVALID_BLOCK = "INVALID_BLOCK"
    THEME_NOT_FOUND = "THEME_NOT_FOUND"
    INVALID_OPTIONS = "INVALID_OPTIONS"
    INVALID_CORRECT = "INVALID_CORRECT"
    INVALID_SOURCE_PAGE = "INVALID_SOURCE_PAGE"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    def __init__(self, schema: ImportSchema, db: Session):
        """
        Initialize validator.

        Args:
            schema: Import schema with validation rules
            db: Database session for tag resolution
        """
        self.schema = schema
        self.db = db
        self.rules = schema.rules_json
        self.required_fields = self.rules.get("required", [])

    def validate(self, canonical_data: dict[str, Any]) -> list[ValidationError]:
        """
        Validate canonical question data.

        Args:
            canonical_data: Mapped question data

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[ValidationError] = []

        # Check required fields
        for field in self.required_fields:
            if field == "correct":
                # Special handling for correct (it's mapped to correct_index)
                if "correct" not in canonical_data or canonical_data["correct"] is None:
                    errors.append(
                        ValidationError(
                            self.MISSING_REQUIRED,
                            f"Required field 'correct' is missing",
                            "correct",
                        )
                    )
            elif field not in canonical_data or not canonical_data.get(field):
                errors.append(
                    ValidationError(
                        self.MISSING_REQUIRED,
                        f"Required field '{field}' is missing or empty",
                        field,
                    )
                )

        # Validate year
        year_value = canonical_data.get("year")
        if year_value is not None:
            if not isinstance(year_value, int) or year_value not in [1, 2]:
                errors.append(
                    ValidationError(
                        self.INVALID_YEAR,
                        f"Invalid year '{year_value}', must be 1 or 2",
                        "year",
                    )
                )

        # Validate block
        block_code = canonical_data.get("block")
        if block_code is not None:
            if not isinstance(block_code, str) or block_code.upper() not in [
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
            ]:
                errors.append(
                    ValidationError(
                        self.INVALID_BLOCK,
                        f"Invalid block '{block_code}', must be A-F",
                        "block",
                    )
                )

        # Validate theme resolution (requires year + block)
        if year_value and block_code and not errors:
            theme_name = canonical_data.get("theme")
            if theme_name:
                resolved = self._resolve_theme(year_value, block_code, theme_name)
                if not resolved:
                    errors.append(
                        ValidationError(
                            self.THEME_NOT_FOUND,
                            f"Theme '{theme_name}' not found for Year {year_value} Block {block_code}",
                            "theme",
                        )
                    )
                else:
                    # Store resolved IDs
                    canonical_data["year_id"] = resolved["year_id"]
                    canonical_data["block_id"] = resolved["block_id"]
                    canonical_data["theme_id"] = resolved["theme_id"]

        # Validate options
        options = [
            canonical_data.get("option_a"),
            canonical_data.get("option_b"),
            canonical_data.get("option_c"),
            canonical_data.get("option_d"),
            canonical_data.get("option_e"),
        ]
        if any(opt is None or not str(opt).strip() for opt in options):
            errors.append(
                ValidationError(
                    self.INVALID_OPTIONS,
                    "All 5 options (option_a through option_e) must be non-empty",
                    "options",
                )
            )

        # Validate correct answer
        correct_index = canonical_data.get("correct")
        if correct_index is not None:
            if not isinstance(correct_index, int) or correct_index not in [0, 1, 2, 3, 4]:
                errors.append(
                    ValidationError(
                        self.INVALID_CORRECT,
                        f"Invalid correct answer '{correct_index}', must be 0-4 (or A-E in CSV)",
                        "correct",
                    )
                )

        # Validate source_page if present
        source_page = canonical_data.get("source_page")
        if source_page is not None and not isinstance(source_page, int):
            errors.append(
                ValidationError(
                    self.INVALID_SOURCE_PAGE,
                    f"Invalid source_page '{source_page}', must be an integer",
                    "source_page",
                )
            )

        return errors

    def _resolve_theme(
        self, year_value: int, block_code: str, theme_name: str
    ) -> dict[str, int] | None:
        """
        Resolve theme name to year_id, block_id, theme_id.

        Args:
            year_value: Year (1 or 2)
            block_code: Block code (A-F)
            theme_name: Theme name

        Returns:
            Dict with year_id, block_id, theme_id or None if not found
        """
        try:
            # Find year
            year = self.db.query(Year).filter(Year.name == f"Year {year_value}").first()
            if not year:
                return None

            # Find block
            block = (
                self.db.query(Block)
                .filter(Block.year_id == year.id, Block.code == block_code.upper())
                .first()
            )
            if not block:
                return None

            # Find theme by name (case-insensitive)
            theme = (
                self.db.query(Theme)
                .filter(
                    Theme.block_id == block.id,
                    Theme.title.ilike(theme_name.strip()),
                )
                .first()
            )
            if not theme:
                return None

            return {
                "year_id": year.id,
                "block_id": block.id,
                "theme_id": theme.id,
            }

        except Exception as e:
            print(f"Error resolving theme: {e}")
            return None
