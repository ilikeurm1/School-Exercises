import os
import math
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

# debug
from utils.scripts.debug import DebugManager

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

    # Debug manager
    debug = DebugManager(DEBUG_MODE, screen, font_tiny, screen_w, screen_h)
    debug.print_legend()

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

            elif event.type == pg.KEYDOWN:
                time_left = debug.handle_event(
                    event, state, Player._registry, food,
                    time_left, GAME_DURATION, _spawn_food, FOOD_PER_PLAYER,
                )

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
            if debug.noclip:
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
            time_left = debug.update_timer(time_left, dt, GAME_DURATION)
            if time_left == 0:
                state = "win"

            # ── Draw ────────────────────────────────────────────────────────
            debug.draw_world(food_bounds)

            Player.draw_all()

            debug.draw_players(Player._registry)

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

        debug.draw_overlay(state, Player._registry, food, mouse_pos, dt, time_left)

        pg.display.flip()
        dt = clock.tick(max_fps) / 1000
        dt = debug.apply_dt(dt)

    pg.quit()
    debug.on_quit()
    print("Pygame ran succesfully!")


if __name__ == "__main__":
    main()
