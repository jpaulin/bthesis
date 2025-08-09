"""
robot_armada_programmer.py

Robot-T armada with RAM, interpreter, and a mouse-driven programming UI + legibility evaluator.

Run:
    pip install pygame numpy
    python robot_armada_programmer.py
"""

import pygame
import random
import math
import numpy as np
from collections import Counter

# ---------------- Config ----------------
WIDTH, HEIGHT = 500, 500
PANEL_W = 320
WIN_W, WIN_H = WIDTH + PANEL_W, HEIGHT
BOT_RADIUS = 3
N_AGENTS = 5
FOV_DEG = 30
FOV_RANGE = 75
BOT_SPEED = 2.0
RAM_WORDS = 256  # 1 KB (256 * 4 bytes)
FPS = 60

# Opcodes (8-bit)
OP_NOP  = 0
OP_MOV  = 1
OP_ADD  = 2
OP_SUB  = 3
OP_JMP  = 4
OP_JZ   = 5
OP_CMP  = 6
OP_SEN  = 7
OP_ACT  = 8
OP_LDK  = 9
OP_WRT  = 10

OP_NAMES = {
    OP_NOP: "NOP", OP_MOV: "MOV", OP_ADD: "ADD", OP_SUB: "SUB",
    OP_JMP: "JMP", OP_JZ: "JZ", OP_CMP: "CMP", OP_SEN: "SEN",
    OP_ACT: "ACT", OP_LDK: "LDK", OP_WRT: "WRT"
}

# Registers indices
R0, R1, R2, R3 = 0, 1, 2, 3
NREG = 4

# Shared knowledge repository
REPO = []

# --- Helpers for encoding/decoding 32-bit instruction words ---
def encode(op, a=0, b=0, imm=0):
    return np.uint32((op & 0xFF) << 24 | (a & 0xFF) << 16 | (b & 0xFF) << 8 | (imm & 0xFF))

def decode(word):
    w = int(np.uint32(word))
    op = (w >> 24) & 0xFF
    a  = (w >> 16) & 0xFF
    b  = (w >> 8) & 0xFF
    imm= w & 0xFF
    return op, a, b, imm

def asm_from_word(word):
    op, a, b, imm = decode(word)
    name = OP_NAMES.get(op, f"OP{op}")
    if op in (OP_MOV, OP_ADD, OP_SUB, OP_CMP):
        # format common: MN A, B/IMM
        if b == 0:
            return f"{name} R{a}, {imm}"
        else:
            return f"{name} R{a}, R{b}"
    elif op in (OP_JMP, OP_JZ):
        return f"{name} {a}"
    elif op == OP_SEN:
        return f"{name} R{a}, {imm}"
    elif op == OP_ACT:
        return f"{name} R{a}"
    elif op == OP_LDK:
        return f"{name} R{a}, {imm}"
    elif op == OP_WRT:
        return f"{name} {imm}"
    elif op == OP_NOP:
        return "NOP"
    else:
        return f"{name} {a} {b} {imm}"

# ---------------- Legibility Evaluator ----------------
def legibility_score(source_lines):
    """
    Compute a 0..100 readability score for an assembly-like source (list of lines).
    Heuristics:
      - shorter average line length -> better
      - fewer excessively long lines (>80 chars) -> better
      - higher variety of instructions (not repeating same line) -> better
      - presence of multiple opcodes -> slightly better
    This is intentionally simple and fast — it's a heuristic "legibility" signal used as part of a penalty.
    """
    if not source_lines:
        return 100.0

    # clean lines
    lines = [ln.strip() for ln in source_lines if ln.strip()]
    if not lines:
        return 100.0

    avg_len = sum(len(ln) for ln in lines) / len(lines)
    long_lines_ratio = sum(1 for ln in lines if len(ln) > 80) / len(lines)

    # repetitiveness: unique lines ratio
    unique_ratio = len(set(lines)) / len(lines)

    # opcode diversity
    opcodes = []
    for ln in lines:
        parts = ln.split()
        if parts:
            opcodes.append(parts[0])
    unique_opcodes = len(set(opcodes))
    opcode_diversity = unique_opcodes / max(1, len(opcodes))

    # heuristic penalties/bonuses
    score = 100.0

    # average line length penalty (scaled)
    score -= max(0.0, (avg_len - 40.0)) * 0.6  # lines longer than 40 cost points

    # long line heavy penalty
    score -= long_lines_ratio * 20.0

    # repetitiveness penalty
    score -= (1.0 - unique_ratio) * 30.0

    # opcode diversity bonus
    score += opcode_diversity * 10.0

    # clamp
    score = max(0.0, min(100.0, score))
    return score

# ---------------- Pygame Init ----------------
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Robot-T Armada — Programmer UI")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 16)
bigfont = pygame.font.SysFont(None, 20)

# ---------------- World (resources) ----------------
RESOURCE_COUNT = 12
resources = [(random.randint(20, WIDTH-20), random.randint(20, HEIGHT-20)) for _ in range(RESOURCE_COUNT)]

# ---------------- Bot Class with Interpreter ----------------
class Bot:
    def __init__(self, x, y, angle, idnum):
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)
        self.id = idnum
        self.ram = np.zeros(RAM_WORDS, dtype=np.uint32)
        self.reg = np.zeros(NREG, dtype=np.int32)
        self.pc = 0
        self.zero_flag = False
        self.energy = 100.0
        # boot small program (optional) - leave zeros by default
        self.init_ptr = 0

    def find_next_free(self):
        # find first index from 0 where ram==0 (treat 0 as free)
        nz = np.nonzero(self.ram)[0]
        if len(nz) == 0:
            return 0
        # find first gap after last nonzero? We'll append after last nonzero index
        last = int(nz.max())
        if last + 1 < RAM_WORDS:
            return last + 1
        # wrap search for any zero
        zeros = np.where(self.ram == 0)[0]
        if zeros.size > 0:
            return int(zeros[0])
        return 0  # fallback

    def append_instr(self, word):
        idx = self.find_next_free()
        self.ram[idx] = word
        return idx

    def clear_ram(self):
        self.ram.fill(0)
        self.pc = 0

    def get_program_lines(self):
        lines = []
        # decode until a zero or RAM_WORDS
        for w in self.ram:
            if int(w) == 0:
                break
            lines.append(asm_from_word(w))
        return lines

    # Interpreter step (simple version)
    def step(self):
        if self.energy <= 0:
            return
        word = int(self.ram[self.pc])
        op, a, b, imm = decode(word)
        def reg_val(idx):
            return int(self.reg[idx]) if 0 <= idx < NREG else 0
        def set_reg(idx, val):
            if 0 <= idx < NREG:
                self.reg[idx] = int(val)
        next_pc = (self.pc + 1) % RAM_WORDS
        if op == OP_NOP:
            pass
        elif op == OP_MOV:
            val = imm if b == 0 else reg_val(b)
            set_reg(a, val)
        elif op == OP_ADD:
            val = reg_val(a) + (reg_val(b) if b != 0 else imm)
            set_reg(a, val)
        elif op == OP_SUB:
            val = reg_val(a) - (reg_val(b) if b != 0 else imm)
            set_reg(a, val)
        elif op == OP_JMP:
            next_pc = a % RAM_WORDS
        elif op == OP_JZ:
            if self.zero_flag:
                next_pc = a % RAM_WORDS
        elif op == OP_CMP:
            left = reg_val(a)
            right = reg_val(b) if b != 0 else imm
            self.zero_flag = (left == right)
        elif op == OP_SEN:
            reading = self.sensor(imm)
            set_reg(a, int(reading))
        elif op == OP_ACT:
            self.act(reg_val(a))
        elif op == OP_LDK:
            idx = imm
            if 0 <= idx < len(REPO):
                set_reg(a, int(REPO[idx] & 0xFF))
            else:
                set_reg(a, 0)
        elif op == OP_WRT:
            marker = imm
            REPO.append(marker & 0xFF)
        else:
            pass
        self.energy -= 0.02
        self.pc = next_pc

    # primitives
    def sensor(self, sensor_id):
        if sensor_id == 0:
            dist_left = self.x
            dist_right = WIDTH - self.x
            dist_top = self.y
            dist_bottom = HEIGHT - self.y
            return int(min(dist_left, dist_right, dist_top, dist_bottom))
        elif sensor_id == 1:
            return int((math.sin(self.x / 30.0) + math.cos(self.y / 30.0)) * 50 + 50)
        elif sensor_id == 2:
            if resources:
                dists = [math.hypot(rx - self.x, ry - self.y) for rx, ry in resources]
                return int(min(dists))
            return 999
        else:
            return 0

    def act(self, val):
        if val <= 0:
            return
        if resources:
            dists = [(math.hypot(rx - self.x, ry - self.y), rx, ry) for rx, ry in resources]
            dists.sort()
            dist, rx, ry = dists[0]
            if dist < 2:
                try:
                    resources.remove((rx, ry))
                except ValueError:
                    pass
                self.energy = min(200, self.energy + 8)
            else:
                step = min(BOT_SPEED * (val / 2.0), 2.0)
                ang = math.atan2(ry - self.y, rx - self.x)
                self.x += math.cos(ang) * step
                self.y += math.sin(ang) * step
        self.x = max(BOT_RADIUS, min(WIDTH - BOT_RADIUS, self.x))
        self.y = max(BOT_RADIUS, min(HEIGHT - BOT_RADIUS, self.y))

    def wander(self):
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * (BOT_SPEED * 0.15)
        self.y += math.sin(rad) * (BOT_SPEED * 0.15)
        if self.x <= BOT_RADIUS or self.x >= WIDTH - BOT_RADIUS:
            self.angle = (180 - self.angle) % 360
        if self.y <= BOT_RADIUS or self.y >= HEIGHT - BOT_RADIUS:
            self.angle = (-self.angle) % 360
        self.angle += random.uniform(-8, 8)
        self.angle %= 360

    def draw(self, surface, highlight=False):
        color = (180, 180, 180) if not highlight else (255, 220, 120)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), BOT_RADIUS)
        # FOV arc
        step_deg = 6
        points = [(self.x, self.y)]
        start = int(self.angle - FOV_DEG / 2)
        end   = int(self.angle + FOV_DEG / 2)
        for deg in range(start, end + 1, step_deg):
            rad = math.radians(deg)
            px = self.x + math.cos(rad) * FOV_RANGE
            py = self.y + math.sin(rad) * FOV_RANGE
            points.append((px, py))
        pygame.draw.polygon(surface, (90, 100, 160), points, width=1)

    def hud_lines(self):
        return [
            f"ID:{self.id} PC:{self.pc} E:{self.energy:.1f}",
            f"R0:{self.reg[0]} R1:{self.reg[1]} Z:{int(self.zero_flag)}",
            f"ProgLines:{len(self.get_program_lines())} REPO:{len(REPO)}"
        ]

# ---------------- Create bots ----------------
bots = []
for i in range(N_AGENTS):
    x = random.randint(40, WIDTH - 40)
    y = random.randint(40, HEIGHT - 40)
    angle = random.uniform(0, 360)
    bots.append(Bot(x, y, angle, idnum=i))

selected_bot = None

# ---------------- UI helpers ----------------
def draw_panel_bg():
    panel_rect = pygame.Rect(WIDTH, 0, PANEL_W, WIN_H)
    pygame.draw.rect(screen, (40, 40, 45), panel_rect)
    pygame.draw.line(screen, (70,70,80), (WIDTH,0), (WIDTH,WIN_H), 2)

def draw_text(x, y, txt, c=(220,220,220), big=False):
    f = bigfont if big else font
    screen.blit(f.render(txt, True, c), (x, y))

# Interactive control state (for building instruction operands)
ctrl_a = 0      # register a (0..3)
ctrl_b_is_reg = True
ctrl_b = 0      # if b is reg index (0..3), if not used then imm used
ctrl_imm = 0    # immediate 0..255

# Buttons definition (rects)
BUTTONS = []
def make_button(x, y, w, h, label):
    r = pygame.Rect(x, y, w, h)
    BUTTONS.append((r, label))
    return r

# create mnemonic buttons in panel grid
btn_x = WIDTH + 12
btn_y = 160
btn_w = 140
btn_h = 30
gap = 8

mnemonics = [("MOV", OP_MOV), ("ADD", OP_ADD), ("SUB", OP_SUB), ("JMP", OP_JMP),
             ("JZ", OP_JZ), ("CMP", OP_CMP), ("SEN", OP_SEN), ("ACT", OP_ACT),
             ("LDK", OP_LDK), ("WRT", OP_WRT), ("NOP", OP_NOP), ("CLEAR", "CLEAR"),
             ("INC_IMM", "INC_IMM"), ("DEC_IMM", "DEC_IMM")]
rows = 4
for i, (label, code) in enumerate(mnemonics):
    x = btn_x + (i % 2) * (btn_w + gap)
    y = btn_y + (i // 2) * (btn_h + gap)
    make_button(x, y, btn_w, btn_h, label)

# helper to draw buttons
def draw_buttons(mouse_pos):
    for rect, label in BUTTONS:
        pygame.draw.rect(screen, (70,70,80), rect)
        pygame.draw.rect(screen, (100,100,110), rect, 2)
        txt = font.render(label, True, (220,220,220))
        screen.blit(txt, (rect.x + 8, rect.y + 6))
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (140,140,140), rect, 2)

def handle_button_click(pos):
    global selected_bot, ctrl_a, ctrl_b_is_reg, ctrl_b, ctrl_imm
    for rect, label in BUTTONS:
        if rect.collidepoint(pos):
            if selected_bot is None:
                return
            bot = selected_bot
            if label == "CLEAR":
                bot.clear_ram()
                return
            if label == "INC_IMM":
                ctrl_imm = (ctrl_imm + 1) % 256
                return
            if label == "DEC_IMM":
                ctrl_imm = (ctrl_imm - 1) % 256
                return
            # find opcode
            opname = label
            op = None
            if opname in OP_NAMES.values():
                for k,v in OP_NAMES.items():
                    if v == opname:
                        op = k
                        break
            if opname == "NOP":
                op = OP_NOP
            if opname == "MOV":
                # MOV a, imm or reg
                b_field = 0 if not ctrl_b_is_reg else ctrl_b
                imm_field = ctrl_imm if (not ctrl_b_is_reg) else 0
                word = encode(OP_MOV, ctrl_a, (ctrl_b if ctrl_b_is_reg else 0), (ctrl_imm if not ctrl_b_is_reg else 0))
                bot.append_instr(word)
            elif opname == "ADD":
                word = encode(OP_ADD, ctrl_a, (ctrl_b if ctrl_b_is_reg else 0), (ctrl_imm if not ctrl_b_is_reg else 0))
                bot.append_instr(word)
            elif opname == "SUB":
                word = encode(OP_SUB, ctrl_a, (ctrl_b if ctrl_b_is_reg else 0), (ctrl_imm if not ctrl_b_is_reg else 0))
                bot.append_instr(word)
            elif opname == "JMP":
                word = encode(OP_JMP, ctrl_imm, 0, 0)
                bot.append_instr(word)
            elif opname == "JZ":
                word = encode(OP_JZ, ctrl_imm, 0, 0)
                bot.append_instr(word)
            elif opname == "CMP":
                word = encode(OP_CMP, ctrl_a, (ctrl_b if ctrl_b_is_reg else 0), (ctrl_imm if not ctrl_b_is_reg else 0))
                bot.append_instr(word)
            elif opname == "SEN":
                word = encode(OP_SEN, ctrl_a, 0, ctrl_imm)
                bot.append_instr(word)
            elif opname == "ACT":
                word = encode(OP_ACT, ctrl_a, 0, 0)
                bot.append_instr(word)
            elif opname == "LDK":
                word = encode(OP_LDK, ctrl_a, 0, ctrl_imm)
                bot.append_instr(word)
            elif opname == "WRT":
                word = encode(OP_WRT, 0, 0, ctrl_imm)
                bot.append_instr(word)
            elif opname == "NOP":
                word = encode(OP_NOP, 0, 0, 0)
                bot.append_instr(word)
            return

# ---------------- Main Loop ----------------
running = True
paused = False

while running:
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx < WIDTH:
                # clicked in world: select bot if near
                sel = None
                for b in bots:
                    if math.hypot(b.x - mx, b.y - my) < 8:
                        sel = b
                        break
                selected_bot = sel
            else:
                # clicked in panel region: handle button clicks & control areas
                handle_button_click(event.pos)
                # check small controls for A, B toggles, imm area
                # A reg selector area
                ax, ay, aw, ah = WIDTH + 12, 40, 120, 28
                bx = WIDTH + 12; by = 80
                if ax <= mx <= ax + aw and ay <= my <= ay + ah:
                    # cycle A register
                    ctrl_a = (ctrl_a + 1) % 4
                # B mode toggle area
                if bx <= mx <= bx + aw and by <= my <= by + ah:
                    ctrl_b_is_reg = not ctrl_b_is_reg
                # imm inc/dec clickable small areas
                imm_x, imm_y = WIDTH + 150, 40
                if imm_x <= mx <= imm_x + 140 and imm_y <= my <= imm_y + 28:
                    ctrl_imm = (ctrl_imm + 1) % 256
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused
            if event.key == pygame.K_r:
                REPO.clear()
            if event.key == pygame.K_ESCAPE:
                running = False

    if not paused:
        for bot in bots:
            bot.step()
            bot.wander()

    # Draw world
    screen.fill((28,28,28))
    # resources
    for rx, ry in resources:
        pygame.draw.circle(screen, (0,170,0), (int(rx), int(ry)), 4)
    # bots
    mx, my = pygame.mouse.get_pos()
    for b in bots:
        highlight = (selected_bot is b) or (math.hypot(b.x - mx, b.y - my) < 12)
        b.draw(screen, highlight=highlight)

    # Draw right panel
    draw_panel_bg()
    # Title + instructions
    draw_text(WIDTH + 12, 6, "Robot-T Programmer", big=True)
    draw_text(WIDTH + 12, 28, "Click a bot to select it. Use controls then click mnemonic.")

    # Controls: A register
    draw_text(WIDTH + 12, 40, f"A (dest reg): R{ctrl_a}")
    pygame.draw.rect(screen, (60,60,70), (WIDTH + 12, 40, 120, 28), 2)
    draw_text(WIDTH + 12, 80, f"B mode: {'Reg' if ctrl_b_is_reg else 'IMM'} (click to toggle)")
    pygame.draw.rect(screen, (60,60,70), (WIDTH + 12, 80, 120, 28), 2)
    # show B reg if reg-mode
    draw_text(WIDTH + 12, 112, f"B reg: R{ctrl_b}" if ctrl_b_is_reg else f"IMM: {ctrl_imm}")
    # imm box
    pygame.draw.rect(screen, (60,60,70), (WIDTH + 150, 40, 140, 28), 2)
    draw_text(WIDTH + 152, 44, f"IMM: {ctrl_imm}")

    # Draw buttons
    draw_buttons(mouse_pos)

    # Selected bot info and program listing
    if selected_bot:
        draw_text(WIDTH + 12, 220, f"Selected Bot: ID {selected_bot.id}", big=True)
        # Show basic HUD
        for i, line in enumerate(selected_bot.hud_lines()):
            draw_text(WIDTH + 12, 250 + i*16, line)
        # Program lines
        lines = selected_bot.get_program_lines()
        draw_text(WIDTH + 12, 320, "Program (RAM):", big=True)
        y0 = 344
        for i, ln in enumerate(lines[:10]):  # show top 10 lines
            draw_text(WIDTH + 12, y0 + i*14, f"{i:03}: {ln}", c=(200,200,200))
        if len(lines) > 10:
            draw_text(WIDTH + 12, y0 + 10*14, f"... ({len(lines)} lines total)")

        # Legibility score
        score = legibility_score(lines)
        draw_text(WIDTH + 12, y0 + 12*14, f"Readability: {score:.1f} / 100", big=True)

    else:
        draw_text(WIDTH + 12, 220, "No bot selected. Click a bot on the field.", big=True)

    # REPO preview
    draw_text(WIDTH + 12, WIN_H - 80, f"REPO (last 8): {', '.join(map(str, REPO[-8:]))}")

    # hint
    draw_text(WIDTH + 12, WIN_H - 40, "Space: pause | R: clear global REPO | Click panel elements with mouse")

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
