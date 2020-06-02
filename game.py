import pyplatform
import pygame
import os, sys
import struct
import socket

class PyPlatformClientNetwork(pyplatform.network.PyPlatformNetwork):
    def __init__(self, host, port, protocol):
        super().__init__(protocol)
        self.host = host
        self.port = port

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        try:
            self.init_socket()
            self.socket.connect((self.host, self.port))
            self.connection_made()
        except Exception as e:
            raise e


class Game(pyplatform.protocol.PyPlatformProtocol):

    def __init__(self):
        # Super
        self.network = PyPlatformClientNetwork("localhost", 5555, self)
        super().__init__(self.network)

        # Config variables
        self.size = {'w': 1366, 'h': 768}
        self.background = "717B9C"
        self.fps = 60
        self.screen = pygame.display.set_mode((self.size['w'], self.size['h']))
        self.stopped = False

        # Helpers
        self.physics = pyplatform.physics.Physics(self)
        self.editor = pyplatform.editor.Editor(self)
        self.maps = pyplatform.maps.Maps()

        # Main variables
        self.player = pyplatform.player.PhysicPlayer()
        self.players = {}
        self.current_map = None

    def connect_to_network(self):
        try:
            self.network.connect()
        except Exception as e:
            print("[PyPlatformProtocol | Error] Couldn't connect to network: " + str(e))

    def connection_made(self):
        print("[Game | Info] Connection to network made !")

    def connection_lost(self, exception=None):
        self.stopped = True
        if exception is not None:
            print("[Game | Error] Connection to network lost: " + str(exception))

    def parse_data(self, category, event, content):
        # print(category, event, content)
        if category == "\x1A":  # Message
            if event == "\x01":  # Received normal message
                message_len = struct.unpack("!I", content[:4])
                message = struct.unpack("!%ds" % message_len, content[4:])[0]
                print(message.decode("utf-8"))
        elif category == "\x1B":  # Room
            if event == "\x01":  # Update room players data
                players_count = struct.unpack("!h", content[:2])[0]
                content = content[2:]
                for i in range(players_count):
                    player_id = struct.unpack("!I", content[:4])[0]
                    if player_id in self.players:  # If a new player come, its entering packet could arrive later than this packet
                        self.players[player_id].update(content[4:16])
                    content = content[16:]
            elif event == "\x02":  # Set room map
                # Initial format: "!II%dsI%dsII"
                id = struct.unpack("!I", content[:4])[0]
                content = content[4:]
                author_len = struct.unpack("!I", content[:4])[0]
                content = content[4:]
                author = struct.unpack("!%ds" % author_len, content[:author_len])
                content = content[author_len:]
                xml_len = struct.unpack("!I", content[:4])[0]
                content = content[4:]
                xml = struct.unpack("!%ds" % xml_len, content[:xml_len])[0]
                content = content[xml_len:]
                updated_at, created_at = struct.unpack("!II", content[:8])
                self.current_map = pyplatform.maps.Map(id, author, xml, updated_at, created_at)
            elif event == "\x03":  # A player left the room
                id = struct.unpack("!I", content)[0]
                if id in self.players:
                    del self.players[id]
            elif event == "\x04":  # A player entered the room
                player_id = struct.unpack("!I", content[:4])[0]
                if player_id not in self.players:
                    self.players[player_id] = pyplatform.player.Player(content)
            elif event == "\x05":  # Init room players ids (when entering a room)
                players_number = struct.unpack("!h", content[:2])[0]
                players_id = struct.unpack("!" + "I" * players_number, content[2:])
                for i, player_id in enumerate(players_id):
                    self.players[player_id] = pyplatform.player.Player()
                    self.players[player_id].id = player_id
        elif category == "\x1C":  # Player
            if event == "\x01":  # Set player id
                self.player.id = struct.unpack("!I", content)[0]
            elif event == "\x02":  # Spawn / Respawn
                self.player.respawn(self.current_map)
        else:
            print("[Game | Error] Unkown category « " + repr(category) + " »")

    def send_enter_room(self, room_name):
        if room_name != "":
            self.player.room_name = room_name
            bytes_room_name = bytes(room_name, "utf-8")
            self.send_data("\x1B", "\x01", struct.pack("!I%ds" % len(bytes_room_name), len(bytes_room_name), bytes_room_name))

    def run(self):

        print(">>> Initialisation du jeu ...")

        pygame.display.set_caption("PyPlatform - 0.1")

        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,30"
        if sys.platform.startswith('win'):
            os.system('title PyPlatform')
        else:
            pass

        pygame.init()

        print(">>> Initialisation réseau ...")

        self.connect_to_network()

        if not self.is_connected():
            return

        print(">>> En cours d'exécution ...")

        clock = pygame.time.Clock()
        self.stopped = False

        self.send_enter_room("1")

        self.stopped = False

        while not self.stopped:
            self.send_data("\x1B", "\x02")  # Get room players data

            # Assignation des frames/sec
            pyplatform.physics.Physics.dtf = clock.tick(self.fps) / 1000

            # Récupération des événements ayant eu lieu durant cette frame
            events = pygame.event.get()

            # Récupération des touches du clavier enfoncées
            kpressed = pygame.key.get_pressed()

            # Récupération des boutons de la souris enfoncés
            mbpressed = pygame.mouse.get_pressed()

            # Récupération des boutons de souris enfoncées lors de l'événement
            mbpressedt = [False, False, False]
            mbreleasedt = [False, False, False]

            events_list = {
                "keyd": False,
                "keyu": False,
                "moused": False,
                "mouseu": False,
                "mousem": False,
                "quit": False
            }

            for event in events:
                if event.type == pygame.QUIT:  # Clique sur la croix de la fenêtre
                    events_list["quit"] = True
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:  # Enfoncement d'un bouton de souris
                    if event.button < 3:
                        events_list["moused"] = True
                        mbpressedt[event.button - 1] = True
                elif event.type == pygame.MOUSEBUTTONUP:  # Relâchement d'un bouton de souris
                    if event.button < 3:
                        events_list["mouseu"] = True
                        mbreleasedt[event.button - 1] = True
                elif event.type == pygame.MOUSEMOTION:  # Mouvement de la souris
                    events_list["mousem"] = True
                elif event.type == pygame.KEYDOWN:  # Enfoncement d'une touche du clavier
                    events_list["keyd"] = True
                elif event.type == pygame.KEYUP:  # Relâchement d'une touche du clavier
                    events_list["keyu"] = True

            if events_list["quit"]:  # Arrêt du jeu
                self.stopped = True
                break

            # Gestion des événements ayant eu lieu durant la frame

            # Enfoncement d'une touche du clavier
            if events_list["keyd"]:
                if kpressed[pygame.K_e] and not kpressed[pygame.K_LCTRL]:
                    pass

            self.screen.fill(pyplatform.miscellaneous.hex_to_tuple(self.background))

            # Affichage des sols
            if isinstance(self.current_map, pyplatform.maps.Map):
                self.maps.show_map(self.current_map, self.screen)

            if self.player.is_spawned:  # Si le joueur est spawn

                self.player.save_past_position()
                self.player.apply_physic(kpressed)
                self.player.update_position(self)

                self.physics.check_collision()
                self.player.check_holes_collision(self)
                self.player.check_checkpoints_collision(self)

                self.send_data("\x1C", "\x03", bytes(self.player))

                self.player.draw_sprite(self.screen)

            # Fin player.is_spawned

            # Affichage des joueurs
            for i, player in self.players.items():
                if player.id != self.player.id and player.is_spawned:
                    player.draw_sprite(self.screen)

            # Rafraichissement de pygame
            pygame.display.update()

        # Fin self.stop
