from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict


@dataclass
class SourceDoc:
    """A normalized 'document' we can cite in the final answer."""
    source_type: str  # e.g. serp, reddit_serp, x_serp, answer_engine, archive
    title: str
    url: str
    snippet: str = ""
    published_at: Optional[str] = None
    score: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchRun:
    question: str
    created_at_iso: str
    agent_name: str
    docs: List[SourceDoc] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "created_at_iso": self.created_at_iso,
            "agent_name": self.agent_name,
            "notes": self.notes,
            "docs": [
                {
                    "source_type": d.source_type,
                    "title": d.title,
                    "url": d.url,
                    "snippet": d.snippet,
                    "published_at": d.published_at,
                    "score": d.score,
                    "meta": d.meta,
                }
                for d in self.docs
            ],
        }
