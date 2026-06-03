"""File-backed player feedback capture."""

from datetime import datetime
import os

from presentation import sanitize_player_text


DEFAULT_SUGGESTIONS_FILE = "suggestions.md"
DEFAULT_AI_SUGGESTIONS_FILE = "ai_suggestions.md"
DEFAULT_BUGS_FILE = "bugs.md"


def append_feedback(username, message, file_path, label):
    """Append one timestamped player-authored feedback line."""
    clean_message = sanitize_player_text(message).strip()
    if not clean_message:
        return None

    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f'- {username} {label} at {timestamp}: "{clean_message}"\n'
    with open(file_path, "a", encoding="utf-8") as feedback_file:
        feedback_file.write(line)
    return line
