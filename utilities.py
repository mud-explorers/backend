class Traversal:
    def __init__(self, starting_room):
        self.traversal = {}
        self.visited_rooms = set()
        self.cur_room = starting_room
        self.reverse_direction = {'n':'s', 'w':'e', 'e': 'w', 's':'n'}
        self.visited_rooms.add(starting_room["room_id"])
        available_directions = {}
        for exits in starting_room["exits"]:
            available_directions[exits] = "?"
        self.traversal[starting_room["room_id"]] = available_directions
        pass

    def new_room_discored(self, room, direction):
        self.visited_rooms.add(room["room_id"])
        available_directions = {}
        for exits in room["exits"]:
            available_directions[exits] = "?"
        self.traversal[room["room_id"]] = available_directions
        self.traversal[self.cur_room["room_id"]][direction], self.traversal[room["room_id"]][self.reverse_direction[direction]] = room["room_id"], self.cur_room["room_id"]
        self.cur_room = room
    
# Testing:
traversal = Traversal({
    "room_id": 0,
    "title": "A brightly lit room",
    "description": "You are standing in the center of a brightly lit room. You notice a shop to the west and exits to the north, south and east.",
    "coordinates": "(60,60)",
    "elevation": 0,
    "terrain": "NORMAL",
    "players": [
        "player54",
    ],
    "items": [],
    "exits": [
        "n",
        "s",
        "e",
        "w"
    ],
    "cooldown": 60,
    "errors": [],
    "messages": [
        "You have walked south."
    ]
})
print(traversal.visited_rooms) # {0}
print(traversal.traversal) # {0: {'n': '?', 's': '?', 'e': '?', 'w': '?'}}

traversal.new_room_discored({
    "room_id": 10,
    "title": "A misty room",
    "description": "You are standing on grass and surrounded by a dense mist. You can barely make out the exits in any direction.",
    "coordinates": "(60,61)",
    "elevation": 0,
    "terrain": "NORMAL",
    "players": [
        "player146"
    ],
    "items": [],
    "exits": [
        "n",
        "s",
        "w"
    ],
    "cooldown": 1,
    "errors": [],
    "messages": []
}, "n")

print(traversal.traversal) #{0: {'n': 10, 's': '?', 'e': '?', 'w': '?'}, 10: {'n': '?', 's': 0, 'w': '?'}}
print(traversal.visited_rooms) # {0, 10}
print(traversal.cur_room)