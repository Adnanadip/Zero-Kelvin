import os
import pygame

class AssetManager:
    def __init__(self, base_path="data/images"):
        self.base_path = base_path
        self.images = {}
        self.load_all()

    def load_image(self, path, fallback_color=(100, 100, 100), size=(16, 16)):
        full_path = os.path.join(self.base_path, path)
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
        # Base tile size is now 16x16
        self.images["tile_normal"] = self.load_image("platform/normal/0.png", (80, 80, 100), (16, 16))
        self.images["tile_ice"] = self.load_image("platform/ice/0.png", (100, 200, 255), (16, 16))
        self.images["tile_crack0"] = self.load_image("platform/cracked/0.png", (120, 100, 80), (16, 16))
        
        # Props & Tokens
        spike_img = self.load_image("decor/spike.png", (220, 50, 50), (10, 10))
        # Vertically flip the spike asset
        self.images["spike"] = pygame.transform.flip(spike_img, False, True)
        
        self.images["snowflake"] = self.load_image("particle/snowflake.png", (200, 240, 255), (3, 3))
        self.images["dof"] = self.load_image("token/dof.png", (255, 180, 0), (10, 10))
        
        # Player Robot (Scaled down for sleeker look)
        robot_surf = pygame.Surface((8, 14), pygame.SRCALPHA)
        robot_surf.fill((60, 200, 220))
        pygame.draw.rect(robot_surf, (20, 30, 50), (1, 2, 6, 4))
        pygame.draw.rect(robot_surf, (255, 50, 50), (3, 3, 2, 2))
        self.images["robot"] = robot_surf