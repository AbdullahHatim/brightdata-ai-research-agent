from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class RoutePlan:
    use_reddit: bool = True
    use_x: bool = True
    use_answer_engine: bool = True
    use_archive_probe: bool = True

    reason: str = "default: enabled all tools"


SENTIMENT_HINTS = {
    "sentiment", "reddit", "subreddit", "hacker news", "hn", "twitter", "x.com", "drama",
    "complaints", "complaint", "issues", "broken", "bug", "bugs", "community", "what do people think",
}
HISTORY_HINTS = {"history", "historical", "years", "older", "archive", "wayback", "2019", "2020", "2021", "2022", "2023", "2024"}
SPEED_HINTS = {"quick", "summary", "overview", "tl;dr"}


def auto_route(question: str) -> RoutePlan:
    q = question.lower()
    use_reddit = any(h in q for h in SENTIMENT_HINTS)
    use_x = any(h in q for h in SENTIMENT_HINTS)
    use_archive = any(h in q for h in HISTORY_HINTS)
    use_answer_engine = any(h in q for h in SPEED_HINTS) or True  # useful most of the time

    # If nothing triggers, keep everything on (demo-friendly)
    if not (use_reddit or use_x or use_archive):
        return RoutePlan(reason="no strong hints → run full multi-source plan")

    reasons = []
    if use_reddit or use_x:
        reasons.append("sentiment hints → include social")
    if use_archive:
        reasons.append("history hints → include archive probe")
    if use_answer_engine:
        reasons.append("include answer engine for cross-check/synthesis")

    return RoutePlan(
        use_reddit=use_reddit,
        use_x=use_x,
        use_answer_engine=use_answer_engine,
        use_archive_probe=use_archive,
        reason="; ".join(reasons),
    )
