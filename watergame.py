import pygame
import random
import math
import sys

# -----------------------
# CONFIGURATION
# -----------------------
WIDTH, HEIGHT = 1000, 700
FPS = 60
TEAM_SIZE = 4

DESK_COLOR = (160, 160, 160)
WATER_COLOR = (0, 120, 255)
WHITEBOARD_COLOR = (220, 220, 180)
BACKGROUND = (30, 30, 35)

DEV_COLORS = [
    (255, 100, 100),
    (100, 255, 100),
    (100, 150, 255),
    (255, 200, 100),
]

# VTR colors
ACTIVITY_COLORS = {
    "T": (255, 255, 255),
    "V": (0, 200, 255),
    "R": (255, 180, 0),
}

# -----------------------
# DEVELOPER CLASS
# -----------------------
class Developer:
    def __init__(self, name, color, home_pos):
        self.name = name
        self.color = color
        self.pos = pygame.Vector2(home_pos)
        self.home = pygame.Vector2(home_pos)
        self.target = pygame.Vector2(home_pos)
        self.speed = random.uniform(1.2, 1.8)
        self.activity = "T"
        self.activity_timer = random.randint(120, 240)

    def choose_new_activity(self):
        self.activity = random.choices(
            ["T", "V", "R"],
            weights=[65, 15, 20]
        )[0]

        if self.activity == "T":
            self.target = self.home
        elif self.activity == "V":
            self.target = pygame.Vector2(WIDTH - 150, HEIGHT // 2)
        elif self.activity == "R":
            self.target = pygame.Vector2(WIDTH // 2, 100)

        self.activity_timer = random.randint(180, 360)

    def update(self):
        direction = self.target - self.pos
        if direction.length() > 1:
            direction = direction.normalize()
            self.pos += direction * self.speed
        else:
            self.activity_timer -= 1
            if self.activity_timer <= 0:
                self.choose_new_activity()

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, self.pos, 12)
        pygame.draw.circle(screen, ACTIVITY_COLORS[self.activity], self.pos, 16, 2)

# -----------------------
# MAIN
# -----------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PAT VTR Office Simulation")
    clock = pygame.time.Clock()

    # Desk layout
    desks = [
        (150, 200),
        (150, 400),
        (350, 200),
        (350, 400),
    ]

    developers = []
    for i in range(TEAM_SIZE):
        dev = Developer(
            name=f"Dev{i+1}",
            color=DEV_COLORS[i],
            home_pos=desks[i]
        )
        developers.append(dev)

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BACKGROUND)

        # Draw desks
        for d in desks:
            pygame.draw.rect(screen, DESK_COLOR, (*d, 80, 50), border_radius=6)

        # Draw water cooler
        pygame.draw.circle(screen, WATER_COLOR, (WIDTH - 150, HEIGHT // 2), 40)

        # Draw roadmap whiteboard
        pygame.draw.rect(
            screen,
            WHITEBOARD_COLOR,
            (WIDTH // 2 - 100, 40, 200, 80),
            border_radius=8
        )

        # Labels
        font = pygame.font.SysFont(None, 24)
        screen.blit(font.render("Roadmap (R)", True, (0, 0, 0)),
                    (WIDTH // 2 - 60, 70))
        screen.blit(font.render("Vision (V)", True, (255, 255, 255)),
                    (WIDTH - 190, HEIGHT // 2 - 70))

        # Update & draw developers
        for dev in developers:
            dev.update()
            dev.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()