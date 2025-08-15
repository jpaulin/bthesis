import pygame
import numpy as np
import random

# --- Config ---
WIDTH, HEIGHT = 800, 600
BOT_COUNT = 500
DOT_COUNT = 15
BOT_SPEED = 2
TURN_ANGLE = 1
MOVE_COST = 0.3
DOT_ENERGY = 200
SEQ_MIN_LEN = 4
PREF_INCREASE = 0.01
FAT_FACTOR = 1.2  # 20% more energy than self
TRAIL_REACH_DIST = 1  # Distance threshold to "arrive" at trail target

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# --- Command definitions ---
FWD, RT, LT, FWD_UNTIL, TRAIL = 0, 1, 2, 3, 4
COMMANDS = [FWD, RT, LT, FWD_UNTIL, TRAIL]

def draw_dashed_line(surf, color, start_pos, end_pos, width=1, dash_length=5):
    """Draw a dashed line between two points."""
    x1, y1 = start_pos
    x2, y2 = end_pos
    dl = dash_length

    length = np.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    dx = (x2 - x1) / length
    dy = (y2 - y1) / length

    for i in np.arange(0, length, dl * 2):
        start = (x1 + dx * i, y1 + dy * i)
        end = (x1 + dx * min(i + dl, length), y1 + dy * min(i + dl, length))
        pygame.draw.line(surf, color, start, end, width)

class Bot:
    def __init__(self, x, y, color, all_bots_ref):
        self.x, self.y = x, y
        self.angle = random.uniform(0, 360)
        self.energy = 30
        self.color = color
        
        # Start with a random sequence
        self.command_queue = [random.choice(COMMANDS) for _ in range(6)]
        self.cmd_index = 0
        
        # Learning: store sequences and preferences
        self.preferences = {tuple(self.command_queue): 1.0}
        self.bounty_count = 0
        
        # Access to other bots
        self.all_bots_ref = all_bots_ref
        
        # Trail state
        self.trail_target = None
        self.is_trailing = False
    
    def _move_forward(self, dots, check_only=False):
        """Moves forward by one step, returns False if edge or bounty found."""
        new_x = self.x + BOT_SPEED * np.cos(np.radians(self.angle))
        new_y = self.y + BOT_SPEED * np.sin(np.radians(self.angle))

        # Check arena bounds (edge detection)
        if new_x < 5 or new_x > WIDTH - 5 or new_y < 5 or new_y > HEIGHT - 5:
            return False  # Hit arena edge

        # Check for bounty (energy dot)
        for dx, dy in dots:
            if np.hypot(new_x - dx, new_y - dy) < 8:
                if not check_only:
                    self.energy += DOT_ENERGY
                    self.bounty_count += 1
                    dots.remove([dx, dy])
                return False

        if not check_only:
            self.x, self.y = new_x, new_y
            self.energy -= MOVE_COST
        return True
    
    def _set_trail_target(self):
        """Pick a new trail target based on well-off bots."""
        well_off = [b for b in self.all_bots_ref if b is not self and b.energy >= self.energy * FAT_FACTOR]
        if len(well_off) < 2:
            return None
        avg_x = sum(b.x for b in well_off) / len(well_off)
        avg_y = sum(b.y for b in well_off) / len(well_off)
        return (avg_x, avg_y)
    
    def _follow_trail_target(self, dots):
        """Move toward the current trail target."""
        if not self.trail_target:
            return
        tx, ty = self.trail_target
        dx, dy = tx - self.x, ty - self.y
        dist = np.hypot(dx, dy)
        if dist < TRAIL_REACH_DIST:
            self.trail_target = None
            return
        target_angle = np.degrees(np.arctan2(dy, dx))
        self.angle = target_angle
        self._move_forward(dots)
    
    def step(self, dots):
        if self.energy <= 0:
            return
        
        self.is_trailing = False  # Reset each step
        
        cmd = self.command_queue[self.cmd_index]
        self.cmd_index = (self.cmd_index + 1) % len(self.command_queue)

        if cmd == FWD:
            self._move_forward(dots)

        elif cmd == RT:
            self.angle += TURN_ANGLE
            self.energy -= MOVE_COST

        elif cmd == LT:
            self.angle -= TURN_ANGLE
            self.energy -= MOVE_COST

        elif cmd == FWD_UNTIL:
            moved = True
            while moved and self.energy > 0:
                moved = self._move_forward(dots, check_only=True)
                if moved:
                    self._move_forward(dots)  # Actually move and spend energy
        
        elif cmd == TRAIL:
            if not self.trail_target:
                self.trail_target = self._set_trail_target()
            if self.trail_target:
                self.is_trailing = True
                self._follow_trail_target(dots)
    
    def learn(self):
        if self.bounty_count > 0:
            seq = tuple(self.command_queue)
            if seq not in self.preferences:
                self.preferences[seq] = 1.0
            self.preferences[seq] *= (1.0 + PREF_INCREASE)
        self.bounty_count = 0
    
    def mutate_sequence(self):
        # Occasionally try another sequence
        if random.random() < 0.2:
            self.command_queue = [random.choice(COMMANDS) for _ in range(6)]
            self.cmd_index = 0
        else:
            # Weighted pick of known sequences
            sequences = list(self.preferences.keys())
            weights = np.array([self.preferences[s] for s in sequences])
            weights /= weights.sum()
            chosen = random.choices(sequences, weights=weights)[0]
            self.command_queue = list(chosen)
            self.cmd_index = 0

def spawn_dots():
    return [[random.randint(0, WIDTH), random.randint(0, HEIGHT)] for _ in range(DOT_COUNT)]

# --- Main ---
bots = []
bots.extend(Bot(random.randint(0, WIDTH), random.randint(0, HEIGHT),
                (random.randint(100,255), random.randint(100,255), random.randint(100,255)),
                bots)
            for _ in range(BOT_COUNT))

dots = spawn_dots()
running = True
frame_counter = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    screen.fill((0, 0, 0))
    
    # Draw dots
    for dx, dy in dots:
        pygame.draw.circle(screen, (0, 255, 0), (int(dx), int(dy)), 5)
    
    # Update and draw bots
    for bot in bots:
        bot.step(dots)
        pygame.draw.circle(screen, bot.color, (int(bot.x), int(bot.y)), 6)
        if bot.is_trailing and bot.trail_target:
            draw_dashed_line(screen, (0, 0, 255), (bot.x, bot.y), bot.trail_target, width=1, dash_length=6)
    
    pygame.display.flip()
    clock.tick(60)
    
    frame_counter += 1
    if frame_counter % 300 == 0:  # Every 5 seconds
        for bot in bots:
            bot.learn()
            bot.mutate_sequence()
        if len(dots) < DOT_COUNT:
            dots.extend(spawn_dots()[:DOT_COUNT - len(dots)])

pygame.quit()

