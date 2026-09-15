"""Load and apply the declarative RADAR venue-identity registry."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "radar/venue_identities.json"
IDENTITY_FIELDS = ("name", "city", "state", "country")
RADAR_AREAS = frozenset({"dmv", "baltimore", "philadelphia", "newark", "new_york", "tokyo", "kanagawa", "saitama", "new_jersey", "unassigned"})


class VenueIdentityError(ValueError):
    """The versioned venue registry or an event venue is not usable."""


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise VenueIdentityError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    try:
        data = json.loads(path.read_text(), object_pairs_hook=unique_object)
    except VenueIdentityError:
        raise
    except (OSError, json.JSONDecodeError) as error:
        raise VenueIdentityError(f"{path}: {error}") from error
    if data.get("schema_version") != 1 or not isinstance(data.get("venues"), dict):
        raise VenueIdentityError(f"{path}: expected schema_version 1 and venues object")
    aliases: set[str] = set()
    for venue_id, identity in data["venues"].items():
        if not isinstance(venue_id, str) or not venue_id:
            raise VenueIdentityError(f"{path}: venue IDs must be non-empty strings")
        if not isinstance(identity, dict) or not all(isinstance(identity.get(key), str) and identity[key] for key in IDENTITY_FIELDS):
            raise VenueIdentityError(f"{path}: {venue_id} requires canonical name, city, state, and country")
        if not isinstance(identity.get("radar_area"), str) or identity["radar_area"] not in RADAR_AREAS:
            raise VenueIdentityError(f"{path}: {venue_id}.radar_area requires a controlled area")
        alias_data = identity.get("aliases", {})
        if not isinstance(alias_data, dict) or set(alias_data) != {"ids", "names", "cities"}:
            raise VenueIdentityError(f"{path}: {venue_id}.aliases requires ids, names, and cities")
        for key, values in alias_data.items():
            if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
                raise VenueIdentityError(f"{path}: {venue_id}.aliases.{key} must be strings")
        for alias in alias_data["ids"]:
            if alias == venue_id or alias in data["venues"] or alias in aliases:
                raise VenueIdentityError(f"{path}: retired venue alias {alias} is ambiguous")
            aliases.add(alias)
    return data


def alias_index(registry: dict) -> dict[str, str]:
    return {
        alias: venue_id
        for venue_id, identity in registry["venues"].items()
        for alias in identity["aliases"]["ids"]
    }


def canonicalize_venue(venue: dict, registry: dict) -> tuple[dict, list[dict]]:
    """Return the canonical venue and an explicit, field-level normalization diff."""
    if not isinstance(venue, dict) or not isinstance(venue.get("id"), str):
        raise VenueIdentityError("venue requires an id")
    canonical_id = alias_index(registry).get(venue["id"], venue["id"])
    identity = registry["venues"].get(canonical_id)
    if identity is None:
        raise VenueIdentityError(f"unknown venue id {venue['id']}")
    normalized = deepcopy(venue)
    changes = []
    desired = {"id": canonical_id, **{field: identity[field] for field in IDENTITY_FIELDS}}
    for field, value in desired.items():
        if normalized.get(field) != value:
            changes.append({"field": f"venue.{field}", "before": normalized.get(field), "after": value})
            normalized[field] = value
    return normalized, changes


def validate_venue(venue: dict, registry: dict) -> None:
    normalized, changes = canonicalize_venue(venue, registry)
    if changes or venue != normalized:
        venue_id = venue.get("id", "<missing>") if isinstance(venue, dict) else "<invalid>"
        raise VenueIdentityError(f"venue must use canonical registry identity for {venue_id}")
