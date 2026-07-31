from neta_backend.database.base import Base
from neta_backend.database.models import __all__ as all_models


def test_alembic_metadata_contains_control_plane_models() -> None:
    assert all_models
    assert {
        "pipeline_source_state",
        "pipeline_source_config_revision",
        "pipeline_run_request",
        "pipeline_run",
        "pipeline_audit_event",
    }.issubset(Base.metadata.tables)
