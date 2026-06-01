"""Minimal example for adding a command module."""


def handle_example(player, raw_args):
    message = raw_args.strip() or "No arguments supplied."
    player.sendLine(f"Example command: {message}".encode("utf-8"))


COMMANDS = {
    "example": lambda player, players_in_rooms, raw_args, split_args: handle_example(
        player, raw_args
    ),
}
