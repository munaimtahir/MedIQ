"""Warehouse export module for Snowflake data pipeline.

This module provides:
- Export row contracts (stable Pydantic schemas)
- Mapping functions (Postgres → Export Rows)
- Export run tracking (via warehouse_export_run table)

Note: Snowflake loading is NOT implemented here - this is contract definition only.
"""

from app.warehouse.contracts import (
    AttemptExportRow,
    EventExportRow,
    ExportEnvelope,
    MasterySnapshotExportRow,
    RevisionQueueDailyExportRow,
)
from app.warehouse.mappers import (
    map_attempts,
    map_events,
    map_mastery_snapshots,
    map_revision_queue_daily,
)

__all__ = [
    "AttemptExportRow",
    "EventExportRow",
    "ExportEnvelope",
    "MasterySnapshotExportRow",
    "RevisionQueueDailyExportRow",
    "map_attempts",
    "map_events",
    "map_mastery_snapshots",
    "map_revision_queue_daily",
]

# Audit event types for warehouse operations (use with AuditLog.action):
# - "warehouse.mode_switch"
# - "warehouse.export_run_start"
# - "warehouse.export_run_finish"
# - "warehouse.export_blocked"
# - "warehouse.transform_run" (reserved for future)

# Runtime config extension (add to AlgoRuntimeConfig.config_json):
# {
#   "warehouse_mode": "disabled" | "shadow" | "active",
#   "warehouse_freeze": false
# }
