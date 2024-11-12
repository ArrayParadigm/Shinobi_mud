
def handle_look(protocol):
    protocol.sendLine(b"You look around.")

def handle_north(protocol):
    protocol.sendLine(b"You move north.")

COMMANDS = {
    "look": handle_look,
    "north": handle_north
}
