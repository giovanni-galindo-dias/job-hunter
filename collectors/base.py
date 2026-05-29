"""
Interface base para todos os coletores de vagas.

Para adicionar uma nova fonte:
  1. Crie collectors/minha_fonte.py herdando de BaseCollector.
  2. Implemente _fetch(queries) retornando list[RawJob].
  3. Registre em collectors/registry.py.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import re


@dataclass
class RawJob:
    title: str
    company: str
    url: str
    source: str
    external_id: str = ""
    location: str = ""
    description: str = ""
    posted_at: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def job_id(self) -> str:
        uid = self.external_id or self.url or f"{self.title}:{self.company}"
        return hashlib.md5(f"{self.source}:{uid}".encode()).hexdigest()


@dataclass
class CollectorResult:
    name: str
    jobs: list[RawJob]
    error: str | None = None
    queries_run: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None


class BaseCollector(ABC):
    name: str = "base"

    @abstractmethod
    async def _fetch(self, queries: list[str]) -> list[RawJob]: ...

    async def collect(self, queries: list[str]) -> CollectorResult:
        """Executa coleta com erro isolado — nunca derruba a busca inteira."""
        try:
            jobs = await self._fetch(queries)
            return CollectorResult(name=self.name, jobs=jobs, queries_run=len(queries))
        except Exception as exc:
            return CollectorResult(name=self.name, jobs=[], error=str(exc), queries_run=0)


# ── Helpers compartilhados pelos coletores ────────────────────────────────────

import httpx

TIMEOUT = httpx.Timeout(18.0)
UA = {"User-Agent": "JobHunterApp/2.0 (educational; contact giovannigdias1@gmail.com)"}


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def epoch_to_date(epoch) -> str:
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""
