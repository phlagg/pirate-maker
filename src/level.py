import sys
from typing import Iterable

from pygame.math import Vector2 as vector
from settings import *
from support import *
from sprites import GenericSprite, AnimatedSprite, Player, Coin, Particle, Spikes, Tooth, Shell, Block, Pearl
from timer import Timer


class Level:
    def __init__(self, grid, switch, asset_dict) -> None:
        self.display_surface = pygame.display.get_surface()
        self.switch = switch
        self.switch_timer = Timer(500)
        # groups
        self.all_sprites = CameraGroup()
        self.bg_sprites = pygame.sprite.Group()
        self.damage_sprites = pygame.sprite.Group()
        self.coin_sprites = pygame.sprite.Group()
        self.collision_sprites = pygame.sprite.Group()
        self.shell_sprites = pygame.sprite.Group()
        self.pearl_sprites = pygame.sprite.Group()

        self.build_level(grid, asset_dict)

        # animation support
        self.particle_surfs = asset_dict['particle']
        self.pearl_surf = asset_dict['pearl']

    def build_level(self, grid, asset_dict) -> None:
        for layer_name, layer in grid.items():
            for pos, data in layer.items():
                if layer_name == 'terrain':
                    GenericSprite(
                        pos= pos, 
                        surf= asset_dict['land'][data], 
                        groups= [self.all_sprites,self.collision_sprites])
                if layer_name == 'water':
                    if data == 'top':
                        AnimatedSprite(
                            pos= pos,
                            frames= asset_dict['water top'],
                            groups= self.all_sprites,
                            z= LEVEL_LAYERS['water'])
                    else:
                        GenericSprite(
                            pos= pos, 
                            surf= asset_dict['water bottom'], 
                            groups= self.all_sprites,
                            z= LEVEL_LAYERS['water'])
                match data:
                    case 0: self.player = Player(pos, asset_dict['player'], self.all_sprites, self.collision_sprites)
                    case 1: pass # sky
                    case 4: Coin(pos, asset_dict['gold'], [self.all_sprites, self.coin_sprites],coin_type='gold') 
                    case 5: Coin(pos, asset_dict['silver'], [self.all_sprites, self.coin_sprites],coin_type='silver')
                    case 6: Coin(pos, asset_dict['diamond'],[self.all_sprites, self.coin_sprites],coin_type='diamond')
                    # enemies
                    case 7: Spikes(pos, asset_dict['spikes'],[self.all_sprites, self.damage_sprites])
                    case 8: Tooth(pos, asset_dict['tooth'],[self.all_sprites, self.damage_sprites])
                    case 9: Shell(
                                orientation='left', 
                                pos= pos, 
                                frames=asset_dict['shell'],
                                groups=[self.all_sprites,self.collision_sprites,self.shell_sprites],
                                create_pearl = self.create_pearl,
                                damage_sprites = self.damage_sprites)
                    case 10: Shell(
                                orientation='right', 
                                pos= pos, 
                                frames=asset_dict['shell'],
                                groups=[self.all_sprites,self.collision_sprites,self.shell_sprites],
                                create_pearl = self.create_pearl,
                                damage_sprites = self.damage_sprites)
                    
                    # palm trees
                    case 11: 
                        AnimatedSprite(pos, asset_dict['palms']['small_fg'], self.all_sprites)
                        Block(pos, (76,50), self.collision_sprites)
                    case 12: 
                        AnimatedSprite(pos, asset_dict['palms']['large_fg'], self.all_sprites)
                        Block(pos, (76,50), self.collision_sprites)
                    case 13: 
                        AnimatedSprite(pos, asset_dict['palms']['left_fg' ], self.all_sprites)
                        Block(pos, (76,50), self.collision_sprites)
                    case 14: 
                        AnimatedSprite(pos, asset_dict['palms']['right_fg'], self.all_sprites)
                        Block(pos+vector(50,0), (76,50), self.collision_sprites)

                    case 15: AnimatedSprite(pos, asset_dict['palms']['small_bg'], self.all_sprites, LEVEL_LAYERS['bg'])
                    case 16: AnimatedSprite(pos, asset_dict['palms']['large_bg'], self.all_sprites, LEVEL_LAYERS['bg'])
                    case 17: AnimatedSprite(pos, asset_dict['palms']['left_bg' ], self.all_sprites, LEVEL_LAYERS['bg'])
                    case 18: AnimatedSprite(pos, asset_dict['palms']['right_bg'], self.all_sprites, LEVEL_LAYERS['bg'])
                    case '_': print('Error creating object')
        for sprite in self.shell_sprites:
            setattr(sprite, 'player', self.player)
    
    def create_pearl(self, pos, direction) -> None:
        Pearl(
            pos=pos,
            groups= [self.all_sprites, self.damage_sprites, self.pearl_sprites],
            surf= self.pearl_surf,
            direction= direction,
            speed= 150 )
        
    def get_coins(self) -> None: 
        collided_coins = pygame.sprite.spritecollide(sprite=self.player, group=self.coin_sprites, dokill=True)
        sprite:Coin
        for sprite in collided_coins:
            Particle(pos=sprite.rect.center, frames= self.particle_surfs, groups=self.all_sprites)
            if sprite.coin_type == 'gold':
                # add coin value to player coin total
                pass
            
    def event_loop(self) -> None:      
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if not self.switch_timer.active:
                    self.switch_timer.activate()
                    self.switch()

    def run(self, dt) -> None:
        # update
        self.event_loop()
        self.switch_timer.update()
        self.all_sprites.update(dt)
        self.get_coins()
        # draw
        self.display_surface.fill(SKY_COLOR)
        self.all_sprites.custom_draw(self.player)

class CameraGroup(pygame.sprite.Group):
    def __init__(self) -> None:
        super().__init__()
        self.display_surface =  pygame.display.get_surface()
        self.offset = vector()

    def custom_draw(self, player = None) -> None:
        self.offset.x = player.rect.centerx - WINDOW_WIDTH / 2
        self.offset.y = player.rect.centery - WINDOW_HEIGHT /2
        for sprite in self:
            for layer in LEVEL_LAYERS.values():
                if sprite.z == layer:
                    offset_rect = sprite.rect.copy()
                    offset_rect.center -= self.offset
                    self.display_surface.blit(sprite.image, offset_rect)