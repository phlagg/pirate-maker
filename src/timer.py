import pygame

class Timer:
    def __init__(self, duration, func = None) -> None:
        self.duration = duration
        self.active = False
        self.start_time = 0
        self.func = func

    def activate(self) -> None:
        self.active = True
        self.start_time = pygame.time.get_ticks()

    def deactivate(self) -> None:
        self.active = False
        self.start_time = 0


    def update(self) -> None:
        current_time = pygame.time.get_ticks()
        if current_time - self.start_time >= self.duration:
            if self.func and self.start_time:
                self.func()
            self.deactivate()