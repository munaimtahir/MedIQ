"""Row mapper for import engine."""

from typing import Any

from app.models.import_schema import ImportSchema


class RowMapper:
    """Map CSV rows to canonical question fields according to schema."""

    def __init__(self, schema: ImportSchema):
        """
        Initialize row mapper.

        Args:
            schema: Import schema with mapping configuration
        """
        self.schema = schema
        self.mapping = schema.mapping_json
        self.rules = schema.rules_json

    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        """
        Map a CSV row to canonical question fields.

        Args:
            row: Raw CSV row (column_name -> value)

        Returns:
            Canonical question dict with mapped fields
        """
        canonical = {}

        for canonical_field, config in self.mapping.items():
            column_name = config.get("column")
            if not column_name:
                continue

            # Get raw value from row
            raw_value = row.get(column_name, "").strip()

            # Apply transformations if any
            mapped_value = self._transform_value(canonical_field, raw_value, config)

            # Store if not empty (unless it's external_id which can be empty)
            if mapped_value or canonical_field == "external_id":
                canonical[canonical_field] = mapped_value

        return canonical

    def _transform_value(self, field: str, value: str, config: dict) -> Any:
        """
        Transform a field value according to config.

        Args:
            field: Canonical field name
            value: Raw string value
            config: Field configuration from mapping

        Returns:
            Transformed value
        """
        if not value:
            return None

        # Handle correct answer format (letter -> index)
        if field == "correct" and config.get("format") == "letter":
            # Convert A-E to 0-4
            letter = value.upper()
            if letter in ["A", "B", "C", "D", "E"]:
                return ord(letter) - ord("A")  # A=0, B=1, etc.
            return value  # Return as-is for validation to catch

        # Handle integer fields
        if field in ["year", "source_page"]:
            try:
                return int(value)
            except (ValueError, TypeError):
                return value  # Return as-is for validation to catch

        # Default: return string value
        return value
