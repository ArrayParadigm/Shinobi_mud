
def handle_say(protocol, message, players_in_rooms):
    if not message:
        protocol.sendLine(b"You must specify a message.")
        return
    current_room = protocol.current_room
    for player in players_in_rooms.get(current_room, []):
        player.sendLine(f'{protocol.username} says, "{message}"'.encode('utf-8'))

def handle_ooc(protocol, message, players_in_rooms):
    if not message:
        protocol.sendLine(b"You must specify a message.")
        return
    for player in players_in_rooms.values():
        for p in player:
            p.sendLine(f'({protocol.username}) {message}'.encode('utf-8'))

def handle_emote(protocol, action, players_in_rooms):
    if not action:
        protocol.sendLine(b"You must specify an action.")
        return
    current_room = protocol.current_room
    for player in players_in_rooms.get(current_room, []):
        player.sendLine(f'{protocol.username} {action}'.encode('utf-8'))

COMMANDS = {
    "say": lambda protocol, players_in_rooms, *args: handle_say(protocol, " ".join(args), players_in_rooms),
    "ooc": lambda protocol, players_in_rooms, *args: handle_ooc(protocol, " ".join(args), players_in_rooms),
    "emote": lambda protocol, players_in_rooms, *args: handle_emote(protocol, " ".join(args), players_in_rooms)
}
