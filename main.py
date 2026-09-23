"""ÚLTIMA RUA — sobrevivência em um bairro tomado por zumbis."""
from __future__ import annotations

import argparse
from collections import deque
import math
import os
from pathlib import Path

from core import World, camera_position, load_config

BASE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1180, 760


def main():
    parser = argparse.ArgumentParser(description="ÚLTIMA RUA · Sobreviva à horda")
    parser.add_argument("--config", type=Path, default=BASE / "config.json")
    parser.add_argument("--preset", type=int, default=1, help="Cenário inicial, começando em 1")
    parser.add_argument("--smoke-test", action="store_true", help="Testa a renderização sem abrir janela")
    parser.add_argument("--screenshot", type=Path, help="Salva um frame e encerra")
    parser.add_argument("--screen", choices=("playing", "menu", "paused", "won", "dead"), default="playing")
    parser.add_argument("--preview-seconds", type=float, default=0, help="Avança a simulação antes da captura (0 a 30 s)")
    args = parser.parse_args()
    try:
        settings, presets = load_config(args.config)
        if not 1 <= args.preset <= len(presets):
            raise ValueError("--preset fora do intervalo disponível.")
        if not math.isfinite(args.preview_seconds) or not 0 <= args.preview_seconds <= 30:
            raise ValueError("--preview-seconds deve estar entre 0 e 30.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Erro de configuração: {exc}\n")

    if args.smoke_test or args.screenshot:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame as pg
    from visuals import StreetArt, PAPER, INK, MUTED, RUST, GOLD
    from sound import Sounds

    pg.init()
    window = pg.display.set_mode((WIDTH, HEIGHT), pg.RESIZABLE)
    pg.display.set_caption("ÚLTIMA RUA | Sobreviva à horda")
    canvas = pg.Surface((WIDTH, HEIGHT))
    clock = pg.time.Clock()
    fonts = {s: pg.font.SysFont("consolas", s) for s in (12, 14, 16, 18, 22, 28, 36)}
    bold = {s: pg.font.SysFont("bahnschrift", s, bold=True) for s in (14, 16, 18, 22, 28, 36, 52)}
    title_font = pg.font.SysFont("impact", 98)
    titles = [title_font.render(line, True, PAPER) for line in ("ÚLTIMA", "RUA")]
    # Desgaste discreto nas letras, desenhado uma única vez.
    for title in titles:
        for x in range(7, title.get_width(), 19):
            pg.draw.line(title, INK, (x, 21 + x % 59), (x + 3, 21 + x % 59), 1)
    viewport = pg.Rect(0, 0, WIDTH, HEIGHT - 88)
    art = StreetArt(viewport.size)
    sounds = Sounds()
    veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    selected = args.preset - 1
    world = None
    mode = "menu"
    grid = False
    effects = []
    stains = deque(maxlen=160)
    accumulator = 0.0
    facing = 0
    moving = False
    buttons = []
    running = True
    frames = 0

    def text(message, x, y, size=16, color=PAPER, heavy=False, target=None):
        surface = target if target is not None else canvas
        surface.blit((bold if heavy else fonts)[size].render(str(message), True, color), (round(x), round(y)))

    def button(label, rect, name, primary=False):
        pg.draw.rect(canvas, PAPER if primary else INK, rect)
        pg.draw.rect(canvas, PAPER if primary else (98, 101, 85), rect, 1)
        text(label, rect.x + 18, rect.y + 15, 18, INK if primary else PAPER, True)
        text(">", rect.right - 32, rect.y + 15, 18, INK if primary else PAPER)
        buttons.append((rect, name))

    def reset(start=False):
        nonlocal world, mode, accumulator, facing, moving
        if world:
            world.close()
        preset = presets[selected]
        world = World(settings, preset["enemies"], preset["area_size"])
        mode = "playing" if start else "menu"
        effects.clear()
        stains.clear()
        accumulator = 0
        facing, moving = 0, False

    def action(name):
        nonlocal mode, selected, running, accumulator
        if name.startswith("preset:"):
            selected = int(name.split(":")[1])
            reset()
        elif name in ("start", "restart"):
            reset(True)
        elif name == "resume":
            mode = "playing"
            accumulator = 0
        elif name == "menu":
            reset()
        elif name == "quit":
            running = False

    def use_grenade():
        targets = [(enemy.id, enemy.x, enemy.y) for area in world.loaded.values() for enemy in area.enemies
                   if math.hypot(enemy.x - world.x, enemy.y - world.y) <= settings.pulse_radius
                   and enemy.health <= settings.pulse_damage]
        if world.pulse():
            sounds.play("blast")
            effects.append([world.x, world.y, 0.0])
            for enemy_id, x, y in targets:
                stains.append((x, y, enemy_id % 5))

    def draw_map(camera):
        # Mapa de papel: mantém as nove áreas legíveis, sem painel lateral.
        rect = pg.Rect(WIDTH - 212, 28, 184, 196)
        pg.draw.rect(canvas, (17, 21, 17), rect.move(5, 6))
        pg.draw.rect(canvas, (183, 181, 148), rect)
        text("BAIRRO / 09", rect.x + 13, rect.y + 12, 14, INK, True)
        map_rect = pg.Rect(rect.x + 15, rect.y + 37, 154, 125)
        current = world.key_at(world.x, world.y)
        for row in range(3):
            for col in range(3):
                cell = pg.Rect(map_rect.x + col * map_rect.w // 3, map_rect.y + row * map_rect.h // 3,
                               map_rect.w // 3 - 2, map_rect.h // 3 - 2)
                active = (col, row) in world.loaded
                pg.draw.rect(canvas, (126, 139, 99) if active else (155, 156, 128), cell)
                pg.draw.rect(canvas, (80, 86, 66), cell, 1)
                if current == (col, row):
                    pg.draw.rect(canvas, INK, cell, 2)
                text(str(row * 3 + col + 1), cell.x + 4, cell.y + 2, 12, (68, 74, 57))
        sx, sy = map_rect.w / world.size, map_rect.h / world.size
        camera_rect = pg.Rect(map_rect.x + camera[0] * sx, map_rect.y + camera[1] * sy, viewport.w * sx, viewport.h * sy)
        pg.draw.rect(canvas, (218, 214, 184), camera_rect.clip(map_rect), 1)
        pg.draw.circle(canvas, (127, 42, 28), (round(map_rect.x + world.x * sx), round(map_rect.y + world.y * sy)), 4)
        text("• você  /  verde: ativa", rect.x + 10, rect.y + 172, 12, INK)
        pg.draw.polygon(canvas, (156, 146, 102), [(rect.x + 57, 21), (rect.x + 129, 25),
                                                               (rect.x + 124, 39), (rect.x + 54, 36)])

    def draw_hud(camera, visible):
        pg.draw.rect(canvas, INK, (24, 25, 234, 63))
        pg.draw.rect(canvas, RUST, (24, 25, 4, 63))
        text("ÚLTIMA RUA", 40, 30, 28, PAPER, True)
        text("DIA 09 / " + presets[selected]["name"].upper(), 41, 66, 12, MUTED)
        remain = max(0, math.ceil(settings.survival_seconds - world.elapsed))
        pg.draw.rect(canvas, INK, (510, 23, 160, 72))
        text("AGUENTE ATÉ", 533, 30, 14, MUTED)
        text(f"{remain // 60:02}:{remain % 60:02}", 534, 48, 36, GOLD, True)
        draw_map(camera)
        pg.draw.rect(canvas, (25, 29, 24), (0, HEIGHT - 88, WIDTH, 88))
        pg.draw.line(canvas, (90, 91, 72), (24, HEIGHT - 88), (WIDTH - 24, HEIGHT - 88))
        health_color = (153, 165, 110) if world.health > 25 else RUST
        text("SAÚDE", 28, 686, 12, MUTED)
        text("[M] SOM " + ("ON" if sounds.enabled else "OFF"), 91, 741, 12, MUTED)
        text(f"{math.ceil(world.health):03}", 28, 701, 28, health_color, True)
        for index in range(10):
            color = health_color if world.health / settings.player_health * 10 > index else (59, 64, 50)
            pg.draw.rect(canvas, color, (91 + index * 12, 712, 9, 12))
        canvas.blit(art.medkit, (262, 700))
        text(f"{world.medkits:02}  KIT MÉDICO", 301, 702, 18, PAPER, True)
        text("[H] usar", 301, 727, 12, MUTED)
        canvas.blit(art.ammo, (499, 700))
        text(f"{world.ammo:02}  CARGAS", 539, 702, 18, GOLD, True)
        text("[ESPAÇO / CLIQUE] explosão", 539, 727, 12, MUTED)
        text(f"{world.kills:03} ABATIDOS", 806, 701, 18, PAPER, True)
        text("WASD mover / P pausa", 952, 703, 12, MUTED)
        text("G setores e dados da IA", 952, 726, 12, MUTED)
        if grid:
            pg.draw.rect(canvas, INK, (24, 106, 366, 103))
            text("SIMULAÇÃO / DIAGNÓSTICO", 39, 118, 14, GOLD)
            text(f"Áreas ativas: {len(world.loaded)}/9  |  FPS: {clock.get_fps():.0f}", 39, 144, 14)
            text(f"NPCs por passo: {world.updated_npcs} / {world.enemy_count}", 39, 166, 14)
            text(f"NPCs na câmera: {visible}", 39, 187, 12, MUTED)

    def overlay():
        veil.fill((12, 16, 12, 150 if mode == "menu" else 208))
        canvas.blit(veil, (0, 0))
        if mode == "menu":
            pg.draw.rect(canvas, INK, (0, 0, 550, HEIGHT))
            pg.draw.line(canvas, (83, 85, 66), (550, 0), (550, HEIGHT))
            pg.draw.rect(canvas, RUST, (49, 48, 5, 20))
            text("ZONA DE EVACUAÇÃO / DIA 09", 66, 50, 14, MUTED)
            canvas.blit(titles[0], (46, 91))
            canvas.blit(titles[1], (46, 190))
            text("A rua ficou para eles.", 52, 321, 22, PAPER, True)
            text(f"Sobreviva por {settings.survival_seconds:g} segundos.", 52, 359, 16, MUTED)
            text("Recolha suprimentos. Não fique parado.", 52, 384, 16, MUTED)
            text("ESCOLHA A HORDA", 52, 433, 12, GOLD)
            page_start = (selected // 3) * 3
            for j, index in enumerate(range(page_start, min(page_start + 3, len(presets)))):
                preset = presets[index]
                y = 459 + j * 39
                chosen = index == selected
                rect = pg.Rect(48, y, 452, 35)
                if chosen:
                    pg.draw.rect(canvas, (57, 62, 47), rect)
                    pg.draw.rect(canvas, GOLD, (48, y, 3, 35))
                text(("> " if chosen else "  ") + preset["name"].upper(), 60, y + 8, 16, PAPER if chosen else MUTED, chosen)
                label = f"{preset['enemies']:,} zumbis".replace(",", ".")
                text(label, 341, y + 8, 14, GOLD if chosen else MUTED)
                buttons.append((rect, f"preset:{index}"))
            button("ENTRAR NA RUA", pg.Rect(50, 606, 450, 54), "start", True)
            text("ENTER iniciar / ← → escolher horda", 53, 677, 12, MUTED)
            text("WASD mover   H curar   ESPAÇO explosão", 53, 701, 12, MUTED)
            # Vinheta ilustrada com os mesmos sprites utilizados durante a partida.
            for i, (x, y, variant) in enumerate(((764, 344, 1), (944, 419, 0), (858, 231, 2),
                                                (1088, 314, 3), (703, 506, 4), (1028, 554, 1))):
                sprite = art.zombies[variant, i % 4, art.direction(827 - x, 453 - y)]
                large = pg.transform.scale(sprite, (sprite.get_width() * 3, sprite.get_height() * 3))
                canvas.blit(large, large.get_rect(center=(x, y)))
            survivor = art.survivors[0, 14]
            large = pg.transform.scale(survivor, (survivor.get_width() * 3, survivor.get_height() * 3))
            canvas.blit(large, large.get_rect(center=(827, 453)))
            text("NÃO DEIXE A HORDA FECHAR O CERCO.", 637, 637, 16, PAPER, True)
            text("Kits e cargas são coletados ao passar sobre eles.", 617, 670, 12, MUTED)
            text("A explosão atinge os zumbis ao seu redor.", 648, 693, 12, MUTED)
        else:
            won, paused = world.status == "won", mode == "paused"
            pg.draw.rect(canvas, INK, (228, 165, 724, 426))
            pg.draw.rect(canvas, GOLD if paused or won else RUST, (228, 165, 5, 426))
            text("ÚLTIMA RUA / " + ("PAUSA" if paused else "FIM DA PARTIDA"), 269, 197, 14, MUTED)
            title = "Respire um pouco." if paused else ("Você resistiu." if won else "A rua levou mais um.")
            text(title, 266, 249, 52, PAPER if paused or won else (201, 113, 84), True)
            text(f"{world.elapsed:.1f}s sobrevividos   /   {world.kills} zumbis abatidos", 269, 338, 18)
            text("O tempo está parado." if paused else ("A horda ficou para trás." if won else "Tente outra rota. Guarde uma carga para o cerco."),
                 269, 375, 14, MUTED)
            button("CONTINUAR" if paused else "TENTAR DE NOVO", pg.Rect(269, 437, 302, 54),
                   "resume" if paused else "restart", True)
            button("VOLTAR AO MENU", pg.Rect(590, 437, 320, 54), "menu")
            text("ENTER continuar" if paused else "ENTER ou R para tentar de novo", 269, 530, 12, MUTED)

    try:
        reset(args.smoke_test or bool(args.screenshot))
        if args.screenshot:
            for _ in range(round(args.preview_seconds * 60)):
                world.update(1 / 60)
            if args.screen in ("won", "dead"):
                world.status = args.screen
                world.health = settings.player_health if args.screen == "won" else 0
                world.elapsed = settings.survival_seconds if args.screen == "won" else max(12, world.elapsed)
                mode = "ended"
            else:
                mode = args.screen
        while running:
            dt = min(clock.tick(60) / 1000, 0.1)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                elif event.type == pg.WINDOWFOCUSLOST and mode == "playing":
                    mode = "paused"
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_m:
                        sounds.toggle()
                    elif event.key == pg.K_g:
                        grid = not grid
                    elif mode == "menu":
                        if event.key == pg.K_RETURN:
                            action("start")
                        elif event.key in (pg.K_LEFT, pg.K_RIGHT):
                            action(f"preset:{(selected + (1 if event.key == pg.K_RIGHT else -1)) % len(presets)}")
                    elif event.key in (pg.K_ESCAPE, pg.K_p) and world.status == "playing":
                        mode = "playing" if mode == "paused" else "paused"
                        accumulator = 0
                    elif mode == "playing":
                        if event.key == pg.K_h:
                            if world.heal():
                                sounds.play("heal")
                        elif event.key == pg.K_SPACE:
                            use_grenade()
                    elif event.key == pg.K_RETURN:
                        action("resume" if mode == "paused" else "restart")
                    elif event.key == pg.K_r and mode == "ended":
                        action("restart")
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    scale = min(window.get_width() / WIDTH, window.get_height() / HEIGHT)
                    mx = (event.pos[0] - (window.get_width() - WIDTH * scale) / 2) / scale
                    my = (event.pos[1] - (window.get_height() - HEIGHT * scale) / 2) / scale
                    if mode == "playing" and viewport.collidepoint(mx, my) and my < HEIGHT - 88:
                        use_grenade()
                    else:
                        for rect, name in buttons:
                            if rect.collidepoint(mx, my):
                                action(name)
                                break
            if mode == "playing":
                keys = pg.key.get_pressed()
                move_x = int(keys[pg.K_d] or keys[pg.K_RIGHT]) - int(keys[pg.K_a] or keys[pg.K_LEFT])
                move_y = int(keys[pg.K_s] or keys[pg.K_DOWN]) - int(keys[pg.K_w] or keys[pg.K_UP])
                moving = bool(move_x or move_y)
                if moving:
                    facing = art.direction(move_x, move_y)
                accumulator += dt
                previous_health = world.health
                previous_items = world.medkits + world.ammo
                while accumulator >= 1 / 60 and world.status == "playing":
                    world.update(1 / 60, move_x, move_y)
                    accumulator -= 1 / 60
                if world.medkits + world.ammo > previous_items:
                    sounds.play("pickup")
                if world.health < previous_health and int(world.elapsed * 4) != int((world.elapsed - dt) * 4):
                    sounds.play("hurt")
                for effect in effects:
                    effect[2] += dt
                effects[:] = [e for e in effects if e[2] < 0.4]
                if world.status != "playing":
                    mode = "ended"
            buttons.clear()
            canvas.fill(INK)
            camera = camera_position(world.x, world.y, *viewport.size, world.size)
            canvas.set_clip(viewport)
            visible = art.draw(canvas, world, camera, facing, moving, effects, stains, grid)
            canvas.set_clip(None)
            if mode != "menu":
                draw_hud(camera, visible)
            if mode != "playing":
                overlay()
            scale = min(window.get_width() / WIDTH, window.get_height() / HEIGHT)
            scaled = pg.transform.scale(canvas, (max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale))))
            window.fill((15, 19, 15))
            window.blit(scaled, scaled.get_rect(center=window.get_rect().center))
            pg.display.flip()
            frames += 1
            if args.screenshot:
                pg.image.save(canvas, str(args.screenshot))
                running = False
            if args.smoke_test and frames >= 5:
                print(f"OK: {frames} frames renderizados; {len(world.loaded)} áreas carregadas; {world.updated_npcs} NPCs atualizados.")
                running = False
    finally:
        if world:
            world.close()
        pg.quit()


if __name__ == "__main__":
    main()
