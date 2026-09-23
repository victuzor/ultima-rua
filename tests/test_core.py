import math
from pathlib import Path
import unittest

from core import Enemy, Item, Settings, World, camera_position, load_config


class SimulationTests(unittest.TestCase):
    def world(self, **settings):
        world = World(Settings(**settings), 45, 520)
        self.addCleanup(world.close)
        return world

    def clear_enemies(self, world):
        for area in world.loaded.values():
            area.enemies.clear()

    def test_activation_center_border_and_corner(self):
        world = self.world()
        self.assertEqual(world.active_keys(), {(1, 1)})
        world.y = 530
        self.assertEqual(world.active_keys(), {(1, 0), (1, 1)})
        world.x = 530
        self.assertEqual(world.active_keys(), {(0, 0), (1, 0), (0, 1), (1, 1)})

    def test_maximum_four_active_areas_throughout_world(self):
        world = self.world()
        for x in range(0, 1560, 13):
            for y in range(0, 1560, 17):
                world.x, world.y = x, y
                active = world.active_keys()
                self.assertLessEqual(len(active), 4)
                self.assertIn(world.key_at(x, y), active)

    def test_invalid_threshold_cannot_activate_opposite_neighbors(self):
        with self.assertRaises(ValueError):
            World(Settings(activation_distance=260), 45, 520)

    def test_inactive_area_is_unloaded_frozen_and_restored(self):
        world = self.world()
        area = world.loaded[(1, 1)]
        enemy = area.enemies[0]
        enemy.health = 17
        area.items.pop()
        expected = (enemy.x, enemy.y, enemy.health, len(area.items))
        enemy_id = enemy.id
        world.x = world.y = 260
        world.sync_areas()
        self.assertNotIn((1, 1), world.loaded)
        self.assertTrue(world._path((1, 1)).exists())
        for _ in range(60):
            world.update(1 / 60)
        world.x = world.y = 780
        world.sync_areas()
        restored = world.loaded[(1, 1)]
        enemy = next(e for e in restored.enemies if e.id == enemy_id)
        self.assertEqual((enemy.x, enemy.y, enemy.health, len(restored.items)), expected)

    def test_only_active_npcs_are_updated(self):
        world = self.world()
        before = [(e.x, e.y) for e in world.loaded[(1, 1)].enemies]
        world.update(1 / 60)
        self.assertEqual(world.updated_npcs, 5)
        after = [(e.x, e.y) for e in world.loaded[(1, 1)].enemies]
        self.assertNotEqual(before, after)

    def test_npc_migrates_once_without_duplicates(self):
        world = self.world()
        world.x, world.y = 530, 780
        world.sync_areas()
        self.clear_enemies(world)
        world.loaded[(0, 1)].enemies.append(Enemy(123, 519.5, 780, 55, 60))
        world.update(1 / 60)
        self.assertEqual(world.updated_npcs, 1)
        self.assertEqual(len(world.loaded[(0, 1)].enemies), 0)
        self.assertEqual(len(world.loaded[(1, 1)].enemies), 1)
        self.assertAlmostEqual(world.loaded[(1, 1)].enemies[0].x, 520.5)

    def test_contact_damage_is_proportional_to_time(self):
        world = self.world()
        self.clear_enemies(world)
        world.loaded[(1, 1)].enemies.append(Enemy(1, world.x, world.y, 55, 60))
        for _ in range(60):
            world.update(1 / 60)
        self.assertAlmostEqual(world.health, 91)

    def test_collect_then_use_health_and_ammo(self):
        world = self.world()
        self.clear_enemies(world)
        area = world.loaded[(1, 1)]
        area.items = [Item(world.x, world.y, "health"), Item(world.x, world.y, "ammo")]
        world.update(1 / 60)
        self.assertEqual((world.medkits, world.ammo, area.items), (2, 5, []))
        self.assertFalse(world.heal())
        self.assertEqual(world.medkits, 2)
        world.health = 75
        self.assertTrue(world.heal())
        self.assertEqual((world.health, world.medkits), (100, 1))

    def test_pulse_range_death_cooldown_and_consumption(self):
        world = self.world()
        area = world.loaded[(1, 1)]
        area.enemies = [Enemy(1, world.x + 100, world.y, 55, 60),
                        Enemy(2, world.x + 141, world.y, 55, 60)]
        self.assertTrue(world.pulse())
        self.assertEqual(world.kills, 1)
        self.assertEqual([e.id for e in area.enemies], [2])
        self.assertEqual(world.ammo, 2)
        self.assertFalse(world.pulse())
        self.assertEqual(world.ammo, 2)

    def test_death_stops_simulation_and_item_use(self):
        world = self.world()
        self.clear_enemies(world)
        world.health = 0.01
        world.loaded[(1, 1)].enemies.append(Enemy(1, world.x, world.y, 55, 60))
        world.update(1 / 60)
        self.assertEqual((world.status, world.health), ("dead", 0))
        elapsed = world.elapsed
        world.update(1 / 60, 1, 1)
        self.assertEqual(world.elapsed, elapsed)
        self.assertFalse(world.heal())
        self.assertFalse(world.pulse())

    def test_survival_wins_and_freezes_time(self):
        world = self.world(survival_seconds=0.1)
        self.clear_enemies(world)
        for _ in range(20):
            world.update(1 / 60)
        self.assertEqual(world.status, "won")
        self.assertAlmostEqual(world.elapsed, 0.1)

    def test_movement_normalization_and_world_bounds(self):
        world = self.world()
        self.clear_enemies(world)
        before = (world.x, world.y)
        world.update(1 / 60, 1, 1)
        self.assertAlmostEqual(math.hypot(world.x - before[0], world.y - before[1]), 215 / 60)
        world.x = world.y = 13
        world.update(1 / 60, -1, -1)
        self.assertEqual((world.x, world.y), (13, 13))

    def test_camera_is_continuous_across_grid_border(self):
        a = camera_position(519, 780, 840, 526, 1560)
        b = camera_position(521, 780, 840, 526, 1560)
        self.assertEqual(b[0] - a[0], 2)
        self.assertEqual(a[1], b[1])

    def test_seed_and_total_enemy_count(self):
        world = self.world()
        total = sum(len(world._generate((c, r)).enemies) for c in range(3) for r in range(3))
        self.assertEqual(total, 45)
        self.assertEqual(world._generate((0, 0)), world._generate((0, 0)))

    def test_load_project_configuration(self):
        settings, presets = load_config(Path(__file__).resolve().parents[1] / "config.json")
        self.assertEqual(len(presets), 3)
        self.assertEqual(settings.seed, 42)

    def test_nonfinite_settings_rejected(self):
        with self.assertRaises(ValueError):
            Settings(player_speed=float("nan"))


if __name__ == "__main__":
    unittest.main()
