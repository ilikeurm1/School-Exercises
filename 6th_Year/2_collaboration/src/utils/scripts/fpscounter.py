import pygame as pg  # type: ignore


class FPSCounter:
    """fps counter class"""

    def __init__(
        self,
        surface: pg.Surface,
        font: pg.font.Font,
        clock: pg.time.Clock,
        color: tuple[int, int, int] | str,
        pos: tuple[int, int, int, int],
    ) -> None:
        self.surface = surface
        self.font = font
        self.clock = clock
        self.color = color
        self.pos = pos

        self.fps_text = self.font.render(
            str(int(self.clock.get_fps())) + "FPS", False, self.color
        )
        self.fps_text_rect = self.fps_text.get_rect(
            center=(self.pos[0] + (self.pos[2] // 2), self.pos[1] + (self.pos[3] // 2))
        )

    def draw(self) -> None:
        # Draw the counter
        self.surface.blit(self.fps_text, self.fps_text_rect)

    def update(self) -> None:
        text = f"FPS: {self.clock.get_fps():2.0f}"
        self.fps_text = self.font.render(text, True, self.color)
        self.fps_text_rect = self.fps_text.get_rect(
            center=(self.pos[0] + (self.pos[2] // 2), self.pos[1] + (self.pos[3] // 2))
        )


# The fpscounter test
def main() -> None:
    print("FPS COUNTER TEST\n\n")

    # region consts

    max_fps = 60
    screen_dims = (1280, 720)
    screen_w, screen_h = screen_dims
    avg_fps_update_ms = 2000

    # endregion consts

    # pygame initialization
    pg.init()
    screen = pg.display.set_mode(screen_dims)
    pg.display.set_caption("FPS counter")
    clock = pg.time.Clock()

    # Fps counter
    fps_counter = FPSCounter(
        screen,
        pg.font.Font(None, 100),
        clock,
        (255, 255, 255),
        (5, 0, screen_w, screen_h),
    )

    # region variables

    running = True
    allow_fps_change = True
    fps_list = []
    avg_fps_text = f"Avg fps ({1000 / avg_fps_update_ms}hz): 0"

    # events
    FPS_CHANGE_EVENT = pg.USEREVENT + 1
    GET_AVG_FPS = pg.USEREVENT + 2

    # event timers
    pg.time.set_timer(FPS_CHANGE_EVENT, 100)
    pg.time.set_timer(GET_AVG_FPS, avg_fps_update_ms)

    # endregion variables

    # main game loop
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == FPS_CHANGE_EVENT:
                allow_fps_change = True
            elif event.type == GET_AVG_FPS:
                if len(fps_list) > 0:
                    avg_fps_text = f"Avg fps ({1000 / avg_fps_update_ms:.1f}hz): {sum(fps_list) / len(fps_list):.2f}"
                    fps_list.clear()

        # also quit if esc is pressed
        keys = pg.key.get_pressed()
        if keys[pg.K_ESCAPE]:
            running = False

        if allow_fps_change:
            if keys[pg.K_LSHIFT]:
                if keys[pg.K_UP]:
                    max_fps += 10
                elif keys[pg.K_DOWN]:
                    max_fps -= 10
                allow_fps_change = False
            else:
                if keys[pg.K_UP]:
                    max_fps += 1
                elif keys[pg.K_DOWN]:
                    max_fps -= 1
                allow_fps_change = False

            if max_fps < 10:
                max_fps = 10
            elif max_fps > 350:
                max_fps = 350

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("black")

        # region update

        fps_counter.update()

        # update the fps text
        max_fps_text = "FPS Limit: " + str(max_fps)
        fps_font = pg.font.Font(None, 24)
        fps_text = fps_font.render(max_fps_text, True, (255, 255, 255))
        fps_text_rect = fps_text.get_rect(center=(screen_w / 2, 15))

        # update the avg fps text
        avg_text = fps_font.render(avg_fps_text, True, (255, 255, 255))
        avg_text_rect = avg_text.get_rect(center=(screen_w / 2, screen_h - 15))

        # endregion update

        # region drawing

        fps_counter.draw()
        screen.blit(fps_text, fps_text_rect)
        screen.blit(avg_text, avg_text_rect)

        # endregion drawing

        # update the dt
        clock.tick(max_fps)

        fps_list.append(clock.get_fps())

        # flip
        pg.display.flip()

    # Quit the pygame context
    pg.quit()


if __name__ == "__main__":
    main()
    print("Program done!")
