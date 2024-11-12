
def handle_shutdown(protocol):
    protocol.sendLine(b"Shutting down the server...")
    reactor.stop()

COMMANDS = {
    "shutdown": handle_shutdown
}
