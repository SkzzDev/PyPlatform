import pygame.draw
from pyplatform import json, grounds, miscellaneous
import game
# import time


class Maps:

    def __init__(self, game = None):
        self.game = game

    def get_map(self, code):
        if isinstance(code, int) and code > 0:
            sql = "SELECT * FROM `maps` WHERE `id` = %s;"
            mapdb = game.Game.database.select(sql, (code,))[0]
            if mapdb is not None:
                return Map(mapdb["id"], mapdb["author"], mapdb["xml"], mapdb["updated_at"], mapdb["created_at"])
        return None

    def get_random_map(self):
        sql = "SELECT * FROM `maps` ORDER BY RAND() LIMIT 0, 1;"
        mapdb = game.Game.database.select(sql)[0]
        if mapdb is not None:
            return Map(mapdb["id"], mapdb["author"], mapdb["xml"], mapdb["updated_at"], mapdb["created_at"])
        return None

    '''
    def addMap(self, author, mapData):
        if isinstance(author, str) and isinstance(mapData, str):
            timestamp = time.time()
            sql = "INSERT INTO `maps` (author, map, updated_at, created_at) VALUES (%s, %s, %s, %s);"
            values = (author, mapData, timestamp, timestamp)
            self.game.database.insert(sql, values)
            self.game.database.commit()
            print("Une nouvelle map a été ajoutée !")

    def nextMap(self):
        if self.game.editor.isOpened:
            self.reloadCheckpoints()
            if self.game.player.can_spawn:
                self.game.player.respawn()
        else:
            self.loadMap(self.getRandomMap())
    '''

    def show_map(self, map):
        self.show_map_grounds(map)
        self.show_map_holes(map)
        self.show_map_checkpoints(map)

    def show_map_grounds(self, map):
        map.grounds.show(self.game.screen)

    def show_map_holes(self, map):
        for hole in map.holes:
            pygame.draw.rect(self.game.screen, miscellaneous.hex_to_list(hole.color), hole.rect)

    def show_map_checkpoints(self, map):
        for checkpoint in map.checkpoints:
            color = checkpoint.color
            if self.game.editor.isOpened and checkpoint.state:
                color = "ACFA58"
            if not checkpoint.state or self.game.editor.isOpened:
                pygame.draw.rect(self.game.screen, miscellaneous.hex_to_list(color), checkpoint.rect)

    '''
    def resetCurrentMap(self):
        self.currentMap = Map(self.game)

    def reloadCheckpoints(self):
        for checkpoint in self.currentMap.checkpoints:
            if checkpoint.state == True:
                self.currentMap.checkpointsLeft += 1
            checkpoint.state = False
    '''


class Map:
    def __init__(self, id = -1, author = "", xml = "", updated_at = 0, created_at = 0):
        self.id = id
        self.author = author
        self.xml = xml
        self.grounds = grounds.Grounds()
        self.spawn = {'x': 678, 'y': 379}
        self.holes = []
        self.checkpoints = []
        self.checkpointsLeft = 0
        self.updated_at = updated_at
        self.created_at = created_at

        if xml != "":
            objXml = json.json2obj(xml)
            self.load_grounds(objXml.grounds)
            self.load_data(objXml.data.spawn, objXml.data.holes, objXml.data.checkpoints)

    def load_grounds(self, ground_list):
        for ground in ground_list:
            self.grounds.add_ground([ground.x, ground.y, ground.w, ground.h], ground.type)

    def load_data(self, spawn, holes, checkpoints):
        self.spawn = {'x': spawn.x, 'y': spawn.y}
        for hole in holes:
            self.add_hole(hole.x, hole.y)
        for checkpoint in checkpoints:
            self.add_checkpoint(checkpoint.x, checkpoint.y)

    def show_spawn(self, screen):
        pygame.draw.rect(screen, miscellaneous.hex_to_list(Spawn.properties["color"]), (self.spawn['x'], self.spawn['y'], Spawn.properties["height"], Spawn.properties["width"]))

    def move_spawn(self, x, y):
        self.spawn["x"], self.spawn["y"] = x, y

    def add_hole(self, x, y):
        self.holes.append(Hole(x, y))

    def add_checkpoint(self, x, y):
        self.checkpoints.append(Checkpoint(x, y))
        self.checkpointsLeft += 1

    def delete_element(self, x, y):
        found = False
        if self.holes:
            for hole in reversed(self.holes):
                if hole.rect.x <= x <= hole.rect.x + hole.rect.w:
                    if hole.rect.y <= y <= hole.rect.y + hole.rect.h:
                        self.holes.remove(hole)
                        found = True
                        break
        if not found:
            if self.checkpoints:
                for checkpoint in reversed(self.checkpoints):
                    if checkpoint.rect.x <= x <= checkpoint.rect.x + checkpoint.rect.w:
                        if checkpoint.rect.y <= y <= checkpoint.rect.y + checkpoint.rect.h:
                            if not checkpoint.state:
                                self.checkpointsLeft -= 1
                            self.checkpoints.remove(checkpoint)
                            found = True
                            break
            if not found:
                if self.grounds.ground_list:
                    for ground in reversed(self.grounds.ground_list):
                        if ground.rect.x <= x <= ground.rect.x + ground.rect.w:
                            if ground.rect.y <= y <= ground.rect.y + ground.rect.h:
                                self.grounds.ground_list.remove(ground)
                                break

    def __str__(self):
        return str(self.id) + "\x1F" + str(self.author) + "\x1F" + str(self.xml) + "\x1F" + str(self.updated_at) + "\x1F" + str(self.created_at)


class Spawn:

    properties = {
        "width": 10,
        "height": 10,
        "color": "FF0000"
    }


class Hole:

    properties = {
        "width": 10,
        "height": 10,
        "color": "000000"
    }

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, Hole.properties["height"], Hole.properties["width"])
        self.color = Hole.properties["color"]


class Checkpoint:

    properties = {
        "width": 10,
        "height": 10,
        "color": "6834D6"
    }

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, Checkpoint.properties["height"], Checkpoint.properties["width"])
        self.color = Checkpoint.properties["color"]
        self.state = False
