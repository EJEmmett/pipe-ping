from pipe_ping.models.provider import PipelineResult
from pipe_ping.repository.in_memory import InMemoryRepository


class TestInMemoryRepository:
    async def test_round_trip(
        self, repository: InMemoryRepository, pipeline_result: PipelineResult
    ) -> None:
        async with repository.transaction() as tx:
            doc = await tx.write_one_pipeline_result(pipeline_result)
            result = await tx.read_one_pipeline_result(doc.id)
        assert result == doc

    async def test_close_clears_store(
        self, repository: InMemoryRepository, pipeline_result: PipelineResult
    ) -> None:
        async with repository.transaction() as tx:
            doc = await tx.write_one_pipeline_result(pipeline_result)

        await repository.close()
        await repository.open()

        async with repository.transaction() as tx:
            result = await tx.read_one_pipeline_result(doc.id)
        assert result is None
