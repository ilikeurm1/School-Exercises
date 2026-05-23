import math
from dataclasses import dataclass, field

import pygame as pg  # type: ignore


@dataclass
class FallingSlash:
    x: float
    y: float
    speed: float
    damage: float
    width: int = 30
    height: int = 30
    surface: pg.Surface = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.surface = _build_slash_surface(self.width, self.height)

    @property
    def rect(self) -> pg.Rect:
        return pg.Rect(
            round(self.x - self.width / 2),
            round(self.y - self.height / 2),
            self.width,
            self.height,
        )

    def update(self, dt: float) -> None:
        self.y += self.speed * dt


@dataclass
class Fireball:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    radius: int = 16
    is_barrage: bool = False

    @property
    def rect(self) -> pg.Rect:
        diameter = self.radius * 2
        return pg.Rect(
            round(self.x - self.radius),
            round(self.y - self.radius),
            diameter,
            diameter,
        )

    @property
    def hit_rect(self) -> pg.Rect:
        # Keep hitbox slightly tighter than the sprite while still matching the new larger visuals.
        if self.is_barrage:
            tight_size = max(24, round(self.radius * 2.35))
        else:
            tight_size = max(18, round(self.radius * 1.65))
        return pg.Rect(
            round(self.x - tight_size / 2),
            round(self.y - tight_size / 2),
            tight_size,
            tight_size,
        )

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt


@dataclass
class LaserStrike:
    start: tuple[float, float]
    end: tuple[float, float]
    warning_timer: float
    active_timer: float
    thickness: int

    @property
    def in_warning(self) -> bool:
        return self.warning_timer > 0.0

    @property
    def is_active(self) -> bool:
        return self.warning_timer <= 0.0 and self.active_timer > 0.0

    @property
    def is_done(self) -> bool:
        return self.warning_timer <= 0.0 and self.active_timer <= 0.0

    def update(self, dt: float) -> None:
        if self.warning_timer > 0.0:
            self.warning_timer = max(0.0, self.warning_timer - dt)
            return

        self.active_timer = max(0.0, self.active_timer - dt)


def create_falling_slash(sprite_rect: pg.Rect, speed: float, damage: float) -> FallingSlash:
    return FallingSlash(
        x=sprite_rect.centerx + sprite_rect.width * 0.1,
        y=sprite_rect.bottom - 26,
        speed=speed,
        damage=damage,
    )


def _build_slash_surface(width: int, height: int) -> pg.Surface:
    radius = max(width, height)
    sw = radius * 2 + 20
    sh = radius * 2 + 20
    surface = pg.Surface((sw, sh), pg.SRCALPHA)

    cx = sw // 2
    cy = sh // 2

    # Draw outer circle directly on surface
    pg.draw.circle(surface, (220, 230, 255, 255), (cx, cy), radius)

    # Punch a transparent hole: white mask with alpha=0 inside inner circle.
    # BLEND_RGBA_MIN keeps min of each channel — alpha becomes 0 in the hole,
    # RGB channels are untouched (255 >= any existing value).
    offset_y = int(radius * 0.28)
    inner_r  = int(radius * 0.82)
    mask = pg.Surface((sw, sh), pg.SRCALPHA)
    mask.fill((255, 255, 255, 255))
    pg.draw.circle(mask, (255, 255, 255, 0), (cx, cy - offset_y), inner_r)
    surface.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

    return surface


def draw_slash_projectile(screen: pg.Surface, projectile: FallingSlash) -> None:
    draw_rect = projectile.surface.get_rect(center=projectile.rect.center)
    screen.blit(projectile.surface, draw_rect.topleft)


def create_fireball(
    origin: tuple[float, float],
    target: tuple[float, float],
    speed: float,
    damage: float,
    radius: int = 20,
    is_barrage: bool = False,
) -> Fireball:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    length = math.hypot(dx, dy) or 1.0
    return Fireball(
        x=origin[0],
        y=origin[1],
        vx=dx / length * speed,
        vy=dy / length * speed,
        damage=damage,
        radius=radius,
        is_barrage=is_barrage,
    )


def draw_fireball(screen: pg.Surface, fireball: Fireball, sprite: pg.Surface | None = None) -> None:
    if sprite is not None:
        draw_size = max(26, fireball.radius * 2 + 24)
        scaled = pg.transform.smoothscale(sprite, (draw_size, draw_size))
        # The source art points downward at rest, so we offset by +90deg.
        angle = -math.degrees(math.atan2(fireball.vy, fireball.vx)) + 90.0
        rotated = pg.transform.rotate(scaled, angle)
        draw_rect = rotated.get_rect(center=(round(fireball.x), round(fireball.y)))
        screen.blit(rotated, draw_rect.topleft)
        return

    center = (round(fireball.x), round(fireball.y))
    pg.draw.circle(screen, (255, 110, 35), center, fireball.radius + 6)
    pg.draw.circle(screen, (255, 175, 55), center, fireball.radius + 2)
    pg.draw.circle(screen, (255, 235, 130), center, fireball.radius - 2)
    pg.draw.circle(screen, (255, 255, 220), center, max(2, fireball.radius - 8))


def draw_edge_indicator(
    screen: pg.Surface,
    origin: tuple[float, float],
    progress: float,
    *,
    large: bool = False,
    danger: bool = False,
) -> None:
    pulse = 0.6 + math.sin(progress * math.tau * 3.0) * 0.4
    base_radius = 18 if not large else 36
    radius = round(base_radius + pulse * (8 if not large else 12))
    alpha = max(50, min(190, round(120 + pulse * 70)))

    indicator = pg.Surface((radius * 2 + 12, radius * 2 + 12), pg.SRCALPHA)
    center = (indicator.get_width() // 2, indicator.get_height() // 2)
    pg.draw.circle(indicator, (255, 165, 80, alpha), center, radius)
    pg.draw.circle(indicator, (255, 235, 175, min(255, alpha + 50)), center, max(4, radius - 6), 2)

    if danger:
        warn_h = max(8, radius // 2)
        warn_w = max(3, radius // 8)
        warn_top = center[1] - warn_h // 2
        pg.draw.rect(
            indicator,
            (255, 52, 52, min(255, alpha + 50)),
            pg.Rect(center[0] - warn_w // 2, warn_top, warn_w, warn_h),
            border_radius=2,
        )
        pg.draw.circle(
            indicator,
            (255, 52, 52, min(255, alpha + 50)),
            (center[0], warn_top + warn_h + 5),
            max(2, warn_w),
        )

    draw_pos = indicator.get_rect(center=(round(origin[0]), round(origin[1])))
    screen.blit(indicator, draw_pos.topleft)


def draw_laser(screen: pg.Surface, strike: LaserStrike, elapsed_time: float) -> None:
    laser_surface = pg.Surface(screen.get_size(), pg.SRCALPHA)
    start = (round(strike.start[0]), round(strike.start[1]))
    end = (round(strike.end[0]), round(strike.end[1]))

    if strike.in_warning:
        blink = int((elapsed_time * 8.0) % 2 == 0)
        alpha = 180 if blink else 70
        color = (255, 235, 210, alpha)
        pg.draw.line(laser_surface, color, start, end, max(4, strike.thickness // 2))
        screen.blit(laser_surface, (0, 0))
        return

    pg.draw.line(laser_surface, (255, 245, 235, 150), start, end, strike.thickness + 16)
    pg.draw.line(laser_surface, (255, 255, 255, 240), start, end, strike.thickness)
    screen.blit(laser_surface, (0, 0))


def laser_collides_rect(strike: LaserStrike, rect: pg.Rect) -> bool:
    # Keep laser collision tighter than visual width so precise dodges feel fair.
    collision_padding = max(0, strike.thickness // 12)
    collision_rect = rect.inflate(-collision_padding, collision_padding)
    return bool(collision_rect.clipline(strike.start, strike.end))


def draw_transform_particles(screen: pg.Surface, sprite_rect: pg.Rect, elapsed_time: float) -> None:
    flame_colors = [
        (255, 120, 60),
        (255, 170, 70),
        (255, 210, 120),
        (255, 145, 65),
    ]

    for index, color in enumerate(flame_colors):
        side = -1 if index % 2 == 0 else 1
        sway = math.sin(elapsed_time * (2.0 + index * 0.2) + index * 0.9)
        bounce = abs(math.sin(elapsed_time * (3.2 + index * 0.15) + index * 0.7))
        x = round(sprite_rect.centerx + side * (sprite_rect.width * 0.22 + 10) + sway * 12)
        y = round(sprite_rect.bottom - 12 - bounce * (32 + index * 7))
        radius = 5 + (index % 2)

        pg.draw.circle(screen, color, (x, y), radius)
        pg.draw.circle(screen, (255, 245, 210), (x, y - 1), max(2, radius - 2))


def draw_dizzy_dots(screen: pg.Surface, sprite_rect: pg.Rect, elapsed_time: float) -> None:
    orbit_center_y = round(sprite_rect.top + sprite_rect.height * 0.2)
    orbit_radius_x = sprite_rect.width * 0.26

    for index in range(3):
        angle = elapsed_time * 3.2 + index * 2.1
        dot_pos = (
            round(sprite_rect.centerx + math.cos(angle) * orbit_radius_x),
            round(orbit_center_y + math.sin(angle * 1.25) * 12),
        )
        pg.draw.circle(screen, (255, 230, 90), dot_pos, 7)
        pg.draw.circle(screen, (255, 255, 255), dot_pos, 7, 2)
