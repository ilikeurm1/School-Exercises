import math
import random
from pathlib import Path

import pygame as pg  # type: ignore

from ..settings import (  # type: ignore
    ENEMY_DIZZY_CHANCE,
    ENEMY_FIREBALL_DAMAGE,
    ENEMY_LASER_DAMAGE,
    ENEMY_MAX_HEALTH,
    ENEMY_PHASE_TWO_THRESHOLD,
    ENEMY_SLASH_DAMAGE,
    HEIGHT,
    WIDTH,
)

try:
    from utils.scripts.helpers import get_image, load_sound
    from utils.scripts.enemy_helper import (
        Fireball,
        FallingSlash,
        LaserStrike,
        create_fireball,
        create_falling_slash,
        draw_dizzy_dots,
        draw_edge_indicator,
        draw_fireball,
        draw_laser,
        laser_collides_rect,
        draw_slash_projectile,
        draw_transform_particles,
    )
except ModuleNotFoundError:
    from .helpers import get_image, load_sound
    from .enemy_helper import (
        Fireball,
        FallingSlash,
        LaserStrike,
        create_fireball,
        create_falling_slash,
        draw_dizzy_dots,
        draw_edge_indicator,
        draw_fireball,
        draw_laser,
        laser_collides_rect,
        draw_slash_projectile,
        draw_transform_particles,
    )

# ── Shared ───────────────────────────────────────────────────────────────────
ENEMY_SPRITE_SIZE: tuple[int, int]       = (150, 185)   # all sprites scaled to this
ENEMY_MOVEMENT_SPEED: float              = 300.0         # descend and return speed
ENEMY_IDLE_DURATION: float               = 1.15
ENEMY_DIZZY_DURATION: float              = 1.6           # phase-1 stagger window
ENEMY_TRANSFORM_DURATION: float          = 3.0
# ── Phase 1 ──────────────────────────────────────────────────────────────────
ENEMY_SLASH_SPEED: float                 = 540.0
ENEMY_LASER_COOLDOWN: float              = 4.0           # seconds between lasers
ENEMY_LASER_WARNING_DURATION: float      = 0.7
ENEMY_LASER_ACTIVE_DURATION: float       = 0.3
# ── Phase 2 ──────────────────────────────────────────────────────────────────
ENEMY_FIREBALL_SPEED: float              = 420.0
ENEMY_FIREBALL_TELEGRAPH_DURATION: float = 0.85
ENEMY_BARRAGE_TELEGRAPH_DURATION: float  = 1.0
ENEMY_BARRAGE_COUNT: int                 = 32
ENEMY_PHASE_TWO_COOLDOWN: float          = 3.4           # seconds between attacks
ENEMY_PHASE_TWO_DIZZY_CHANCE: float      = 0.80
ENEMY_PHASE_TWO_DIZZY_DURATION: float    = 2.8


class Enemy:
    # States
    STATE_IDLE = "idle"
    STATE_DESCENDING = "descending"
    STATE_SWIPING = "swiping"
    STATE_RETURNING = "returning"
    STATE_DIZZY = "dizzy"
    STATE_TRANSFORMING = "transforming"

    def __init__(self, screen: pg.Surface) -> None:
        self.screen = screen
        self.max_health = float(ENEMY_MAX_HEALTH)
        self.health = float(ENEMY_MAX_HEALTH)
        self.phase_count = 1

        self.home_x = float(WIDTH // 2)
        self.home_y = 240.0
        self.x = self.home_x
        self.y = self.home_y
        self.attack_y = float(HEIGHT - 100)
        self.attack_target_x = float(WIDTH // 2)
        self.elapsed_time = 0.0
        self.state = self.STATE_IDLE
        self.state_timer = ENEMY_IDLE_DURATION
        self.transform_timer = 0.0
        self.transform_start_health = self.health
        self.swipe_spawned = False
        self.slash_projectiles: list[FallingSlash] = []
        self.phase_one_lasers: list[LaserStrike] = []
        self.phase_one_laser_cooldown = random.uniform(ENEMY_LASER_COOLDOWN * 0.75, ENEMY_LASER_COOLDOWN * 1.25)
        self.fireballs: list[Fireball] = []
        self.pending_fireballs: list[tuple[float, Fireball]] = []
        self.phase_two_cooldown = random.uniform(ENEMY_PHASE_TWO_COOLDOWN * 0.75, ENEMY_PHASE_TWO_COOLDOWN * 1.25)
        self.phase_two_telegraph_timer = 0.0
        self.phase_two_telegraph_duration = ENEMY_FIREBALL_TELEGRAPH_DURATION
        self.phase_two_indicator_origin = (self.home_x, self.home_y)
        self.phase_two_attack_target_x = self.home_x
        self.phase_two_is_barrage = False
        self.phase_two_attack_was_active = False
        self._phase_two_dizzy_pending = False
        self._phase_two_dizzy_target: tuple[float, float] = (self.home_x, self.home_y)
        self.last_player_damage_source = "none"
        self._projectile_damage_source = "none"
        self.fireball_sprite: pg.Surface | None = None
        self.pending_true_magic_timer = -1.0

        self.get_components()

    def get_components(self):
        path: Path = Path("chud")
 
        self.normal_sprite = get_image(path / "chud stance.png", ENEMY_SPRITE_SIZE)
        self.dizzy_sprite = get_image(path / "dizzy.png", ENEMY_SPRITE_SIZE)
        self.transform_frames = [
            get_image(path / f"transformation_{index}.png", ENEMY_SPRITE_SIZE)
            for index in range(5)
        ]
        self.wizard_idle_frames = [
            get_image(path / f"wizard_idle_{index}.png", ENEMY_SPRITE_SIZE)
            for index in range(3)
        ]
        self.attack_frames = [
            get_image(path / f"attack_{index}.png", ENEMY_SPRITE_SIZE)
            for index in range(3)
        ]
        self.fireball_sprite = get_image(Path("fireballs") / "fireball.png", 54)
        self.hit_sounds = [
            load_sound(path / f"owch_{index}.mp3", volume=0.35)
            for index in range(1, 6)
        ]
        self.dizzy_sound = load_sound(path / "stun.mp3", volume=0.35)
        self.transform_sound = load_sound(path / "transform.mp3", volume=0.5)
        self.true_magic_sound = load_sound(path / "true_magic.mp3", volume=0.45)

 


    @property
    def is_dizzy(self) -> bool:
        return self.state == self.STATE_DIZZY

    @staticmethod
    def _move_axis(current: float, target: float, speed: float, dt: float) -> float:
        delta = target - current
        max_step = speed * dt
        if abs(delta) <= max_step:
            return target
        return current + math.copysign(max_step, delta)

    def _idle_y(self) -> float:
        return self.home_y + math.sin(self.elapsed_time * 1.7) * 6

    def _swipe_frame_index(self) -> int:
        if self.state != self.STATE_SWIPING:
            return 0

        progress = 1.0 - max(0.0, self.state_timer / 0.42)
        return min(len(self.attack_frames) - 1, int(progress * len(self.attack_frames)))

    def _spawn_slash(self, sprite_rect: pg.Rect) -> None:
        self.slash_projectiles.append(
            create_falling_slash(
                sprite_rect,
                speed=ENEMY_SLASH_SPEED,
                damage=float(ENEMY_SLASH_DAMAGE),
            )
        )

    def _move_toward_home(self, dt: float) -> None:
        self.x = self._move_axis(self.x, self.home_x, ENEMY_MOVEMENT_SPEED, dt)
        self.y = self._move_axis(self.y, self._idle_y(), ENEMY_MOVEMENT_SPEED, dt)

    def _update_pending_fireballs(self, dt: float) -> None:
        active_pending: list[tuple[float, Fireball]] = []
        for delay, fireball in self.pending_fireballs:
            next_delay = delay - dt
            if next_delay <= 0.0:
                self.fireballs.append(fireball)
            else:
                active_pending.append((next_delay, fireball))

        self.pending_fireballs = active_pending

    def _update_projectiles(self, dt: float, player_rect: pg.Rect, player_dash_timing: bool) -> float:
        self._update_pending_fireballs(dt)
        damage = 0.0
        source = "none"

        active_slashes: list[FallingSlash] = []
        for projectile in self.slash_projectiles:
            projectile.update(dt)
            projectile_rect = projectile.rect

            if projectile_rect.top > HEIGHT:
                continue

            if projectile_rect.colliderect(player_rect):
                if projectile.damage >= damage:
                    damage = projectile.damage
                    source = "slash"
                continue

            active_slashes.append(projectile)

        self.slash_projectiles = active_slashes

        active_fireballs: list[Fireball] = []
        for fireball in self.fireballs:
            fireball.update(dt)

            if (
                fireball.x < -420.0
                or fireball.x > WIDTH + 420.0
                or fireball.y < -420.0
                or fireball.y > HEIGHT + 420.0
            ):
                continue

            if fireball.hit_rect.colliderect(player_rect):
                if fireball.is_barrage and player_dash_timing:
                    continue

                if fireball.damage >= damage:
                    damage = fireball.damage
                    source = "barrage" if fireball.is_barrage else "fireball"
                continue

            active_fireballs.append(fireball)

        self.fireballs = active_fireballs
        self._projectile_damage_source = source
        return damage

    def _start_phase_one_attack(self) -> None:
        half_width = self.attack_frames[0].get_width() // 2
        target_left = half_width
        target_right = WIDTH - half_width

        self.attack_target_x = random.uniform(target_left, target_right)

        self.state = self.STATE_DESCENDING

    def _return_home(self) -> None:
        self.state = self.STATE_RETURNING

    def _schedule_phase_two_attack(self) -> None:
        self.phase_two_is_barrage = random.random() < 0.18
        self.phase_two_telegraph_duration = (
            ENEMY_BARRAGE_TELEGRAPH_DURATION
            if self.phase_two_is_barrage
            else ENEMY_FIREBALL_TELEGRAPH_DURATION
        )
        self.phase_two_telegraph_timer = self.phase_two_telegraph_duration

        ground_y = float(HEIGHT - 68)
        origin_x = random.uniform(90.0, WIDTH - 90.0)
        self.phase_two_indicator_origin = (origin_x, -26.0)
        self.phase_two_attack_target_x = origin_x
        fireballs_to_spawn: list[tuple[float, Fireball]] = []

        if self.phase_two_is_barrage:
            angle = random.uniform(32.0, 63.0)
            if random.random() < 0.5:
                angle = -angle

            radians = math.radians(angle)
            direction = (math.sin(radians), math.cos(radians))
            perpendicular = (-direction[1], direction[0])
            diagonal = math.hypot(WIDTH, HEIGHT)
            center = (WIDTH / 2, HEIGHT / 2)
            base_origin = (
                center[0] - direction[0] * diagonal * 0.68,
                center[1] - direction[1] * diagonal * 0.68,
            )
            span = diagonal * 1.6
            self.phase_two_indicator_origin = (
                min(max(base_origin[0], 24.0), WIDTH - 24.0),
                min(max(base_origin[1], 24.0), HEIGHT - 24.0),
            )
            self.phase_two_attack_target_x = WIDTH / 2

            for index in range(ENEMY_BARRAGE_COUNT):
                offset = -span / 2 + (span * index / max(1, ENEMY_BARRAGE_COUNT - 1))
                origin = (
                    base_origin[0] + perpendicular[0] * offset,
                    base_origin[1] + perpendicular[1] * offset,
                )
                target = (
                    origin[0] + direction[0] * diagonal * 1.95,
                    origin[1] + direction[1] * diagonal * 1.95,
                )
                fireball = create_fireball(
                    origin=origin,
                    target=target,
                    speed=ENEMY_FIREBALL_SPEED,
                    damage=float(ENEMY_FIREBALL_DAMAGE),
                    radius=30,
                    is_barrage=True,
                )
                fireballs_to_spawn.append((self.phase_two_telegraph_duration, fireball))

        else:
            safe_width = 140.0
            safe_x = random.uniform(safe_width / 2 + 30, WIDTH - safe_width / 2 - 30)
            candidate_targets = [
                x_pos
                for x_pos in [90.0, 160.0, 230.0, 300.0, 370.0, 440.0, 510.0, 580.0, 650.0, 720.0]
                if abs(x_pos - safe_x) > safe_width / 2
            ]
            random.shuffle(candidate_targets)
            fireball_count = min(5, len(candidate_targets))

            for target_x in candidate_targets[:fireball_count]:
                fireballs_to_spawn.append(
                    (
                        self.phase_two_telegraph_duration + random.uniform(0.0, 0.12),
                        create_fireball(
                            origin=(origin_x, -28.0),
                            target=(target_x, ground_y),
                            speed=ENEMY_FIREBALL_SPEED,
                            damage=float(ENEMY_FIREBALL_DAMAGE),
                            is_barrage=False,
                        ),
                    )
                )

        self.pending_fireballs.extend(fireballs_to_spawn)

    def _update_phase_two(self, dt: float, player_rect: pg.Rect) -> float:
        if self.state == self.STATE_DIZZY:
            # Stay put at ground level — do NOT move back home while stunned.
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self.state = self.STATE_IDLE
                self.state_timer = ENEMY_IDLE_DURATION
                self.phase_two_cooldown = random.uniform(ENEMY_PHASE_TWO_COOLDOWN * 0.75, ENEMY_PHASE_TWO_COOLDOWN * 1.25)
            return 0.0

        self.phase_two_cooldown -= dt
        if self.phase_two_cooldown <= 0.0 and self.phase_two_telegraph_timer <= 0.0 and not self.pending_fireballs and not self._phase_two_dizzy_pending:
            self._schedule_phase_two_attack()
            self.phase_two_cooldown = random.uniform(ENEMY_PHASE_TWO_COOLDOWN * 0.75, ENEMY_PHASE_TWO_COOLDOWN * 1.25)
            if self.phase_two_is_barrage:
                self.phase_two_cooldown += random.uniform(1.8, 2.6)

        if self.phase_two_telegraph_timer > 0.0:
            self.phase_two_telegraph_timer = max(0.0, self.phase_two_telegraph_timer - dt)

        phase_two_attack_window = (
            self.phase_two_telegraph_timer > 0.0
            or bool(self.pending_fireballs)
            or bool(self.fireballs)
        )

        # Detect the moment the attack window closes; roll for a pending dizzy.
        if not phase_two_attack_window and self.phase_two_attack_was_active:
            if random.random() < ENEMY_PHASE_TWO_DIZZY_CHANCE:
                self._phase_two_dizzy_pending = True
                # Aim at player position clamped to safe screen bounds, at ground level.
                dizzy_x = float(max(90, min(WIDTH - 90, player_rect.centerx)))
                self._phase_two_dizzy_target = (dizzy_x, self.attack_y - 38.0)

        self.phase_two_attack_was_active = phase_two_attack_window

        if phase_two_attack_window:
            attack_y = self.attack_y - 38.0
            self.x = self._move_axis(self.x, self.phase_two_attack_target_x, ENEMY_MOVEMENT_SPEED * 0.8, dt)
            self.y = self._move_axis(self.y, attack_y, ENEMY_MOVEMENT_SPEED * 0.75, dt)
        elif self._phase_two_dizzy_pending:
            # Descend toward the ground near the player, then enter dizzy on arrival.
            tx, ty = self._phase_two_dizzy_target
            self.x = self._move_axis(self.x, tx, ENEMY_MOVEMENT_SPEED, dt)
            self.y = self._move_axis(self.y, ty, ENEMY_MOVEMENT_SPEED, dt)
            if abs(self.x - tx) < 28.0 and abs(self.y - ty) < 28.0:
                self._phase_two_dizzy_pending = False
                self.state = self.STATE_DIZZY
                self.state_timer = ENEMY_PHASE_TWO_DIZZY_DURATION
                self.dizzy_sound.play()
        else:
            # No pending action — float back home.
            self._move_toward_home(dt)

        return 0.0

    def _spawn_phase_one_laser(self) -> None:
        center_x = random.uniform(100.0, WIDTH - 100.0)
        center_y = HEIGHT / 2

        angle_mag = random.uniform(8.0, 32.0)
        angle = math.radians(angle_mag if random.random() < 0.5 else -angle_mag)
        direction_x = math.sin(angle)
        direction_y = math.cos(angle)

        line_extent = math.hypot(WIDTH, HEIGHT)
        start = (
            center_x - direction_x * line_extent,
            center_y - direction_y * line_extent,
        )
        end = (
            center_x + direction_x * line_extent,
            center_y + direction_y * line_extent,
        )

        self.phase_one_lasers.append(
            LaserStrike(
                start=start,
                end=end,
                warning_timer=ENEMY_LASER_WARNING_DURATION,
                active_timer=ENEMY_LASER_ACTIVE_DURATION,
                thickness=22,
            )
        )

    def _update_phase_one_lasers(self, dt: float, player_rect: pg.Rect) -> float:
        if self.state != self.STATE_DIZZY:
            self.phase_one_laser_cooldown -= dt
            if self.phase_one_laser_cooldown <= 0.0:
                self._spawn_phase_one_laser()
                self.phase_one_laser_cooldown = random.uniform(
                    ENEMY_LASER_COOLDOWN * 0.75,
                    ENEMY_LASER_COOLDOWN * 1.25,
                )

        damage = 0.0
        active_lasers: list[LaserStrike] = []
        for strike in self.phase_one_lasers:
            strike.update(dt)

            if strike.is_active and laser_collides_rect(strike, player_rect):
                damage = max(damage, ENEMY_LASER_DAMAGE)

            if not strike.is_done:
                active_lasers.append(strike)

        self.phase_one_lasers = active_lasers
        return damage

    def _update_phase_one(self, dt: float) -> None:
        if self.state == self.STATE_IDLE:
            self._move_toward_home(dt)
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self._start_phase_one_attack()
            return

        if self.state == self.STATE_DESCENDING:
            self.x = self._move_axis(self.x, self.attack_target_x, ENEMY_MOVEMENT_SPEED, dt)
            self.y = self._move_axis(self.y, self.attack_y, ENEMY_MOVEMENT_SPEED, dt)

            if abs(self.x - self.attack_target_x) < 4.0 and abs(self.y - self.attack_y) < 4.0:
                self.x = self.attack_target_x
                self.y = self.attack_y
                self.state = self.STATE_SWIPING
                self.state_timer = 0.42
                self.swipe_spawned = False
            return

        if self.state == self.STATE_SWIPING:
            self.state_timer -= dt
            _, sprite_rect = self._get_sprite_and_rect()
            if not self.swipe_spawned and self._swipe_frame_index() >= len(self.attack_frames) - 1:
                self._spawn_slash(sprite_rect)
                self.swipe_spawned = True

            if self.state_timer <= 0.0:
                if random.random() < ENEMY_DIZZY_CHANCE:
                    self.state = self.STATE_DIZZY
                    self.state_timer = ENEMY_DIZZY_DURATION
                    self.dizzy_sound.play()
                else:
                    self._return_home()
            return

        if self.state == self.STATE_DIZZY:
            self.state_timer -= dt
            if self.state_timer <= 0.0:
                self._return_home()
            return

        if self.state == self.STATE_RETURNING:
            self._move_toward_home(dt)
            idle_target_y = self._idle_y()
            if abs(self.x - self.home_x) < 2.0 and abs(self.y - idle_target_y) < 4.0:
                self.state = self.STATE_IDLE
                self.state_timer = ENEMY_IDLE_DURATION

    def _get_current_sprite(self) -> pg.Surface:
        if self.state == self.STATE_TRANSFORMING:
            progress = min(1.0, self.transform_timer / ENEMY_TRANSFORM_DURATION)
            index = min(
                len(self.transform_frames) - 1,
                int(progress * (len(self.transform_frames) - 1)),
            )
            return self.transform_frames[index]

        # Dizzy check must come BEFORE the phase-2 idle animation branch.
        if self.state == self.STATE_DIZZY:
            if self.phase_count == 2:
                # Use the first wizard idle frame as a stationary dizzy pose.
                return self.wizard_idle_frames[0]
            return self.dizzy_sprite

        if self.phase_count == 2:
            frame_index = int(self.elapsed_time * 5.0) % len(self.wizard_idle_frames)
            return self.wizard_idle_frames[frame_index]

        if self.state == self.STATE_SWIPING:
            return self.attack_frames[self._swipe_frame_index()]

        return self.normal_sprite

    def _get_sprite_and_rect(self) -> tuple[pg.Surface, pg.Rect]:
        sprite = self._get_current_sprite()
        sprite_rect = sprite.get_rect(midbottom=(round(self.x), round(self.y)))
        return sprite, sprite_rect

    @property
    def hurtbox(self) -> pg.Rect:
        _, sprite_rect = self._get_sprite_and_rect()
        return sprite_rect.inflate(-round(sprite_rect.width * 0.32), -round(sprite_rect.height * 0.16))

    def update(self, dt: float, player_rect: pg.Rect, player_dash_timing: bool = False) -> float:
        self.elapsed_time += dt

        if self.pending_true_magic_timer >= 0.0:
            self.pending_true_magic_timer -= dt
            if self.pending_true_magic_timer <= 0.0:
                self.pending_true_magic_timer = -1.0
                self.true_magic_sound.play()

        player_damage = self._update_projectiles(dt, player_rect, player_dash_timing)
        self.last_player_damage_source = self._projectile_damage_source if player_damage > 0.0 else "none"

        if self.state == self.STATE_TRANSFORMING:
            self.transform_timer += dt
            self._move_toward_home(dt)
            transform_progress = min(1.0, self.transform_timer / ENEMY_TRANSFORM_DURATION)
            heal_target = self.max_health
            self.health = self.transform_start_health + (heal_target - self.transform_start_health) * transform_progress
            if self.transform_timer >= ENEMY_TRANSFORM_DURATION:
                self.transform_timer = ENEMY_TRANSFORM_DURATION
                self.state = self.STATE_IDLE
                self.state_timer = ENEMY_IDLE_DURATION
                self.health = heal_target
                self.pending_true_magic_timer = 0.32
            return player_damage

        if self.phase_count == 2:
            player_damage = max(player_damage, self._update_phase_two(dt, player_rect))
            return player_damage

        self._update_phase_one(dt)
        laser_damage = self._update_phase_one_lasers(dt, player_rect)
        if laser_damage > player_damage:
            player_damage = laser_damage
            self.last_player_damage_source = "laser"
        elif player_damage <= 0.0:
            self.last_player_damage_source = "none"

        return player_damage

    def try_take_hit(self, attack_rect: pg.Rect | None, damage: float) -> bool:
        if attack_rect is None or not self.is_dizzy:
            return False

        if not attack_rect.colliderect(self.hurtbox):
            return False

        # damage (10% chance to crit dmg * [1.5, 2.0])
        dealt_damage = damage if random.random() > 0.1 else damage * (1.5 + random.random() * .5)
        next_health = max(0.0, self.health - dealt_damage)
        is_transform_hit = (
            self.phase_count == 1
            and next_health <= self.max_health * ENEMY_PHASE_TWO_THRESHOLD
        )

        if is_transform_hit:
            self.transform_sound.play()
            self.transform_sound.fadeout(round(max(0.1, ENEMY_TRANSFORM_DURATION - 0.25) * 1000))
        else:
            random.choice(self.hit_sounds).play()

        self.health = next_health

        if is_transform_hit:
            self.phase_count = 2
            self.state = self.STATE_TRANSFORMING
            self.state_timer = 0.0
            self.transform_timer = 0.0
            self.transform_start_health = self.health
            self.phase_two_cooldown = ENEMY_PHASE_TWO_COOLDOWN
            self.phase_two_telegraph_timer = 0.0
            self.phase_two_attack_was_active = False
            self._phase_two_dizzy_pending = False
            self._phase_two_dizzy_target = (self.home_x, self.home_y)
            self.pending_fireballs.clear()
            self.fireballs.clear()
            self.phase_one_lasers.clear()
        else:
            self._return_home()

        return True

    def draw(self) -> None:
        sprite, sprite_rect = self._get_sprite_and_rect()

        # State stuff
        if self.state == self.STATE_TRANSFORMING:
            draw_transform_particles(self.screen, sprite_rect, self.elapsed_time)

        if self.state == self.STATE_DIZZY:
            draw_dizzy_dots(self.screen, sprite_rect, self.elapsed_time)

        for strike in self.phase_one_lasers:
            draw_laser(self.screen, strike, self.elapsed_time)

        # Draw the correct enemy
        self.screen.blit(sprite, sprite_rect)

        if self.phase_two_telegraph_timer > 0.0:
            telegraph_progress = 1.0 - (self.phase_two_telegraph_timer / self.phase_two_telegraph_duration)
            draw_edge_indicator(
                self.screen,
                self.phase_two_indicator_origin,
                telegraph_progress,
                large=self.phase_two_is_barrage,
                danger=self.phase_two_is_barrage,
            )

        # Draw all the projectiles
        for projectile in self.slash_projectiles:
            draw_slash_projectile(self.screen, projectile)

        for fireball in self.fireballs:
            draw_fireball(self.screen, fireball, self.fireball_sprite)
