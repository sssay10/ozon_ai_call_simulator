from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from scenarios import (
    DEFAULT_SCENARIO_ID,
    RKO_SCENARIO_IDS,
)


@dataclass(frozen=True)
class ScenarioResolution:
    requested_label: str | None
    domain: str | None
    archetype: str | None
    level: int | None
    scenario_id: str
    exact_match: bool
    fallback_reason: str | None = None

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "requested_label": self.requested_label,
            "domain": self.domain,
            "archetype": self.archetype,
            "level": self.level,
            "scenario_id": self.scenario_id,
            "exact_match": self.exact_match,
            "fallback_reason": self.fallback_reason,
        }


_RKO_PATTERN = re.compile(
    r"^\s*(?P<domain>[^/]+)\s*/\s*(?P<archetype>[^/]+)\s*/\s*level\s*(?P<level>\d+)\s*$",
    re.IGNORECASE,
)


def _parse_training_scenario_name(label: str | None) -> tuple[str | None, str | None, int | None]:
    if not label or not label.strip():
        return None, None, None

    match = _RKO_PATTERN.match(label.strip())
    if not match:
        return None, None, None

    domain = match.group("domain").strip().lower()
    archetype = match.group("archetype").strip().lower()
    level = int(match.group("level"))
    return domain, archetype, level


def resolve_judge_scenario(label: str | None) -> ScenarioResolution:
    domain, archetype, level = _parse_training_scenario_name(label)

    if domain == "rko" and archetype in RKO_SCENARIO_IDS and level in {1, 2, 3, 4}:
        return ScenarioResolution(
            requested_label=label,
            domain=domain,
            archetype=archetype,
            level=level,
            scenario_id=RKO_SCENARIO_IDS[archetype][level],
            exact_match=True,
        )

    return ScenarioResolution(
        requested_label=label,
        domain=domain,
        archetype=archetype,
        level=level,
        scenario_id=DEFAULT_SCENARIO_ID,
        exact_match=False,
        fallback_reason=(
            "Training scenario name is missing or not recognized by the judge mapping; "
            "falling back to novice_ip_no_account_easy."
        ),
    )
