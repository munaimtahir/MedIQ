"""CSV parser for import engine."""

import csv
import io
from typing import Iterator

from app.models.import_schema import ImportSchema


class CSVParseError(Exception):
    """CSV parsing error."""

    pass


class CSVParser:
    """Parse CSV files according to schema configuration."""

    def __init__(self, schema: ImportSchema):
        """
        Initialize CSV parser.

        Args:
            schema: Import schema with parsing configuration
        """
        self.schema = schema
        self.delimiter = schema.delimiter
        self.quote_char = schema.quote_char
        self.has_header = schema.has_header
        self.encoding = schema.encoding

    def parse(self, file_content: bytes) -> Iterator[tuple[int, dict[str, str]]]:
        """
        Parse CSV file content.

        Args:
            file_content: Raw file bytes

        Yields:
            Tuple of (row_number, row_dict)

        Raises:
            CSVParseError: If file cannot be parsed
        """
        try:
            # Decode content
            text_content = file_content.decode(self.encoding)
        except UnicodeDecodeError as e:
            raise CSVParseError(f"Failed to decode file with encoding {self.encoding}: {e}")

        try:
            # Create CSV reader
            reader = csv.DictReader(
                io.StringIO(text_content),
                delimiter=self.delimiter,
                quotechar=self.quote_char,
            )

            # If no header, we need to handle differently
            if not self.has_header:
                raise CSVParseError("CSV without header row is not yet supported")

            # Yield rows
            for row_number, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                # Filter out None keys (from extra delimiters)
                cleaned_row = {k: v for k, v in row.items() if k is not None}
                yield row_number, cleaned_row

        except csv.Error as e:
            raise CSVParseError(f"CSV parsing error: {e}")
        except Exception as e:
            raise CSVParseError(f"Unexpected error parsing CSV: {e}")
