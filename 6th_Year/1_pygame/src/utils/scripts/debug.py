import sys
import math
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame as pg  # type: ignore


class DebugManager:
    """Encapsulates all debug state, input handling, and drawing."""

    def __init__(
        self,
        enabled: bool,
        screen: pg.Surface,
        font_tiny: pg.font.Font,
        screen_w: int,
        screen_h: int,
    ) -> None:
        self.enabled = enabled
        self.screen = screen
        self.font_tiny = font_tiny
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.overlay = enabled
        self.show_spawn_bounds = False
        self.freeze_timer = False
        self.show_hitboxes = False
        self.show_velocity = False
        self.noclip = False
        self.selected_player = 0
        self.slow_motion = False
        self.show_grid = False
        self.infinite_time = False
        self.last_action = ""

    # ── Console ──────────────────────────────────────────────────────────

    def print_legend(self) -> None:
        if not self.enabled:
            return
        print(
            "\n"
            "┌─────────────────── DEBUG MODE ───────────────────┐\n"
            "│  F1  : Toggle overlay HUD                        │\n"
            "│  F2  : Spawn +5 food per player                  │\n"
            "│  F3  : Show food spawn boundary                  │\n"
            "│  F4  : Freeze / unfreeze timer                   │\n"
            "│  F5  : Infinite time (timer stays full)          │\n"
            "│  F6  : Show hitbox circles                       │\n"
            "│  F7  : Show velocity vectors                     │\n"
            "│  F8  : Noclip mode (no player collisions)        │\n"
            "│  F9  : Teleport selected player to mouse         │\n"
            "│  F10 : Add 10 s to timer                         │\n"
            "│  F11 : Remove 10 s from timer                    │\n"
            "│  F12 : Slow-motion (half speed)                  │\n"
            "│  TAB : Cycle selected player                     │\n"
            "│  G   : Toggle coordinate grid                    │\n"
            "│  C   : Clear all food                            │\n"
            "│  R   : Respawn default food                      │\n"
            "│  0   : Reset all scores                          │\n"
            "│  P   : +1 score to selected player               │\n"
            "└──────────────────────────────────────────────────┘\n"
        )

    def _action(self, msg: str) -> None:
        self.last_action = msg
        sys.stdout.write(f"\r[DBG] {msg}" + " " * 20)
        sys.stdout.flush()

    def on_quit(self) -> None:
        if self.enabled:
            print("\n")

    # ── Event handling ───────────────────────────────────────────────────

    def handle_event(
        self,
        event: pg.event.Event,
        state: str,
        players: list,
        food: dict[int, list[tuple[int, int]]],
        time_left: float,
        game_duration: float,
        spawn_food_fn,
        food_per_player: int,
    ) -> float:
        """Process a single key-down event. Returns (possibly updated) time_left."""
        if not self.enabled or event.type != pg.KEYDOWN:
            return time_left

        key = event.key

        if key == pg.K_F1:
            self.overlay = not self.overlay
            self._action(f"Overlay {'ON' if self.overlay else 'OFF'}")

        elif key == pg.K_F2 and state == "playing":
            for p in players:
                food[p.index].extend(spawn_food_fn() for _ in range(5))
            self._action("Spawned +5 food per player")

        elif key == pg.K_F3:
            self.show_spawn_bounds = not self.show_spawn_bounds
            self._action(f"Spawn bounds {'ON' if self.show_spawn_bounds else 'OFF'}")

        elif key == pg.K_F4:
            self.freeze_timer = not self.freeze_timer
            self._action(f"Timer {'FROZEN' if self.freeze_timer else 'RUNNING'}")

        elif key == pg.K_F5:
            self.infinite_time = not self.infinite_time
            if self.infinite_time:
                time_left = game_duration
            self._action(f"Infinite time {'ON' if self.infinite_time else 'OFF'}")

        elif key == pg.K_F6:
            self.show_hitboxes = not self.show_hitboxes
            self._action(f"Hitboxes {'ON' if self.show_hitboxes else 'OFF'}")

        elif key == pg.K_F7:
            self.show_velocity = not self.show_velocity
            self._action(f"Velocity vectors {'ON' if self.show_velocity else 'OFF'}")

        elif key == pg.K_F8:
            self.noclip = not self.noclip
            self._action(f"Noclip mode {'ON' if self.noclip else 'OFF'}")

        elif key == pg.K_F9 and state == "playing":
            mx, my = pg.mouse.get_pos()
            p = players[self.selected_player]
            p.x, p.y = float(mx), float(my)
            p.vx, p.vy = 0.0, 0.0
            self._action(f"Teleported P{self.selected_player + 1} to ({mx}, {my})")

        elif key == pg.K_F10 and state == "playing":
            time_left = min(time_left + 10, game_duration)
            self._action(f"Timer +10s → {time_left:.1f}s")

        elif key == pg.K_F11 and state == "playing":
            time_left = max(0.0, time_left - 10)
            self._action(f"Timer -10s → {time_left:.1f}s")

        elif key == pg.K_F12:
            self.slow_motion = not self.slow_motion
            self._action(f"Slow motion {'ON' if self.slow_motion else 'OFF'}")

        elif key == pg.K_TAB and state == "playing":
            self.selected_player = (self.selected_player + 1) % len(players)
            sel = players[self.selected_player]
            self._action(f"Selected P{self.selected_player + 1} ({sel.color})")

        elif key == pg.K_g:
            self.show_grid = not self.show_grid
            self._action(f"Grid {'ON' if self.show_grid else 'OFF'}")

        elif key == pg.K_c and state == "playing":
            for p in players:
                food[p.index].clear()
            self._action("Cleared all food")

        elif key == pg.K_r and state == "playing":
            for p in players:
                food[p.index] = [spawn_food_fn() for _ in range(food_per_player)]
            self._action("Respawned default food")

        elif key == pg.K_0 and state == "playing":
            for p in players:
                p.score = 0
            self._action("Reset all scores to 0")

        elif key == pg.K_p and state == "playing":
            players[self.selected_player].score += 1
            s = players[self.selected_player].score
            self._action(f"P{self.selected_player + 1} score → {s}")

        return time_left

    # ── Timer logic ──────────────────────────────────────────────────────

    def update_timer(self, time_left: float, dt: float, game_duration: float) -> float:
        if self.enabled and self.freeze_timer:
            return time_left
        if self.enabled and self.infinite_time:
            return game_duration
        return max(0.0, time_left - dt)

    def apply_dt(self, dt: float) -> float:
        if self.enabled and self.slow_motion:
            return dt * 0.5
        return dt

    # ── Drawing ──────────────────────────────────────────────────────────

    def draw_world(self, food_bounds: pg.Rect) -> None:
        if not self.enabled:
            return
        if self.show_grid:
            grid_color = (40, 40, 40)
            label_color = (80, 80, 80)
            for gx in range(0, self.screen_w, 50):
                pg.draw.line(self.screen, grid_color, (gx, 0), (gx, self.screen_h))
                lbl = self.font_tiny.render(str(gx), True, label_color)
                self.screen.blit(lbl, (gx + 2, 2))
            for gy in range(0, self.screen_h, 50):
                pg.draw.line(self.screen, grid_color, (0, gy), (self.screen_w, gy))
                lbl = self.font_tiny.render(str(gy), True, label_color)
                self.screen.blit(lbl, (2, gy + 2))
        if self.show_spawn_bounds:
            pg.draw.rect(self.screen, (255, 255, 0), food_bounds, 1)

    def draw_players(self, players: list) -> None:
        if not self.enabled:
            return
        if self.show_hitboxes:
            for player in players:
                pg.draw.circle(
                    self.screen, (255, 255, 255),
                    (int(player.x), int(player.y)), player.radius, 1,
                )
                if player.index == self.selected_player:
                    pg.draw.circle(
                        self.screen, (255, 255, 0),
                        (int(player.x), int(player.y)), player.radius + 3, 2,
                    )
        if self.show_velocity:
            scale = 0.3
            for player in players:
                ex = int(player.x + player.vx * scale)
                ey = int(player.y + player.vy * scale)
                pg.draw.line(
                    self.screen, (255, 255, 0),
                    (int(player.x), int(player.y)), (ex, ey), 2,
                )

    def draw_overlay(
        self,
        state: str,
        players: list,
        food: dict[int, list[tuple[int, int]]],
        mouse_pos: tuple[int, int],
        dt: float,
        time_left: float,
    ) -> None:
        if not self.enabled or not self.overlay:
            return

        if state == "playing":
            lines: list[str] = [
                "DEBUG",
                f"State: {state}  |  dt: {dt:.4f}s",
                f"Mouse: {mouse_pos}",
            ]
            sel = players[self.selected_player]
            lines.append(f"Selected: P{self.selected_player + 1} ({sel.color})")
            lines.append("")
            for p in players:
                spd = math.hypot(p.vx, p.vy)
                lines.append(
                    f"P{p.index + 1} pos=({p.x:.1f},{p.y:.1f})  "
                    f"vel=({p.vx:.1f},{p.vy:.1f})  spd={spd:.1f}  "
                    f"score={p.score}  food={len(food[p.index])}"
                )
            lines.append("")
            flag_map = [
                (self.freeze_timer, "FROZEN"),
                (self.infinite_time, "INF-TIME"),
                (self.noclip, "NOCLIP"),
                (self.slow_motion, "SLOW-MO"),
                (self.show_spawn_bounds, "BOUNDS"),
                (self.show_hitboxes, "HITBOX"),
                (self.show_velocity, "VEL-VEC"),
                (self.show_grid, "GRID"),
            ]
            flags = [name for on, name in flag_map if on]
            lines.append(f"Flags: {' | '.join(flags) if flags else 'none'}")
            if self.last_action:
                lines.append("")
                lines.append(f"Last: {self.last_action}")

            panel_w = 420
            panel_h = len(lines) * 16 + 10
            panel_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
            panel_surf.fill((0, 0, 0, 170))
            self.screen.blit(panel_surf, (5, 50))
            for idx, line in enumerate(lines):
                dl = self.font_tiny.render(line, True, (0, 255, 100))
                self.screen.blit(dl, (10, 55 + idx * 16))
        else:
            info = [
                "DEBUG",
                f"State: {state}  |  Mouse: {mouse_pos}",
                "F1:overlay  G:grid  F3:bounds",
            ]
            panel_w = 320
            panel_h = len(info) * 16 + 10
            panel_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
            panel_surf.fill((0, 0, 0, 170))
            self.screen.blit(panel_surf, (5, 5))
            for idx, line in enumerate(info):
                dl = self.font_tiny.render(line, True, (0, 255, 100))
                self.screen.blit(dl, (10, 10 + idx * 16))
