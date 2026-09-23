"""Mede a simulação (sem renderização) e compara duas estratégias simples."""
from pathlib import Path
import math
import time

from core import World, load_config


def main():
    settings, presets = load_config(Path(__file__).resolve().parent / "config.json")
    print("Cenário | estratégia | resultado | tempo jogo | eliminações | máx. áreas | máx. NPCs/passo | ms/passo")
    for preset in presets:
        for strategy in ("parado", "rota + itens"):
            world = World(settings, preset["enemies"], preset["area_size"])
            max_areas = max_npcs = steps = 0
            # Uma volta no mapa, atravessando áreas e suas fronteiras.
            low, high = world.area_size / 2, world.size - world.area_size / 2
            route = [(high, low), (high, high), (low, high), (low, low)]
            waypoint = 0
            start = time.perf_counter()
            try:
                while world.status == "playing":
                    dx = dy = 0
                    if strategy != "parado":
                        tx, ty = route[waypoint]
                        dx, dy = tx - world.x, ty - world.y
                        if math.hypot(dx, dy) < 12:
                            waypoint = (waypoint + 1) % len(route)
                        if world.health <= 60:
                            world.heal()
                        if any(math.hypot(e.x - world.x, e.y - world.y) < 65 for a in world.loaded.values() for e in a.enemies):
                            world.pulse()
                    world.update(1 / 60, dx, dy)
                    steps += 1
                    max_areas = max(max_areas, len(world.loaded))
                    max_npcs = max(max_npcs, world.updated_npcs)
                ms = (time.perf_counter() - start) * 1000 / steps
                print(f"{preset['name']} ({preset['enemies']}) | {strategy} | {world.status} | {world.elapsed:.1f}s | {world.kills} | {max_areas} | {max_npcs} | {ms:.3f}")
            finally:
                world.close()


if __name__ == "__main__":
    main()
