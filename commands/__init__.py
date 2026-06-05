"""Domain command modules for Veilborn MUD."""


def command_subset(source, names):
    """Return a stable command dictionary from another module's registry."""
    return {name: source.COMMANDS[name] for name in names if name in source.COMMANDS}
