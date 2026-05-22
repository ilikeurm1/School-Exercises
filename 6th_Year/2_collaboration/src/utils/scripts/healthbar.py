import pygame as pg  # type: ignore

from utils.scripts.helpers import get_image, lerp_color


class Healthbar:
    def __init__(
        self,
        surface: pg.Surface,
        pos: tuple[int, int],
        max_health: float,
        health: float | None = None,
    ) -> None:
        self.surface = surface
        self.pos = pos

        self.outline = get_image("Healthbar.png")
        self.outline_rect = self.outline.get_rect(center=self.pos)
        self.fill_area = self._find_fill_area(self.outline)
        self.slot_rect = self.fill_area.move(self.outline_rect.left, self.outline_rect.top)

        self.full_color = (35, 130, 45)
        self.low_color = (210, 45, 45)
        self.empty_color = (25, 25, 25)

        self.max_health = 1.0
        self.health = 0.0
        self.health_ratio = 0.0
        self.fill_color = self.low_color
        self.fill_rect = self.slot_rect.copy()

        self.update(health=max_health if health is None else health, max_health=max_health)

    @staticmethod
    def _find_fill_area(outline: pg.Surface) -> pg.Rect:
        width, height = outline.get_size()
        min_x = width
        min_y = height
        max_x = -1
        max_y = -1

        for y in range(height):
            for x in range(width):
                if outline.get_at((x, y))[3] != 0:
                    continue

                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            return outline.get_rect()

        return pg.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def update(
        self,
        health: float | None = None,
        max_health: float | None = None,
    ) -> None:
        if max_health is not None:
            self.max_health = max(1.0, float(max_health))

        if health is not None:
            self.health = float(health)

        self.health = max(0.0, min(self.health, self.max_health))
        self.health_ratio = self.health / self.max_health
        self.fill_color = lerp_color(self.low_color, self.full_color, self.health_ratio)

        self.fill_rect = pg.Rect(
            self.slot_rect.left,
            self.slot_rect.top,
            round(self.slot_rect.width * self.health_ratio),
            self.slot_rect.height,
        )

    def draw(self) -> None:
        pg.draw.rect(
            self.surface,
            self.empty_color,
            self.slot_rect,
            border_radius=self.slot_rect.height // 2,
        )

        if self.fill_rect.width > 0:
            fill_radius = min(self.fill_rect.height // 2, max(0, self.fill_rect.width // 2))
            pg.draw.rect(
                self.surface,
                self.fill_color,
                self.fill_rect,
                border_radius=fill_radius,
            )

        self.surface.blit(self.outline, self.outline_rect)