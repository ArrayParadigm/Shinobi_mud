"""Builder-editable command help layered over executable command metadata."""

import json
import logging


DEFAULT_HELP_FILE = "helpfiles/commands.json"
DEFAULT_CATEGORY_FILE = "helpfiles/command_categories.json"


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
        summary = summary.strip()
        if not bool(entry.get("published", False)):
            summary = f"{summary} (i)"
        return {"summary": summary, "details": [line.strip() for line in details]}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logging.warning("Unable to use editable help for %s: %s", command.name, exc)
        return fallback


def load_command_categories(category_file=DEFAULT_CATEGORY_FILE):
    """Load builder-editable command groups, falling back to one uncategorized group."""
    try:
        with open(category_file, "r", encoding="utf-8") as file:
            categories = json.load(file)
        if not isinstance(categories, dict):
            raise ValueError("Command categories must be an object.")
        if not all(
            isinstance(label, str)
            and label.strip()
            and isinstance(commands, list)
            and all(isinstance(command, str) and command.strip() for command in commands)
            for label, commands in categories.items()
        ):
            raise ValueError("Command categories must contain named command lists.")
        return categories
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logging.warning("Unable to load editable command categories: %s", exc)
        return {}
