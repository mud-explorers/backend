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
    def __init__(self):
        pass


class Graph(object):
    def __init__(self):
        self.rooms = dict()
        self.visited_rooms = set()


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
