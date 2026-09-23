"""Arte procedural do bairro: texturas e sprites pequenos, reutilizados por frame."""
from __future__ import annotations

import math
import random

import pygame as pg

PAPER = (217, 209, 180)
INK = (35, 37, 32)
MUTED = (157, 159, 139)
RUST = (174, 66, 44)
GOLD = (210, 171, 92)


class StreetArt:
    def __init__(self, size):
        self.size = size
        self.tiles = [self._tile(seed) for seed in range(4)]
        # Pré-calcular direções evita rotacionar centenas de sprites a cada frame.
        self.zombies = {}
        for variant in range(5):
            for frame in range(4):
                sprite = self._person(variant, frame)
                for direction in range(16):
                    self.zombies[variant, frame, direction] = pg.transform.rotate(sprite, -direction * 22.5)
        self.survivors = {}
        for frame in range(4):
            for direction in range(16):
                self.survivors[frame, direction] = pg.transform.rotate(self._person(-1, frame), -direction * 22.5)
        self.medkit = self._item(True)
        self.ammo = self._item(False)
        self.vignette = pg.Surface(size, pg.SRCALPHA)
        # Uma vinheta fixa: sem criar superfícies de tela inteira por frame.
        for inset in range(0, 130, 5):
            pg.draw.rect(self.vignette, (10, 13, 11, int(65 * (1 - inset / 130) ** 2)),
                         self.vignette.get_rect().inflate(-inset * 2, -inset * 2), 5)
        self.fog = pg.Surface(size, pg.SRCALPHA)
        self.light = pg.Surface((400, 400), pg.SRCALPHA)
        for radius in range(195, 10, -8):
            pg.draw.circle(self.light, (202, 175, 108, 2), (200, 200), radius)
        pg.draw.polygon(self.light, (216, 202, 143, 12), [(200, 200), (355, 146), (375, 200), (355, 254)])
        self.lights = [pg.transform.rotate(self.light, -d * 22.5) for d in range(16)]
        self.lettering = pg.font.SysFont("bahnschrift", 42, bold=True).render("EVACUAR", True, (102, 103, 83))
        self.small = pg.font.SysFont("consolas", 12)
        self.shadow = pg.Surface((46, 26), pg.SRCALPHA)
        pg.draw.ellipse(self.shadow, (5, 8, 6, 100), (0, 0, 46, 26))

    @staticmethod
    def _tile(seed):
        rng = random.Random(903 + seed)
        tile = pg.Surface((128, 128))
        tile.fill((51, 55, 51))
        for _ in range(2100):
            shade = rng.randrange(43, 63)
            tile.set_at((rng.randrange(128), rng.randrange(128)), (shade, shade + 3, shade))
        for _ in range(5):
            x, y = rng.randrange(128), rng.randrange(128)
            points = [(x, y)]
            for _ in range(rng.randrange(3, 7)):
                x += rng.randrange(-10, 11)
                y += rng.randrange(3, 13)
                points.append((x, y))
            pg.draw.lines(tile, (32, 37, 33), False, points, 1)
        for _ in range(5):
            x, y = rng.randrange(128), rng.randrange(128)
            pg.draw.line(tile, (92, 92, 75), (x, y), (x + 2, y), 1)
        return pg.transform.scale(tile, (256, 256)).convert()

    @staticmethod
    def _person(variant, frame):
        """Silhueta voltada à direita, com roupas e passada próprias."""
        sprite = pg.Surface((24, 24), pg.SRCALPHA)
        player = variant == -1
        coat = (185, 144, 74) if player else [(94, 105, 73), (113, 76, 62), (67, 90, 99),
                                                             (121, 114, 89), (77, 77, 67)][variant]
        skin = (200, 170, 123) if player else (139 + variant * 5, 150 + variant * 3, 107 + variant * 3)
        dark = (24, 28, 24)
        step = (0, 1, 0, -1)[frame]
        # Pernas separadas e passada alternada; braços estendidos nos zumbis.
        pg.draw.rect(sprite, dark, (5 + step, 6, 8, 4))
        pg.draw.rect(sprite, dark, (5 - step, 14, 8, 4))
        pg.draw.rect(sprite, (61, 65, 55), (7 + step, 7, 6, 2))
        pg.draw.rect(sprite, (61, 65, 55), (7 - step, 15, 6, 2))
        pg.draw.rect(sprite, dark, (8, 5, 8, 14))
        pg.draw.rect(sprite, coat, (9, 6, 6, 12))
        pg.draw.rect(sprite, tuple(max(0, c - 23) for c in coat), (9, 13, 3, 4))
        pg.draw.rect(sprite, coat, (13, 4 + step, 5, 3))
        pg.draw.rect(sprite, coat, (13, 17 - step, 5, 3))
        pg.draw.rect(sprite, skin, (17, 4 + step, 4, 2))
        pg.draw.rect(sprite, skin, (17, 18 - step, 4, 2))
        pg.draw.rect(sprite, dark, (13, 8, 7, 8))
        pg.draw.rect(sprite, skin, (14, 9, 6, 6))
        pg.draw.rect(sprite, (66, 64, 48), (13, 8, 4, 7))
        if player:
            pg.draw.rect(sprite, (59, 74, 58), (7, 8, 4, 8))  # mochila
            pg.draw.line(sprite, (117, 128, 92), (8, 9), (8, 14))
            pg.draw.rect(sprite, (190, 183, 146), (20, 17, 3, 3))  # lanterna
        else:
            pg.draw.rect(sprite, (101, 44, 33), (13, 14, 3, 3))
            pg.draw.rect(sprite, (53, 51, 37), (19, 10, 1, 2))
            pg.draw.rect(sprite, (78, 39, 30), (19, 13, 2, 2))
        return pg.transform.scale(sprite, (40, 40))

    @staticmethod
    def _item(health):
        sprite = pg.Surface((18, 18), pg.SRCALPHA)
        pg.draw.rect(sprite, (18, 22, 18), (2, 5, 15, 12))
        if health:
            pg.draw.rect(sprite, (156, 153, 123), (5, 2, 7, 4), 1)
            pg.draw.rect(sprite, (204, 196, 167), (2, 5, 13, 9))
            pg.draw.rect(sprite, (151, 52, 37), (7, 6, 3, 7))
            pg.draw.rect(sprite, (151, 52, 37), (5, 8, 7, 3))
        else:
            pg.draw.rect(sprite, (110, 118, 73), (2, 4, 13, 10))
            pg.draw.line(sprite, (165, 158, 107), (3, 5), (14, 5))
            for x in (5, 8, 11):
                pg.draw.rect(sprite, (218, 178, 91), (x, 8, 2, 4))
        return pg.transform.scale(sprite, (30, 30))

    @staticmethod
    def direction(dx, dy):
        return round(math.atan2(dy, dx) / math.tau * 16) % 16

    def ground(self, surface, world, camera):
        cx, cy = camera
        w, h = self.size
        surface.fill((24, 29, 24))
        old_clip = surface.get_clip()
        surface.set_clip(old_clip.clip(pg.Rect(round(-cx), round(-cy), math.ceil(world.size), math.ceil(world.size))))
        for tx in range(math.floor(cx / 256), math.ceil((cx + w) / 256)):
            for ty in range(math.floor(cy / 256), math.ceil((cy + h) / 256)):
                surface.blit(self.tiles[(tx * 7 + ty * 13) % 4], (round(tx * 256 - cx), round(ty * 256 - cy)))
        # Faixas e calçadas baixas são marcas no piso, não obstáculos físicos.
        for row in range(3):
            middle = (row + 0.5) * world.area_size - cy
            for side in (-1, 1):
                y = round(middle + side * 145)
                pg.draw.rect(surface, (65, 67, 58), (-cx, y, world.size, 30))
                pg.draw.line(surface, (93, 92, 74), (0, y), (w, y), 2)
                pg.draw.line(surface, (31, 36, 31), (0, y + 30), (w, y + 30), 3)
                for x in range(math.floor(cx / 64) * 64, math.ceil((cx + w) / 64) * 64, 64):
                    pg.draw.line(surface, (45, 49, 43), (round(x - cx), y), (round(x - cx), y + 30))
            for x in range(math.floor(cx / 120) * 120, math.ceil((cx + w) / 120) * 120, 120):
                pg.draw.rect(surface, (140, 128, 79), (round(x - cx), round(middle - 3), 49, 3))
                pg.draw.rect(surface, (122, 114, 75), (round(x - cx), round(middle + 4), 49, 2))
            for col in range(3):
                center = (col + 0.5) * world.area_size - cx
                # Faixa de pedestres, ralo, poças e vestígios da evacuação.
                for dy in range(-108, 119, 32):
                    pg.draw.rect(surface, (127, 129, 110), (round(center + 170), round(middle + dy), 48, 13))
                    pg.draw.line(surface, (67, 71, 61), (round(center + 185), round(middle + dy)),
                                 (round(center + 208), round(middle + dy + 9)), 3)
                grate = pg.Rect(round(center - 173), round(middle + 118), 42, 19)
                pg.draw.rect(surface, (26, 31, 28), grate)
                for offset in range(4, 40, 6):
                    pg.draw.line(surface, (77, 79, 65), (grate.x + offset, grate.y + 2), (grate.x + offset, grate.bottom - 3), 2)
                pg.draw.ellipse(surface, (39, 43, 39), (center + 45, middle - 96, 94, 35))
                pg.draw.arc(surface, (68, 72, 62), (center + 45, middle - 96, 94, 35), 0.1, 2.2, 1)
                pg.draw.ellipse(surface, (65, 43, 34), (center - 120, middle - 40, 48, 24))
                for i in range(5):
                    pg.draw.circle(surface, (66, 43, 34), (round(center - 80 + i * 9), round(middle - 26 + i * 3)), 3 - i % 3)
                surface.blit(self.lettering, (round(center - 105), round(middle - 265)))
                pg.draw.polygon(surface, (113, 113, 89), [(center + 77, middle - 238), (center + 96, middle - 238),
                                                                      (center + 96, middle - 246), (center + 112, middle - 233),
                                                                      (center + 96, middle - 221), (center + 96, middle - 229), (center + 77, middle - 229)])
        surface.set_clip(old_clip)
        self.fog.fill((17, 23, 20, 135))
        active_rects = [pg.Rect(round(col * world.area_size - cx), round(row * world.area_size - cy),
                               math.ceil(world.area_size), math.ceil(world.area_size)) for col, row in world.loaded]
        for rect in active_rects:
            for margin in range(96, 0, -8):
                pg.draw.rect(self.fog, (17, 23, 20, round(135 * margin / 96)),
                             rect.inflate(margin * 2, margin * 2), border_radius=margin)
        for rect in active_rects:
            pg.draw.rect(self.fog, (0, 0, 0, 0), rect)
        surface.blit(self.fog, (0, 0))

    def draw(self, surface, world, camera, facing, moving, effects, stains, debug):
        cx, cy = camera
        self.ground(surface, world, camera)
        for x, y, variant in stains:
            px, py = round(x - cx), round(y - cy)
            if surface.get_rect().inflate(70, 70).collidepoint(px, py):
                pg.draw.ellipse(surface, (69, 40, 30), (px - 18, py - 9, 36, 19))
                pg.draw.line(surface, (47, 46, 36), (px - 10, py - 3), (px + 10, py + 6), 9)
                pg.draw.rect(surface, (100, 106, 72), (px + 8, py + 2, 7, 6))
        for area in world.loaded.values():
            for item in area.items:
                px, py = round(item.x - cx), round(item.y - cy)
                if surface.get_rect().inflate(40, 40).collidepoint(px, py):
                    sprite = self.medkit if item.kind == "health" else self.ammo
                    surface.blit(sprite, (px - 15, py - 15))
        visible = 0
        for area in world.loaded.values():
            for enemy in area.enemies:
                px, py = round(enemy.x - cx), round(enemy.y - cy)
                if not surface.get_rect().inflate(60, 60).collidepoint(px, py):
                    continue
                visible += 1
                frame = int(world.elapsed * (4 + enemy.speed / 30) + enemy.id) % 4
                direction = self.direction(world.x - enemy.x, world.y - enemy.y)
                sprite = self.zombies[enemy.id % 5, frame, direction]
                surface.blit(self.shadow, (px - 19, py - 6))
                surface.blit(sprite, sprite.get_rect(center=(px, py)))
                if enemy.health < world.settings.enemy_health:
                    pg.draw.rect(surface, RUST, (px - 10, py - 23, round(20 * enemy.health / world.settings.enemy_health), 2))
        px, py = round(world.x - cx), round(world.y - cy)
        light = self.lights[facing]
        surface.blit(light, light.get_rect(center=(px, py)))
        frame = int(world.elapsed * 12) % 4 if moving else 0
        sprite = self.survivors[frame, facing]
        surface.blit(self.shadow, (px - 19, py - 6))
        surface.blit(sprite, sprite.get_rect(center=(px, py)))
        for ex, ey, age in effects:
            x, y = round(ex - cx), round(ey - cy)
            radius = world.settings.pulse_radius * min(1, age / 0.13)
            for i in range(28):
                angle = i * math.tau / 28
                distance = radius * (0.5 + (i % 4) * 0.16)
                point = (round(x + math.cos(angle) * distance), round(y + math.sin(angle) * distance))
                pg.draw.circle(surface, GOLD if age < 0.12 else (124, 110, 77), point, max(1, round(7 * (1 - age / 0.4))))
            if age < 0.10:
                pg.draw.circle(surface, (240, 215, 151), (x, y), max(1, round(30 * (1 - age / 0.10))))
        surface.blit(self.vignette, (0, 0))
        if debug:
            for row in range(3):
                for col in range(3):
                    rect = pg.Rect(round(col * world.area_size - cx), round(row * world.area_size - cy),
                                   math.ceil(world.area_size), math.ceil(world.area_size))
                    color = (154, 168, 112) if (col, row) in world.loaded else (76, 83, 69)
                    pg.draw.rect(surface, color, rect, 1)
                    pg.draw.rect(surface, color, rect.inflate(-2 * world.settings.activation_distance, -2 * world.settings.activation_distance), 1)
                    surface.blit(self.small.render(f"SETOR {row * 3 + col + 1:02}", True, color), (rect.x + 8, rect.y + 8))
        return visible
