import random
import pygame

class ParticleSystem:
    def __init__(self, width, height, snowflake_img):
        self.width = width
        self.height = height
        self.snowflake_img = snowflake_img
        self.snowflakes = [
            [random.randint(0, width), random.randint(0, height), random.uniform(0.5, 2.0)]
            for _ in range(60)
        ]

    def update_and_draw(self, surface):
        for flake in self.snowflakes:
            flake[1] += flake[2] # Fall speed
            flake[0] += random.uniform(-0.3, 0.3) # Drift
            
            if flake[1] > self.height:
                flake[1] = -10
                flake[0] = random.randint(0, self.width)
                
            surface.blit(self.snowflake_img, (int(flake[0]), int(flake[1])))