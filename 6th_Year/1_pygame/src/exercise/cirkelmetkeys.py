import os
import pygame as pg

# Import the FPSCounter class if it exists otherwise just make a dummy class
if os.path.exists(f"{os.path.dirname(__file__)}/utils/scripts/fpscounter.py"):
    from utils.scripts.fpscounter import FPSCounter

    print("Succesfully imported fpscounter.py")
else:
    # FPSCounter dummy class
    class FPSCounter:  # type: ignore
        def __init__(self, surface, font, clock, color, pos):
            pass

        def draw(self):
            pass

        def update(self):
            pass


def main():
    # Consts
    (screen_w, screen_h) = (1280, 720)
    colors = ["white", "black", "blue", "firebrick", "green", "violet"]
    max_fps = 60

    # Variables
    running = True
    r = 10
    vel = 250
    dt = 1 / max_fps

    bg_color = ""
    circle_color = ""

    # Get the bg_color and circle color
    print("Which color do you want the background to be (use nums):")
    for i, c in enumerate(colors):
        print(f"    {i}: {c}")

    while not bg_color:
        try:
            color_idx = int(input("index: "))
            bg_color = colors[color_idx]
        except (ValueError, IndexError):
            print(
                f"{color_idx} is not a valid idx please choose from 0-{len(colors) - 1}"
            )

    colors.remove(bg_color)  # remove bg_color so the circle cant be the same color

    print("Which color do you want the background to be (idx again please)")
    for i, c in enumerate(colors):
        print(f"    {i}: {c}")

    while not circle_color:
        try:
            color_idx = int(input("index: "))
            circle_color = colors[color_idx]
        except (ValueError, IndexError):
            print(
                f"{color_idx} is not a valid idx please choose from 0-{len(colors) - 1}"
            )

    # pygame initialization
    pg.init()
    screen = pg.display.set_mode((screen_w, screen_h))
    pg.display.set_caption("Anger burds")
    clock = pg.time.Clock()

    # Fps counter
    fps_counter = FPSCounter(
        screen,
        pg.font.Font(None, 24),
        clock,
        ("black" if bg_color == "white" else "white"),
        (5, 0, 75, 30),
    )

    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        # also quit if esc is pressed
        keys = pg.key.get_pressed()
        if keys[pg.K_ESCAPE]:
            running = False

        # Update

        # Circle movement
        if keys[pg.K_RIGHT] or keys[pg.K_UP]:
            if r + vel * dt < (screen_w // 2) and r + vel * dt < (screen_h // 2):
                r += vel * dt
            else:
                r = min(screen_h, screen_w) // 2

        if keys[pg.K_LEFT] or keys[pg.K_DOWN]:
            if r > 5 + vel * dt:
                r -= vel * dt
                # print(f"{r = } (did {r + vel * dt} - {vel * dt})")
            else:
                r = 5

        # FPScounter
        fps_counter.update()

        # Clear screen
        screen.fill(bg_color)

        # draw
        pg.draw.circle(screen, circle_color, (screen_w // 2, screen_h // 2), r)
        fps_counter.draw()

        # flip
        pg.display.flip()

        # dt is not neccesary => there are no physics but still...
        dt = clock.tick(max_fps) / 1000


if __name__ == "__main__":
    main()
    print("Program done!")
