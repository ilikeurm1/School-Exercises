from pathlib import Path
from time import sleep
import os

from pygame.mixer import Sound

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame as pg

# Get the utils paths
UTILS_PATH = Path(__file__).parent.parent
IMG_PATH = UTILS_PATH / "imgs"
SFX_PATH = UTILS_PATH / "sounds"

# Init sound module
pg.mixer.init()

mixer = pg.mixer
music = mixer.music

# region helper functions


def get_image(name: str | Path, size: int | tuple[int, int] | None = None) -> pg.Surface:
    image: pg.Surface = pg.image.load(IMG_PATH.joinpath(name))

    scale_size = size if isinstance(size, tuple) else (size, size)

    return pg.transform.scale(image, scale_size) if size else image

def load_sound(sound_file: str | Path,  *, volume: float = 0.5) -> Sound:
    sfx_file: Path = SFX_PATH / sound_file
    if sfx_file.suffix not in (".mp3", ".ogg"):
        raise NameError(
            "File does not have suffix (.mp3 / .ogg) and is therefore not supported"
        )
    
    sound = mixer.Sound(sfx_file)

    sound.set_volume(volume)
    
    return sound

def play_sound(
    sound_file: str, *, loops: int = 0, volume: float = 0.5, time: float = 0, wait: bool = False
) -> None:
    """Plays the sound with filename sound_file at volume

    time uses the mixer.music.play(fade_ms=time) argument to make the audio play for t seconds this means that the audio will get quiter over time.
    To bypass this you could make/trim the soundbyte only the part you actually need.

    Args:
        sound_file (str): the name of the file located in the utils/sounds folder
        volume (float, optional): Volume to be played at. Defaults to .5
        time (float, optional): The amount of time the sound plays (in s), if 0 the sound plays until done. Defaults to 0
        wait (bool, optional): If the program should wait until the sound is done playing. Defaults to False
    """

    sfx_file: Path = SFX_PATH / sound_file
    if sfx_file.suffix not in (".mp3", ".ogg"):
        raise NameError(
            "File does not have suffix (.mp3 / .ogg) and is therefore not supported"
        )

    music.set_volume(volume)
    music.load(SFX_PATH / sound_file)
    music.play(loops=loops, fade_ms=round(time * 1000))

    if wait:
        while music.get_busy():
            sleep(0.01)


def stop_sound(t: float | None = None) -> None:
    """Small helper that stops the current sound an optional argument t is provided to give an amount of seconds for fadeout.

    Args:
        t (float | None, optional): the amount of *seconds* the music will fade out over. Defaults to None.
    """
    if t:
        return music.fadeout(round(t * 1000))  # convert to ms

    return music.stop()


def lerp_color(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    ratio: float,
) -> tuple[int, int, int]:
    return tuple(
        round(start[index] + (end[index] - start[index]) * ratio)
        for index in range(3)
    )


_font_cache: dict[int, pg.font.Font] = {}


def get_game_font(size: int) -> pg.font.Font:
    """Return a FiraCode font at the requested pixel size, falling back to Consolas / monospace."""
    if size not in _font_cache:
        path = pg.font.match_font("firacode,fira code,consolas,inconsolata,courier new")
        _font_cache[size] = pg.font.Font(path, size) if path else pg.font.Font(None, size)
    return _font_cache[size]

# endregion helper functions

# region TESTING


# TESTING
def main() -> None:
    pg.init()

    from time import time, sleep

    print(IMG_PATH)
    print(SFX_PATH)
    get_image(Path("bgs") / "menu_background.jpg", 30)
    start_time = time()
    play_sound("alone at the edge of a universe.ogg")
    sleep(4)
    stop_sound(1)
    end_time = time()

    print(f"Played sound for: {end_time - start_time:.5}s")

    screen = pg.display.set_mode((800, 600))
    pg.display.set_caption("Night Fight")
    clock = pg.time.Clock()


    # Draw healthbar
    pg.draw.rect(screen, "white", (90, 285, 620, 30))

    for x in range(100, 701):
        pg.draw.line(screen, lerp_color((35, 130, 45), (210, 45, 45), (x - 100)/600), (x, 290), (x, 310))

    # flip
    pg.display.flip()

    running = True
    while running:
        keys = pg.key.get_pressed()
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                running = False

        # also quit if esc is pressed
        if keys[pg.K_ESCAPE]:
            break

        # update the dt
        clock.tick(24) / 1000

    # Quit the pygame context
    pg.quit()
        


if __name__ == "__main__":
    main()
    print("Program done!")

# endregion TESTING
