import math
import random
from dataclasses import dataclass

import pygame as pg

from ..settings import HEIGHT, WIDTH

# Spawn pacing tuned to feel helpful without becoming common spam.
PICKUP_SPAWN_MIN: float = 6.5
PICKUP_SPAWN_MAX: float = 11.0
PICKUP_LIFETIME: float = 8.0
PICKUP_HEAL_MIN_RATIO: float = 0.10
PICKUP_HEAL_MAX_RATIO: float = 0.25
PICKUP_SIZE: int = 26
PICKUP_GROUND_Y: float = HEIGHT - 58


@dataclass
class HealthPickup:
    x: float
    y: float
    size: int
    lifetime: float

    @property
    def rect(self) -> pg.Rect:
        return pg.Rect(
            round(self.x - self.size / 2),
            round(self.y - self.size / 2),
            self.size,
            self.size,
        )


class HealthPickupManager:
    def __init__(self, screen: pg.Surface) -> None:
        self.screen = screen
        self.pickup: HealthPickup | None = None
        self.spawn_timer = random.uniform(PICKUP_SPAWN_MIN, PICKUP_SPAWN_MAX)
        self.elapsed_time = 0.0

    def _spawn_pickup(self) -> None:
        self.pickup = HealthPickup(
            x=random.uniform(48.0, WIDTH - 48.0),
            y=PICKUP_GROUND_Y,
            size=PICKUP_SIZE,
            lifetime=PICKUP_LIFETIME,
        )

    def update(self, dt: float, player_rect: pg.Rect, player_max_health: float) -> float:
        self.elapsed_time += dt

        if self.pickup is None:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0.0:
                self._spawn_pickup()
                self.spawn_timer = random.uniform(PICKUP_SPAWN_MIN, PICKUP_SPAWN_MAX)
            return 0.0

        self.pickup.lifetime -= dt
        if self.pickup.lifetime <= 0.0:
            self.pickup = None
            return 0.0

        if self.pickup.rect.colliderect(player_rect):
            heal_ratio = random.uniform(PICKUP_HEAL_MIN_RATIO, PICKUP_HEAL_MAX_RATIO)
            self.pickup = None
            return player_max_health * heal_ratio

        return 0.0

    def draw(self) -> None:
        if self.pickup is None:
            return

        pulse = 0.5 + 0.5 * math.sin(self.elapsed_time * 5.0)
        bob = math.sin(self.elapsed_time * 3.2) * 3.5
        alpha = round(180 + pulse * 55)
        outer_size = self.pickup.size + 10

        outer_surface = pg.Surface((outer_size, outer_size), pg.SRCALPHA)
        outer_rect = outer_surface.get_rect(
            center=(round(self.pickup.x), round(self.pickup.y + bob))
        )

        center = (outer_size // 2, outer_size // 2)
        pg.draw.circle(
            outer_surface,
            (95, 235, 140, alpha),
            center,
            outer_size // 2,
            3,
        )
        self.screen.blit(outer_surface, outer_rect.topleft)

        box_rect = self.pickup.rect.move(0, round(bob))
        pg.draw.rect(self.screen, (42, 175, 82), box_rect, border_radius=6)
        pg.draw.rect(self.screen, (200, 255, 210), box_rect, 2, border_radius=6)

        cross_w = max(4, box_rect.width // 4)
        cross_h = max(4, box_rect.height // 4)
        v_rect = pg.Rect(0, 0, cross_w, cross_h * 2)
        h_rect = pg.Rect(0, 0, cross_h * 2, cross_w)
        v_rect.center = box_rect.center
        h_rect.center = box_rect.center
        pg.draw.rect(self.screen, (240, 255, 245), v_rect, border_radius=2)
        pg.draw.rect(self.screen, (240, 255, 245), h_rect, border_radius=2)
