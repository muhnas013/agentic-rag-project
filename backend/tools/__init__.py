"""Tool yang dapat dipilih Agent (PRD §8 dan §14).

Modul ini menyimpan jejak pemanggilan tool selama satu permintaan. Agent
menjalankan tool di dalam graf LangChain, sehingga endpoint tidak bisa
langsung melihat tool mana yang dipakai maupun potongan dokumen mana yang
terambil. `tool_trace` menjembataninya: setiap tool mencatat dirinya ke
ContextVar, lalu endpoint membacanya setelah agent selesai.

ContextVar dipilih, bukan variabel global biasa, karena nilainya terisolasi
per task asyncio — dua permintaan yang berjalan bersamaan tidak saling
mencampuri jejaknya.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

_trace: ContextVar[list["ToolInvocation"] | None] = ContextVar("tool_trace", default=None)


@dataclass
class ToolInvocation:
    """Satu kali pemanggilan tool beserta hasilnya."""

    name: str
    ok: bool
    detail: str = ""
    sources: list[Any] = field(default_factory=list)


def start_trace() -> list[ToolInvocation]:
    """Mulai jejak baru untuk satu permintaan."""
    jejak: list[ToolInvocation] = []
    _trace.set(jejak)
    return jejak


def record(invocation: ToolInvocation) -> None:
    """Catat pemanggilan tool. Diabaikan bila tool dipakai di luar agent."""
    jejak = _trace.get()
    if jejak is not None:
        jejak.append(invocation)


def current_trace() -> list[ToolInvocation]:
    return _trace.get() or []
