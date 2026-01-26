"""Database models."""

# Import all models here so Alembic can detect them
from app.models.academic import (
    AcademicBlock,
    AcademicSubject,
    AcademicYear,
    UserBlock,
    UserProfile,
    UserSubject,
)
from app.models.attempt import AttemptAnswer, AttemptSession
from app.models.admin_security import AdminSecurityRuntime
from app.models.auth import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.models.system_flags import SystemFlag
from app.models.email import EmailOutbox, EmailRuntimeConfig, EmailSwitchEvent
from app.models.bkt import BKTSkillParams, BKTUserSkillState, MasterySnapshot
from app.models.bookmark import Bookmark
from app.models.csp_report import CSPReport
from app.models.difficulty import (
    DifficultyQuestionRating,
    DifficultyUpdateLog,
    DifficultyUserRating,
    RatingScope,
)
from app.models.irt import IrtCalibrationRun, IrtItemFit, IrtItemParams, IrtUserAbility
from app.models.rank import (
    RankActivationEvent,
    RankConfig,
    RankModelRun,
    RankPredictionSnapshot,
    RankRunStatus,
    RankSnapshotStatus,
)
from app.models.graph_revision import (
    GraphRevisionActivationEvent,
    GraphRevisionConfig,
    GraphRevisionRun,
    GraphRevisionRunStatus,
    PrereqEdge,
    PrereqSyncRun,
    PrereqSyncStatus,
    ShadowRevisionPlan,
)
from app.models.neo4j_sync import (
    Neo4jSyncRun,
    Neo4jSyncRunStatus,
    Neo4jSyncRunType,
)
from app.models.irt_activation import (
    IrtActivationDecision,
    IrtActivationEvent,
    IrtActivationEventType,
    IrtActivationPolicy,
)
from app.models.algo_runtime import (
    AlgoBridgeConfig,
    AlgoRuntimeConfig,
    AlgoRuntimeProfile,
    AlgoStateBridge,
    AlgoSwitchEvent,
    BanditThemeState,
    UserMasteryState,
    UserRevisionState,
    UserThemeStats,
)
from app.models.import_schema import (
    ImportFileType,
    ImportJob,
    ImportJobRow,
    ImportJobStatus,
    ImportSchema,
)
from app.models.learning import AlgoParams, AlgoRun, AlgoVersion
from app.models.learning_difficulty import QuestionDifficulty
from app.models.learning_mastery import UserThemeMastery
from app.models.learning_revision import RevisionQueue
from app.models.mfa import MFATOTP, MFABackupCode
from app.models.mistakes import MistakeLog

# UserAllowedBlock model deprecated - table left in DB but no longer used for restrictions
# from app.models.user_allowed_blocks import UserAllowedBlock
from app.models.notification import Notification
from app.models.user_notification_preferences import UserNotificationPreferences
from app.models.oauth import OAuthIdentity, OAuthProvider
from app.models.platform_settings import PlatformSettings

# Legacy Question model - commented out to avoid conflicts with CMS Question
# from app.models.question import Question
from app.models.question_cms import (
    AuditLog,
    ChangeKind,
    MediaAsset,
    MediaRole,
    QuestionMedia,
    QuestionStatus,
    QuestionVersion,
    StorageProvider,
)
from app.models.question_cms import (
    Question as CMSQuestion,
)

# Alias for backward compatibility
Question = CMSQuestion
from app.models.session import (
    AttemptEvent,
    SessionAnswer,
    SessionMode,
    SessionQuestion,
    SessionStatus,
    TestSession,
)
from app.models.search_indexing import (
    SearchOutbox,
    SearchOutboxEventType,
    SearchOutboxStatus,
    SearchSyncRun,
    SearchSyncRunStatus,
    SearchSyncRunType,
)
from app.models.srs import SRSConceptState, SRSReviewLog, SRSUserParams
from app.models.syllabus import Block, Theme, Year
from app.models.user import User, UserRole
from app.models.warehouse import (
    WarehouseExportDataset,
    WarehouseExportRun,
    WarehouseExportRunStatus,
    WarehouseExportRunType,
    WarehouseExportState,
)
from app.models.mock import (
    MockBlueprint,
    MockBlueprintMode,
    MockBlueprintStatus,
    MockBlueprintVersion,
    MockGenerationRun,
    MockGenerationRunStatus,
    MockInstance,
)
from app.models.ranking_mock import MockRanking, MockResult, RankingRun, RankingRunStatus
from app.models.runtime_control import (
    ModuleOverride,
    RuntimeProfile,
    SessionRuntimeSnapshot,
    SwitchAuditLog,
    TwoPersonApproval,
)

__all__ = [
    "User",
    "UserRole",
    "AdminSecurityRuntime",
    "RefreshToken",
    "PasswordResetToken",
    "EmailVerificationToken",
    "OAuthIdentity",
    "OAuthProvider",
    "MFATOTP",
    "MFABackupCode",
    "Year",
    "Block",
    "Theme",
    "Question",  # Alias for CMSQuestion for backward compatibility
    "CMSQuestion",  # New CMS question model (aliased as Question in question_cms.py)
    "QuestionStatus",
    "QuestionVersion",
    "ChangeKind",
    "MediaAsset",
    "QuestionMedia",
    "StorageProvider",
    "MediaRole",
    "AuditLog",
    "ImportSchema",
    "ImportFileType",
    "ImportJob",
    "ImportJobStatus",
    "ImportJobRow",
    "TestSession",
    "SessionMode",
    "SessionStatus",
    "SessionQuestion",
    "SessionAnswer",
    "AttemptEvent",
    "AttemptSession",
    "AttemptAnswer",
    "Bookmark",
    "AlgoVersion",
    "AlgoParams",
    "AlgoRun",
    "UserThemeMastery",
    "RevisionQueue",
    "QuestionDifficulty",
    "MistakeLog",
    "BKTSkillParams",
    "BKTUserSkillState",
    "MasterySnapshot",
    "DifficultyUserRating",
    "DifficultyQuestionRating",
    "DifficultyUpdateLog",
    "RatingScope",
    "IrtCalibrationRun",
    "IrtItemParams",
    "IrtUserAbility",
    "IrtItemFit",
    "IrtActivationPolicy",
    "IrtActivationDecision",
    "IrtActivationEvent",
    "IrtActivationEventType",
    "AlgoRuntimeConfig",
    "AlgoRuntimeProfile",
    "AlgoSwitchEvent",
    "AlgoBridgeConfig",
    "UserThemeStats",
    "UserRevisionState",
    "UserMasteryState",
    "AlgoStateBridge",
    "BanditThemeState",
    "SRSUserParams",
    "SRSConceptState",
    "SRSReviewLog",
    "AcademicYear",
    "AcademicBlock",
    "WarehouseExportRun",
    "WarehouseExportState",
    "WarehouseExportRunType",
    "WarehouseExportRunStatus",
    "WarehouseExportDataset",
    "AcademicSubject",
    "UserProfile",
    "UserBlock",
    "UserSubject",
    # "UserAllowedBlock",  # Deprecated - no longer used
    "Notification",
    "PlatformSettings",
    "PrereqEdge",
    "PrereqSyncRun",
    "PrereqSyncStatus",
    "ShadowRevisionPlan",
    "GraphRevisionRun",
    "GraphRevisionRunStatus",
    "GraphRevisionConfig",
    "GraphRevisionActivationEvent",
    "SearchOutbox",
    "SearchOutboxEventType",
    "SearchOutboxStatus",
    "SearchSyncRun",
    "SearchSyncRunStatus",
    "SearchSyncRunType",
    "Neo4jSyncRun",
    "Neo4jSyncRunStatus",
    "Neo4jSyncRunType",
    "WarehouseExportRun",
    "WarehouseExportState",
    "WarehouseExportRunType",
    "WarehouseExportRunStatus",
    "WarehouseExportDataset",
    "MockBlueprint",
    "MockBlueprintMode",
    "MockBlueprintStatus",
    "MockBlueprintVersion",
    "MockGenerationRun",
    "MockGenerationRunStatus",
    "MockInstance",
    "MockResult",
    "MockRanking",
    "RankingRun",
    "RankingRunStatus",
    "EmailOutbox",
    "EmailRuntimeConfig",
    "EmailSwitchEvent",
    "UserNotificationPreferences",
    "SystemFlag",
    "RuntimeProfile",
    "ModuleOverride",
    "SwitchAuditLog",
    "SessionRuntimeSnapshot",
    "TwoPersonApproval",
]
