"""Metadata and shared validation for player commands."""

from dataclasses import dataclass
import logging
from typing import Callable, Optional


@dataclass(frozen=True)
class CommandSpec:
    """Describe a command and validate common dispatch rules."""

    name: str
    handler: Callable
    usage: str
    description: str
    permission: str = "player"
    aliases: tuple = ()
    min_args: int = 0
    max_args: Optional[int] = None
    args_validator: Optional[Callable] = None

    def __call__(self, player, players_in_rooms, raw_args, split_args):
        """Run a validated command while preserving the callable interface."""
        if self.permission == "admin" and not player.is_admin:
            player.sendLine(b"You do not have permission to use that command.")
            logging.warning(
                "Non-admin user %s attempted admin command %s.",
                player.username,
                self.name,
            )
            return
        if self.permission == "builder" and not (player.is_admin or getattr(player, "is_builder", False)):
            player.sendLine(b"You do not have permission to use that command.")
            logging.warning(
                "Non-builder user %s attempted builder command %s.",
                player.username,
                self.name,
            )
            return

        if len(split_args) < self.min_args or (
            self.max_args is not None and len(split_args) > self.max_args
        ) or (self.args_validator and not self.args_validator(split_args)):
            player.sendLine(f"Usage: {self.usage}".encode("utf-8"))
            return

        return self.handler(player, players_in_rooms, raw_args, split_args)
