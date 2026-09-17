import os
import pygame

class AssetManager:
    def __init__(self, base_path=None):
        if base_path is None:
            self.base_path = os.path.join("data", "images")
        else:
            self.base_path = base_path
        self.images = {}
        self.load_all()

    def load_image(self, relative_path, fallback_color=(100, 100, 100), size=(16, 16)):
        path_parts = relative_path.split("/")
        full_path = os.path.join(self.base_path, *path_parts)
        
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path).convert_alpha()
                return pygame.transform.scale(img, size)
            except Exception:
                pass
                
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(fallback_color)
        pygame.draw.rect(surf, (255, 255, 255), surf.get_rect(), 1)
        return surf

    def load_all(self):
        # Background
        self.images["bgm"] = self.load_image("background/Bgm.png", (15, 18, 28), (500, 400))

        # Base tile sizes (16x16)
        self.images["tile_normal"] = self.load_image("platform/normal/0.png", (80, 80, 100), (16, 16))
        self.images["tile_ice"] = self.load_image("platform/ice/0.png", (100, 200, 255), (16, 16))
        
        # All 5 cracked platform frames (0 to 4)
        for i in range(5):
            self.images[f"tile_crack{i}"] = self.load_image(f"platform/cracked/{i}.png", (120, 100, 80), (16, 16))
        
        # Obstacles & Decor
        spike_img = self.load_image("decor/spike.png", (220, 50, 50), (10, 10))
        self.images["spike"] = pygame.transform.flip(spike_img, False, True)
        self.images["rock0"] = self.load_image("decor/rock/0.png", (100, 100, 110), (12, 10))
        self.images["rock1"] = self.load_image("decor/rock/1.png", (100, 100, 110), (12, 10))
        self.images["bush"] = self.load_image("decor/bush.png", (50, 150, 50), (12, 10))
        
        # Tokens & Particles
        self.images["snowflake"] = self.load_image("particle/snowflake.png", (200, 240, 255), (8, 8))
        self.images["dof"] = self.load_image("token/dof.png", (255, 180, 0), (10, 10))
        
        # Player Robot
        robot_surf = pygame.Surface((8, 14), pygame.SRCALPHA)
        robot_surf.fill((60, 200, 220))
        pygame.draw.rect(robot_surf, (20, 30, 50), (1, 2, 6, 4))
        pygame.draw.rect(robot_surf, (255, 50, 50), (3, 3, 2, 2))
        self.images["robot"] = robot_surf

        self.images["player_idle"] = self.load_image("player/Stand.png", (200, 60, 180), (16, 20))
        self.images["player_jump"] = self.load_image("player/Jump.png", (200, 60, 180), (16, 20))
        self.images["player_run"] = [
            self.load_image("player/Fwd1.png", (200, 60, 180), (16, 20)),
            self.load_image("player/Fwd2.png", (200, 60, 180), (16, 20))
        ]