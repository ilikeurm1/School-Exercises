# --- Constants ---

# Screen
WIDTH: int = 800
HEIGHT: int = 600
MAX_FPS: int = 60

# Player tuning
PLAYER_DRAG: float = 0.125  # 0.0 = ice, 1.0 = instant stop on release (recomended = .125)
PLAYER_ACCEL_TIME: float = 0.2  # Seconds to settle toward max speed while input is held
DASH_COOLDOWN: float = 4.5 # The dash cooldown in s
DASH_STRENGTH: float = 1000 
DASH_I_FRAMES: float = 5 # The amount of frames the player is invincible after dashing
PLAYER_MAX_HEALTH: int = 100
PLAYER_ATTACK_DAMAGE: int = 15
PLAYER_ATTACK_DURATION: float = 0.18
PLAYER_ATTACK_COOLDOWN: float = 0.45
PLAYER_ATTACK_RANGE: int = 110

# Enemy tuning
ENEMY_MAX_HEALTH: int = 200
ENEMY_PHASE_TWO_THRESHOLD: float = 0.4
ENEMY_DIZZY_CHANCE: float = 0.45
ENEMY_SLASH_DAMAGE: int = 15
ENEMY_FIREBALL_DAMAGE: int = 30
ENEMY_LASER_DAMAGE: float = 22.0