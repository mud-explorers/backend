import json
import time
import datetime
import random
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests
import sys
import os

apikey = None
with open('./.key') as f:
    apikey = f.readlines()[0]

map_file = './map.graph'
map_visited_file = './map.visited'


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

    def __str__(self):
        exits = dict()
        for x in self.get_exits():
            exits[x] = '?' if type(self.get_room_in_direction(
                x)) == str else self.get_room_in_direction(x).id
        return f"{self.id}:[{(self.x, self.y)},{exits}]"


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

    def save_graph(self):
        output = "\u007b"
        for k, room in self.rooms.items():
            output += str(room)+','
        output = output[:-1]+"\u007d"
        f = open(map_file, 'w')
        f.write(output)
        f.close()

    def load_graph(self):
        if os.path.exists(map_file):
            with open(map_file, 'r') as f:
                content = eval(f.readline())
                for k, v in content.items():
                    room_id = k
                    x, y = v[0]
                    room = Room(room_id, x, y)
                    self.add_room(room)
                for k, v in content.items():
                    room_id = k
                    exits = v[1]
                    if 'n' in exits:
                        if exits['n'] == '?':
                            self.rooms[room_id].n_to = '?'
                        else:
                            self.rooms[room_id].connect_rooms(
                                'n', self.rooms[exits['n']])
                    if 's' in exits:
                        if exits['s'] == '?':
                            self.rooms[room_id].s_to = '?'
                        else:
                            self.rooms[room_id].connect_rooms(
                                's', self.rooms[exits['s']])
                    if 'e' in exits:
                        if exits['e'] == '?':
                            self.rooms[room_id].e_to = '?'
                        else:
                            self.rooms[room_id].connect_rooms(
                                'e', self.rooms[exits['e']])
                    if 'w' in exits:
                        if exits['w'] == '?':
                            self.rooms[room_id].w_to = '?'
                        else:
                            self.rooms[room_id].connect_rooms(
                                'w', self.rooms[exits['w']])
        else:
            return None

    def save_visited(self):
        output = "\u007b"
        for room_id in list(self.visited_rooms):
            output += str(room_id)+','
        output = output[:-1]+"\u007d"
        f = open(map_visited_file, 'w')
        f.write(output)
        f.close()

    def load_visited(self):
        if os.path.exists(map_visited_file):
            with open(map_visited_file, 'r') as f:
                content = eval(f.readline())
                for id in list(content):
                    self.visited_rooms.add(id)
        else:
            return None


class Player(object):
    def __init__(self, name):
        self.name = name
        self.current_room = None

    def travel(self, direction):
        next_room = self.current_room.get_room_in_direction(direction)
        if next_room is not None:
            self.current_room = next_room
        else:
            print("Cannot move in that direction!")

    def save_position(self):
        f = open('./player.position', 'a')
        f.write(
            f"{datetime.datetime.now()}: ({self.current_room.x},{self.current_room.y})\n")
        f.close()

    def autonomous_play(self):
        pass

    def map_rooms(self):
        if len(sys.argv) > 1:
            node = f"http://{sys.argv[1]}:{int(sys.argv[2])}"
        else:
            node = "http://localhost:5000"

        res = requests.get(url=node+'/init').json()

        id = res.get('room_id')
        title = res.get('title')
        x, y = eval(res.get('coordinates'))
        cooldown = res.get('cooldown')
        exits = res.get('exits')

        first_room = Room(id, x, y, title)
        first_room.n_to = "?" if "n" in exits else None
        first_room.s_to = "?" if "s" in exits else None
        first_room.e_to = "?" if "e" in exits else None
        first_room.w_to = "?" if "w" in exits else None

        graph.add_room(first_room)
        self.current_room = graph.rooms[id]
        time.sleep(cooldown)
        self.save_position()

        while len(graph.rooms) < 500:
            # check the current room
            # get exits
            # do random action
            # if current room not in self.rooms, add it
            # sleep X
            # save graph
            # repeat

            exits = self.current_room.get_exits()
            random.shuffle(exits)
            direction = exits[0]
            post_data = {"direction": direction}

            res = requests.post(url=node+"/move", json=post_data).json()

            id = res.get('room_id')
            cooldown = res.get('cooldown')
            title = res.get('title')
            x, y = eval(res.get('coordinates'))
            exits = res.get('exits')
            if id not in graph.rooms:
                new_room = Room(id, x, y, title)
                new_room.n_to = "?" if "n" in exits else None
                new_room.s_to = "?" if "s" in exits else None
                new_room.e_to = "?" if "e" in exits else None
                new_room.w_to = "?" if "w" in exits else None
                graph.add_room(new_room)
            else:
                new_room = graph.rooms[id]

            if self.current_room.get_room_in_direction(direction) == '?':
                self.current_room.connect_rooms(
                    direction, graph.rooms[new_room.id])

            self.travel(direction)
            graph.save_graph()
            self.save_position()
            time.sleep(cooldown)


app = Flask(__name__)
graph = Graph()
graph.load_graph()
graph.load_visited()
player = Player('Solver')


# ========================== MAP ENDPOINTS ======================
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
    [direction, next_room_id] = [
        values[k] if k in values else None for k in ("direction", "next_room_id")]

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/move/'
    headers = {"Authorization": f"Token {apikey}"}
    body = {"direction": direction}
    # check that next_room_id is the right one so we do not get a cooldown penalty....
    if not not next_room_id and True:
        body["next_room_id"] = next_room_id

    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/dash', methods=['POST'])
def dash():
    values = request.get_json()
    [direction, num_rooms] = [
        values[k] if k in values else None for k in ("direction", "num_rooms")]

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/dash/'
    headers = {"Authorization": f"Token {apikey}"}
    body = {"direction": direction, "num_rooms": num_rooms}

    next_room_ids = ""
    # from the current room, generate the ids for num_rooms in direction
    body["next_rooms_ids"] = next_room_ids
    # r = requests.post(url=url, headers=headers, json=body)
    # return jsonify(r.json()), 200


# ========================== TREASURE ENDPOINTS ======================
@app.route('/examine', methods=['POST'])
def examine():
    values = request.get_json()
    name = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/examine/'
    headers = {"Authorization": f"Token {apikey}"}
    body = {"name": name}

    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/take', methods=['POST'])
def take():
    values = request.get_json()
    treasure = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/take/'
    headers = {"Authorization": f"Token {apikey}"}
<<<<<<< HEAD
    # check to see if item is in room we are in, to avoid cooldown penalty.
    if True:
        body = { "name": treasure }
        r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200
=======
    body = {"name": treasure}
>>>>>>> 9bc45e7ea4b142bdf03e8e9f2806bfed61134908


@app.route('/drop', methods=['POST'])
def drop():
    values = request.get_json()
    treasure = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/take/'
    headers = {"Authorization": f"Token {apikey}"}
<<<<<<< HEAD
    # check if we have treasure in inventory to avoid cooldown penalty.
    if True:
        body = { "name": treasure }
        r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200
=======
    body = {"name": treasure}
>>>>>>> 9bc45e7ea4b142bdf03e8e9f2806bfed61134908


# ========================== PLAYER ENDPOINTS ======================
@app.route('/status', methods=['GET'])
def status():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/status/'
    headers = {"Authorization": f"Token {apikey}"}
    r = requests.post(url=url, headers=headers)
    return jsonify(r.json()), 200


@app.route('/name-changer', methods=['POST'])
def changer():
    # check if we have the name changer...
    values = request.get_json()
    new_name = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/change_name/'
    headers = {"Authorization": f"Token {apikey}"}
    body = {"name": new_name}
    # check if we have name-changer power, cooldown penalty is 150

    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200
