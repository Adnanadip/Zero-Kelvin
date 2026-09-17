import sys
import random
import pygame
from assets import AssetManager
from effects import ParticleSystem

pygame.init()
WIDTH, HEIGHT = 800, 450
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zero Kelvin")
CLOCK = pygame.time.Clock()

assets = AssetManager()
particles = ParticleSystem(WIDTH, HEIGHT, assets.images["snowflake"])

# DOF Types: 0: LEFT, 1: UP, 2: DOWN, 3: RIGHT
DOF_TYPES = ["LEFT", "UP", "DOWN", "RIGHT"]
current_dof_idx = 0
dof_charges = 3
last_charge_time = pygame.time.get_ticks()

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, p_type="normal"):
        super().__init__()
        self.p_type = p_type
        self.image = assets.images.get(f"platform_{p_type}", assets.images["platform_normal"]).copy()
        self.rect = self.image.get_rect(topleft=(x, y))

    def apply_dof(self, dof_type):
        if dof_type == "LEFT": self.rect.x -= 30
        elif dof_type == "RIGHT": self.rect.x += 30
        elif dof_type == "UP": self.rect.y -= 25
        elif dof_type == "DOWN": self.rect.y += 25

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = assets.images["robot"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        self.speed = 4
        self.is_grounded = False

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        
        # Horizontal Movement (A and D)
        if keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_d]:
            self.rect.x += self.speed

        # Jump (Space)
        if keys[pygame.K_SPACE] and self.is_grounded:
            self.vel_y = -10
            self.is_grounded = False

        # Apply Gravity
        self.vel_y += 0.5
        self.rect.y += int(self.vel_y)

        # Platform Collisions
        self.is_grounded = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                # Check landing from above
                if self.vel_y > 0 and self.rect.bottom <= platform.rect.bottom:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.is_grounded = True

        # Reset position if fallen off screen
        if self.rect.top > HEIGHT:
            self.rect.x, self.rect.y = 120, 200
            self.vel_y = 0

# Instantiate Platforms & Player
platforms = pygame.sprite.Group()
for i in range(6):
    platforms.add(Platform(100 + i * 120, 320 - (i % 2) * 20, random.choice(["normal", "ice", "crack0"])))

player = Player(120, 200)
all_sprites = pygame.sprite.Group(player)

# Main Game Loop
running = True
while running:
    dt = CLOCK.tick(60) / 1000.0
    now = pygame.time.get_ticks()

    # Recharging DOF token every 30 seconds
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
                pos = pygame.mouse.get_pos()
                for p in platforms:
                    if p.rect.collidepoint(pos):
                        p.apply_dof(DOF_TYPES[current_dof_idx])
                        dof_charges -= 1
                        break

    # Update Physics
    player.update(platforms)

    # Render
    SCREEN.fill((15, 18, 28))
    particles.update_and_draw(SCREEN)
    platforms.draw(SCREEN)
    all_sprites.draw(SCREEN)

    # UI / HUD
    dof_text = f"DOF Mode: < {DOF_TYPES[current_dof_idx]} > | Charges: {dof_charges}/3"
    font = pygame.font.SysFont("Consolas", 16, bold=True)
    surf = font.render(dof_text, True, (230, 240, 255))
    SCREEN.blit(surf, (20, 20))
    SCREEN.blit(assets.images["dof"], (20, 45))

    pygame.display.flip()

pygame.quit()
sys.exit()