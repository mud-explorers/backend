import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests
import sys

apikey = None
with open('./.key') as f:
    apikey = f.readlines()[0]


class Room(object):
    def __init__(self, id=0, x=None, y=None, title="", description="", elevation=0, terrain=""):
        self.id = id
        self.x = x
        self.y = y
        self.title = title
        self.description = description
        self.elevation = elevation
        self.n_to = None
        self.s_to = None
        self.e_to = None
        self.w_to = None
        self.terrain = terrain

    def get_exits(self):
        exits = []
        if self.n_to is not None:
            exits.append('n')
        if self.s_to is not None:
            exits.append('s')
        if self.e_to is not None:
            exits.append('e')
        if self.w_to is not None:
            exits.append('w')
        return exits

    def connect_rooms(self, direction, connecting_room):
        if direction == 'n':
            self.n_to = connecting_room
            connecting_room.s_to = self
        elif direction == 's':
            self.s_to = connecting_room
            connecting_room.n_to = self
        elif direction == 'e':
            self.e_to = connecting_room
            connecting_room.w_to = self
        elif direction == 'w':
            self.w_to = connecting_room
            connecting_room.e_to = self
        else:
            return None

    def get_room_in_direction(self, direction):
        if direction == 'n':
            return self.n_to
        elif direction == 's':
            return self.s_to
        elif direction == 'e':
            return self.e_to
        elif direction == 'w':
            return self.w_to
        else:
            return None

    def coords(self):
        return self.x, self.y


class Graph(object):
    def __init__(self):
        self.rooms = dict()
        self.visited_rooms = set()

    def add_room(self, room):
        if room.id not in self.rooms:
            self.rooms[room.id] = room
        else:
            return None

    def visited_room(self, room_id):
        return room_id in self.visited_rooms

    def visit_room(self, room_id):
        self.visited_rooms.add(room_id)


class Player(object):
    def __init__(self):
        pass


app = Flask(__name__)


@app.route('/', methods=['GET'])
def root_route():
    return jsonify({'message': 'API ok'}), 200


@app.route('/init', methods=['GET'])
def init_route():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/init/'
    headers = {"Authorization": f"Token {apikey}"}
    r = requests.get(url=url, headers=headers)
    return jsonify(r.json()), 200


@app.route('/move', methods=['POST'])
def move():
    values = request.get_json()
    [direction, next_room_id] = [values[k] if k in values else None for k in ("direction", "next_room_id")]

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/move/'
    headers = {"Authorization": f"Token {apikey}"}
    body = { "direction": direction }
    # check that next_room_id is the right one so we do not get a cooldown penalty....
    if not not next_room_id and True:
        body["next_room_id"] = next_room_id
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200
