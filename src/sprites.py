from pygame.math import Vector2 as vector

from settings import *
from settings import LEVEL_LAYERS
from support import *
from timer import Timer
from typing import Callable

class GenericSprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups, z = LEVEL_LAYERS['main']) -> None:
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft= pos)
        self.z = z

class Block(GenericSprite):
    def __init__(self, pos, size, groups) -> None:
        surf = pygame.Surface(size)
        super().__init__(pos, surf, groups)

class AnimatedSprite(GenericSprite):
    def __init__(self, pos, frames, groups, z = LEVEL_LAYERS['main']) -> None:
        self.frames = frames
        self.frame_index = 0
        super().__init__(pos, self.frames[self.frame_index], groups, z)
        self.animation_speed = ANIMATION_SPEED

    def animate(self, dt) -> None:
        self.frame_index += self.animation_speed * dt
        self.frame_index = 0 if self.frame_index >= len(self.frames) else self.frame_index
        self.image = self.frames[int(self.frame_index)]
    
    def update(self, dt) -> None:
        self.animate(dt)
        
class Coin(AnimatedSprite):
    def __init__(self, pos, frames, groups, coin_type) -> None:
        super().__init__(pos, frames, groups)
        self.rect = self.image.get_rect(center=pos)
        self.coin_type = coin_type

class Particle(AnimatedSprite):
    def __init__(self, pos, frames, groups) -> None:
        super().__init__(pos, frames, groups)
        self.rect = self.image.get_rect(center=pos)
    
    def animate(self, dt) -> None:
        self.frame_index += self.animation_speed * dt
        if self.frame_index < len(self.frames):
            self.image = self.frames[int(self.frame_index)]
        else:
            self.kill()

class Spikes(GenericSprite):
    def __init__(self, pos, surf, groups) -> None:
        super().__init__(pos, surf, groups)

class Tooth(GenericSprite):
    def __init__(self, pos, frames, groups) -> None:
        self.frame_index = 0
        self.frames = frames
        self.orientation = 'left'
        surf = self.frames[f'run_{self.orientation}'][self.frame_index]
        super().__init__(pos, surf, groups)
        self.rect.bottom = self.rect.top + TILE_SIZE

class Shell(GenericSprite):
    def __init__(self, orientation, pos, frames, groups, create_pearl, damage_sprites) -> None:
        self.frame_index = 0
        self.orientation = orientation
        self.pearl_direction = -1 # default left
        self.state = 'idle'
        self.frames = frames.copy()  # added copy to prevent from flipping assets for all instances
        if orientation =='right':
            self.flip_frames()
            self.pearl_direction = 1
        surf = self.frames[self.state][self.frame_index]
        super().__init__(pos, surf, groups) 
        self.rect.bottom = self.rect.top+TILE_SIZE
        # attack
        self.create_pearl: Callable[[], None] =  create_pearl
        self.has_shot = False
        self.attack_cooldown = Timer(2000)
        self.damage_sprites = damage_sprites
    
    def animate(self, dt) -> None:
        current_frames = self.frames[self.state]
        self.frame_index += ANIMATION_SPEED * dt
        if self.frame_index >= len(current_frames):
            self.frame_index = 0
            if self.has_shot:
                self.attack_cooldown.activate()
                self.has_shot = False
        self.image = current_frames[int(self.frame_index)]

        if int(self.frame_index) == 2 and self.state == 'attack' and not self.has_shot:
            self.create_pearl(self.rect.center, self.pearl_direction)
            self.has_shot = True

    def get_state(self) -> None:
        shell_pos = vector(self.rect.center)
        player_pos = vector(self.player.hitbox.center)
        player_level = abs(shell_pos.y - player_pos.y) < 30
        player_near = shell_pos.distance_to(player_pos) < 500
        player_front = shell_pos.x < player_pos.x if self.pearl_direction > 0 \
            else shell_pos.x  > player_pos.x
        if player_near and player_front and player_level and not self.attack_cooldown.active :
            self.state = 'attack'
        else:
            self.state = 'idle'

    def flip_frames(self) -> None:
        for key, surfs in self.frames.items():
            self.frames[key] = [pygame.transform.flip(surf, True, False) for surf in surfs]

    def update(self, dt) -> None:
        self.get_state()
        self.animate(dt)
        self.attack_cooldown.update()

class Pearl(GenericSprite):
    def __init__(self, pos, direction, surf, groups, speed) -> None:
        super().__init__(pos, surf, groups)
        self.image = surf
        self.direction = direction
        self.pearl_offset = vector(45*self.direction, 6)
        self.rect = self.image.get_frect(center= pos + self.pearl_offset)
        self.speed = speed
        # self destruct
        self.lifetime_timer = Timer(6000)
        self.lifetime_timer.activate()
        self.has_collided = False


    def update(self, dt) -> None:
        self.lifetime_timer.update()
        if not self.lifetime_timer.active or self.has_collided:
            self.kill()
        else:
            self.rect.x += self.speed * self.direction * dt
            

class Player(GenericSprite):
    def __init__(self, pos, assets, groups, collision_sprites) -> None:
        # animation
        self.animation_speed = ANIMATION_SPEED
        self.frames = assets
        self.frame_index = 0
        self.state = 'idle'
        self.orientation = 'right'
        surf = self.frames[f'{self.state}_{self.orientation}'][self.frame_index]
        super().__init__(pos, surf, groups)
        # movement
        self.direction = vector()
        self.pos = vector(self.rect.center)
        self.speed = 300
        self.gravity = 4
        self.on_floor = False

        # collision
        self.collision_sprites:list[pygame.sprite.Sprite] = collision_sprites
        self.hitbox = self.rect.inflate(-50,0)

    def get_state(self) -> None:
        if self.direction.y < 0 :
            self.state = 'jump'
        elif self.direction.y > 0.5:
            self.state = 'fall'
        else:
            self.state = 'run' if self.direction.x != 0 else 'idle'

    def animate(self, dt) -> None:
        current_animation = self.frames[f'{self.state}_{self.orientation}']
        self.frame_index += self.animation_speed * dt
        self.frame_index = 0 if self.frame_index >= len(current_animation) else self.frame_index
        self.image = current_animation[int(self.frame_index)]
    
    def input(self) -> None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]: 
            self.direction.x = 1
            self.orientation = 'right'
        elif keys[pygame.K_LEFT]: 
            self.direction.x = -1
            self.orientation = 'left'
        else: self.direction.x = 0

        if keys[pygame.K_SPACE] and self.on_floor:
            self.direction.y = -2

    def move(self,dt) -> None:
        # horizontal movement
        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.rect.centerx = self.hitbox.centerx
        self.collision('horizontal')
        # vertical movement
        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self.rect.centery = self.hitbox.centery
        self.collision('vertical')

    def apply_gravty(self, dt) -> None:
        self.direction.y += self.gravity * dt
        self.rect.y += self.direction.y
            

    def check_on_floor(self) -> None:
        self.floor_rect = pygame.Rect(self.hitbox.left,self.hitbox.bottom,self.hitbox.width,2)
        floor_sprites = [sprite for sprite in self.collision_sprites if sprite.rect.colliderect(self.floor_rect)]
        self.on_floor = True if floor_sprites else False

    def collision(self, direction) -> None:
        # sprite:pygame.sprite.Sprite
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox):
                if direction == 'horizontal':
                    # moving right
                    self.hitbox.right = sprite.rect.left if self.direction.x > 0 else self.hitbox.right
                    # moving left
                    self.hitbox.left = sprite.rect.right if self.direction.x < 0 else self.hitbox.left
                    self.rect.centerx, self.pos.x = self.hitbox.centerx, self.hitbox.centerx
                    
                if direction == 'vertical':
                    self.hitbox.top = sprite.rect.bottom if self.direction.y < 0 else self.hitbox.top
                    self.hitbox.bottom = sprite.rect.top if self.direction.y > 0 else self.hitbox.bottom
                    self.rect.centery, self.pos.y = self.hitbox.centery, self.hitbox.centery
                    self.direction.y = 0
                
    def update(self,dt) -> None:
        self.input()
        self.apply_gravty(dt)
        self.move(dt)
        self.check_on_floor()

        self.get_state()
        self.animate(dt)
