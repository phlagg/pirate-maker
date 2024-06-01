import os

from pygame.image import load
from pygame.math import Vector2 as vector
from editor import Editor
from level import Level
from settings import *
from support import *


class Main:
    def __init__(self) -> None:
        working_dir = os.path.dirname(__file__)
        os.chdir(working_dir)

        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.imports()

        self.editor_active = True
        self.transition = Transition(self.toggle)
        self.editor = Editor(self.land_tiles, self.switch)

        # cursor
        surf = load("../graphics/cursors/mouse.png").convert_alpha()
        cursor = pygame.cursors.Cursor((0, 0), surf)
        pygame.mouse.set_cursor(cursor)

    def imports(self) -> None:
        # terrain
        self.land_tiles = import_folder_dict('../graphics/terrain/land')
        self.water_bottom = load('../graphics/terrain/water/water_bottom.png').convert_alpha()
        self.water_top_animation = import_folder('../graphics/terrain/water/animation')
        # coins
        self.gold = import_folder('../graphics/items/gold')
        self.silver = import_folder('../graphics/items/silver')
        self.diamond = import_folder('../graphics/items/diamond')
        self.particle = import_folder('../graphics/items/particle')
        # palm trees
        self.palms = import_subfolder_dict('../graphics/terrain/palm')
        # enemies
        self.spikes = load('../graphics/enemies/spikes/spikes.png').convert_alpha()
        self.tooth = import_subfolder_dict('../graphics/enemies/tooth')
        self.shell = import_subfolder_dict('../graphics/enemies/shell_left')
        self.pearl = load('../graphics/enemies/pearl/pearl.png').convert_alpha()
        # player
        self.player_graphics = import_subfolder_dict('../graphics/player')

        

    def toggle(self) -> None:
        self.editor_active = not self.editor_active

    def switch(self, grid = None) -> None:
        if not self.transition.active:
            self.transition.active = True
            if grid:
                self.level = Level(grid, self.switch, {
                    'land': self.land_tiles,
                    'water bottom': self.water_bottom,
                    'water top': self.water_top_animation,
                    'gold': self.gold,
                    'silver': self.silver,
                    'diamond': self.diamond,
                    'particle': self.particle,
                    'palms': self.palms,
                    'spikes': self.spikes,
                    'tooth': self.tooth,
                    'shell': self.shell,
                    'pearl': self.pearl,
                    'player': self.player_graphics

                    })

    def run(self):
        while True:
            dt = self.clock.tick() / 1000
            # limit the size of dt to prevent issues when moving the window
            max_dt = 0.1
            dt = min(dt, max_dt)
            if self.editor_active: 
                self.editor.run(dt)
            else:
                self.level.run(dt)
            self.transition.display(dt)
            pygame.display.update()

class Transition:
    def __init__(self, toggle) -> None:
        self.display_surface = pygame.display.get_surface()
        self.toggle = toggle
        self.active = False
        self.border_width: int = 0
        self.direction = 1
        self.center = (WINDOW_WIDTH/2, WINDOW_HEIGHT/2)
        self.radius = vector(self.center).magnitude()
        self.threshold = self.radius + 100
    def display(self, dt) -> None:
        if self.active:
            self.border_width += int(8000 * self.direction * dt)
            if self.border_width >= self.threshold:
                self.border_width = int(self.threshold)
                self.direction = -1
                self.toggle()
            if self.border_width < 0:
                self.active = False
                self.border_width = 0
                self.direction = 1

            pygame.draw.circle(
                surface=self.display_surface, 
                color='black', 
                center=self.center, 
                radius=self.radius,
                width= self.border_width)


if __name__ == "__main__":
    main = Main()
    main.run()
