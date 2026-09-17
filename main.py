import sys
import random
import pygame
from assets import AssetManager
from effects import ParticleSystem

pygame.init()

# Game Canvas (320x240) and Window Scale
GAME_W, GAME_H = 320, 240
SCALE = 3
WINDOW_W, WINDOW_H = GAME_W * SCALE, GAME_H * SCALE

SCREEN = pygame.display.set_mode((WINDOW_W, WINDOW_H))
CANVAS = pygame.Surface((GAME_W, GAME_H))
pygame.display.set_caption("Zero Kelvin - Endless")
CLOCK = pygame.time.Clock()

assets = AssetManager()
particles = ParticleSystem(GAME_W, GAME_H, assets.images["snowflake"])

DOF_TYPES = ["LEFT", "UP", "DOWN", "RIGHT"]
current_dof_idx = 0
dof_charges = 3
last_charge_time = pygame.time.get_ticks()

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width_in_tiles=4, p_type="normal"):
        super().__init__()
        self.p_type = p_type
        self.width_in_tiles = width_in_tiles
        self.tile_img = assets.images.get(f"tile_{p_type}", assets.images["tile_normal"])
        
        # Render dynamic wide platform surface
        self.image = pygame.Surface((16 * width_in_tiles, 16), pygame.SRCALPHA)
        for i in range(width_in_tiles):
            self.image.blit(self.tile_img, (i * 16, 0))
            
        self.rect = self.image.get_rect(topleft=(x, y))

    def apply_dof(self, dof_type):
        if dof_type == "LEFT": self.rect.x -= 24
        elif dof_type == "RIGHT": self.rect.x += 24
        elif dof_type == "UP": self.rect.y -= 20
        elif dof_type == "DOWN": self.rect.y += 20

class Token(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = assets.images["dof"]
        self.rect = self.image.get_rect(center=(x, y))

class Spike(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = assets.images["spike"]
        self.rect = self.image.get_rect(bottomleft=(x, y))

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = assets.images["robot"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        self.speed = 2.0
        self.is_grounded = False

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_d]:
            self.rect.x += self.speed

        if keys[pygame.K_SPACE] and self.is_grounded:
            self.vel_y = -5.5
            self.is_grounded = False

        self.vel_y += 0.3
        self.rect.y += int(self.vel_y)

        self.is_grounded = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0 and self.rect.bottom - int(self.vel_y) <= platform.rect.top + 4:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.is_grounded = True

# Groups
platforms = pygame.sprite.Group()
tokens = pygame.sprite.Group()
spikes = pygame.sprite.Group()
player = Player(40, 140)

# Improved Infinite World Generation State
last_spawn_x = 0
last_spawn_y = 180
min_gap, max_gap = 25, 45
game_time = 0

def spawn_world_chunk():
    global last_spawn_x, last_spawn_y
    while last_spawn_x < player.rect.x + GAME_W + 120:
        # Calculate dynamic gaps based on game progression
        gap = random.randint(int(min_gap), int(max_gap))
        
        # Keep next platform height within reachable jump distance
        y_change = random.choice([-25, -15, 0, 15, 25])
        spawn_y = max(80, min(GAME_H - 40, last_spawn_y + y_change))
        
        # Dynamic platform width (4 to 7 tiles wide)
        tile_count = random.randint(4, 7)
        spawn_x = last_spawn_x + gap
        
        p_type = random.choice(["normal", "ice", "crack0"])
        plat = Platform(spawn_x, spawn_y, tile_count, p_type)
        platforms.add(plat)
        
        # Hazard and Token Placement
        if random.random() < 0.3:
            spike_offset = random.randint(1, tile_count - 1) * 16
            spikes.add(Spike(spawn_x + spike_offset, spawn_y))
        elif random.random() < 0.25:
            token_offset = (tile_count * 16) // 2
            tokens.add(Token(spawn_x + token_offset, spawn_y - 10))

        last_spawn_x = spawn_x + (tile_count * 16)
        last_spawn_y = spawn_y

# Initial safe starting platform
start_plat = Platform(10, 180, 8, "normal")
platforms.add(start_plat)
last_spawn_x = 10 + (8 * 16)

# Main Loop
camera_x = 0
running = True
font = pygame.font.SysFont("Consolas", 10, bold=True)

while running:
    dt = CLOCK.tick(60) / 1000.0
    game_time += dt
    
    # Scale gap size slightly over time
    max_gap = min(80, 45 + (game_time * 0.4))

    now = pygame.time.get_ticks()
    if dof_charges < 3 and now - last_charge_time > 30000:
        dof_charges += 1
        last_charge_time = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEWHEEL:
            current_dof_idx = (current_dof_idx + event.y) % len(DOF_TYPES)
            
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if dof_charges > 0:
                m_x, m_y = pygame.mouse.get_pos()
                c_x, c_y = m_x // SCALE + camera_x, m_y // SCALE
                
                for p in platforms:
                    if p.rect.collidepoint((c_x, c_y)):
                        p.apply_dof(DOF_TYPES[current_dof_idx])
                        dof_charges -= 1
                        break

    spawn_world_chunk()
    player.update(platforms)
    
    # Pickups
    if pygame.sprite.spritecollide(player, tokens, True):
        dof_charges = min(3, dof_charges + 1)

    # Spike hazard or fell down
    if pygame.sprite.spritecollide(player, spikes, False) or player.rect.top > GAME_H:
        player.rect.x, player.rect.y = camera_x + 20, 100
        player.vel_y = 0

    # Cleanup off-screen
    for entity in list(platforms) + list(tokens) + list(spikes):
        if entity.rect.right < camera_x - 60:
            entity.kill()

    # Smooth Camera
    camera_x += (player.rect.x - camera_x - 60) * 0.1

    # RENDER
    CANVAS.fill((15, 18, 28))
    particles.update_and_draw(CANVAS)

    for p in platforms: CANVAS.blit(p.image, (p.rect.x - camera_x, p.rect.y))
    for s in spikes: CANVAS.blit(s.image, (s.rect.x - camera_x, s.rect.y))
    for t in tokens: CANVAS.blit(t.image, (t.rect.x - camera_x, t.rect.y))
    CANVAS.blit(player.image, (player.rect.x - camera_x, player.rect.y))

    # HUD
    hud_surf = font.render(f"DOF: {DOF_TYPES[current_dof_idx]} | {dof_charges}/3", True, (240, 240, 255))
    CANVAS.blit(hud_surf, (5, 5))
    CANVAS.blit(assets.images["dof"], (5, 18))

    scaled_surface = pygame.transform.scale(CANVAS, (WINDOW_W, WINDOW_H))
    SCREEN.blit(scaled_surface, (0, 0))

    pygame.display.flip()

pygame.quit()
sys.exit()