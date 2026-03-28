from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RunMode = Literal["local_only", "dual_layer"]

DEFAULT_PROJECT_MEMORY = Path("data/memory.json")
DEFAULT_SHARED_GROWTH_DIR = Path("data/shared_growth_memory")


@dataclass(frozen=True)
class AgentPaths:
    project_root: Path
    project_memory_path: Path
    shared_growth_path: Path | None
    mode: RunMode
    source_project: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "project_root": str(self.project_root),
            "project_memory_path": str(self.project_memory_path),
            "shared_growth_path": None if self.shared_growth_path is None else str(self.shared_growth_path),
            "mode": self.mode,
            "source_project": self.source_project,
        }


def resolve_agent_paths(
    *,
    project_root: str | Path | None = None,
    project_memory_path: str | Path | None = None,
    shared_growth_path: str | Path | None = None,
    mode: RunMode = "local_only",
    source_project: str | None = None,
) -> AgentPaths:
    resolved_root = Path(project_root or os.getenv("REFLECTIVE_AGENT_PROJECT_ROOT", ".")).expanduser().resolve()
    resolved_project_memory = _resolve_path(
        project_memory_path or os.getenv("REFLECTIVE_AGENT_PROJECT_MEMORY_PATH") or DEFAULT_PROJECT_MEMORY,
        project_root=resolved_root,
    )

    shared_value = shared_growth_path or os.getenv("REFLECTIVE_AGENT_SHARED_GROWTH_DIR")
    resolved_shared_growth: Path | None = None
    if mode == "dual_layer":
        resolved_shared_growth = _resolve_path(
            shared_value or DEFAULT_SHARED_GROWTH_DIR,
            project_root=resolved_root,
        )

    return AgentPaths(
        project_root=resolved_root,
        project_memory_path=resolved_project_memory,
        shared_growth_path=resolved_shared_growth,
        mode=mode,
        source_project=source_project or os.getenv("REFLECTIVE_AGENT_SOURCE_PROJECT", "reflective-growth-agent"),
    )


def _resolve_path(path_value: str | Path, *, project_root: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()
