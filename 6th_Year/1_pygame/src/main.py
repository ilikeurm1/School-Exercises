import os
import math
import sys
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

# pygame
import pygame as pg  # type: ignore
from random import randint

# fps counter
from utils.scripts.fpscounter import FPSCounter

# settings
from utils.settings.settings import load_settings

# player
from utils.scripts.player import Player

# ── Debug Configuration ─────────────────────────────────────────────────────
DEBUG_MODE = True  # Master toggle — set to False to disable all debug features

GAME_DURATION = 60  # seconds per round


def _draw_button(
    surface: pg.Surface,
    font: pg.font.Font,
    text: str,
    rect: pg.Rect,
    bg: tuple,
    fg: tuple = (255, 255, 255),
    border: tuple = (255, 255, 255),
) -> None:
    pg.draw.rect(surface, bg, rect, border_radius=8)
    pg.draw.rect(surface, border, rect, 2, border_radius=8)
    label = font.render(text, True, fg)
    surface.blit(label, label.get_rect(center=rect.center))


def main():
    # Load settings
    setts = load_settings()

    IMG_FOLDER = setts.get("IMG_FOLDER", os.path.dirname(__file__))
    (screen_w, screen_h) = setts.get("SCREEN_DIMS", (640, 360))
    max_fps = setts.get("START_FPS", 60)

    # pygame initialisation
    pg.init()
    screen = pg.display.set_mode((screen_w, screen_h))
    pg.display.set_caption("Anger burds")
    pg.display.set_icon(pg.image.load(os.path.join(IMG_FOLDER, "Chuck-1.png")))
    clock = pg.time.Clock()

    fps_counter = FPSCounter(
        screen, pg.font.Font(None, 24), clock, (255, 255, 255), (5, 0, 75, 30)
    )

    # Fonts (created once after pg.init)
    font_path = r"C:\Users\yeetl\AppData\Local\Microsoft\Windows\Fonts\FiraCodeNerdFont-Regular.ttf"
    font_huge = pg.font.Font(font_path, 112)
    font_large = pg.font.Font(font_path, 64)
    font_medium = pg.font.Font(font_path, 40)
    font_small = pg.font.Font(font_path, 24)
    font_tiny = pg.font.Font(font_path, 16)

    # Buttons
    btn_w, btn_h = 240, 64
    start_btn = pg.Rect(
        screen_w // 2 - btn_w // 2, screen_h // 2 + 120, btn_w, btn_h
    )
    retry_btn = pg.Rect(
        screen_w // 2 - btn_w // 2, screen_h // 2 + 120, btn_w, btn_h
    )

    # Game constants
    player_radius = 30
    food_size = 10
    FOOD_PER_PLAYER = 5
    spawn_ratio = math.ceil(player_radius * (1 - math.sqrt(2) / 2))

    # Mutable game state
    state = "title"  # "title" | "playing" | "win"
    food: dict[int, list[tuple[int, int]]] = {}
    time_left: float = GAME_DURATION
    allow_fps_change = True
    dt: float = 1 / max_fps

    # ── Debug state ─────────────────────────────────────────────────────────
    dbg_overlay = DEBUG_MODE  # F1  — toggle HUD overlay
    dbg_show_spawn_bounds = False  # F3  — show food spawn boundary
    dbg_freeze_timer = False  # F4  — pause the countdown
    dbg_show_hitboxes = False  # F6  — player collision circles
    dbg_show_velocity = False  # F7  — velocity vectors
    dbg_noclip_mode = False  # F8  — disable player-player collisions
    dbg_selected_player = 0  # TAB — cycle selected player
    dbg_slow_motion = False  # F12 — half-speed mode
    dbg_show_grid = False  # G   — coordinate grid
    dbg_infinite_time = False  # F5  — timer stays at GAME_DURATION
    dbg_last_action = ""  # most recent debug action (shown in console)

    # ── Print debug legend to console ───────────────────────────────────────
    if DEBUG_MODE:
        print("\n"
              "┌─────────────────── DEBUG MODE ───────────────────┐")
        print("│  F1  : Toggle overlay HUD                        │")
        print("│  F2  : Spawn +5 food per player                  │")
        print("│  F3  : Show food spawn boundary                  │")
        print("│  F4  : Freeze / unfreeze timer                   │")
        print("│  F5  : Infinite time (timer stays full)          │")
        print("│  F6  : Show hitbox circles                       │")
        print("│  F7  : Show velocity vectors                     │")
        print("│  F8  : Noclip mode (no player collisions)        │")
        print("│  F9  : Teleport selected player to mouse         │")
        print("│  F10 : Add 10 s to timer                         │")
        print("│  F11 : Remove 10 s from timer                    │")
        print("│  F12 : Slow-motion (half speed)                  │")
        print("│  TAB : Cycle selected player                     │")
        print("│  G   : Toggle coordinate grid                    │")
        print("│  C   : Clear all food                            │")
        print("│  R   : Respawn default food                      │")
        print("│  0   : Reset all scores                          │")
        print("│  P   : +1 score to selected player               │")
        print("└──────────────────────────────────────────────────┘")
        print()  # blank line before the action line

    def _dbg_action(msg: str) -> None:
        """Overwrite the console action line with \\r."""
        nonlocal dbg_last_action
        dbg_last_action = msg
        sys.stdout.write(f"\r[DBG] {msg}" + " " * 20)
        sys.stdout.flush()

    def _spawn_food() -> tuple[int, int]:
        return (
            randint(spawn_ratio, screen_w - spawn_ratio),
            randint(spawn_ratio, screen_h - spawn_ratio),
        )

    def init_game() -> None:
        nonlocal food, time_left, allow_fps_change, dt
        Player.reset_registry()
        Player(
            screen, max_vel=750, drag=10, color="red", radius=player_radius
        )  # 0 — WASD
        Player(
            screen, max_vel=750, drag=10, color="blue", radius=player_radius
        )  # 1 — arrows
        Player(
            screen, max_vel=750, drag=10, color="green", radius=player_radius
        )  # 2 — IJKL
        food = {
            p.index: [_spawn_food() for _ in range(FOOD_PER_PLAYER)]
            for p in Player._registry
        }
        time_left = GAME_DURATION
        allow_fps_change = True
        dt = 1 / max_fps

    # Food spawn boundary (used for drawing & reference)
    food_bounds = pg.Rect(
        spawn_ratio, spawn_ratio, screen_w - spawn_ratio * 2, screen_h - spawn_ratio * 2
    )

    # Custom event for FPS-change cooldown
    FPS_CHANGE_EVENT = pg.USEREVENT + 1
    pg.time.set_timer(FPS_CHANGE_EVENT, 100)

    # ── Main loop ───────────────────────────────────────────────────────────
    running = True
    while running:
        # ── Events ──────────────────────────────────────────────────────────
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                running = False

            elif event.type == FPS_CHANGE_EVENT:
                allow_fps_change = True

            # ── Debug key bindings ───────────────────────────────────────
            elif DEBUG_MODE and event.type == pg.KEYDOWN:
                if event.key == pg.K_F1:
                    dbg_overlay = not dbg_overlay
                    _dbg_action(f"Overlay {'ON' if dbg_overlay else 'OFF'}")
                elif event.key == pg.K_F2 and state == "playing":
                    # Spawn 5 extra food for every player
                    for p in Player._registry:
                        food[p.index].extend(_spawn_food() for _ in range(5))
                    _dbg_action("Spawned +5 food per player")
                elif event.key == pg.K_F3:
                    dbg_show_spawn_bounds = not dbg_show_spawn_bounds
                    _dbg_action(f"Spawn bounds {'ON' if dbg_show_spawn_bounds else 'OFF'}")
                elif event.key == pg.K_F4:
                    dbg_freeze_timer = not dbg_freeze_timer
                    _dbg_action(f"Timer {'FROZEN' if dbg_freeze_timer else 'RUNNING'}")
                elif event.key == pg.K_F5:
                    dbg_infinite_time = not dbg_infinite_time
                    if dbg_infinite_time:
                        time_left = GAME_DURATION
                    _dbg_action(f"Infinite time {'ON' if dbg_infinite_time else 'OFF'}")
                elif event.key == pg.K_F6:
                    dbg_show_hitboxes = not dbg_show_hitboxes
                    _dbg_action(f"Hitboxes {'ON' if dbg_show_hitboxes else 'OFF'}")
                elif event.key == pg.K_F7:
                    dbg_show_velocity = not dbg_show_velocity
                    _dbg_action(f"Velocity vectors {'ON' if dbg_show_velocity else 'OFF'}")
                elif event.key == pg.K_F8:
                    dbg_noclip_mode = not dbg_noclip_mode
                    _dbg_action(f"Noclip mode {'ON' if dbg_noclip_mode else 'OFF'}")
                elif event.key == pg.K_F9 and state == "playing":
                    # Teleport selected player to mouse
                    mx, my = pg.mouse.get_pos()
                    p = Player._registry[dbg_selected_player]
                    p.x, p.y = float(mx), float(my)
                    p.vx, p.vy = 0.0, 0.0
                    _dbg_action(f"Teleported P{dbg_selected_player + 1} to ({mx}, {my})")
                elif event.key == pg.K_F10 and state == "playing":
                    time_left = min(time_left + 10, GAME_DURATION)
                    _dbg_action(f"Timer +10s → {time_left:.1f}s")
                elif event.key == pg.K_F11 and state == "playing":
                    time_left = max(0.0, time_left - 10)
                    _dbg_action(f"Timer -10s → {time_left:.1f}s")
                elif event.key == pg.K_F12:
                    dbg_slow_motion = not dbg_slow_motion
                    _dbg_action(f"Slow motion {'ON' if dbg_slow_motion else 'OFF'}")
                elif event.key == pg.K_TAB and state == "playing":
                    dbg_selected_player = (dbg_selected_player + 1) % len(
                        Player._registry
                    )
                    sel = Player._registry[dbg_selected_player]
                    _dbg_action(f"Selected P{dbg_selected_player + 1} ({sel.color})")
                elif event.key == pg.K_g:
                    dbg_show_grid = not dbg_show_grid
                    _dbg_action(f"Grid {'ON' if dbg_show_grid else 'OFF'}")
                elif event.key == pg.K_c and state == "playing":
                    # Clear all food
                    for p in Player._registry:
                        food[p.index].clear()
                    _dbg_action("Cleared all food")
                elif event.key == pg.K_r and state == "playing":
                    # Respawn default food
                    food = {
                        p.index: [_spawn_food() for _ in range(FOOD_PER_PLAYER)]
                        for p in Player._registry
                    }
                    _dbg_action("Respawned default food")
                elif event.key == pg.K_0 and state == "playing":
                    # Reset all scores to 0
                    for p in Player._registry:
                        p.score = 0
                    _dbg_action("Reset all scores to 0")
                elif event.key == pg.K_p and state == "playing":
                    # Give +1 score to the selected player
                    Player._registry[dbg_selected_player].score += 1
                    s = Player._registry[dbg_selected_player].score
                    _dbg_action(f"P{dbg_selected_player + 1} score → {s}")

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if state == "title" and start_btn.collidepoint(event.pos):
                    init_game()
                    state = "playing"
                elif state == "win" and retry_btn.collidepoint(event.pos):
                    init_game()
                    state = "playing"

        screen.fill("black")
        mouse_pos = pg.mouse.get_pos()

        # ── TITLE SCREEN ─────────────────────────────────────────────────────
        if state == "title":
            title_surf = font_huge.render("Anger Burds", True, (255, 200, 50))
            screen.blit(
                title_surf,
                title_surf.get_rect(center=(screen_w // 2, screen_h // 2 - 80)),
            )

            sub_surf = font_small.render(
                f"Collect your coloured food — most points in {GAME_DURATION}s wins!",
                True,
                (180, 180, 180),
            )
            screen.blit(
                sub_surf, sub_surf.get_rect(center=(screen_w // 2, screen_h // 2))
            )

            controls = [
                ("P1 (red)", "WASD", (220, 60, 60)),
                ("P2 (blue)", "Arrow keys", (60, 120, 220)),
                ("P3 (green)", "IJKL", (60, 200, 60)),
            ]
            for idx, (label, keys_str, col) in enumerate(controls):
                line = font_tiny.render(f"{label}: {keys_str}", True, col)
                screen.blit(
                    line,
                    line.get_rect(
                        center=(screen_w // 2, screen_h // 2 + 36 + idx * 22)
                    ),
                )

            hover = start_btn.collidepoint(mouse_pos)
            _draw_button(
                screen,
                font_medium,
                "START",
                start_btn,
                (60, 180, 60) if hover else (30, 110, 30),
            )

        # ── PLAYING ──────────────────────────────────────────────────────────
        elif state == "playing":
            keys = pg.key.get_pressed()

            # FPS limit adjustment (Shift+PageUp/Down = ±10, plain = ±1)
            if allow_fps_change:
                shift = keys[pg.K_LSHIFT] or keys[pg.K_RSHIFT]
                step = 10 if shift else 1
                if keys[pg.K_EQUALS]:
                    max_fps += step
                    allow_fps_change = False
                elif keys[pg.K_MINUS]:
                    max_fps -= step
                    allow_fps_change = False
                max_fps = max(10, min(350, max_fps))

            # Update players
            if dbg_noclip_mode:
                # Update without resolving player–player collisions
                for p in Player._registry:
                    p.update(keys, dt)
            else:
                Player.update_all(keys, dt)

            # Food collision — circle vs axis-aligned square
            for player in Player._registry:
                player_food = food[player.index]
                for i, (fx, fy) in enumerate(player_food):
                    nx = max(fx, min(player.x, fx + food_size))
                    ny = max(fy, min(player.y, fy + food_size))
                    if math.hypot(player.x - nx, player.y - ny) < player.radius:
                        player.score += 1
                        player_food[i] = _spawn_food()

            # Countdown
            if not (DEBUG_MODE and dbg_freeze_timer):
                if DEBUG_MODE and dbg_infinite_time:
                    time_left = GAME_DURATION
                else:
                    time_left = max(0.0, time_left - dt)
            if time_left == 0:
                state = "win"

            # ── Draw ────────────────────────────────────────────────────────
            # Debug: coordinate grid
            if DEBUG_MODE and dbg_show_grid:
                grid_color = (40, 40, 40)
                grid_label_color = (80, 80, 80)
                for gx in range(0, screen_w, 50):
                    pg.draw.line(screen, grid_color, (gx, 0), (gx, screen_h))
                    lbl = font_tiny.render(str(gx), True, grid_label_color)
                    screen.blit(lbl, (gx + 2, 2))
                for gy in range(0, screen_h, 50):
                    pg.draw.line(screen, grid_color, (0, gy), (screen_w, gy))
                    lbl = font_tiny.render(str(gy), True, grid_label_color)
                    screen.blit(lbl, (2, gy + 2))

            # Debug: food spawn boundary
            if DEBUG_MODE and dbg_show_spawn_bounds:
                pg.draw.rect(screen, (255, 255, 0), food_bounds, 1)

            Player.draw_all()

            # Debug: hitbox circles
            if DEBUG_MODE and dbg_show_hitboxes:
                for player in Player._registry:
                    pg.draw.circle(
                        screen,
                        (255, 255, 255),
                        (int(player.x), int(player.y)),
                        player.radius,
                        1,
                    )
                    # Highlight selected player
                    if player.index == dbg_selected_player:
                        pg.draw.circle(
                            screen,
                            (255, 255, 0),
                            (int(player.x), int(player.y)),
                            player.radius + 3,
                            2,
                        )

            # Debug: velocity vectors
            if DEBUG_MODE and dbg_show_velocity:
                for player in Player._registry:
                    scale = 0.3  # pixels per vel-unit for visibility
                    ex = int(player.x + player.vx * scale)
                    ey = int(player.y + player.vy * scale)
                    pg.draw.line(
                        screen,
                        (255, 255, 0),
                        (int(player.x), int(player.y)),
                        (ex, ey),
                        2,
                    )

            # Food squares
            for player in Player._registry:
                for fx, fy in food[player.index]:
                    pg.draw.rect(
                        screen, player.color, (fx, fy, food_size, food_size)
                    )

            # Scores at the bottom, dynamically spaced
            num_players = len(Player._registry)
            for player in Player._registry:
                sx = screen_w * (player.index + 1) / (num_players + 1)
                s = font_small.render(
                    f"P{player.index + 1}: {player.score}", True, player.color
                )
                screen.blit(s, s.get_rect(center=(sx, screen_h - 20)))

            # FPS label (top centre)
            fps_label = font_tiny.render(
                f"FPS Limit: {max_fps}", True, (255, 255, 255)
            )
            screen.blit(
                fps_label, fps_label.get_rect(center=(screen_w // 2, 15))
            )
            fps_counter.update()
            fps_counter.draw()

            # Countdown timer (top right) — turns red in the last 10 s
            total_secs = math.ceil(time_left)
            mins, secs_rem = divmod(total_secs, 60)
            timer_color = (255, 70, 70) if time_left <= 10 else (255, 255, 255)
            timer_surf = font_large.render(
                f"{mins}:{secs_rem:02d}", True, timer_color
            )
            screen.blit(
                timer_surf, timer_surf.get_rect(topright=(screen_w - 10, 5))
            )

            # ── Debug overlay HUD ───────────────────────────────────────────
            if DEBUG_MODE and dbg_overlay:
                dbg_lines: list[str] = []
                dbg_lines.append("DEBUG")
                dbg_lines.append(f"State: {state}  |  dt: {dt:.4f}s")
                dbg_lines.append(f"Mouse: {mouse_pos}")
                sel = Player._registry[dbg_selected_player]
                dbg_lines.append(
                    f"Selected: P{dbg_selected_player + 1} ({sel.color})"
                )
                dbg_lines.append("")
                for p in Player._registry:
                    spd = math.hypot(p.vx, p.vy)
                    dbg_lines.append(
                        f"P{p.index + 1} pos=({p.x:.1f},{p.y:.1f})  "
                        f"vel=({p.vx:.1f},{p.vy:.1f})  spd={spd:.1f}  "
                        f"score={p.score}  food={len(food[p.index])}"
                    )
                dbg_lines.append("")
                flag_map = [
                    (dbg_freeze_timer, "FROZEN"),
                    (dbg_infinite_time, "INF-TIME"),
                    (dbg_noclip_mode, "NOCLIP"),
                    (dbg_slow_motion, "SLOW-MO"),
                    (dbg_show_spawn_bounds, "BOUNDS"),
                    (dbg_show_hitboxes, "HITBOX"),
                    (dbg_show_velocity, "VEL-VEC"),
                    (dbg_show_grid, "GRID"),
                ]
                flags = [name for on, name in flag_map if on]
                dbg_lines.append(
                    f"Flags: {' | '.join(flags) if flags else 'none'}"
                )
                if dbg_last_action:
                    dbg_lines.append("")
                    dbg_lines.append(f"Last: {dbg_last_action}")

                # Semi-transparent background panel
                panel_w = 420
                panel_h = len(dbg_lines) * 16 + 10
                panel_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
                panel_surf.fill((0, 0, 0, 170))
                screen.blit(panel_surf, (5, 50))

                for idx, line in enumerate(dbg_lines):
                    dl = font_tiny.render(line, True, (0, 255, 100))
                    screen.blit(dl, (10, 55 + idx * 16))

        # ── WIN SCREEN ───────────────────────────────────────────────────────
        elif state == "win":
            players = Player._registry
            max_score = max(p.score for p in players)
            winners = [p for p in players if p.score == max_score]

            if len(winners) == 1:
                headline = f"Player {winners[0].index + 1} wins!"
                headline_color = winners[0].color
            else:
                headline = "It's a tie!"
                headline_color = (255, 220, 50)

            h_surf = font_large.render(headline, True, headline_color)
            screen.blit(
                h_surf,
                h_surf.get_rect(center=(screen_w // 2, screen_h // 2 - 150)),
            )

            # Score list — winner(s) underlined
            for i, player in enumerate(players):
                is_winner = player.score == max_score
                s = font_medium.render(
                    f"P{player.index + 1}:  {player.score} pts",
                    True,
                    player.color,
                )
                r = s.get_rect(
                    center=(screen_w // 2, screen_h // 2 - 70 + i * 58)
                )
                screen.blit(s, r)
                if is_winner:
                    pg.draw.line(
                        screen, player.color, r.bottomleft, r.bottomright, 2
                    )

            hover = retry_btn.collidepoint(mouse_pos)
            _draw_button(
                screen,
                font_medium,
                "RETRY",
                retry_btn,
                (60, 100, 210) if hover else (30, 60, 150),
            )

        # Debug: show overlay on non-playing screens too
        if DEBUG_MODE and dbg_overlay and state != "playing":
            dbg_info = [
                "DEBUG",
                f"State: {state}  |  Mouse: {mouse_pos}",
                "F1:overlay  G:grid  F3:bounds",
            ]
            panel_w = 320
            panel_h = len(dbg_info) * 16 + 10
            panel_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
            panel_surf.fill((0, 0, 0, 170))
            screen.blit(panel_surf, (5, 5))
            for idx, line in enumerate(dbg_info):
                dl = font_tiny.render(line, True, (0, 255, 100))
                screen.blit(dl, (10, 10 + idx * 16))

        pg.display.flip()
        dt = clock.tick(max_fps) / 1000
        if DEBUG_MODE and dbg_slow_motion:
            dt *= 0.5

    pg.quit()
    if DEBUG_MODE:
        print("\n")  # preserve the last action line and add newline
    print("Pygame ran succesfully!")


if __name__ == "__main__":
    main()
