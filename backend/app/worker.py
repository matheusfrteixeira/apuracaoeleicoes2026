"""Worker de ingestao separado (producao): python -m app.worker  com INGEST_EMBEDDED=false na API."""
import asyncio

from . import ibge
from .config import settings
from .ingest import Ingestor
from .mock import MockSource
from .store import make_store
from .tse import TseSource


async def main():
    muns = await ibge.load_municipios()
    src = MockSource(muns) if settings.data_mode == "mock" else TseSource(muns)
    await Ingestor(make_store(), src).run()


if __name__ == "__main__":
    asyncio.run(main())
