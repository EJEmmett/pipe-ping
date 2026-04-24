from pipe_ping.models.common import PipelineStatus
from pipe_ping.models.provider import PipelineResult
from pipe_ping.repository.memory import MemoryTransaction


class TestMemoryTransaction:
    async def test_write_returns_composite_id(
        self, transaction: MemoryTransaction, pipeline_result: PipelineResult
    ) -> None:
        doc = await transaction.write_one_pipeline_result(pipeline_result)
        assert doc.id == "owner/repo#42"

    async def test_write_copies_all_fields(
        self, transaction: MemoryTransaction, pipeline_result: PipelineResult
    ) -> None:
        doc = await transaction.write_one_pipeline_result(pipeline_result)
        assert doc.provider == pipeline_result.provider
        assert doc.repo == pipeline_result.repo
        assert doc.branch == pipeline_result.branch
        assert doc.commit_sha == pipeline_result.commit_sha
        assert doc.status == pipeline_result.status
        assert doc.url == pipeline_result.url
        assert doc.created_at == pipeline_result.created_at
        assert doc.started_at == pipeline_result.started_at
        assert doc.finished_at == pipeline_result.finished_at
        assert doc.raw == pipeline_result.raw

    async def test_read_after_write_returns_document(
        self, transaction: MemoryTransaction, pipeline_result: PipelineResult
    ) -> None:
        doc = await transaction.write_one_pipeline_result(pipeline_result)
        result = await transaction.read_one_pipeline_result(doc.id)
        assert result == doc

    async def test_read_unknown_key_returns_none(
        self, transaction: MemoryTransaction
    ) -> None:
        result = await transaction.read_one_pipeline_result("owner/repo#99999")
        assert result is None

    async def test_write_is_upsert(
        self, transaction: MemoryTransaction, pipeline_result: PipelineResult
    ) -> None:
        await transaction.write_one_pipeline_result(pipeline_result)
        updated = pipeline_result.model_copy(update={"status": PipelineStatus.FAILURE})
        doc = await transaction.write_one_pipeline_result(updated)
        result = await transaction.read_one_pipeline_result(doc.id)
        assert result is not None
        assert result.status == PipelineStatus.FAILURE
