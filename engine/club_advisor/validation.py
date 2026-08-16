from __future__ import annotations


class ClubAdvisorError(ValueError):
    pass


def ensure_context_valid(context):
    if context is None:
        raise ClubAdvisorError("context is required")
