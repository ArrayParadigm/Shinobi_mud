"""Builder-editable command help layered over executable command metadata."""

import json
import logging


DEFAULT_HELP_FILE = "helpfiles/commands.json"


def load_help_catalog(help_file=DEFAULT_HELP_FILE):
    """Load one editable help snapshot, falling back to an empty catalog."""
    try:
        with open(help_file, "r", encoding="utf-8") as file:
            catalog = json.load(file)
        if not isinstance(catalog, dict):
            raise ValueError("Help catalog must be an object.")
        return catalog
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logging.warning("Unable to load editable help catalog: %s", exc)
        return {}


def command_help(command, help_file=DEFAULT_HELP_FILE, catalog=None):
    """Return editable help prose with safe command-metadata fallbacks."""
    fallback = {"summary": command.description, "details": []}
    try:
        catalog = load_help_catalog(help_file) if catalog is None else catalog
        entry = catalog.get(command.name, {})
        if not isinstance(entry, dict):
            raise ValueError(f"Help entry for {command.name} must be an object.")
        summary = entry.get("summary", fallback["summary"])
        details = entry.get("details", fallback["details"])
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError(f"Help summary for {command.name} must be text.")
        if isinstance(details, str):
            details = [details]
        if not isinstance(details, list) or not all(
            isinstance(line, str) and line.strip() for line in details
        ):
            raise ValueError(f"Help details for {command.name} must be text lines.")
        return {"summary": summary.strip(), "details": [line.strip() for line in details]}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logging.warning("Unable to use editable help for %s: %s", command.name, exc)
        return fallback
