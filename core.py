"""Simulação independente do Pygame; coordenadas sempre relativas ao mundo."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import random
import tempfile
import zlib


@dataclass(frozen=True)
class Settings:
    seed: int = 42
    survival_seconds: float = 75
    player_speed: float = 215
    player_health: float = 100
    enemy_health: float = 55
    enemy_damage_per_second: float = 9
    enemy_speed_min: float = 38
    enemy_speed_max: float = 68
    activation_distance: float = 150
    pulse_radius: float = 140
    pulse_damage: float = 60
    pulse_cooldown: float = 0.45
    heal_amount: float = 40
    health_items_per_area: int = 3
    ammo_items_per_area: int = 4
    ammo_per_item: int = 2

    def __post_init__(self):
        integer_fields = {"seed", "health_items_per_area", "ammo_items_per_area", "ammo_per_item"}
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Configuração inválida: {name} deve ser um número finito.")
            if name in integer_fields and not isinstance(value, int):
                raise ValueError(f"Configuração inválida: {name} deve ser inteiro.")
            if name != "seed" and value <= 0:
                raise ValueError(f"Configuração inválida: {name} deve ser positivo.")
        if self.enemy_speed_min > self.enemy_speed_max:
            raise ValueError("enemy_speed_min deve ser menor ou igual a enemy_speed_max.")
        if self.pulse_radius > self.activation_distance:
            raise ValueError("pulse_radius deve ser menor ou igual a activation_distance.")


def load_config(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    presets = raw.pop("presets")
    settings = Settings(**raw)
    if not isinstance(presets, list) or not presets:
        raise ValueError("Informe pelo menos um cenário em presets.")
    for preset in presets:
        if not isinstance(preset.get("name"), str) or not preset["name"].strip():
            raise ValueError("Cada cenário precisa de um nome.")
        validate_scenario(settings, preset["enemies"], preset["area_size"])
    return settings, presets


def validate_scenario(settings, enemies, area_size):
    if isinstance(enemies, bool) or not isinstance(enemies, int) or not 1 <= enemies <= 100_000:
        raise ValueError("O número de inimigos deve ser um inteiro entre 1 e 100000.")
    if isinstance(area_size, bool) or not isinstance(area_size, (int, float)) or not math.isfinite(area_size):
        raise ValueError("O tamanho da área deve ser um número finito.")
    if area_size < 360 or settings.activation_distance >= area_size / 2:
        raise ValueError("area_size deve ser >= 360 e activation_distance menor que metade da área.")


@dataclass
class Enemy:
    id: int
    x: float
    y: float
    health: float
    speed: float
    radius: float = 11


@dataclass
class Item:
    x: float
    y: float
    kind: str


@dataclass
class Area:
    key: tuple[int, int]
    enemies: list[Enemy]
    items: list[Item]


class World:
    """No máximo quatro áreas desserializadas; demais estados ficam em disco."""
    def __init__(self, settings: Settings, enemy_count: int, area_size: float):
        validate_scenario(settings, enemy_count, area_size)
        self.settings = settings
        self.enemy_count = enemy_count
        self.area_size = area_size
        self.size = area_size * 3
        self.x = self.y = self.size / 2
        self.radius = 13
        self.health = settings.player_health
        self.medkits = 1
        self.ammo = 3
        self.elapsed = 0.0
        self.cooldown = 0.0
        self.kills = 0
        self.updated_npcs = 0
        self.status = "playing"
        self.loaded: dict[tuple[int, int], Area] = {}
        self._cache = tempfile.TemporaryDirectory(prefix="setor9-")
        self.sync_areas()

    def close(self):
        self._cache.cleanup()

    def key_at(self, x, y):
        return (max(0, min(2, int(x // self.area_size))), max(0, min(2, int(y // self.area_size))))

    def active_keys(self):
        col, row = self.key_at(self.x, self.y)
        local_x, local_y = self.x - col * self.area_size, self.y - row * self.area_size
        distance = self.settings.activation_distance
        cols, rows = [col], [row]
        if local_x <= distance and col > 0:
            cols.append(col - 1)
        elif local_x >= self.area_size - distance and col < 2:
            cols.append(col + 1)
        if local_y <= distance and row > 0:
            rows.append(row - 1)
        elif local_y >= self.area_size - distance and row < 2:
            rows.append(row + 1)
        return {(c, r) for c in cols for r in rows}

    def _path(self, key):
        return Path(self._cache.name) / f"{key[0]}-{key[1]}.json.zlib"

    def _generate(self, key):
        col, row = key
        index = row * 3 + col
        rng = random.Random(self.settings.seed + index * 10007)
        count = self.enemy_count // 9 + (index < self.enemy_count % 9)
        enemies = []
        for i in range(count):
            while True:
                x = col * self.area_size + rng.uniform(22, self.area_size - 22)
                y = row * self.area_size + rng.uniform(22, self.area_size - 22)
                if math.hypot(x - self.size / 2, y - self.size / 2) >= 145:
                    break
            enemies.append(Enemy(index * 100_000 + i, x, y, self.settings.enemy_health,
                                 rng.uniform(self.settings.enemy_speed_min, self.settings.enemy_speed_max)))
        items = []
        for kind, amount in (("health", self.settings.health_items_per_area), ("ammo", self.settings.ammo_items_per_area)):
            for _ in range(amount):
                items.append(Item(col * self.area_size + rng.uniform(35, self.area_size - 35),
                                  row * self.area_size + rng.uniform(35, self.area_size - 35), kind))
        return Area(key, enemies, items)

    def sync_areas(self):
        active = self.active_keys()
        for key in sorted(set(self.loaded) - active):
            area = self.loaded.pop(key)
            data = {"enemies": [asdict(e) for e in area.enemies], "items": [asdict(i) for i in area.items]}
            self._path(key).write_bytes(zlib.compress(json.dumps(data).encode("utf-8")))
        for key in sorted(active - set(self.loaded)):
            path = self._path(key)
            if path.exists():
                data = json.loads(zlib.decompress(path.read_bytes()))
                self.loaded[key] = Area(key, [Enemy(**e) for e in data["enemies"]], [Item(**i) for i in data["items"]])
            else:
                self.loaded[key] = self._generate(key)

    def heal(self):
        if self.status != "playing" or self.medkits <= 0 or self.health >= self.settings.player_health:
            return False
        self.medkits -= 1
        self.health = min(self.settings.player_health, self.health + self.settings.heal_amount)
        return True

    def pulse(self):
        if self.status != "playing" or self.ammo <= 0 or self.cooldown > 0:
            return False
        self.ammo -= 1
        self.cooldown = self.settings.pulse_cooldown
        for area in self.loaded.values():
            survivors = []
            for enemy in area.enemies:
                if math.hypot(enemy.x - self.x, enemy.y - self.y) <= self.settings.pulse_radius:
                    enemy.health -= self.settings.pulse_damage
                if enemy.health > 0:
                    survivors.append(enemy)
                else:
                    self.kills += 1
            area.enemies = survivors
        return True

    def update(self, dt, move_x=0, move_y=0):
        if self.status != "playing" or dt <= 0:
            return
        # O chamador usa passo fixo; o limite também impede saltos entre áreas.
        dt = min(dt, 1 / 30, self.settings.survival_seconds - self.elapsed)
        length = math.hypot(move_x, move_y)
        if length:
            self.x = max(self.radius, min(self.size - self.radius, self.x + move_x / length * self.settings.player_speed * dt))
            self.y = max(self.radius, min(self.size - self.radius, self.y + move_y / length * self.settings.player_speed * dt))
        self.sync_areas()
        self.cooldown = max(0, self.cooldown - dt)
        self.elapsed += dt
        self.updated_npcs = 0
        migrations = []
        contacts = 0
        for key, area in self.loaded.items():
            remaining = []
            for enemy in area.enemies:
                self.updated_npcs += 1
                dx, dy = self.x - enemy.x, self.y - enemy.y
                distance = math.hypot(dx, dy)
                if distance:
                    step = min(distance, enemy.speed * dt)
                    enemy.x += dx / distance * step
                    enemy.y += dy / distance * step
                if math.hypot(self.x - enemy.x, self.y - enemy.y) < self.radius + enemy.radius:
                    contacts += 1
                new_key = self.key_at(enemy.x, enemy.y)
                if new_key != key:
                    migrations.append((new_key, enemy))
                else:
                    remaining.append(enemy)
            area.enemies = remaining
            kept_items = []
            for item in area.items:
                if math.hypot(self.x - item.x, self.y - item.y) <= self.radius + 12:
                    if item.kind == "health":
                        self.medkits += 1
                    else:
                        self.ammo += self.settings.ammo_per_item
                else:
                    kept_items.append(item)
            area.items = kept_items
        for key, enemy in migrations:
            self.loaded[key].enemies.append(enemy)
        self.health = max(0, self.health - contacts * self.settings.enemy_damage_per_second * dt)
        if self.health <= 0:
            self.status = "dead"
        elif self.elapsed >= self.settings.survival_seconds:
            self.status = "won"


def camera_position(player_x, player_y, width, height, world_size):
    """A câmera acompanha posições contínuas, sem encaixar nas células."""
    return (max(0, min(world_size - width, player_x - width / 2)) if width < world_size else (world_size - width) / 2,
            max(0, min(world_size - height, player_y - height / 2)) if height < world_size else (world_size - height) / 2)
