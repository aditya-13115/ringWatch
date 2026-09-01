from functools import lru_cache

from backend.core.config import get_settings
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.repositories.feature_repository import FeatureRepository
from backend.repositories.event_repository import EventRepository
from backend.services.timeline_service import TimelineService
from backend.services.queue_service import QueueService
from backend.services.account_service import AccountService
from backend.services.graph_service import GraphService
from backend.services.evidence_service import EvidenceService
from backend.services.action_service import ActionService
from backend.services.report_service import ReportService
from backend.services.audit_service import AuditService
from backend.services.metrics_service import MetricsService
from backend.services.failure_service import FailureDemoService
from backend.services.llm_investigator_service import LLMInvestigatorService
from backend.services.address_normalizer_service import AddressNormalizerService

settings = get_settings()

_data_store = None


def set_data_store(store):
    global _data_store
    _data_store = store


def get_data_store():
    if _data_store is None:
        raise RuntimeError(
            "Data store is not initialized. "
            "Check that FastAPI lifespan has loaded the data."
        )
    return _data_store


@lru_cache
def get_explainability_repo() -> ExplainabilityRepository:
    store = get_data_store()
    return ExplainabilityRepository(store.explainability_dir)


@lru_cache
def get_feature_repo() -> FeatureRepository:
    store = get_data_store()
    return FeatureRepository(store.features_graph_path)


def get_queue_service() -> QueueService:
    return QueueService(get_explainability_repo())


def get_graph_service() -> GraphService:
    return GraphService(get_explainability_repo())


def get_evidence_service() -> EvidenceService:
    return EvidenceService(get_explainability_repo())


def get_action_service() -> ActionService:
    return ActionService(get_explainability_repo())


def get_report_service() -> ReportService:
    return ReportService(get_explainability_repo())


def get_audit_service() -> AuditService:
    return AuditService(get_explainability_repo())


def get_account_service() -> AccountService:
    return AccountService(
        explainability_repo=get_explainability_repo(),
        feature_repo=get_feature_repo(),
        graph_service=get_graph_service(),
        evidence_service=get_evidence_service(),
        action_service=get_action_service(),
        report_service=get_report_service(),
    )


def get_metrics_service() -> MetricsService:
    return MetricsService(
        settings.model_metrics_path,
        get_explainability_repo(),
    )


def get_failure_service() -> FailureDemoService:
    return FailureDemoService()


def get_llm_investigator_service() -> LLMInvestigatorService:
    return LLMInvestigatorService(
        explainability_repo=get_explainability_repo(),
        feature_repo=get_feature_repo(),
        event_repo=get_event_repo(),
        action_service=get_action_service(),
    )


def get_event_repo() -> EventRepository:
    return EventRepository(settings.data_dir)


@lru_cache
def get_address_normalizer_service() -> AddressNormalizerService:
    return AddressNormalizerService(
        settings.addresses_path
    )


def get_timeline_service() -> TimelineService:
    return TimelineService(get_event_repo())
