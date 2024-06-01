import sys
from pygame.math import Vector2 as vector
from pygame.mouse import get_pos as mouse_pos
from pygame.mouse import get_pressed as mouse_btns
from pygame.image import load
from functools import partial
from typing import NewType
from random import choice, randint
from menu import Menu
from settings import *
from support import *
from timer import Timer

LevelGrid = NewType('LevelGrid', dict[dict])

class Editor:
    def __init__(self, land_tiles, switch) -> None:
        # main setup
        self.display_surface = pygame.display.get_surface()
        self.canvas_data: dict[CanvasTile] = {}
        self.switch = switch
        # imports
        self.land_tiles = land_tiles
        self.imports()
        # clouds
        self.current_clouds = []
        self.cloud_surf = import_folder('../graphics/clouds')
        self.cloud_timer = pygame.USEREVENT + 1
        pygame.time.set_timer(self.cloud_timer, 2000) 
        # navigation
        self.origin = vector()
        self.pan_active = False
        self.pan_offset = vector(0, 0)
        # support lines
        self.support_line_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.support_line_surf.set_colorkey("green")
        self.support_line_surf.set_alpha(30)
        # selection
        self.selection_index = 2
        self.last_selected_cell = None
        self.menu = Menu()
        # objects
        self.canvas_objects = pygame.sprite.Group()
        self.fg_objects = pygame.sprite.Group()
        self.bg_objects = pygame.sprite.Group()
        self.object_drag_active = False
        self.object_timer = Timer(400)
        self.switch_timer = Timer(500)
        
        # player
        CanvasObject(
            pos=(200,WINDOW_HEIGHT/2),
            frames= self.animations[0]['frames'],
            tile_id= 0,
            origin= self.origin,
            groups= [self.canvas_objects, self.fg_objects]
        )
        # sky
        self.sky_handle = CanvasObject(
            pos = (WINDOW_WIDTH/2, WINDOW_HEIGHT/2),
            frames = [self.sky_handle_surface],
            tile_id = 1,
            origin = self.origin,
            groups = [self.canvas_objects, self.bg_objects]
        )
        self.startup_clouds()

    # Support
    def get_current_cell(self, obj = None) -> tuple[int, int]:
        current_pos = vector(mouse_pos()) if not obj else vector(obj.distance_to_origin)
        distance_to_origin = current_pos - self.origin
        if distance_to_origin.x > 0:
            col = int(distance_to_origin.x / TILE_SIZE)
        else:
            col = int(distance_to_origin.x / TILE_SIZE) - 1
        if distance_to_origin.y > 0:
            row = int(distance_to_origin.y / TILE_SIZE)
        else:
            row = int(distance_to_origin.y / TILE_SIZE) - 1
        return col, row

    def check_neighbours(self,cell_pos) -> None:
        # create a local cluster
        cluster_size = 3
        local_cluster = [
            (col + cell_pos[0] - int(cluster_size/2), row + cell_pos[1]- int(cluster_size/2)) 
            for col in range(cluster_size) 
            for row in range(cluster_size)]
        # check neighbours
        for cell in local_cluster:
            if cell in self.canvas_data:
                self.canvas_data[cell].terrain_neighbours = []
                self.canvas_data[cell].water_on_top = False
                for name, side in NEIGHBOR_DIRECTIONS.items():
                    neighbour_cell = (cell[0] + side[0], cell[1]+ side[1])      
                    if neighbour_cell in self.canvas_data:
                        # water top neighbour
                        if self.canvas_data[neighbour_cell].has_water \
                            and self.canvas_data[cell].has_water and name == 'A': 
                            self.canvas_data[cell].water_on_top = True

                        # terrain neighbours 
                        if self.canvas_data[neighbour_cell].has_terrain:
                            self.canvas_data[cell].terrain_neighbours.append(name)
                        
    def imports(self) -> None:
        self.water_bottom = load('../graphics/terrain/water/water_bottom.png').convert_alpha()
        self.sky_handle_surface = load('../graphics/cursors/handle.png').convert_alpha()
        # animations
        self.animations = {}
        for key,value in EDITOR_DATA.items():
            if value['graphics']:
                graphics = import_folder(value['graphics'])
                self.animations[key] = {
                    'frame_index': 0,
                    'frames': graphics,
                    'length': len(graphics)
                }
        # preview
        self.preview_surfs = {key:load(value['preview']) for key,value in EDITOR_DATA.items() if value['preview']}

    def animation_update(self, dt) -> None:
        for value in self.animations.values():
            value['frame_index'] += ANIMATION_SPEED * dt
            if value['frame_index'] >= value['length']:
                value['frame_index'] = 0
    
    def mouse_on_object(self) -> 'CanvasObject':
        for sprite in self.canvas_objects:
            if sprite.rect.collidepoint(mouse_pos()):
                return sprite
    
    def create_grid(self) -> LevelGrid:
        # add objects to tiles
        for tile in self.canvas_data.values():
            tile.objects = []
        for obj in self.canvas_objects:
            current_cell = self.get_current_cell(obj)
            offset = obj.distance_to_origin - (vector(current_cell) * TILE_SIZE) 
            if current_cell in self.canvas_data:
                self.canvas_data[current_cell].add_id(obj.tile_id, offset)
            else:
                self.canvas_data[current_cell] = CanvasTile(obj.tile_id, offset)
        
        # create empty grid
        layers = LevelGrid({
            'water':{},
            'bg palms': {},
            'terrain': {},
            'enemies': {},
            'coins': {},
            'fg objects': {}
        })
        

        # grid offset
        left = sorted(self.canvas_data.keys(), key= lambda tile: tile[0])[0][0] # [first value][x pos]
        top  = sorted(self.canvas_data.keys(), key= lambda tile: tile[1])[0][1] # [first value][y pos]
        
        # fill the grid
        tile:CanvasTile
        for tile_pos, tile in self.canvas_data.items():
            col_adjusted = tile_pos[0] - left
            row_adjusted = tile_pos[1] - top
            x = col_adjusted * TILE_SIZE
            y = row_adjusted * TILE_SIZE

            if tile.has_water:
                layers['water'][(x,y)] = tile.get_water()
            if tile.has_terrain:
                layers['terrain'][(x,y)] = tile.get_terrain() if tile.get_terrain() in self.land_tiles else 'X'
            if tile.coin:
                layers['coins'][(x + TILE_SIZE/2, y + TILE_SIZE/2)] = tile.coin
            if tile.enemy:
                layers['enemies'][(x,y)] = tile.enemy
            if tile.objects:
                for obj, offset in tile.objects:
                    if obj in [key for key,value in EDITOR_DATA.items() if value['style']=='palm_bg']:
                        layers['bg palms'][(int(x + offset.x), int(y + offset.y))] = obj
                    else:
                        layers['fg objects'][(int(x + offset.x), int(y + offset.y))] = obj

        return layers


    # input
    def event_loop(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if not self.switch_timer.active:
                    self.switch_timer.activate()
                    self.switch(self.create_grid())
            
            self.pan_input(event)
            self.selection_hotkeys(event)
            self.menu_click(event)

            self.object_drag(event)

            self.canvas_add()
            self.canvas_remove()

            self.create_clouds(event)

    def pan_input(self, event) -> None:
        # middle mouse button pressed /released
        if event.type == pygame.MOUSEBUTTONDOWN and mouse_btns()[1]:
            self.pan_active = True
            self.pan_offset = vector(mouse_pos()) - self.origin
        if not mouse_btns()[1]:
            self.pan_active = False
        # mousewheel
        if event.type == pygame.MOUSEWHEEL:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LCTRL]:
                self.origin.y -= event.y * 50
            else:
                self.origin.x -= event.y * 50
        # panning update
        if self.pan_active:
            self.origin = vector(mouse_pos()) - self.pan_offset
            for sprite in self.canvas_objects:
                sprite.pan_pos(self.origin)

    def selection_hotkeys(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.selection_index += 1
            if event.key == pygame.K_LEFT:
                self.selection_index -= 1
        self.selection_index = max(min(self.selection_index, 18), 2)

    def menu_click(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and self.menu.rect.collidepoint(
            (mouse_pos())
        ):
            self.selection_index = self.menu.click(mouse_pos(), mouse_btns())

    def canvas_add(self) -> None:
        if mouse_btns()[0] and not self.menu.rect.collidepoint(mouse_pos()) and not self.object_drag_active:
            current_cell = self.get_current_cell()
            # Tiles
            if EDITOR_DATA[self.selection_index]['type'] == 'tile':
                if current_cell != self.last_selected_cell:
                    if current_cell in self.canvas_data:
                        self.canvas_data[current_cell].add_id(self.selection_index)
                    else:
                        self.canvas_data[current_cell] = CanvasTile(self.selection_index)
                    self.check_neighbours(current_cell)
                    self.last_selected_call = current_cell
            # Objects
            else:
                if not self.object_timer.active:
                    groups = [self.canvas_objects]
                    if EDITOR_DATA[self.selection_index]['style'] == 'palm_bg':groups.append(self.bg_objects)
                    else: groups.append(self.fg_objects) 
                    CanvasObject(
                        pos=mouse_pos(),
                        frames = self.animations[self.selection_index]['frames'],
                        tile_id= self.selection_index,
                        origin = self.origin,
                        groups = groups)
                    self.object_timer.activate()
    
    def canvas_remove(self) -> None:
        if mouse_btns()[2] and not self.menu.rect.collidepoint((mouse_pos())):
            # delete object
            selected_object = self.mouse_on_object()
            if selected_object and EDITOR_DATA[selected_object.tile_id]['style'] not in ('player', 'sky'):
                selected_object.kill()
            # delete tiles
            if self.canvas_data:
                current_cell = self.get_current_cell()
                if current_cell in self.canvas_data:
                    self.canvas_data[current_cell].remove_id(self.selection_index)
                
                    if self.canvas_data[current_cell].is_empty:
                        del self.canvas_data[current_cell]
                    self.check_neighbours(current_cell)
    
    def object_drag(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and mouse_btns()[0]:
            for sprite in self.canvas_objects:
                if sprite.rect.collidepoint(event.pos):
                    sprite.start_drag()
                    self.object_drag_active = True
        if event.type == pygame.MOUSEBUTTONUP and self.object_drag_active:
            for sprite in self.canvas_objects:
                if sprite.selected:
                    sprite.end_drag(self.origin)
                    self.object_drag_active = False
    

    # drawing
    def draw_tile_lines(self) -> None:
        cols, rows = WINDOW_WIDTH // TILE_SIZE, WINDOW_HEIGHT // TILE_SIZE
        origin_offset = vector(
            x=self.origin.x - int(self.origin.x / TILE_SIZE) * TILE_SIZE,
            y=self.origin.y - int(self.origin.y / TILE_SIZE) * TILE_SIZE,
        )
        self.support_line_surf.fill("green")
        for col in range(cols + 1):
            x = origin_offset.x + col * TILE_SIZE
            pygame.draw.line(
                self.support_line_surf, LINE_COLOR, (x, 0), (x, WINDOW_HEIGHT)
            )
        for row in range(rows + 1):
            y = origin_offset.y + row * TILE_SIZE
            pygame.draw.line(
                self.support_line_surf, LINE_COLOR, (0, y), (WINDOW_WIDTH, y)
            )
        self.display_surface.blit(self.support_line_surf, (0, 0))

    def draw_level(self) -> None:
        self.bg_objects.draw(self.display_surface)
        for cell_pos, tile in self.canvas_data.items():
            pos = self.origin + vector(cell_pos) * TILE_SIZE
            # water
            if tile.has_water:
                if tile.water_on_top:
                    self.display_surface.blit(self.water_bottom, pos)
                else:
                    frames = self.animations[3]['frames']
                    index = int(self.animations[3]['frame_index'])
                    surf = frames[index]
                    self.display_surface.blit(surf, pos)
            # coins
            if tile.coin:
                frames = self.animations[tile.coin]['frames']
                index = int(self.animations[tile.coin]['frame_index'])
                surf = frames[index]
                rect = surf.get_rect(center= (pos.x + TILE_SIZE//2, pos.y + TILE_SIZE//2))
                self.display_surface.blit(surf, rect)
            # enemies
            if tile.enemy:
                frames = self.animations[tile.enemy]['frames']
                index = int(self.animations[tile.enemy]['frame_index'])
                surf = frames[index]
                rect = surf.get_rect(midbottom= (pos.x + TILE_SIZE//2, pos.y + TILE_SIZE))
                self.display_surface.blit(surf, rect)
            # terrain
            if tile.has_terrain:
                terrain_string = ''.join(tile.terrain_neighbours)
                terrain_style = terrain_string if terrain_string in self.land_tiles else 'X'
                self.display_surface.blit(self.land_tiles[terrain_style], pos)
        self.fg_objects.draw(self.display_surface)
    
    def preview(self) -> None:
        selected_object = self.mouse_on_object()
        if not self.menu.rect.collidepoint(mouse_pos()):    
            if selected_object:
                rect = selected_object.rect.inflate(10,10)
                color = 'black'
                width = 3
                size = 15
                # draws lines around objects when hovering
                corner = partial(pygame.draw.lines,
                    surface=self.display_surface, 
                    color=color, 
                    closed=False, 
                    width=width)
                # top left 
                corner(points=((rect.left,rect.top+size), rect.topleft,(rect.left+size,rect.top)))
                # bottom left
                corner(points=((rect.left,rect.bottom-size),rect.bottomleft,(rect.left+size,rect.bottom)))                
                # top right
                corner(points=((rect.right,rect.top+size),rect.topright,(rect.right-size,rect.top)))                
                # bottom right 
                corner(points=((rect.right,rect.bottom-size),rect.bottomright,(rect.right-size,rect.bottom)))
                
            else:
                # preview
                type_dict = {key: value['type'] for key,value in EDITOR_DATA.items()}
                surf = self.preview_surfs[self.selection_index].copy()
                surf.set_alpha(200)
                # tile
                if type_dict[self.selection_index] == 'tile':
                    current_cell = self.get_current_cell()
                    rect = surf.get_rect(topleft = self.origin + vector(current_cell) * TILE_SIZE)
                # object
                else:
                    rect = surf.get_rect(center = mouse_pos())
                self.display_surface.blit(surf, rect)
    
    def display_sky(self, dt) -> None:
        self.display_surface.fill(SKY_COLOR)
        y = self.sky_handle.rect.centery

        # horizon lines
        if y > 0 :
            horizon_rect1 = pygame.Rect(0, y - 10, WINDOW_WIDTH, 10)
            horizon_rect2 = pygame.Rect(0, y - 16, WINDOW_WIDTH,  4)
            horizon_rect3 = pygame.Rect(0, y - 20, WINDOW_WIDTH, 3)
            pygame.draw.rect(self.display_surface, HORIZON_TOP_COLOR, horizon_rect1)
            pygame.draw.rect(self.display_surface, HORIZON_TOP_COLOR, horizon_rect2)
            pygame.draw.rect(self.display_surface, HORIZON_TOP_COLOR, horizon_rect3)
            self.display_clouds(dt, y)
        
        # sea
        if 0< y < WINDOW_HEIGHT:
            sea_rect = pygame.Rect(0,y, WINDOW_WIDTH, WINDOW_HEIGHT)
            pygame.draw.rect(self.display_surface, SEA_COLOR, sea_rect )
            pygame.draw.line(self.display_surface, HORIZON_COLOR, (0,y), (WINDOW_WIDTH, y), 3)
        if y <= 0:
            self.display_surface.fill(SEA_COLOR)
    
    def display_clouds(self, dt, horizon_y) -> None:
        for cloud in self.current_clouds: #[{surf, pos, speed}]
            cloud['pos'][0] -= cloud ['speed'] * dt
            x = cloud['pos'][0]
            y = horizon_y - cloud['pos'][1]
            self.display_surface.blit(cloud['surf'], (x,y))             
    
    def create_clouds(self, event) -> None:
        if event.type == self.cloud_timer:
            surf = choice(self.cloud_surf)
            surf = pygame.transform.scale2x(surf) if randint(0,4) < 2 else surf
            pos = [WINDOW_WIDTH + randint(50,100),randint(0,WINDOW_HEIGHT)]
            speed = randint(20,50)
            self.current_clouds.append({'surf':surf, 'pos': pos, 'speed': speed})
            # remove clouds
            self.current_clouds = [cloud for cloud in self.current_clouds if cloud['pos'][0] > -400]
    
    def startup_clouds(self) -> None:
        for i in range(20):
            surf = choice(self.cloud_surf)
            surf = pygame.transform.scale2x(surf) if randint(0,4) < 2 else surf
            pos = [randint(0,WINDOW_WIDTH),randint(0,WINDOW_HEIGHT-self.sky_handle.rect.bottom)]
            speed = randint(15,45)
            self.current_clouds.append({'surf':surf, 'pos': pos, 'speed': speed})
            
    
    # update
    def run(self, dt) -> None:
        self.event_loop()
        # updating
        self.animation_update(dt)
        self.canvas_objects.update(dt)
        self.object_timer.update()
        self.switch_timer.update()

        # drawing
        self.display_surface.fill("gray")
        self.display_sky(dt)
        self.draw_level()
        self.draw_tile_lines()
        # pygame.draw.circle(self.display_surface, "red", self.origin, 10)
        self.preview()
        self.menu.display(self.selection_index)


class CanvasTile:
    def __init__(self, tile_id, offset = vector()) -> None:
        # terrain
        self.has_terrain = False
        self.terrain_neighbours = []
        # water
        self.has_water = False
        self.water_on_top = False
        # coin
        self.coin = None  # 4, 5, 6
        # enemy
        self.enemy = None
        # objects
        self.objects: list[CanvasObject] = []
        self.add_id(tile_id, offset=offset)
        self.is_empty = False

    def add_id(self, tile_id, offset = vector()) -> None:
        options = {key: value["style"] for key, value in EDITOR_DATA.items()}
        match options[tile_id]:
            case "terrain": self.has_terrain = True
            case "water": self.has_water = True
            case "coin": self.coin = tile_id
            case "enemy": self.enemy = tile_id
            case _:
                if (tile_id, offset) not in self.objects:
                    self.objects.append((tile_id,offset))
            
    def remove_id(self, tile_id) -> None:
        options = {key: value["style"] for key, value in EDITOR_DATA.items()}
        match options[tile_id]:
            case "terrain": self.has_terrain = False
            case "water": self.has_water = False
            case "coin": self.coin = None
            case "enemy": self.enemy = None
            case _: print("invalid tile")
        self.check_content()

    def check_content(self) -> None:
        if not self.has_terrain and not self.has_water and not self.coin and not self.enemy:
            self.is_empty = True

    def get_water(self) -> str:
        return 'bottom' if self.water_on_top else 'top'
    
    def get_terrain(self) -> str:
        return ''.join(self.terrain_neighbours)

class CanvasObject(pygame.sprite.Sprite):
    def __init__(self, pos, frames, tile_id, origin, groups) -> None:
        super().__init__(groups)
        self.tile_id = tile_id
        # animation
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center = pos)
        # movement
        self.distance_to_origin = vector(self.rect.topleft) - origin
        self.selected = False
        self.mouse_offset = vector()
    
    def start_drag(self) -> None:
        self.selected = True
        self.mouse_offset = vector(mouse_pos()) - vector(self.rect.topleft)
    
    def end_drag(self, origin) -> None:
        self.selected = False
        self.distance_to_origin = vector(self.rect.topleft) - origin

    def drag(self) -> None:
        if self.selected:
            self.rect.topleft = mouse_pos() -self.mouse_offset
    
    def animate(self, dt) -> None:
        self.frame_index += ANIMATION_SPEED * dt
        if self.frame_index >= len(self.frames):
            self.frame_index = 0
        self.image = self.frames[int(self.frame_index)]
        self.rect = self.image.get_rect(midbottom = self.rect.midbottom)

    def pan_pos(self, origin) -> None:
        self.rect.topleft = origin + self.distance_to_origin

    def update(self,dt) -> None:
        self.animate(dt)
        self.drag()