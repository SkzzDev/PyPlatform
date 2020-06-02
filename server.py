import socket
import struct
import pyplatform


class PyPlatformClientHandler(pyplatform.protocol.PyPlatformProtocol):
    def __init__(self, server, socket):
        # Super
        self.network = pyplatform.network.PyPlatformNetwork(self)
        self.network.assign_socket(socket)
        super().__init__(self.network)

        # Main variables
        self.server = server
        self.player = pyplatform.player.Player()
        self.room = None

        # Assign player an id
        self.player.id = server.generate_player_id()
        self.send_data("\x1C", "\x01", struct.pack("!I", self.player.id))  # Set player id

    def connection_made(self):
        print("[PyPlatformClientHandler | Info] Connection to network made !")

    def connection_lost(self, exception=None):
        if exception is not None:
            print("[PyPlatformClientHandler | Error] Connection to network lost: " + str(exception))
        self.server.disconnect_client(self)

    def parse_data(self, category, event, content):
        if category == "\x1A":  # Message
            pass
        elif category == "\x1B":  # Room
            if event == "\x01":  # Player enter room
                room_name_len = int(struct.unpack("!I", content[:4])[0])
                room_name = struct.unpack("!%ds" % room_name_len, content[4:])[0].decode("utf-8")
                self.server.player_entered_room(self, room_name)
            elif event == "\x02":  # Get room players data
                players = self.server.get_room_players_data(self.room.name)
                self.send_data("\x1B", "\x01", players)  # Update room players data
        elif category == "\x1C":  # Player
            if event == "\x01":  # Player died
                self.player.is_spawned = False
                self.server.check_should_change_map(self.room.name)
            elif event == "\x02":  # Player entered hole
                self.player.is_spawned = False
                self.server.check_should_change_map(self.room.name)
            elif event == "\x03":  # Updating player data
                self.player.id, self.player.x, self.player.y, r, g, b, self.player.is_spawned = struct.unpack("!IffBBB?", content)
                self.player.color = pyplatform.miscellaneous.tuple_to_hex((r, g, b))


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

    def send_all_data(self, category, event, packet_data=None):
        for i, client in self.clients.items():
            client.send_data(category, event, packet_data)

    def send_all_excepted_data(self, category, event, packet_data, excepted):
        for i, client in self.clients.items():
            if client != excepted:
                client.send_data(category, event, packet_data)

    def __len__(self):
        return len(self.clients)


class PyPlatformServer():

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.maps = pyplatform.maps.Maps()

        self.current_client_id = 0
        self.rooms = {}

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def generate_player_id(self):
        self.current_client_id += 1
        return self.current_client_id

    def player_entered_room(self, client, room_name):
        if room_name in self.rooms:
            # Room with people already inside
            self.rooms[room_name].client_enter_room(client)
            client.send_data("\x1B", "\x05", self.get_room_players_id(room_name))  # Init room players id
            client.send_data("\x1B", "\x02", bytes(self.rooms[room_name].current_map))  # Set room map
            client.send_data("\x1C", "\x02")  # Respawn
            self.rooms[room_name].send_all_excepted_data("\x1B", "\x04", bytes(client.player), client)  # A player entered the room
        else:
            # Empty room, create a new one
            self.rooms[room_name] = PyPlatformRoomHandler(self, room_name)
            self.rooms[room_name].client_enter_room(client)
            client.send_data("\x1B", "\x05", self.get_room_players_id(room_name))  # Init room players id
            map = self.maps.get_random_map()
            if map is not None:
                self.rooms[room_name].current_map = map
                client.send_data("\x1B", "\x02", bytes(map))  # Set room map
                client.send_data("\x1C", "\x02")  # Respawn
            else:
                server.disconnect_client(client)

    def player_exit_room(self, client):
        client_room = client.room
        if client.room is not None:  # If player is inside a room
            self.rooms[client_room.name].client_exit_room(client)
            client.player.is_spawned = False

    def get_room_players_id(self, room_name):
        buffer = b""
        if room_name in self.rooms:
            buffer = struct.pack("!h", len(self.rooms[room_name].clients))
            for i, client in self.rooms[room_name].clients.items():
                buffer += struct.pack("!I", client.player.id)
        return buffer

    def get_room_players_data(self, room_name):
        buffer = b""
        if room_name in self.rooms:
            buffer = struct.pack("!h", len(self.rooms[room_name].clients))
            for i, client in self.rooms[room_name].clients.items():
                buffer += bytes(client.player)
        return buffer

    def disconnect_client(self, client):
        client_room = client.room
        client_was_spawned = client.player.is_spawned
        if client_room is not None:  # If player is inside a room
            self.player_exit_room(client)
            if len(self.rooms[client_room.name]) == 0:  # If nobody left in the room
                del self.rooms[client_room.name]
            else:  # If there is still people inside the room
                client_room.send_all_data("\x1B", "\x03", struct.pack("!I", client.player.id))  # A player left the room
                if client_was_spawned:
                    self.check_should_change_map(client_room.name)

    def check_should_change_map(self, room_name):
        if self.count_players_alive_room(room_name) == 0:  # If nobody is still alive in the room
            map = self.maps.get_random_map()
            if map is not None:  # If we could get a map
                self.rooms[room_name].current_map = map
                self.rooms[room_name].send_all_data("\x1B", "\x02", bytes(map))  # Set room map
                self.rooms[room_name].send_all_data("\x1C", "\x02")  # Respawn

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


try:
    print("[Server | Info] Starting server...")

    server = PyPlatformServer("localhost", 5555)
    server.init_socket()
    server.socket.bind((server.host, server.port))
    server.socket.listen()

    print("[Server | Info] Server is running.")

    while True:
        print("[Server | Info] Waiting for new connections...")

        socket, address = server.socket.accept()
        client = PyPlatformClientHandler(server, socket)

except Exception as e:
    print("[Server | Error] " + str(e))
