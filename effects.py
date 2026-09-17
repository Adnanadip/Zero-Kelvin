import random
import pygame

class ParticleSystem:
    def __init__(self, width, height, snowflake_img):
        self.width = width
        self.height = height
        self.snowflake_img = snowflake_img
        # [x, y, fall_speed, drift_speed]
        self.snowflakes = [
            [
                random.randint(0, width),
                random.randint(0, height),
                random.uniform(0.8, 2.0),
                random.uniform(-0.3, 0.3)
            ]
            for _ in range(60)
        ]

    def update_and_draw(self, surface, camera_x=0):
        for flake in self.snowflakes:
            flake[1] += flake[2]  # Fall
            flake[0] += flake[3]  # Drift

            # Reset above canvas when falling off bottom
            if flake[1] > self.height:
                flake[1] = random.randint(-20, -5)
                flake[0] = camera_x + random.randint(0, self.width)

            # Reset within camera bounds if drifting too far horizontally
            if flake[0] < camera_x - 50 or flake[0] > camera_x + self.width + 50:
                flake[0] = camera_x + random.randint(0, self.width)
                flake[1] = random.randint(-20, self.height)

            # Render relative to camera offset
            surface.blit(self.snowflake_img, (int(flake[0] - camera_x), int(flake[1])))