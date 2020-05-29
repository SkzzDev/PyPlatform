import socket
from _thread import *
import pyplatform


class PyPlatformClientHandler:
    def __init__(self, id, server, socket):
        self.id = id
        self.server = server
        self.socket = socket
        self.player = pyplatform.player.Player()
        self.room = None

    def send_data(self, str_data):
        # print("[ThreadClient | " + self.player.get_id_and_room_name() + " | Info] Sending data: " + str(str_data))
        self.socket.send(str.encode(str_data))

    def received_data(self, decoded_data):
        # print("[ThreadClient | " + self.player.get_id_and_room_name() + " | Info] Data received: " + decoded_data)
        args = decoded_data.split(" ")
        if args[0] == "get-room-players":
            players = self.server.get_room_player_list(self.room.name)
            self.send_data("set-room-players " + players)
        elif args[0] == "enter-room":
            room_name = args[1]
            self.server.player_enter_room(self, room_name)
        elif args[0] == "player-died":
            self.player.is_spawned = False
            self.server.check_should_change_map(self.room.name)
        elif args[0] == "player-entered-hole":
            self.player.is_spawned = False
        elif args[0] == "update-player":
            id, x, y, color, is_spawned = args[1].split("\x1F")
            self.player.id = int(id)
            self.player.x = float(x)
            self.player.y = float(y)
            self.player.color = color
            self.player.is_spawned = (is_spawned == "True")


class PyPlatformRoomHandler(object):
    def __init__(self, server, name):
        self.server = server
        self.name = name
        self.max_size = 10
        self.clients = {}
        self.current_map = pyplatform.maps.Map()

    def client_enter_room(self, client):
        client.room = self
        client.player.room_name = self.name
        self.clients[client.player.id] = client

    def client_exit_room(self, client):
        if client.player.id in self.clients:
            del self.clients[client.player.id]
            client.player.room_name = ""
            client.room = None

    def send_all_data(self, raw_data):
        for i, client in self.clients.items():
            client.send_data(raw_data)

    def __len__(self):
        return len(self.clients)


class PyPlatformServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.db = pyplatform.database.db.Database()
        self.maps = pyplatform.maps.Maps()

        self.rooms = {}

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def player_enter_room(self, client, room_name):
        if room_name in self.rooms:
            # Room with people already inside
            self.rooms[room_name].client_enter_room(client)
            client.send_data("set-map " + str(self.rooms[room_name].current_map))
            client.send_data("spawn")
        else:
            # Empty room, create a new one
            self.rooms[room_name] = PyPlatformRoomHandler(self, room_name)
            self.rooms[room_name].client_enter_room(client)
            map = self.maps.get_random_map()
            if map != None:
                self.rooms[room_name].current_map = map
                client.send_data("set-map " + str(map))
                client.send_data("spawn")

    def player_exit_room(self, client):
        client_room = client.room
        if client.room != None:  # If player is inside a room
            self.rooms[client_room.name].client_exit_room(client)
            client.player.is_spawned = False

    def get_room_player_list(self, room_name):
        buffer = ""
        if room_name in self.rooms:
            for i, client in self.rooms[room_name].clients.items():
                buffer += str(client.player) + "\x1E"
            if len(buffer) > 0:
                buffer = buffer[:-1]
        return buffer

    def client_disconnected(self, client):
        client_room = client.room
        client_was_spawned = client.player.is_spawned
        if client_room != None:  # If player is inside a room
            self.player_exit_room(client)
            if len(self.rooms[client_room.name]) == 0:  # If nobody left in the room
                del self.rooms[client_room.name]
            else:  # If there is still people inside the room
                client_room.send_all_data("player-disconnected " + str(client.player.id))
                if client_was_spawned:
                    self.check_should_change_map(client_room.name)

    def check_should_change_map(self, room_name):
       if self.count_players_alive_room(room_name) == 0:  # If nobody is still alive in the room
            map = self.maps.get_random_map()
            if map != None:  # If we could get a map
                self.rooms[room_name].current_map = map
                self.rooms[room_name].send_all_data("set-map " + str(map))
                self.rooms[room_name].send_all_data("spawn")

    def count_players_room(self, room_name, alive = False):
        if alive:
            count = 0
            for i, client in self.rooms[room_name].clients.items():
                if client.player.is_spawned:
                    count += 1
            return count
        else:
            return len(self.rooms[room_name].clients)

    def count_players_alive_room(self, room_name):
        return self.count_players_room(room_name, True)


def thread_client(client):
    global server
    client.player.id = client.id
    client.send_data("set-player-id " + str(client.id))

    while True:
        try:
            client.received_data(client.socket.recv(1024*4).decode())
        except Exception as e:
            print("[ThreadClient | " + str(address) + " | Info] Lost connection (" + str(e) + ")")
            break

    if client.player.room_name != "":
        server.client_disconnected(client)

    print("[ThreadClient | " + str(address) + " | Info] Player disconnected.")
    client.socket.close()


try:
    server = PyPlatformServer("localhost", 5555)
    server.init_socket()

    server.socket.bind((server.host, server.port))

    server.socket.listen()
    print("[Server | Info] Server running: waiting for connections.")

    current_client_id = 1

    while True:
        socket, address = server.socket.accept()
        print("[Server | Info] Player just connected (" + str(address) + ")")

        client = PyPlatformClientHandler(current_client_id, server, socket)

        start_new_thread(thread_client, (client, ))

        current_client_id += 1

        print("[Server | Info] Waiting for new connections...")

except socket.error as e:
    print("[Server | Error] " + str(e))
