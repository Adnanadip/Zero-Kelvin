import sys
import random
import os
import math
import pygame
from assets import AssetManager
from effects import ParticleSystem

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

pygame.init()
pygame.mixer.init()

GAME_W, GAME_H = 500, 400
SCALE = 3
WINDOW_W, WINDOW_H = GAME_W * SCALE, GAME_H * SCALE

SCREEN = pygame.display.set_mode((WINDOW_W, WINDOW_H))
CANVAS = pygame.Surface((GAME_W, GAME_H))
pygame.display.set_caption("Zero Kelvin - Endless")
CLOCK = pygame.time.Clock()

assets = AssetManager()
particles = ParticleSystem(GAME_W, GAME_H, assets.images["snowflake"])

# Load Audio Files using absolute paths
AUDIO_DIR = get_resource_path(os.path.join("data", "audio"))

# 1. Background Music
bgm_path = os.path.join(AUDIO_DIR, "bgm.mp3")
if os.path.exists(bgm_path):
    pygame.mixer.music.load(bgm_path)
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1)

# 2. Jump SFX
jump_sound = None
jump_path = os.path.join(AUDIO_DIR, "jump.mp3")
if os.path.exists(jump_path):
    jump_sound = pygame.mixer.Sound(jump_path)
    jump_sound.set_volume(0.6)

# Particle lists & state
dust_particles = []
screen_shake = 0

DOF_TYPES = ["LEFT", "UP", "DOWN", "RIGHT"]
current_dof_idx = 0
dof_charges = 3
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
        if dof_type == "LEFT": dx = -32
        elif dof_type == "RIGHT": dx = 32
        elif dof_type == "UP": dy = -28
        elif dof_type == "DOWN": dy = 28
        
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
        self.facing = 1
        
        self.booster_locked = False
        self.booster_lock_timer = 0.0
        self.lock_cooldown_timer = random.uniform(8.0, 15.0)
        
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.image = assets.images["player_idle"]

    def apply_slow(self, duration):
        self.slow_timer = duration

    def update_animation(self, dt, input_dir):
        if not self.is_grounded:
            current_img = assets.images["player_jump"]
        elif input_dir != 0 or abs(self.slide_vel) > 0.5:
            self.anim_timer += dt * 8
            self.anim_frame = int(self.anim_timer) % len(assets.images["player_run"])
            current_img = assets.images["player_run"][self.anim_frame]
        else:
            self.anim_timer = 0
            current_img = assets.images["player_idle"]

        if self.facing == -1:
            self.image = pygame.transform.flip(current_img, True, False)
        else:
            self.image = current_img

    def update(self, platforms, dt):
        keys = pygame.key.get_pressed()
        
        if self.booster_locked:
            self.booster_lock_timer -= dt
            if self.booster_lock_timer <= 0:
                self.booster_locked = False
                self.lock_cooldown_timer = random.uniform(10.0, 20.0)
        else:
            self.lock_cooldown_timer -= dt
            if self.lock_cooldown_timer <= 0:
                self.booster_locked = True
                self.booster_lock_timer = random.uniform(3.0, 5.0)
        
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

        if keys[pygame.K_SPACE] and self.is_grounded and not self.booster_locked:
            self.vel_y = -5.5
            self.is_grounded = False
            if jump_sound:
                jump_sound.play()

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

        if self.is_grounded and (input_dir != 0 or abs(self.slide_vel) > 0.4):
            if random.random() < 0.35:
                dust_particles.append([
                    self.rect.centerx + random.uniform(-3, 3),
                    self.rect.bottom - 1,
                    random.uniform(-0.6, 0.6),
                    random.uniform(-0.4, -0.1),
                    random.uniform(1.0, 2.0),
                    1.0
                ])

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

        self.is_grounded = False
        
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

        self.update_animation(dt, input_dir)

# Groups Setup
platforms = pygame.sprite.Group()
tokens = pygame.sprite.Group()
spikes = pygame.sprite.Group()
rocks = pygame.sprite.Group()
bushes = pygame.sprite.Group()
player = Player(40, 140)

last_spawn_x = 0
last_spawn_y = 180
game_time = 0

def reset_game_state():
    global last_spawn_x, last_spawn_y, game_time, dof_charges, camera_x
    player.x = 40.0
    player.y = 140.0
    player.rect.x = 40
    player.rect.y = 140
    player.vel_y = 0.0
    player.slide_vel = 0.0
    player.slow_timer = 0.0
    player.booster_locked = False
    player.lock_cooldown_timer = random.uniform(8.0, 15.0)
    
    platforms.empty()
    tokens.empty()
    spikes.empty()
    rocks.empty()
    bushes.empty()
    dust_particles.clear()
    
    start_plat = Platform(10, 180, 8, "normal")
    platforms.add(start_plat)
    last_spawn_x = 10 + (8 * 16)
    last_spawn_y = 180
    game_time = 0
    dof_charges = 3
    camera_x = 0

def spawn_world_chunk():
    global last_spawn_x, last_spawn_y
    
    while last_spawn_x < player.rect.x + GAME_W + 200:
        dist = player.rect.x // 10
        
        # Difficulty weighting
        if dist < 30:
            scenarios = ["STANDARD", "STANDARD", "HIGH_WALL"]
        elif dist < 100:
            scenarios = ["STANDARD", "GAP_IMPOSSIBLE", "HIGH_WALL", "FLOATING_STAIRS"]
        else:
            scenarios = ["GAP_IMPOSSIBLE", "HIGH_WALL", "FLOATING_STAIRS", "ISLAND_DROP"]

        choice = random.choice(scenarios)

        if choice == "GAP_IMPOSSIBLE":
            # Uncrossable gap: requires DOF LEFT
            gap = random.randint(110, 145)
            tile_count = random.randint(2, 4)
            spawn_x = last_spawn_x + gap
            spawn_y = max(80, min(GAME_H - 60, last_spawn_y + random.choice([-15, 0, 15])))
            
            plat = Platform(spawn_x, spawn_y, tile_count, "normal")
            platforms.add(plat)
            
            if random.random() < 0.8:
                tokens.add(Token(spawn_x + 8, spawn_y - 12, plat))

        elif choice == "HIGH_WALL":
            # Platform blocking path: requires DOF DOWN or RIGHT
            gap = random.randint(30, 45)
            spawn_x = last_spawn_x + gap
            spawn_y = max(60, last_spawn_y - 55)
            tile_count = random.randint(3, 5)
            
            plat = Platform(spawn_x, spawn_y, tile_count, "ice")
            platforms.add(plat)
            
            # Wall extension downwards
            wall_block = Platform(spawn_x, spawn_y + 16, tile_count, "normal")
            platforms.add(wall_block)

        elif choice == "FLOATING_STAIRS":
            # Spawns far above unreachable by jumping: requires DOF DOWN
            gap = random.randint(50, 70)
            spawn_x = last_spawn_x + gap
            spawn_y = max(50, last_spawn_y - 75)
            tile_count = random.randint(2, 3)
            
            plat = Platform(spawn_x, spawn_y, tile_count, "crack0")
            platforms.add(plat)

        else: # STANDARD
            gap = random.randint(35, 55)
            spawn_x = last_spawn_x + gap
            spawn_y = max(80, min(GAME_H - 50, last_spawn_y + random.choice([-25, 0, 25])))
            tile_count = random.randint(3, 5)
            
            plat = Platform(spawn_x, spawn_y, tile_count, random.choice(["normal", "ice"]))
            platforms.add(plat)
            
            if random.random() < 0.4:
                obs = random.choice(["spike", "rock0", "bush"])
                obs_offset = random.randint(0, tile_count - 1) * 16
                if obs == "spike":
                    spikes.add(Obstacle(spawn_x + obs_offset, spawn_y, "spike", plat))
                elif obs == "rock0":
                    rocks.add(Obstacle(spawn_x + obs_offset, spawn_y, "rock0", plat))
                elif obs == "bush":
                    bushes.add(Obstacle(spawn_x + obs_offset, spawn_y, "bush", plat))

        last_spawn_x = spawn_x + (tile_count * 16)
        last_spawn_y = spawn_y

reset_game_state()

camera_x = 0
title_font = pygame.font.SysFont("Impact", 36)
font = pygame.font.SysFont("Consolas", 11, bold=True)
alert_font = pygame.font.SysFont("Impact", 14)

in_start_screen = True

while True:
    # ------------------- START SCREEN -------------------
    while in_start_screen:
        dt_ui = CLOCK.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                m_x, m_y = pygame.mouse.get_pos()
                c_x, c_y = m_x // SCALE, m_y // SCALE
                btn_rect = pygame.Rect(GAME_W // 2 - 50, GAME_H // 2 + 25, 100, 26)
                if btn_rect.collidepoint((c_x, c_y)):
                    reset_game_state()
                    in_start_screen = False

        CANVAS.blit(assets.images["bgm"], (0, 0))
        particles.update_and_draw(CANVAS, camera_x)
        
        title_shadow = title_font.render("ZERO-KELVIN", True, (10, 20, 35))
        title_surf = title_font.render("ZERO-KELVIN", True, (120, 220, 255))
        CANVAS.blit(title_shadow, (GAME_W // 2 - title_shadow.get_width() // 2 + 2, 72))
        CANVAS.blit(title_surf, (GAME_W // 2 - title_surf.get_width() // 2, 70))

        sub_text = "SHIFT PLATFORMS | SURVIVE THE FROST"
        sub_shadow = font.render(sub_text, True, (10, 15, 30))
        sub_surf = font.render(sub_text, True, (255, 255, 255))
        CANVAS.blit(sub_shadow, (GAME_W // 2 - sub_shadow.get_width() // 2 + 1, 116))
        CANVAS.blit(sub_surf, (GAME_W // 2 - sub_surf.get_width() // 2, 115))

        score_surf = font.render(f"BEST DISTANCE: {best_distance}m", True, (255, 215, 0))
        CANVAS.blit(score_surf, (GAME_W // 2 - score_surf.get_width() // 2, 145))
        
        btn_rect = pygame.Rect(GAME_W // 2 - 50, GAME_H // 2 + 25, 100, 26)
        pygame.draw.rect(CANVAS, (30, 50, 80), btn_rect.inflate(4, 4), border_radius=6)
        pygame.draw.rect(CANVAS, (80, 150, 240), btn_rect, border_radius=4)
        btn_text = font.render("START GAME", True, (255, 255, 255))
        CANVAS.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2, btn_rect.centery - btn_text.get_height() // 2))

        scaled_surface = pygame.transform.scale(CANVAS, (WINDOW_W, WINDOW_H))
        SCREEN.blit(scaled_surface, (0, 0))
        pygame.display.flip()

    # ------------------- MAIN GAME LOOP -------------------
    running = True
    while running:
        dt = CLOCK.tick(60) / 1000.0
        game_time += dt

        now = pygame.time.get_ticks()
        if dof_charges < 3 and now - last_charge_time > 8000:
            dof_charges += 1
            last_charge_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
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
                            screen_shake = 4
                            break

        spawn_world_chunk()
        platforms.update()
        player.update(platforms, dt)
        
        current_distance = max(0, int((player.rect.x - 40) / 10))
        if current_distance > best_distance:
            best_distance = current_distance
            save_high_score(best_distance)
        
        if pygame.sprite.spritecollide(player, tokens, True):
            dof_charges = min(3, dof_charges + 1)

        hit_rocks = pygame.sprite.spritecollide(player, rocks, True)
        if hit_rocks:
            dof_charges = max(0, dof_charges - 1)
            screen_shake = 10

        if pygame.sprite.spritecollide(player, bushes, False):
            player.apply_slow(1.5)

        # Death condition
        if pygame.sprite.spritecollide(player, spikes, False) or player.rect.top > GAME_H:
            screen_shake = 12
            in_start_screen = True
            running = False
            break

        # Garbage Collection
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
        
        for dust in dust_particles[:]:
            dust[0] += dust[2]
            dust[1] += dust[3]
            dust[5] -= dt * 2.5
            if dust[5] <= 0:
                dust_particles.remove(dust)
            else:
                alpha_val = int(255 * max(0, dust[5]))
                dust_surf = pygame.Surface((int(dust[4] * 2), int(dust[4] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(dust_surf, (220, 240, 255, alpha_val), (int(dust[4]), int(dust[4])), int(dust[4]))
                CANVAS.blit(dust_surf, (int(dust[0] - camera_x), int(dust[1])))

        CANVAS.blit(player.image, (player.rect.x - camera_x, player.rect.y))

        # HUD
        hud_surf = font.render(f"DOF: {DOF_TYPES[current_dof_idx]} | {dof_charges}/3", True, (240, 240, 255))
        CANVAS.blit(hud_surf, (5, 5))
        CANVAS.blit(assets.images["dof"], (5, 18))

        if player.booster_locked:
            warn_box = pygame.Rect(GAME_W // 2 - 75, 10, 150, 20)
            pygame.draw.rect(CANVAS, (180, 40, 40), warn_box, border_radius=4)
            pygame.draw.rect(CANVAS, (255, 200, 200), warn_box, 1, border_radius=4)
            alert_surf = alert_font.render("BOOSTER LOST POWER!", True, (255, 255, 255))
            CANVAS.blit(alert_surf, (warn_box.centerx - alert_surf.get_width() // 2, warn_box.centery - alert_surf.get_height() // 2))

        shake_x = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
        shake_y = random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0
        if screen_shake > 0:
            screen_shake -= 1

        scaled_surface = pygame.transform.scale(CANVAS, (WINDOW_W, WINDOW_H))
        SCREEN.blit(scaled_surface, (0, 0))

        pygame.display.flip()