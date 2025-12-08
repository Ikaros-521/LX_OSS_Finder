from datetime import datetime, timezone
from typing import Dict, Any, List


def freshness_score(updated_at: str) -> float:
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return 0.2
    days = (datetime.now(timezone.utc) - updated).days
    if days <= 7:
        return 1.0
    if days <= 30:
        return 0.9
    if days <= 90:
        return 0.75
    if days <= 180:
        return 0.6
    if days <= 1825:
        return 0.5
    return 0.3


def readme_hint_score(description: str | None, topics: List[str]) -> float:
    text = (description or "").lower()
    score = 0.2
    if "example" in text or "demo" in text:
        score += 0.3
    if topics:
        score += 0.2
    return min(score, 1.0)


def activity_score(stars: int, forks: int, issues: int) -> float:
    star_component = min(stars / 5000, 1.0)
    fork_component = min(forks / 1000, 1.0)
    issue_component = 0.7 if issues < 20 else 0.4
    return 0.5 * star_component + 0.3 * fork_component + 0.2 * issue_component


def compute_score(repo: Dict[str, Any]) -> float:
    freshness = freshness_score(repo.get("updated_at", ""))
    activity = activity_score(
        repo.get("stargazers_count", 0),
        repo.get("forks_count", 0),
        repo.get("open_issues_count", 0),
    )
    docs = readme_hint_score(repo.get("description"), repo.get("topics", []))
    return round(0.45 * freshness + 0.4 * activity + 0.15 * docs, 3)

