import pyplatform
import pygame
import socket
import os, sys
from _thread import *


class PyPlatformClientNetwork:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.could_connect = False

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        try:
            self.socket.connect((self.host, self.port))
            self.could_connect = True
        except Exception as e:
            print(e)

    def send(self, data):
        try:
            self.socket.send(str.encode(data))
        except Exception as e:
            print(e)


class Game:

    database = pyplatform.database.db.Database()

    def __init__(self):
        # Config variables
        self.size = {'w': 1366, 'h': 768}
        self.background = "717B9C"
        self.fps = 60
        self.screen = pygame.display.set_mode((self.size['w'], self.size['h']))
        self.stopped = False

        # Helpers
        self.network = PyPlatformClientNetwork("localhost", 5555)
        self.physics = pyplatform.physics.Physics(self)
        self.editor = pyplatform.editor.Editor(self)
        self.maps = pyplatform.maps.Maps(self)

        # Main variables
        self.player = pyplatform.player.PhysicPlayer()
        self.players = {}
        self.current_map = None

    def thread_receive_data(self):
        while True:
            try:
                received_data = self.network.socket.recv(1024*4).decode()
                self.received_data(received_data)
                print(received_data)
            except Exception as e:
                print("[ThreadClient | " + self.player.get_id_and_room_name() + " | Info] Lost connection (" + str(e) + ")")
                break

        print("[ThreadClient | " + self.player.get_id_and_room_name() + " | Info] Closing Game")
        self.network.socket.close()
        self.stopped = True

    def run(self):

        print(">>> Initialisation réseau ...")

        self.network.init_socket()
        self.network.connect()

        if not self.network.could_connect:
            print(">>> Connexion échouée ...")
            return

        start_new_thread(self.thread_receive_data, ())

        print(">>> Initialisation du jeu ...")

        pygame.display.set_caption("PyPlatform - 0.1")

        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,30"
        if sys.platform.startswith('win'):
            os.system('title PyPlatformNetwork')
        else:
            pass

        pygame.init()
        clock = pygame.time.Clock()

        print(">>> En cours d'exécution ...")

        self.stopped = False

        self.player.room_name = "1"
        self.send_data("enter-room 1")

        while not self.stopped:
            self.send_data("get-room-players")

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
                    # editor.toggleEditor()
                    pass

            self.screen.fill(pyplatform.miscellaneous.hex_to_list(self.background))

            # Affichage des sols
            if isinstance(self.current_map, pyplatform.maps.Map):
                self.maps.show_map(self.current_map)

            if self.player.is_spawned:  # Si le joueur est spawn

                self.player.save_past_position()
                self.player.apply_physic(kpressed)
                self.player.update_position(self)

                self.physics.check_collision()
                self.player.check_holes_collision(self)
                self.player.check_checkpoints_collision(self)

                self.send_data("update-player " + str(self.player))

                self.player.draw_sprite(self.screen)

            # Fin player.is_spawned

            # Affichage des joueurs
            for i, player in self.players.items():
                if player.id != self.player.id and player.is_spawned:
                    player.draw_sprite(self.screen)

            # Rafraichissement de pygame
            pygame.display.update()

        # Fin self.stop

    def send_data(self, raw_data):
        raw_str_data = str(raw_data)
        # print("[ThreadClient | " + self.player.get_id_and_room_name() + " | Info] Sending data: " + raw_str_data)
        self.network.socket.send(str.encode(raw_str_data))

    def received_data(self, decoded_data):
        # print("[ThreadClient | " + self.player.get_id_and_room_name() + " | Info] Data received (" + str(len(decoded_data)) + ") : " + decoded_data)
        args = decoded_data.split(" ")
        if args[0] == "set-player-id":
            self.player.id = int(args[1])
        elif args[0] == "set-room-players":
            players = decoded_data[len("set-room-players") + 1:].split("\x1E")
            for i, player in enumerate(players):
                id, x, y, color, is_spawned = player.split("\x1F")
                id = int(id)
                if id not in self.players:
                    self.players[id] = pyplatform.player.Player()
                self.players[id].id = id
                self.players[id].x = float(x)
                self.players[id].y = float(y)
                self.players[id].color = color
                self.players[id].is_spawned = (is_spawned == "True")
        elif args[0] == "set-map":
            id, author, xml, updated_at, created_at = decoded_data[len("set-map") + 1:].split("\x1F")
            self.current_map = pyplatform.maps.Map(id, author, xml, updated_at, created_at)
        elif args[0] == "spawn" or args[0] == "respawn":
            print("i want to spawn")
            self.player.respawn(self.current_map)
        elif args[0] == "player-disconnected":
            id = int(args[1])
            if id in self.players:
                del self.players[id]
        else:
            pass
            # print("data received : " + decoded_data)
