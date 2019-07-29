import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests
import sys


class API(object):
    def __init__(self):
        pass

app = Flask(__name__)

@app.route('/', methods=['GET'])
def root_route():
    return jsonify({ 'message': 'API ok' }), 200