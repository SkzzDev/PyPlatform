import struct

import pygame.draw
from pyplatform import json, grounds, miscellaneous
from pyplatform.database.db import Database


class Maps:

    def get_map(self, code):
        if isinstance(code, int) and code > 0:
            sql = "SELECT * FROM `maps` WHERE `id` = %s;"
            mapdb = Database.wake_up().select(sql, (code,))[0]
            if mapdb is not None:
                return Map(mapdb["id"], mapdb["author"], mapdb["xml"], mapdb["updated_at"], mapdb["created_at"])
        return None

    def get_random_map(self):
        sql = "SELECT * FROM `maps` ORDER BY RAND() LIMIT 0, 1;"
        mapdb = Database.wake_up().select(sql)[0]
        if mapdb is not None:
            return Map(mapdb["id"], mapdb["author"], mapdb["xml"], mapdb["updated_at"], mapdb["created_at"])
        return None

    def show_map(self, map, screen):
        self.show_map_grounds(map, screen)
        self.show_map_holes(map, screen)
        self.show_map_checkpoints(map, screen)

    def show_map_grounds(self, map, screen):
        map.grounds.show(screen)

    def show_map_holes(self, map, screen):
        for hole in map.holes:
            pygame.draw.rect(screen, miscellaneous.hex_to_tuple(hole.color), hole.rect)

    def show_map_checkpoints(self, map, screen):
        for checkpoint in map.checkpoints:
            color = checkpoint.color
            pygame.draw.rect(screen, miscellaneous.hex_to_tuple(color), checkpoint.rect)


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
        pygame.draw.rect(screen, miscellaneous.hex_to_tuple(Spawn.properties["color"]), (self.spawn['x'], self.spawn['y'], Spawn.properties["height"], Spawn.properties["width"]))

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

    def __bytes__(self):
        bytes_author = bytes(self.author, "utf-8")
        bytes_xml = bytes(self.xml, "utf-8")
        return struct.pack("!II%dsI%dsII" % (len(bytes_author), len(bytes_xml)), self.id, len(bytes_author), bytes_author, len(bytes_xml), bytes_xml, self.updated_at, self.created_at)


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
