import sys
import random
import os
import pygame
from assets import AssetManager
from effects import ParticleSystem

pygame.init()

GAME_W, GAME_H = 500, 400
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
dof_charges = 4
last_charge_time = pygame.time.get_ticks()

SCORE_FILE = "highscore.txt"

def load_high_score():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r") as f:
            try:
                return int(f.read())
            except ValueError:
                return 0
    return 0

def save_high_score(score):
    with open(SCORE_FILE, "w") as f:
        f.write(str(score))

best_distance = load_high_score()

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width_in_tiles=4, p_type="normal"):
        super().__init__()
        self.p_type = p_type
        self.width_in_tiles = width_in_tiles
        self.crack_frame = 0 if p_type.startswith("crack") else None
        self.decay_start_time = None
        self.attached_entities = []
        
        self.update_appearance()
        self.rect = self.image.get_rect(topleft=(x, y))

    def update_appearance(self):
        if self.crack_frame is not None:
            tile_key = f"tile_crack{min(4, self.crack_frame)}"
        else:
            tile_key = f"tile_{self.p_type}"
            
        self.tile_img = assets.images.get(tile_key, assets.images["tile_normal"])
        self.image = pygame.Surface((16 * self.width_in_tiles, 16), pygame.SRCALPHA)
        for i in range(self.width_in_tiles):
            self.image.blit(self.tile_img, (i * 16, 0))

    def step_on(self):
        if self.crack_frame is not None and self.decay_start_time is None:
            self.decay_start_time = pygame.time.get_ticks()

    def update(self):
        if self.decay_start_time is not None:
            elapsed = (pygame.time.get_ticks() - self.decay_start_time) / 1000.0
            if elapsed >= 3.0:
                self.destroy()
            else:
                new_frame = int((elapsed / 3.0) * 5)
                if new_frame != self.crack_frame and new_frame <= 4:
                    self.crack_frame = new_frame
                    self.update_appearance()

    def destroy(self):
        for entity in self.attached_entities:
            entity.kill()
        self.attached_entities.clear()
        self.kill()

    def apply_dof(self, dof_type):
        dx, dy = 0, 0
        if dof_type == "LEFT": dx = -24
        elif dof_type == "RIGHT": dx = 24
        elif dof_type == "UP": dy = -20
        elif dof_type == "DOWN": dy = 20
        
        self.rect.x += dx
        self.rect.y += dy
        
        for entity in self.attached_entities:
            entity.rect.x += dx
            entity.rect.y += dy

class Token(pygame.sprite.Sprite):
    def __init__(self, x, y, platform=None):
        super().__init__()
        self.image = assets.images["dof"]
        self.rect = self.image.get_rect(center=(x, y))
        self.platform = platform
        if platform:
            platform.attached_entities.append(self)

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, y, obs_type="spike", platform=None):
        super().__init__()
        self.obs_type = obs_type
        self.image = assets.images[obs_type]
        self.rect = self.image.get_rect(bottomleft=(x, y))
        self.platform = platform
        if platform:
            platform.attached_entities.append(self)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x + 1, y, 10, 18)
        self.x = float(x)
        self.y = float(y)
        self.vel_y = 0.0
        self.base_speed = 2.0
        self.slow_timer = 0.0
        self.slide_vel = 0.0
        self.is_grounded = False
        self.current_platform = None
        self.facing = 1  # 1 = Right, -1 = Left
        
        # Animation states
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.image = assets.images["player_idle"]

    def apply_slow(self, duration):
        """Fixes Bug #1: Applies speed reduction when hitting bushes."""
        self.slow_timer = duration

    def update_animation(self, dt, input_dir):
        # 1. Airborne state takes priority
        if not self.is_grounded:
            current_img = assets.images["player_jump"]
        # 2. Running / Moving state (only run when actually moving significantly)
        elif input_dir != 0 or abs(self.slide_vel) > 0.5:
            self.anim_timer += dt * 8  # Animation speed
            self.anim_frame = int(self.anim_timer) % len(assets.images["player_run"])
            current_img = assets.images["player_run"][self.anim_frame]
        # 3. Idle state
        else:
            self.anim_timer = 0
            current_img = assets.images["player_idle"]

        # Flip horizontally if facing left
        if self.facing == -1:
            self.image = pygame.transform.flip(current_img, True, False)
        else:
            self.image = current_img

    def update(self, platforms, dt):
        keys = pygame.key.get_pressed()
        
        current_speed = self.base_speed
        if self.slow_timer > 0:
            self.slow_timer -= dt
            current_speed = 0.8
            
        input_dir = 0
        if keys[pygame.K_a]:
            input_dir -= 1
            self.facing = -1
        if keys[pygame.K_d]:
            input_dir += 1
            self.facing = 1

        if keys[pygame.K_SPACE] and self.is_grounded:
            self.vel_y = -5.5
            self.is_grounded = False

        self.vel_y += 0.3

        if self.is_grounded and self.current_platform and self.current_platform.p_type == "ice":
            if input_dir != 0:
                self.slide_vel += input_dir * 0.15
            else:
                self.slide_vel *= 0.92
            self.slide_vel = max(-1.8, min(1.8, self.slide_vel))
        else:
            air_drag = 0.98 if not self.is_grounded else 0.60
            self.slide_vel *= air_drag
            if abs(self.slide_vel) < 0.02:
                self.slide_vel = 0.0

        # Step 1: Horizontal Movement
        total_dx = (input_dir * current_speed) + self.slide_vel
        self.x += total_dx
        self.rect.x = int(self.x)

        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if total_dx > 0:
                    self.rect.right = platform.rect.left
                    self.x = float(self.rect.x)
                elif total_dx < 0:
                    self.rect.left = platform.rect.right
                    self.x = float(self.rect.x)

        # Step 2: Vertical Movement & Ground Check
        was_grounded = self.is_grounded
        self.is_grounded = False
        
        # Test 1 pixel down to maintain steady grounded state without jitter
        self.rect.y += 1
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y >= 0:
                    self.is_grounded = True
                    self.current_platform = platform
                    break
        self.rect.y -= 1

        steps = int(abs(self.vel_y)) + 1
        dy_per_step = self.vel_y / steps

        for _ in range(steps):
            self.y += dy_per_step
            self.rect.y = int(self.y)

            for platform in platforms:
                if self.rect.colliderect(platform.rect):
                    if self.vel_y > 0:
                        self.rect.bottom = platform.rect.top
                        self.y = float(self.rect.y)
                        self.vel_y = 0.0
                        self.is_grounded = True
                        self.current_platform = platform
                        platform.step_on()
                        break
                    elif self.vel_y < 0:
                        self.rect.top = platform.rect.bottom
                        self.y = float(self.rect.y)
                        self.vel_y = 0.0
                        break
            if self.is_grounded:
                break

        # Update frame rendering
        self.update_animation(dt, input_dir)


# Separate Groups for logic handling
platforms = pygame.sprite.Group()
tokens = pygame.sprite.Group()
spikes = pygame.sprite.Group()
rocks = pygame.sprite.Group()
bushes = pygame.sprite.Group()
player = Player(40, 140)

last_spawn_x = 0
last_spawn_y = 180
min_gap, max_gap = 25, 45
game_time = 0

def spawn_world_chunk():
    global last_spawn_x, last_spawn_y
    while last_spawn_x < player.rect.x + GAME_W + 120:
        gap = random.randint(int(min_gap), int(max_gap))
        y_change = random.choice([-25, -15, 0, 15, 25])
        spawn_y = max(80, min(GAME_H - 40, last_spawn_y + y_change))
        
        tile_count = random.randint(4, 7)
        spawn_x = last_spawn_x + gap
        
        p_type = random.choice(["normal", "ice", "crack0"])
        plat = Platform(spawn_x, spawn_y, tile_count, p_type)
        platforms.add(plat)
        
        # Spawn decor/obstacles
        if random.random() < 0.4:
            obs_choice = random.choice(["spike", "rock0", "rock1", "bush"])
            obs_offset = random.randint(1, tile_count - 1) * 16
            
            if obs_choice == "spike":
                spikes.add(Obstacle(spawn_x + obs_offset, spawn_y, obs_choice, plat))
            elif obs_choice in ["rock0", "rock1"]:
                rocks.add(Obstacle(spawn_x + obs_offset, spawn_y, obs_choice, plat))
            elif obs_choice == "bush":
                bushes.add(Obstacle(spawn_x + obs_offset, spawn_y, obs_choice, plat))
                
        elif random.random() < 0.25:
            token_offset = (tile_count * 16) // 2
            tokens.add(Token(spawn_x + token_offset, spawn_y - 10, plat))

        last_spawn_x = spawn_x + (tile_count * 16)
        last_spawn_y = spawn_y

start_plat = Platform(10, 180, 8, "normal")
platforms.add(start_plat)
last_spawn_x = 10 + (8 * 16)

camera_x = 0
running = True
font = pygame.font.SysFont("Consolas", 10, bold=True)

# Start Screen Loop
in_start_screen = True
while in_start_screen:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_x, m_y = pygame.mouse.get_pos()
            c_x, c_y = m_x // SCALE, m_y // SCALE
            btn_rect = pygame.Rect(GAME_W // 2 - 40, GAME_H // 2 + 5, 80, 24)
            if btn_rect.collidepoint((c_x, c_y)):
                in_start_screen = False

    CANVAS.blit(assets.images["bgm"], (0, 0))
    particles.update_and_draw(CANVAS, camera_x)
    
    score_surf = font.render(f"Best Distance: {best_distance}m", True, (240, 240, 255))
    CANVAS.blit(score_surf, (GAME_W // 2 - score_surf.get_width() // 2, GAME_H // 2 - 20))
    
    btn_rect = pygame.Rect(GAME_W // 2 - 40, GAME_H // 2 + 5, 80, 24)
    pygame.draw.rect(CANVAS, (60, 100, 180), btn_rect)
    btn_text = font.render("START", True, (255, 255, 255))
    CANVAS.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2, btn_rect.centery - btn_text.get_height() // 2))

    scaled_surface = pygame.transform.scale(CANVAS, (WINDOW_W, WINDOW_H))
    SCREEN.blit(scaled_surface, (0, 0))
    pygame.display.flip()
    CLOCK.tick(60)

# Main Game Loop
while running:
    dt = CLOCK.tick(60) / 1000.0
    game_time += dt
    
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
    platforms.update()
    player.update(platforms, dt)
    
    current_distance = max(0, int((player.rect.x - 40) / 10))
    if current_distance > best_distance:
        best_distance = current_distance
        save_high_score(best_distance)
    
    # Collect Tokens
    if pygame.sprite.spritecollide(player, tokens, True):
        dof_charges = min(3, dof_charges + 1)

    # Hit Rock -> Lose 1 DOF
    hit_rocks = pygame.sprite.spritecollide(player, rocks, True)
    if hit_rocks:
        dof_charges = max(0, dof_charges - 1)

    # Hit Bush -> Apply Slow Effect
    if pygame.sprite.spritecollide(player, bushes, False):
        player.apply_slow(1.5)

    # Death Check (Only Spikes or Falling)
    if pygame.sprite.spritecollide(player, spikes, False) or player.rect.top > GAME_H:
        in_death_screen = True
        while in_death_screen:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    m_x, m_y = pygame.mouse.get_pos()
                    c_x, c_y = m_x // SCALE, m_y // SCALE
                    retry_btn_rect = pygame.Rect(GAME_W // 2 - 50, GAME_H // 2 + 5, 100, 24)
                    if retry_btn_rect.collidepoint((c_x, c_y)):
                        player.x = 40.0
                        player.y = 140.0
                        player.rect.x = 40
                        player.rect.y = 140
                        player.vel_y = 0.0
                        player.slide_vel = 0.0
                        player.slow_timer = 0.0
                        platforms.empty()
                        tokens.empty()
                        spikes.empty()
                        rocks.empty()
                        bushes.empty()
                        
                        start_plat = Platform(10, 180, 8, "normal")
                        platforms.add(start_plat)
                        last_spawn_x = 10 + (8 * 16)
                        last_spawn_y = 180
                        game_time = 0
                        dof_charges = 3
                        camera_x = 0
                        in_death_screen = False

            CANVAS.blit(assets.images["bgm"], (0, 0))
            
            final_score_surf = font.render(f"Distance: {current_distance}m", True, (240, 240, 255))
            CANVAS.blit(final_score_surf, (GAME_W // 2 - final_score_surf.get_width() // 2, GAME_H // 2 - 20))
            
            retry_btn_rect = pygame.Rect(GAME_W // 2 - 50, GAME_H // 2 + 5, 100, 24)
            pygame.draw.rect(CANVAS, (180, 60, 60), retry_btn_rect)
            retry_text = font.render("PLAY AGAIN", True, (255, 255, 255))
            CANVAS.blit(retry_text, (retry_btn_rect.centerx - retry_text.get_width() // 2, retry_btn_rect.centery - retry_text.get_height() // 2))

            scaled_surface = pygame.transform.scale(CANVAS, (WINDOW_W, WINDOW_H))
            SCREEN.blit(scaled_surface, (0, 0))
            pygame.display.flip()
            CLOCK.tick(60)

    # Garbage collection for off-screen sprites
    all_entities = list(platforms) + list(tokens) + list(spikes) + list(rocks) + list(bushes)
    for entity in all_entities:
        if entity.rect.right < camera_x - 60:
            entity.kill()

    camera_x += (player.rect.x - camera_x - 60) * 0.1

    CANVAS.blit(assets.images["bgm"], (0, 0))
    particles.update_and_draw(CANVAS, camera_x)

    for p in platforms: CANVAS.blit(p.image, (p.rect.x - camera_x, p.rect.y))
    for s in spikes: CANVAS.blit(s.image, (s.rect.x - camera_x, s.rect.y))
    for r in rocks: CANVAS.blit(r.image, (r.rect.x - camera_x, r.rect.y))
    for b in bushes: CANVAS.blit(b.image, (b.rect.x - camera_x, b.rect.y))
    for t in tokens: CANVAS.blit(t.image, (t.rect.x - camera_x, t.rect.y))
    CANVAS.blit(player.image, (player.rect.x - camera_x, player.rect.y))

    hud_surf = font.render(f"DOF: {DOF_TYPES[current_dof_idx]} | {dof_charges}/3", True, (240, 240, 255))
    CANVAS.blit(hud_surf, (5, 5))
    CANVAS.blit(assets.images["dof"], (5, 18))

    scaled_surface = pygame.transform.scale(CANVAS, (WINDOW_W, WINDOW_H))
    SCREEN.blit(scaled_surface, (0, 0))

    pygame.display.flip()

pygame.quit()
sys.exit()