"""Team identity matching."""

from esports_model.identity.normalize import normalize_name
from esports_model.identity.resolver import NameMatch, match_team_name, pair_confidence

__all__ = ["NameMatch", "match_team_name", "normalize_name", "pair_confidence"]