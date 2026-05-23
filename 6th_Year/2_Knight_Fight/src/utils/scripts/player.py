import math
from pathlib import Path

import pygame as pg

from ..settings import (  # type: ignore
    WIDTH,
    HEIGHT,
    MAX_FPS,
    PLAYER_DRAG,
    DASH_STRENGTH,
    DASH_I_FRAMES,
    DASH_COOLDOWN,
    PLAYER_MAX_HEALTH,
    PLAYER_ACCEL_TIME,
    PLAYER_ATTACK_RANGE,
    PLAYER_ATTACK_DAMAGE,
    PLAYER_ATTACK_COOLDOWN,
    PLAYER_ATTACK_DURATION,
)
from .helpers import get_image, get_game_font

# Technical player constants.
PLAYER_SIZE: int                        = 40
PLAYER_SPRITE_SIZE: tuple[int, int]     = (180, 140)
PLAYER_GROUND_OFFSET: int               = 32
PLAYER_HEALTHBAR_SIZE: tuple[int, int]  = (72, 10)
PLAYER_HEALTHBAR_OFFSET: int            = 6
PLAYER_HIT_GRACE_DURATION: float        = 1.5
PLAYER_DASH_TIMING_WINDOW: float        = 0.16
DEBUG_HITBOXES: bool                    = True
DASH_BAR_SIZE: tuple[int, int]          = (80, 5)
DASH_BAR_BOTTOM_OFFSET: int             = 10
DASH_BAR_LEFT_OFFSET: int               = 10

class Player:
    """
    Player class that has movement with drag.
    Also has multiple images in a dict 'stances' with the key being the stance:
        "rest", "attack_prep" and "attack" and the value the name of the image which is used for that stance

    drag is normalized in [0, 1]:
        0.0 = no slowdown after release
        1.0 = instant stop after release
    """

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(
        self,
        screen: pg.Surface,
        max_vel: float,
    ) -> None:
        self.screen: pg.Surface = screen
        self.max_vel: float     = max_vel
        self.drag: float        = max(0.0, min(PLAYER_DRAG, 1.0))
        self.accel_time: float  = PLAYER_ACCEL_TIME
        self.stance: str        = "rest"
        self.facing: int        = 1
        self.can_dash: bool     = True
        self.dash_cooldown_duration: float = DASH_COOLDOWN
        self.dash_cooldown_timer: float = 0.0
        self.dash_fill_display: float = 1.0
        self.i_time: float      = DASH_I_FRAMES * 1 / MAX_FPS # Turn the amount of frames into a time
        self.i_timer: float     = 0.0
        self.dash_timing_timer: float = 0.0
        self.max_health: float  = float(PLAYER_MAX_HEALTH)
        self.health: float      = float(PLAYER_MAX_HEALTH)
        self.attack_damage: float = float(PLAYER_ATTACK_DAMAGE)
        self.attack_duration: float = PLAYER_ATTACK_DURATION
        self.attack_cooldown: float = PLAYER_ATTACK_COOLDOWN
        self.attack_timer: float = 0.0
        self.attack_cooldown_timer: float = 0.0
        self.attack_connected: bool = False

        # Start_pos
        self.x: float = WIDTH * 0.25
        self.y: float = HEIGHT - PLAYER_GROUND_OFFSET

        self.vx: float = 0.0

        rest = get_image(Path("player") / "Spriet_normal.png", PLAYER_SPRITE_SIZE)
        attack = get_image(Path("player") / "Sprite_attack.png", PLAYER_SPRITE_SIZE)
        self.sprites: dict[str, dict[int, pg.Surface]] = {
            "rest": {-1: pg.transform.flip(rest, True, False), 1: rest},
            "attack": {-1: pg.transform.flip(attack, True, False), 1: attack},
        }

        self.controls: dict[str, int] = {"left": pg.K_LEFT, "right": pg.K_RIGHT}
        self.ui_font = get_game_font(20)

    @property
    def is_invincible(self) -> bool:
        return self.i_timer > 0.0

    @property
    def is_attacking(self) -> bool:
        return self.attack_timer > 0.0

    @property
    def in_dash_timing_window(self) -> bool:
        return self.dash_timing_timer > 0.0

    @property
    def can_damage_enemy(self) -> bool:
        return self.is_attacking and not self.attack_connected

    @property
    def dash_charge_ratio(self) -> float:
        if self.dash_cooldown_duration <= 0.0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - (self.dash_cooldown_timer / self.dash_cooldown_duration)))

    @staticmethod
    def _approach(current: float, target: float, dt: float, time_constant: float) -> float:
        if time_constant <= 0.0:
            return target

        blend = 1.0 - math.exp(-dt / time_constant)
        return current + (target - current) * blend

    # ------------------------------------------------------------------
    # Per-frame logic
    # ------------------------------------------------------------------

    def do_dash(self) -> None:
        self.can_dash = False
        self.dash_cooldown_timer = self.dash_cooldown_duration
        self.i_timer = max(self.i_timer, self.i_time)
        self.dash_timing_timer = PLAYER_DASH_TIMING_WINDOW
        self.vx += DASH_STRENGTH * self.facing

    def start_attack(self) -> bool:
        if self.is_attacking or self.attack_cooldown_timer > 0.0:
            return False

        self.attack_timer = self.attack_duration
        self.attack_cooldown_timer = self.attack_cooldown
        self.attack_connected = False
        self.stance = "attack"
        return True

    def register_attack_hit(self) -> None:
        self.attack_connected = True

    def take_damage(self, damage: float, *, source: str = "unknown") -> bool:
        if self.is_invincible:
            print(f"[DMG] blocked source={source}")
            return False

        self.health = max(0.0, self.health - damage)
        self.i_timer = max(self.i_timer, PLAYER_HIT_GRACE_DURATION)
        print(f"[DMG] player hit source={source} amount={damage:.1f} hp={self.health:.1f}/{self.max_health:.1f}")
        return True

    def _get_sprite_and_rect(self) -> tuple[pg.Surface, pg.Rect]:
        stance = "attack" if self.is_attacking else "rest"
        sprite = self.sprites[stance][self.facing]
        vertical_offset = 8 if self.is_attacking else 0
        sprite_rect = sprite.get_rect(midbottom=(round(self.x), round(self.y - vertical_offset)))
        return sprite, sprite_rect

    @property
    def hurtbox(self) -> pg.Rect:
        _, sprite_rect = self._get_sprite_and_rect()
        return sprite_rect.inflate(-round(sprite_rect.width * 0.35), -round(sprite_rect.height * 0.12))

    @property
    def damage_hurtbox(self) -> pg.Rect:
        _, sprite_rect = self._get_sprite_and_rect()
        # Narrow and tall rect fitted to the actual player body within the wide sprite.
        box_w = max(22, round(sprite_rect.width * 0.18))
        box_h = max(55, round(sprite_rect.height * 0.72))
        damage_box = pg.Rect(0, 0, box_w, box_h)
        damage_box.center = (
            sprite_rect.centerx,
            round(sprite_rect.top + sprite_rect.height * 0.54),
        )
        return damage_box

    @property
    def attack_rect(self) -> pg.Rect | None:
        if not self.is_attacking:
            return None

        _, sprite_rect = self._get_sprite_and_rect()
        attack_rect = pg.Rect(0, 0, PLAYER_ATTACK_RANGE, max(150, sprite_rect.height + 40))
        if self.facing < 0:
            attack_rect.midright = (sprite_rect.left + 10, sprite_rect.top + sprite_rect.height // 3)
        else:
            attack_rect.midleft = (sprite_rect.right - 10, sprite_rect.top + sprite_rect.height // 3)

        return attack_rect

    def update(self, keys: pg.key.ScancodeWrapper, dt: float) -> None:
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        self.i_timer = max(0.0, self.i_timer - dt)
        self.dash_timing_timer = max(0.0, self.dash_timing_timer - dt)
        self.dash_cooldown_timer = max(0.0, self.dash_cooldown_timer - dt)
        if self.dash_cooldown_timer <= 0.0:
            self.can_dash = True

        dash_fill_target = self.dash_charge_ratio
        self.dash_fill_display = self._approach(self.dash_fill_display, dash_fill_target, dt, 0.085)
        self.stance = "attack" if self.is_attacking else "rest"

        ctrl = self.controls
        input_dir = 0

        if keys[ctrl["left"]]:
            input_dir -= 1
        if keys[ctrl["right"]]:
            input_dir += 1

        if input_dir != 0:
            self.facing = input_dir
            target_vx = self.max_vel * input_dir
            self.vx = self._approach(self.vx, target_vx, dt, self.accel_time)
        elif self.drag >= 1.0:
            self.vx = 0.0
        elif self.drag > 0.0:
            decay = (1.0 - self.drag) ** (dt * MAX_FPS)
            self.vx *= decay

        if abs(self.vx) < 0.01:
            self.vx = 0.0

        # Integrate position
        self.x += self.vx * dt

        # Wall collision — elastic bounce off screen borders
        if self.x + (PLAYER_SIZE / 2) > WIDTH:
            self.x = WIDTH - (PLAYER_SIZE / 2)
            self.vx = -self.vx * .95
        elif self.x - (PLAYER_SIZE / 2) < 0:
            self.x = (PLAYER_SIZE / 2)
            self.vx = -self.vx * .95

    def _draw_healthbar(self, sprite_rect: pg.Rect) -> None:
        ratio = max(0.0, min(1.0, self.health / self.max_health))
        bar_rect = pg.Rect(0, 0, *PLAYER_HEALTHBAR_SIZE)
        bar_rect.midtop = (sprite_rect.centerx, sprite_rect.bottom + PLAYER_HEALTHBAR_OFFSET)

        pg.draw.rect(self.screen, (30, 30, 30), bar_rect, border_radius=bar_rect.height // 2)

        if ratio > 0.0:
            fill_rect = pg.Rect(bar_rect.left, bar_rect.top, round(bar_rect.width * ratio), bar_rect.height)
            fill_color = (60, 210, 90) if ratio > 0.4 else (225, 90, 70)
            radius = min(fill_rect.height // 2, max(0, fill_rect.width // 2))
            pg.draw.rect(self.screen, fill_color, fill_rect, border_radius=radius)

        pg.draw.rect(self.screen, (230, 230, 230), bar_rect, 1, border_radius=bar_rect.height // 2)

    def _draw_invincibility_shield(self, sprite_rect: pg.Rect) -> None:
        if not self.is_invincible:
            return

        pulse = 0.65 + 0.35 * math.sin(self.i_timer * 14.0)
        alpha = round(80 + 70 * pulse)
        shield_radius = round(max(sprite_rect.width, sprite_rect.height) * (0.52 + 0.08 * pulse))

        shield_surface = pg.Surface((shield_radius * 2 + 8, shield_radius * 2 + 8), pg.SRCALPHA)
        center = (shield_surface.get_width() // 2, shield_surface.get_height() // 2)
        pg.draw.circle(shield_surface, (80, 165, 255, alpha), center, shield_radius, 3)
        pg.draw.circle(shield_surface, (170, 215, 255, min(255, alpha + 40)), center, max(6, shield_radius - 8), 2)
        shield_rect = shield_surface.get_rect(center=sprite_rect.center)
        self.screen.blit(shield_surface, shield_rect.topleft)

    def _draw_dash_bar(self) -> None:
        status_text = "READY" if self.can_dash else "CHARGING"
        status_color = (238, 238, 238) if self.can_dash else (205, 205, 205)
        label = self.ui_font.render(status_text, True, status_color)
        label_pos = (DASH_BAR_LEFT_OFFSET, HEIGHT - DASH_BAR_BOTTOM_OFFSET - DASH_BAR_SIZE[1] - label.get_height() - 6)
        self.screen.blit(label, label_pos)

        bar_rect = pg.Rect(
            DASH_BAR_LEFT_OFFSET,
            HEIGHT - DASH_BAR_BOTTOM_OFFSET - DASH_BAR_SIZE[1],
            DASH_BAR_SIZE[0],
            DASH_BAR_SIZE[1],
        )

        shadow_rect = bar_rect.move(2, 2)
        pg.draw.rect(self.screen, (24, 24, 24, 110), shadow_rect, border_radius=6)
        pg.draw.rect(self.screen, (78, 78, 78), bar_rect, border_radius=6)
        pg.draw.rect(self.screen, (170, 170, 170), bar_rect, 1, border_radius=6)

        fill_width = round(bar_rect.width * max(0.0, min(1.0, self.dash_fill_display)))
        if fill_width > 0:
            fill_rect = pg.Rect(bar_rect.left, bar_rect.top, fill_width, bar_rect.height)
            fill_radius = min(6, max(1, fill_width // 2))
            pg.draw.rect(self.screen, (242, 242, 242), fill_rect, border_radius=fill_radius)
    
    def draw(self) -> None:
        sprite, sprite_rect = self._get_sprite_and_rect()

        self._draw_dash_bar()
        self._draw_invincibility_shield(sprite_rect)
        self.screen.blit(sprite, sprite_rect)

        if DEBUG_HITBOXES:
            pg.draw.rect(self.screen, (95, 255, 170), self.damage_hurtbox, 1)

        self._draw_healthbar(sprite_rect)
