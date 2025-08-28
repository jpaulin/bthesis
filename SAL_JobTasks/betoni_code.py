import pygame
import random
import math

# My intelligence so far: 
#   a toy. Just randomness. a Plan.

# Run me: 
#   $ pip install pygame
# Then, run me normally as python program:
#   $ python ./betoni_code.py 
#
# 

# BeToni explores programmatic program generation.
# MIT / Free. (C) Jukka Paulin
# [ ] decision tree: 3 states; add, stay, delete
# [ ] GUI control via mouse
# [ ] understanding the real functioning of the artefact (Program)
# [ ] the function: ? mystic grand thingie. Undefined.

# [ ] allow giving generic program features, as inputs
# [ ] splitting the Features into Tiles 
# [ ] add a tileselector() that takes from set of algorithms
# [ ] add a tileselector() that can add a UIButton

# Betoni ai code generator, and visualizer. 
#
# "Blueprint" is something that you approximately
# know. It is a 
#   shape
#   coverage in area: surface
#   explanation of what it really does, and "is"
#   made of Tiles 

# 4 main steps, for the program to take as next_step:
# Add 1 Tile
# Stay.
# Delete a Tile
# Add a Wishlist for a Tile
#   - subs, API, etc - or just mockery

# --- Asetukset ---
WIDTH, HEIGHT = 800, 600
TILE_SIZE = 10
FPS = 25


# 
# Real program parts and the rules they carry necessarily:
#
#   hashAlgo  - name, sauce, input
#   dict      - name, input, state 
#   list
# 
#  Sauce is a NIST -classified known standard CS algorithm. 
#   UIElement(code)
#   actionHandler
#   aBindingBetweenElement_actionHandler

# A interface shields something. It reduces
#   the scope, of its internals. Internals are the tiles
#   inside a sheild. 
#
# Shield may break, become "unshielded" iff:
#   - scope violated from inside
#   - a Tile gets loose in the shield's own perimeter

# documenting of a method

# Perimeter is defined as continuous area, of Shield.
# Perimeter is thus the enclosing, which can be walked
# through left, up, right, and down steps. 


# Värit
WHITE = (255, 255, 255)
GREY = (200, 200, 200)
BLUE = (50, 50, 255)
RED = (255, 50, 50)
GREEN = (50, 200, 50)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BeToni™ Etenijä + Poisto")
clock = pygame.time.Clock()

# --- Tietorakenteet ---
tiles = []
connections = []
goal = (WIDTH // 2, HEIGHT // 2)
score = 0  # pisteet lisäyksistä ja poistoista

def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def add_tile():
    """Lisää tiilen sääntöjen mukaan"""
    global score
    if not tiles:
        x = random.randint(0, WIDTH // TILE_SIZE - 1) * TILE_SIZE
        y = random.randint(0, HEIGHT // TILE_SIZE - 1) * TILE_SIZE
    else:
        base_x, base_y = random.choice(tiles)
        options = [
            (base_x + TILE_SIZE, base_y),
            (base_x - TILE_SIZE, base_y),
            (base_x, base_y + TILE_SIZE),
            (base_x, base_y - TILE_SIZE)
        ]
        options = [(ox, oy) for ox, oy in options if 0 <= ox < WIDTH and 0 <= oy < HEIGHT and (ox, oy) not in tiles]
        if not options:
            return
        # valitaan vaihtoehto, joka vie kohti maalia
        options.sort(key=lambda o: distance(o, goal))
        x, y = options[0]

    tiles.append((x, y))
    add_connections(x, y)
    score += 1  # lisäyksestä +1

def remove_tile():
    """Poistaa tiilen, jos minimalismi sallii"""
    global score
    if len(tiles) <= 1:
        return
    # Poistetaan satunnainen tiili, joka ei ole liian lähellä maalia
    removable = [t for t in tiles if distance(t, goal) > TILE_SIZE]
    if not removable:
        return
    t = random.choice(removable)
    tiles.remove(t)
    # Poista yhteydet, joissa esiintyy tämä tiili
    global connections
    connections = [c for c in connections if c[0] != (t[0]+TILE_SIZE//2, t[1]+TILE_SIZE//2) and c[1] != (t[0]+TILE_SIZE//2, t[1]+TILE_SIZE//2)]
    score += 2  # poiston pisteet +2

def add_connections(x, y):
    for (tx, ty) in tiles:
        if (tx, ty) == (x, y):
            continue
        if abs(tx - x) <= TILE_SIZE and abs(ty - y) <= TILE_SIZE:
            connections.append(((x + TILE_SIZE//2, y + TILE_SIZE//2),
                                (tx + TILE_SIZE//2, ty + TILE_SIZE//2)))

def draw():
    screen.fill(WHITE)
    for (start, end) in connections:
        pygame.draw.line(screen, GREY, start, end, 3)
    for (x, y) in tiles:
        pygame.draw.rect(screen, BLUE, (x, y, TILE_SIZE, TILE_SIZE))
    pygame.draw.circle(screen, RED, (goal[0]+TILE_SIZE//2, goal[1]+TILE_SIZE//2), TILE_SIZE//2)
    # Näytetään pisteet
    font = pygame.font.SysFont(None, 30)
    text = font.render(f"Score: {score}", True, GREEN)
    screen.blit(text, (10, 10))
    pygame.display.flip()

# --- Pääsilmukka ---
running = True
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Päätetään satunnaisesti + tai -
    if random.random() < 0.6:  # 60% todennäköisyys lisäykselle
        add_tile()
    else:
        remove_tile()
    draw()

pygame.quit()

