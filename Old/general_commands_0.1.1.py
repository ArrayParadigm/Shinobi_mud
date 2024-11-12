def handle_look(protocol, players_in_rooms=None):
    protocol.display_room()

def handle_north(protocol, players_in_rooms=None):
    protocol.move_player('north')

def handle_south(protocol, players_in_rooms=None):
    protocol.move_player('south')

def handle_east(protocol, players_in_rooms=None):
    protocol.move_player('east')

def handle_west(protocol, players_in_rooms=None):
    protocol.move_player('west')

COMMANDS = {
    "look": handle_look,
    "north": handle_north,
    "south": handle_south,
    "east": handle_east,
    "west": handle_west
}
