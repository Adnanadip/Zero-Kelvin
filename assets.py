import os
import pygame

class AssetManager:
    def __init__(self, base_path="data/images"):
        self.base_path = base_path
        self.images = {}
        self.load_all()

    def load_image(self, path, fallback_color=(100, 100, 100), size=(32, 32)):
        full_path = os.path.join(self.base_path, path)
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path).convert_alpha()
                return pygame.transform.scale(img, size)
            except Exception:
                pass
        # Procedural fallback with outline
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(fallback_color)
        pygame.draw.rect(surf, (255, 255, 255), surf.get_rect(), 2)
        return surf

    def load_all(self):
        # Platform sprites
        self.images["platform_normal"] = self.load_image("platform/normal/0.png", (80, 80, 100), (64, 32))
        self.images["platform_ice"] = self.load_image("platform/ice/0.png", (100, 200, 255), (64, 32))
        self.images["platform_crack0"] = self.load_image("platform/cracked/0.png", (120, 100, 80), (64, 32))
        
        # Props & Items
        self.images["spike"] = self.load_image("decor/spike.png", (220, 50, 50), (16, 24))
        self.images["snowflake"] = self.load_image("particle/snowflake.png", (200, 240, 255), (8, 8))
        self.images["dof"] = self.load_image("token/dof.png", (255, 180, 0), (20, 20))
        
        # Placeholder Robot (Procedural Pixel-Art Style)
        robot_surf = pygame.Surface((24, 36), pygame.SRCALPHA)
        robot_surf.fill((60, 200, 220)) # Cyan body
        pygame.draw.rect(robot_surf, (20, 30, 50), (4, 4, 16, 10)) # Visor
        pygame.draw.rect(robot_surf, (255, 50, 50), (8, 6, 8, 4))   # Eye glow
        self.images["robot"] = robot_surf