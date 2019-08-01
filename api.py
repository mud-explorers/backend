import hashlib
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
from collections import deque, defaultdict, OrderedDict

apikey = None
keyfile = './.key'
complete_map = []
with open(keyfile) as f:
    apikey = f.readlines()[0]

map_file = './map.graph'
map_visited_file = './map.visited'
player_position_file = './player.position'
room_details_file = './rooms.details'
node = "http://localhost:5000"
start_room_setting = 344
dest_position_setting = 495
player_name_setting = "Something"
hashes_file = './hashes.hashes'

transform_room = lambda room, room_id: {
        "room_id": room_id,
        "coordinates": f"({room[0][0]},{room[0][1]})",
        # "title": room[2],
        # "description": room[3],
        "surrounding": room[1],
        # "terrain": room[5] if len(room) > 5 else "NORMAL",
        # "elevation": room[4]
    }

with open(map_file) as f:
    graph = eval(f.readline())
    # complete_map = graph
    for k, room in graph.items():
        complete_map.append(transform_room(room, k))


class Room(object):
    def __init__(self, id=0, x=None, y=None, title="", description="", elevation=0, terrain="NORMAL"):
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
        return f"{self.id}:[{(self.x, self.y)},{exits},\"{self.title}\",\"{self.description}\",{self.elevation},\"{self.terrain}\"]"


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
                    title = v[2] if len(v) == 6 else ""
                    description = v[3] if len(v) == 6 else ""
                    elevation = v[4] if len(v) == 6 else ""
                    terrain = v[5] if len(v) == 6 else ""

                    room = Room(room_id, x, y, title,
                                description, elevation, terrain)
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
        self.new_name = name
        self.current_room = None

        self.name = None
        self.encumbrance: 0
        self.strength = 0
        self.speed = 0
        self.gold = 0
        self.inventory = []
        self.hashes = dict()

    def travel(self, id):
        self.current_room = graph.rooms[id]

    def save_position(self):
        f = open(player_position_file, 'a')
        f.write(
            f"{datetime.datetime.now()}: ({self.current_room.x},{self.current_room.y})\n")
        f.close()

    def save_room(self, room_json):
        f = open(room_details_file, 'a')
        f.write(str(room_json)+"\n")
        f.close()

    def update_player(self):
        res = requests.get(url=node+'/status').json()

        name = res.get('name')
        cooldown = res.get('cooldown')
        encumbrance = res.get('encumbrance')
        strength = res.get('strength')
        speed = res.get('speed')
        gold = res.get('gold')
        inventory = res.get('inventory')
        self.name = name
        self.encumbrance = encumbrance
        self.strength = strength
        self.speed = speed
        self.gold = gold
        self.inventory = inventory
        print(
            f"Currently in the pocket ({self.encumbrance}/{self.strength}): ", self.inventory)
        time.sleep(cooldown)

    def get_opposite_direction(self, direction):
        directions = {
            'n': 's',
            's': 'n',
            'e': 'w',
            'w': 'e',
            None: None
        }
        return directions[direction]

    def bfs(self):
        visited = set()
        queue = deque()
        queue.append([{self.current_room.id: None}])
        while len(queue) > 0:
            path = queue.popleft()
            vertex = list(path[-1])[0]
            if vertex not in visited:
                for news in graph.rooms[vertex].get_exits():
                    new_path = list(path)
                    val = {graph.rooms[vertex].get_room_in_direction(
                        news).id: news} if graph.rooms[vertex].get_room_in_direction(news) != '?' else {'?': news}
                    new_path.append(val)
                    queue.append(new_path)
                    if graph.rooms[vertex].get_room_in_direction(news) == '?':
                        return [list(step.values())[0] for step in new_path[1:]]
                visited.add(vertex)
        return None

    def bfs_to_dest(self, dest_id):
        visited = set()
        queue = deque()
        queue.append([{self.current_room.id: None}])
        while len(queue) > 0:
            path = queue.popleft()
            vertex = list(path[-1])[0]
            if vertex not in visited:
                for news in graph.rooms[vertex].get_exits():
                    new_path = list(path)
                    if graph.rooms[vertex].get_room_in_direction(news) != '?':
                        val = {graph.rooms[vertex].get_room_in_direction(
                            news).id: news}
                        new_path.append(val)
                    queue.append(new_path)
                    if graph.rooms[vertex].get_room_in_direction(news) != None and type(graph.rooms[vertex].get_room_in_direction(news)) is not str:
                        if graph.rooms[vertex].get_room_in_direction(news).id == dest_id:
                            return [list(step.values())[0] for step in new_path[1:]]
                visited.add(vertex)
        return None

    def find_nearest_unexplored_room(self):
        # find path to the nearest room with unexplored paths
        return self.bfs()

    def glue_consecutive_path(self, path):
        # for dash
        glued_path = []
        rooms = []
        tmp = self.current_room
        for elem in path:
            if len(glued_path) > 0:
                if elem != glued_path[-1][0]:
                    glued_path.append(elem)
                    rooms.append([tmp.get_room_in_direction(elem).id]) if tmp.get_room_in_direction(
                        elem) != '?' else None
                else:
                    if tmp.get_room_in_direction(elem) != '?':
                        glued_path[-1] += elem
                        rooms[-1].append(tmp.get_room_in_direction(elem).id)
                    else:
                        glued_path.append(elem)
                tmp = tmp.get_room_in_direction(elem)
                continue
            glued_path.append(elem)
            rooms.append([tmp.get_room_in_direction(elem).id]
                         ) if tmp.get_room_in_direction(elem) != '?' else None
            tmp = tmp.get_room_in_direction(elem)
        return glued_path, rooms

    def take_item(self, item_name):
        post_data = {"name": item_name}
        r = requests.post(url=node+'/take', json=post_data).json()
        cooldown = r.get('cooldown')
        time.sleep(cooldown)
        print(f"Picked up {item_name}!")
        self.update_player()

    def drop_item(self, item_name):
        post_data = {"name": item_name}
        r = requests.post(url=node+'/drop', json=post_data).json()
        cooldown = r.get('cooldown')
        time.sleep(cooldown)
        print(f"Dropped {item_name}!")
        self.update_player()

    def sell_item(self, item_name):
        post_data = {"name": item_name}
        r = requests.post(url=node+'/sell', json=post_data).json()
        cooldown = r.get('cooldown')
        time.sleep(cooldown)
        post_data = {"name": item_name, "confirm": "yes"}
        r = requests.post(url=node+'/sell', json=post_data).json()
        time.sleep(cooldown)
        print(f"Sold {item_name}!")
        self.update_player()

    def autonomous_play(self):
        pass

    def get_num_of_unexplored_rooms(self):
        rooms_unexplored = []
        for k, v in graph.rooms.items():
            exits = [v.get_room_in_direction(
                direction) for direction in v.get_exits()]
            if '?' in exits:
                rooms_unexplored.append(k)
        return len(rooms_unexplored)

    def map_rooms(self):
        res = requests.get(url=node+'/init').json()

        id = res.get('room_id')
        title = res.get('title')
        description = res.get('description')
        elevation = res.get('elevation')
        terrain = res.get('terrain')
        x, y = eval(res.get('coordinates'))
        cooldown = res.get('cooldown')
        exits = res.get('exits')

        first_room = Room(id, x, y, title, description, elevation, terrain)
        first_room.n_to = "?" if "n" in exits else None
        first_room.s_to = "?" if "s" in exits else None
        first_room.e_to = "?" if "e" in exits else None
        first_room.w_to = "?" if "w" in exits else None

        graph.add_room(first_room)
        self.current_room = graph.rooms[start_room_setting]
        time.sleep(cooldown)
        self.save_position()

        self.update_player()

        prev_direction = None
        # without fly & dash
        # newpath = self.find_nearest_unexplored_room()
        # newpath = self.bfs_to_dest(dest_position_setting)

        newpath, newrooms = self.glue_consecutive_path(
            self.bfs_to_dest(dest_position_setting))
        # newpath, newrooms = self.glue_consecutive_path(self.find_nearest_unexplored_room())

        # while self.get_num_of_unexplored_rooms() > 0:
        while True:
            print(f"{len(newpath)} rooms to go through:", newpath)
            for i in range(len(newpath)):
                if len(newpath[i]) > 1:
                    # # use dash
                    # pass
                    direction = newpath[i][0]
                    num_rooms = len(newpath[i])
                    next_room_ids = ",".join(map(str, newrooms[i]))

                    post_data = {
                        "direction": direction,
                        "num_rooms": str(num_rooms),
                        "next_room_ids": next_room_ids
                    }

                    res = requests.post(
                        url=node+"/dash", json=post_data).json()
                else:
                    # go by one room
                    direction = newpath[i]
                    next_room = self.current_room.get_room_in_direction(
                        direction) if self.current_room.get_room_in_direction(direction) != '?' else None
                    if next_room is not None:
                        post_data = {
                            "direction": direction,
                            "next_room_id": str(next_room.id)
                        }
                    else:
                        post_data = {"direction": direction}
                    # uncomment when we get the ability to fly
                    # if(graph.rooms[next_room.id].elevation > self.current_room.elevation):
                    #     res = requests.post(
                    #         url=node+"/fly", json=post_data).json()
                    # else:
                    #     res = requests.post(
                    #         url=node+"/move", json=post_data).json()

                    res = requests.post(
                        url=node+"/move", json=post_data).json()

                id = res.get('room_id')
                cooldown = res.get('cooldown')
                title = res.get('title')
                description = res.get('description')
                elevation = res.get('elevation')
                terrain = res.get('terrain')
                x, y = eval(res.get('coordinates'))
                exits = res.get('exits')
                if id not in graph.rooms:
                    new_room = Room(id, x, y, title,
                                    description, elevation, terrain)
                    new_room.n_to = "?" if "n" in exits else None
                    new_room.s_to = "?" if "s" in exits else None
                    new_room.e_to = "?" if "e" in exits else None
                    new_room.w_to = "?" if "w" in exits else None
                    graph.add_room(new_room)
                    print(
                        f"Mapped a new room! Currently mapped: {len(graph.rooms)} rooms.")
                else:
                    new_room = graph.rooms[id]

                if self.current_room.get_room_in_direction(direction) == '?':
                    self.current_room.connect_rooms(
                        direction, graph.rooms[new_room.id])

                self.travel(id)
                self.save_room(res)
                # check if any items in the room and if so, take it
                try:
                    items = res.get('items')
                    if len(items) > 0:
                        for item_name in items:
                            print(f"Found {item_name}!")
                            if self.encumbrance < self.strength:
                                self.take_item(item_name)
                            else:
                                break
                    else:
                        print("No items in this room.")
                except:
                    print("Cannot see anything in this room.")

                print(
                    f"Current room: {id} ({title} - {x},{y}) - cooldown: {cooldown}")
                prev_direction = direction
                graph.save_graph()
                self.save_position()
                time.sleep(cooldown)
            # break
            # newpath = self.bfs_to_dest(random.randint(0, 499))
            # newpath = self.find_nearest_unexplored_room()
            # newpath = self.find_nearest_unexplored_room() if (self.encumbrance/self.strength) < 0.8 else self.bfs_to_dest(1)
            # newpath, newrooms = self.glue_consecutive_path(self.bfs_to_dest(496)) if (
                # self.encumbrance/self.strength) < 0.8 else self.glue_consecutive_path(self.bfs_to_dest(1))
            # newpath, newrooms = self.glue_consecutive_path(self.find_nearest_unexplored_room())
            if self.strength <= self.encumbrance:
                break

    def change_name_to(self):
        res = requests.post(url=node+'/name-changer',
                            json={"name": self.new_name}).json()
        cooldown = res.get('cooldown')
        time.sleep(cooldown)
        self.update_player()

    def examine(self, name):
        # probably needs more logic
        res = requests.post(url=node+'/examine',
                            json={"name": name}).json()
        cooldown = res.get('cooldown')
        time.sleep(cooldown)

    def shrine(self):
        # probably needs more logic
        res = requests.post(url=node+'/shrine').json()
        cooldown = res.get('cooldown')
        time.sleep(cooldown)

    def wear(self, name):
        # probably needs more logic
        res = requests.post(url=node+'/equipment',
                            json={"name": name}).json()
        cooldown = res.get('cooldown')
        time.sleep(cooldown)

    def transmogrify(self, name):
        # probably needs more logic
        res = requests.post(url=node+'/transmogrify',
                            json={"name": name}).json()
        cooldown = res.get('cooldown')
        time.sleep(cooldown)

    def get_last_proof(self):
        last_proof_json = requests.get(url=node+'/last_proof').json()
        last_proof = last_proof_json.get('proof')
        cooldown = last_proof_json.get('cooldown')
        difficulty = last_proof_json.get('difficulty')
        time.sleep(cooldown)
        return (last_proof, difficulty)

    def get_balance(self):
        res = requests.get(url=node+'/get_balance').json()
        balance = res.get('messages')
        print('Current balance:', balance)

    def proof_of_work(self, last_proof, difficulty):
        proof = 0
        while not self.validate_proof(last_proof, proof, difficulty):
            proof = str(uuid4()).replace('-', '')
            # proof += 1
        return proof

    def validate_proof(self, last_proof, proof, difficulty):
        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[:difficulty] == "0"*difficulty

    def mine(self):
        # lambdacoin mining
        while True:
            last_proof, difficulty = self.get_last_proof()
            print(f"Last proof: {last_proof}")
            print(f"Difficulty: {difficulty}")

            # do some mining
            proof = self.proof_of_work(last_proof, difficulty)

            res = requests.post(url=node+'/mine', json={"proof": proof}).json()
            cooldown = res.get('cooldown')
            time.sleep(cooldown)
            print(res)

    def load_hashes(self):
        if os.path.exists(hashes_file):
            with open(hashes_file, 'r') as f:
                content = eval(f.readline())
                self.hashes = content
        else:
            return None

    def save_hashes(self):
        pass

    def calculate_hashes(self):
        self.load_hashes()
        proof = 0
        while True:
            proof = str(uuid4()).replace('-', '')
            hashval = hashlib.sha256(f'{proof}'.encode()).hexdigest()

            for n in range(5, 65):
                if hashval[:n] == "0"*n:
                    self.hashes[f"{n}"].append(proof)
                    with open(hashes_file, 'w') as f:
                        output = json.dumps(self.hashes)
                        f.write(output)
                    print(f"New hash ({n}) added: {proof}")
        return


app = Flask(__name__)
graph = Graph()
graph.load_graph()
# graph.load_visited()
# player = Player(player_name_setting)
# player.map_rooms()


def bfs_for_path_to(cur_room, target):
    with open(map_file, 'r') as f:
        graph = eval(f.readline())
        visited = set()
        visited.add(cur_room)
        paths = [[cur_room]]
        while target not in visited and len(paths) > 0:
            path = paths.pop(0)
            room = path[-1]
            room_set = graph[room][1]
            for direction, room_id in room_set.items():
                if room_id == target:
                    return [*path, room_id]
                elif room_id not in visited and room_id != '?':
                    visited.add(room_id)
                    paths.append([*path, room_id])
        return "No such path"

# ========================== MAP ENDPOINTS ======================
@app.route('/', methods=['GET'])
def root_route():
    return jsonify({"rooms": complete_map}), 200


@app.route('/init', methods=['GET'])
def init_route():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/init/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}

    r = requests.get(url=url, headers=headers)
    return jsonify(r.json()), 200


@app.route('/move', methods=['POST'])
def move_route():
    values = request.get_json()
    [direction, next_room_id] = [
        values[k] if k in values else None for k in ("direction", "next_room_id")]

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/move/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"direction": direction}
    # check that next_room_id is the right one so we do not get a cooldown penalty....
    if not not next_room_id and True:
        body["next_room_id"] = next_room_id

    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/flight', methods=['POST'])
def flight_route():
    values = request.get_json()
    [direction, next_room_id] = [
        values[k] if k in values else None for k in ("direction", "next_room_id")]

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/flight/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"direction": direction}
    # check that next_room_id is the right one so we do not get a cooldown penalty....
    if not not next_room_id and True:
        body["next_room_id"] = next_room_id

    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/dash', methods=['POST'])
def dash_route():
    values = request.get_json()
    [direction, num_rooms, next_room_ids] = [
        values[k] if k in values else None for k in ("direction", "num_rooms", "next_room_ids")]

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/dash/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"direction": direction, "num_rooms": num_rooms,
            "next_room_ids": next_room_ids}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


# ========================== TREASURE ENDPOINTS ======================
@app.route('/examine', methods=['POST'])
def examine_route():
    values = request.get_json()
    name = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/examine/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": name}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/take', methods=['POST'])
def take_route():
    values = request.get_json()
    treasure = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/take/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": treasure}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/drop', methods=['POST'])
def drop_route():
    values = request.get_json()
    treasure = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/drop/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": treasure}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/sell', methods=['POST'])
def sell_route():
    values = request.get_json()
    treasure = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/sell/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": treasure}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/sell/confirm', methods=['POST'])
def sell_confirm_route():
    values = request.get_json()
    treasure = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/sell/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": treasure, "confirm": "yes"}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


# ========================== PLAYER ENDPOINTS ======================
@app.route('/status', methods=['GET'])
def status_route():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/status/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    r = requests.post(url=url, headers=headers)
    return jsonify(r.json()), 200


@app.route('/name_changer', methods=['POST'])
def changer_route():
    values = request.get_json()
    new_name = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/change_name/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": new_name, "confirm": "aye"}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200

# ========================== MISC ENDPOINTS ======================
@app.route('/shrine', methods=['POST'])
def shrine_route():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/pray/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    r = requests.post(url=url, headers=headers)
    return jsonify(r.json()), 200


@app.route('/transmogrify', methods=['POST'])
def transmogripher_route():
    values = request.get_json()
    name = values.get("name")

<<<<<<< HEAD
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/transmogrify/'
    headers = {"Authorization": f"Token {apikey}"}
=======
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/transmogriphy/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
>>>>>>> 5f77329bbdc2799160289f74673cff567080b826
    body = {"name": name}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200


@app.route('/equipment', methods=['POST'])
def equipment_route():
    values = request.get_json()
    name = values.get("name")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/adv/wear/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"name": name}
    r = requests.post(url=url, headers=headers, json=body)
    return jsonify(r.json()), 200

# ========================== LAMBDACOIN ENDPOINTS ======================
@app.route('/mine', methods=['POST'])
def mine_route():
    values = request.get_json()
    proof = values.get("proof")

    url = 'https://lambda-treasure-hunt.herokuapp.com/api/bc/mine/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    body = {"proof": proof}
    r = requests.post(url=url, headers=headers, json=body)
    if r:
        return jsonify(r.json()), 200
    else:
        res = {'cooldown': 0.0}
        return jsonify(res), 200


@app.route('/last_proof', methods=['GET'])
def last_proof_route():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/bc/last_proof/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    r = requests.get(url=url, headers=headers)
    return jsonify(r.json()), 200


@app.route('/get_balance', methods=['GET'])
def get_balance_route():
    url = 'https://lambda-treasure-hunt.herokuapp.com/api/bc/get_balance/'
    auth = request.headers.get('Authorization')
    token = None
    if not not auth:
        token = auth.split(" ")[1]
    if not not token:
        headers = {"Authorization": f"Token {token}"}
    else:
        headers = {"Authorization": f"Token {apikey}"}
    r = requests.get(url=url, headers=headers)
    return jsonify(r.json()), 200
