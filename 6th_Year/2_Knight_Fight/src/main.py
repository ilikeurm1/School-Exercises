import os
import sys
from pathlib import Path

# turn off ugly prompt
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame as pg

from utils.settings import WIDTH, HEIGHT, MAX_FPS
from utils.scripts.helpers import (
    get_image,
    play_sound,
    stop_sound,
    get_game_font,
)
from utils.scripts.player import Player
from utils.scripts.enemy import Enemy
from utils.scripts.fpscounter import FPSCounter
from utils.scripts.healthbar import Healthbar
from utils.scripts.healthpickup import HealthPickupManager

GAME_INTRO_FADE_DURATION = 0.9
END_FADE_DURATION = 0.45


def _restart_battle_music(skip_intro: bool) -> None:
    stop_sound(0.15)
    if not skip_intro:
        play_sound("intro_name.mp3", wait=True)
    play_sound("main_theme.mp3", loops=-1, volume=0.3)


def _fade_to_black(
    screen: pg.Surface, clock: pg.time.Clock, duration: float
) -> None:
    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.fill("black")
    elapsed = 0.0

    frame = screen.copy()
    while elapsed < duration:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return

        progress = min(1.0, elapsed / max(0.001, duration))
        screen.blit(frame, (0, 0))
        overlay.set_alpha(round(progress * 255))
        screen.blit(overlay, (0, 0))
        pg.display.flip()
        elapsed += clock.tick(MAX_FPS) / 1000


_ARENA_BG: pg.Surface | None = None


def _build_arena_background() -> pg.Surface:
    bg = pg.Surface((WIDTH, HEIGHT))

    # Three-stop vertical gradient: dark slate → slightly lighter mid → near-black floor
    top_color    = (13, 15, 28)
    mid_color    = (17, 20, 36)
    bottom_color = (8,  9,  16)

    for y in range(HEIGHT):
        blend = y / max(1, HEIGHT - 1)
        if blend < 0.55:
            t = blend / 0.55
            color = tuple(round(top_color[i] + (mid_color[i] - top_color[i]) * t) for i in range(3))
        else:
            t = (blend - 0.55) / 0.45
            color = tuple(round(mid_color[i] + (bottom_color[i] - mid_color[i]) * t) for i in range(3))
        pg.draw.line(bg, color, (0, y), (WIDTH, y))

    # Floor edge highlight
    floor_y = HEIGHT - 108
    pg.draw.line(bg, (34, 36, 58), (0, floor_y), (WIDTH, floor_y), 2)

    # Subtle stone tile lines on the floor
    for y in range(floor_y + 28, HEIGHT, 28):
        pg.draw.line(bg, (13, 14, 24), (0, y), (WIDTH, y), 1)
    for x in range(0, WIDTH, 80):
        pg.draw.line(bg, (13, 14, 24), (x, floor_y), (x, HEIGHT), 1)

    # Pre-bake the ground shadow ellipse (it's static)
    pg.draw.ellipse(bg, (18, 18, 30), (WIDTH // 2 - 260, HEIGHT - 120, 520, 95))

    return bg


def _draw_arena_background(screen: pg.Surface) -> None:
    global _ARENA_BG
    if _ARENA_BG is None:
        _ARENA_BG = _build_arena_background()
    screen.blit(_ARENA_BG, (0, 0))


def _draw_game_scene(
    screen: pg.Surface,
    player: Player,
    enemy: Enemy,
    healthbar: Healthbar,
    fps_counter: FPSCounter,
    health_pickups: HealthPickupManager,
) -> None:
    _draw_arena_background(screen)
    enemy.draw()
    health_pickups.draw()
    player.draw()
    healthbar.draw()
    fps_counter.draw()


def _play_game_intro(
    screen: pg.Surface,
    clock: pg.time.Clock,
    player: Player,
    enemy: Enemy,
    healthbar: Healthbar,
    fps_counter: FPSCounter,
    health_pickups: HealthPickupManager,
) -> bool:
    menu_bg = get_image(Path("bgs") / "menu_background.jpg", (WIDTH, HEIGHT))
    fade_overlay = pg.Surface((WIDTH, HEIGHT))
    fade_overlay.fill("black")
    elapsed = 0.0

    # Reset the clock tick from the wait by the intro_name
    clock.tick()

    while elapsed < GAME_INTRO_FADE_DURATION:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return False

        if pg.key.get_pressed()[pg.K_ESCAPE]:
            return False

        progress = min(1.0, elapsed / GAME_INTRO_FADE_DURATION)
        _draw_game_scene(
            screen, player, enemy, healthbar, fps_counter, health_pickups
        )

        menu_overlay = menu_bg.copy()
        menu_overlay.set_alpha(round((1.0 - progress) * 255))
        screen.blit(menu_overlay, (0, 0))

        fade_overlay.set_alpha(round((1.0 - progress) * 120))
        screen.blit(fade_overlay, (0, 0))

        pg.display.flip()
        elapsed += clock.tick(MAX_FPS) / 1000

    return True


def _draw_button(
    screen: pg.Surface,
    rect: pg.Rect,
    label: str,
    font: pg.font.Font,
    hovered: bool,
) -> None:
    bg = (55, 55, 70) if hovered else (35, 35, 50)
    pg.draw.rect(screen, bg, rect, border_radius=10)
    pg.draw.rect(screen, (200, 200, 220), rect, 2, border_radius=10)
    text = font.render(label, True, (240, 240, 255))
    screen.blit(text, text.get_rect(center=rect.center))


def controls_screen(screen: pg.Surface, clock: pg.time.Clock) -> None:
    title_font = get_game_font(54)
    header_font = get_game_font(22)
    body_font = get_game_font(18)
    back_font = get_game_font(32)

    back_rect = pg.Rect(0, 0, 160, 48)
    back_rect.bottomleft = (28, HEIGHT - 22)

    controls = [
        ("\u2190 \u2192  Arrow Keys", "Move left / right"),
        ("SPACE", "Dash  \u2014  brief speed burst to dodge attacks"),
        ("\u2191  Arrow Key", "Attack"),
    ]
    tips = [
        "Phase 1:  Wait for the wizard to swoop down and swipe.",
        "          He sometimes staggers \u2014 hit him while he's stunned!",
        "",
        "Phase 2:  He transforms and rains fireballs from above.",
        "          After each wave he descends to the ground.",
        "          When you see the \u2605 stars, attack him!",
        "          Dash through barrage waves for a brief safety window.",
    ]

    while True:
        mouse_pos = pg.mouse.get_pos()
        hovered = back_rect.collidepoint(mouse_pos)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit(0)
            if event.type == pg.KEYDOWN and event.key in (
                pg.K_ESCAPE,
                pg.K_BACKSPACE,
            ):
                return
            if (
                event.type == pg.MOUSEBUTTONDOWN
                and event.button == 1
                and hovered
            ):
                return

        # Background gradient
        for y in range(HEIGHT):
            blend = y / max(1, HEIGHT - 1)
            color = (
                round(12 + blend * 6),
                round(12 + blend * 8),
                round(28 + blend * 14),
            )
            pg.draw.line(screen, color, (0, y), (WIDTH, y))

        title = title_font.render("CONTROLS", True, (230, 230, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 54)))

        # Controls table
        col_key = 60
        col_desc = 280
        row_y = 120
        for key_text, desc_text in controls:
            key_surf = header_font.render(key_text, True, (200, 200, 255))
            desc_surf = body_font.render(desc_text, True, (210, 210, 210))
            screen.blit(key_surf, (col_key, row_y))
            screen.blit(desc_surf, (col_desc, row_y + 5))
            row_y += 46

        # Divider
        pg.draw.line(
            screen,
            (80, 80, 110),
            (col_key, row_y + 4),
            (WIDTH - col_key, row_y + 4),
            1,
        )
        row_y += 22

        how_label = header_font.render("HOW TO WIN", True, (190, 220, 255))
        screen.blit(how_label, (col_key, row_y))
        row_y += 40
        for line in tips:
            tip_surf = body_font.render(line, True, (195, 195, 195))
            screen.blit(tip_surf, (col_key, row_y))
            row_y += 28

        _draw_button(screen, back_rect, "\u2190  Back", back_font, hovered)
        pg.display.flip()
        clock.tick(MAX_FPS)


def menu_screen(screen: pg.Surface, clock: pg.time.Clock) -> None:
    menu_BG = get_image(Path("bgs") / "menu_background.jpg", (WIDTH, HEIGHT))
    button_font = get_game_font(65)
    small_font = get_game_font(38)

    start_rect = pg.Rect(0, 0, 220, 64)
    start_rect.center = (WIDTH // 2, 470)
    controls_rect = pg.Rect(0, 0, 220, 48)
    controls_rect.center = (WIDTH // 2, 546)

    while True:
        mouse_pos = pg.mouse.get_pos()
        start_hovered = start_rect.collidepoint(mouse_pos)
        ctrl_hovered = controls_rect.collidepoint(mouse_pos)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit(0)
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if start_hovered:
                    return
                if ctrl_hovered:
                    controls_screen(screen, clock)
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                pg.quit()
                sys.exit(0)

        screen.blit(menu_BG, (0, 0))
        _draw_button(screen, start_rect, "Start", button_font, start_hovered)
        _draw_button(
            screen, controls_rect, "Controls", small_font, ctrl_hovered
        )
        pg.display.flip()
        clock.tick(30)


def game(
    screen: pg.surface, clock: pg.time.Clock, *, skip_intro: bool = False
) -> str:
    FONT = get_game_font(18)

    # Fps counter
    fps_counter = FPSCounter(
        screen,
        FONT,
        clock,
        (255, 255, 255),
        (5, 5, 40, 18),
    )

    # region variables

    running = True
    dt = 1 / MAX_FPS  # Init dt for first frame :)

    # Player
    player = Player(screen, 300)
    enemy = Enemy(screen)

    # Healthbar
    healthbar = Healthbar(
        screen, (WIDTH // 2, 30), enemy.max_health, enemy.health
    )
    health_pickups = HealthPickupManager(screen)

    # endregion variables

    _restart_battle_music(skip_intro)

    if not skip_intro and not _play_game_intro(
        screen, clock, player, enemy, healthbar, fps_counter, health_pickups
    ):
        return "quit"

    # main game loop
    while running:
        keys = pg.key.get_pressed()
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                return "quit"

        # also quit if esc is pressed
        if keys[pg.K_ESCAPE]:
            return "quit"

        # Movement is done by the player class, so no need to update here
        if keys[pg.K_SPACE] and player.can_dash:
            player.do_dash()

        if keys[pg.K_UP]:
            player.start_attack()

        # region update

        player.update(keys, dt)
        player_damage = enemy.update(
            dt,
            player.damage_hurtbox,
            player_dash_timing=player.in_dash_timing_window,
        )
        if player_damage > 0.0:
            player.take_damage(
                player_damage, source=enemy.last_player_damage_source
            )

        pickup_heal = health_pickups.update(
            dt, player.hurtbox, player.max_health
        )
        if pickup_heal > 0.0:
            player.health = min(player.max_health, player.health + pickup_heal)

        if player.can_damage_enemy and enemy.try_take_hit(
            player.attack_rect, player.attack_damage
        ):
            player.register_attack_hit()

        if player.health <= 0.0:
            _draw_game_scene(
                screen, player, enemy, healthbar, fps_counter, health_pickups
            )
            pg.display.flip()
            _fade_to_black(screen, clock, END_FADE_DURATION)
            return "defeat"

        if enemy.health <= 0.0:
            _draw_game_scene(
                screen, player, enemy, healthbar, fps_counter, health_pickups
            )
            pg.display.flip()
            _fade_to_black(screen, clock, END_FADE_DURATION)
            return "victory"

        healthbar.update(health=enemy.health)

        fps_counter.update()

        # endregion update

        # region drawing

        _draw_game_scene(
            screen, player, enemy, healthbar, fps_counter, health_pickups
        )

        # endregion drawing

        # update the dt
        dt = clock.tick(MAX_FPS) / 1000

        # flip
        pg.display.flip()

    return "quit"


def end_screen(
    screen: pg.Surface, clock: pg.time.Clock, *, victory: bool
) -> str:
    title_font = get_game_font(112)
    text_font = get_game_font(40)
    body_font = get_game_font(32)

    title = "VICTORY" if victory else "DEFEAT"
    title_color = (245, 245, 245) if victory else (255, 215, 215)

    button_rect = pg.Rect(0, 0, 280, 72)
    button_rect.center = (WIDTH // 2, HEIGHT - 88)

    credits = [
        "Coding: Matthijs",
        "Art: Sus/Kjel",
        "Sound: Kjel/Sus",
        "",
        "Thank you for playing this game, hope it was fun!",
    ]

    while True:
        mouse_pos = pg.mouse.get_pos()
        hovered = button_rect.collidepoint(mouse_pos)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return "quit"
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                return "quit"
            if (
                event.type == pg.MOUSEBUTTONDOWN
                and event.button == 1
                and hovered
            ):
                return "restart"

        top = (18, 34, 62) if victory else (60, 16, 24)
        bottom = (8, 12, 24) if victory else (24, 8, 16)
        for y_pos in range(HEIGHT):
            blend = y_pos / max(1, HEIGHT - 1)
            color = tuple(
                round(top_c + (bottom_c - top_c) * blend)
                for top_c, bottom_c in zip(top, bottom)
            )
            pg.draw.line(screen, color, (0, y_pos), (WIDTH, y_pos))

        title_surf = title_font.render(title, True, title_color)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 120))
        screen.blit(title_surf, title_rect)

        for idx, line in enumerate(credits):
            color = (235, 235, 235) if line else (180, 180, 180)
            line_surf = body_font.render(line, True, color)
            line_rect = line_surf.get_rect(center=(WIDTH // 2, 205 + idx * 42))
            screen.blit(line_surf, line_rect)

        button_color = (72, 155, 112) if hovered else (48, 118, 86)
        pg.draw.rect(screen, button_color, button_rect, border_radius=14)
        pg.draw.rect(screen, (220, 250, 235), button_rect, 2, border_radius=14)
        button_text = text_font.render("Play Again", True, (245, 255, 248))
        button_text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, button_text_rect)

        pg.display.flip()
        clock.tick(MAX_FPS)


def main() -> None:
    # pygame initialization

    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Knight Fight")
    clock = pg.time.Clock()

    # Menu loop
    menu_screen(screen, clock)

    # ==========================================================
    # ==========================================================
    # ==========================================================

    skip_intro = False

    while True:
        outcome = game(screen, clock, skip_intro=skip_intro)
        if outcome == "quit":
            break

        end_action = end_screen(screen, clock, victory=outcome == "victory")
        if end_action != "restart":
            break

        skip_intro = True

    # Quit the pygame context
    pg.quit()


if __name__ == "__main__":
    main()
