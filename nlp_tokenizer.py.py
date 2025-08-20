import pygame
import sys
import math
import random
from typing import List, Tuple

# -----------------------------
# Simple subword tokenizer (demo)
# -----------------------------
# This is NOT the real tokenizer used by LLMs, but a didactic stand-in that
# splits a word into chunks of up to N characters and prefixes continuation
# chunks with "##" to mimic WordPiece-like visuals.

def subword_tokenize(word: str, max_len: int = 4) -> List[str]:
    # keep apostrophes and hyphens with their neighbors for nicer splits
    clean = word
    tokens = []
    i = 0
    while i < len(clean):
        j = min(i + max_len, len(clean))
        piece = clean[i:j]
        if i > 0:
            piece = "##" + piece
        tokens.append(piece)
        i = j
    return tokens

# -----------------------------
# Config
# -----------------------------
W, H = 1100, 700
FPS = 60
WORD_PHASE_SECS = 3.0    # show the full word for 3 seconds
TOKENS_PHASE_SECS = 3.0  # then show tokenization + surroundings for 3 seconds
BG = (12, 14, 18)
FG = (230, 232, 235)
MUTED = (140, 145, 150)
CURSOR = (100, 200, 255)

# Pleasant distinct colors for token surrounds
PALETTE = [
    (250, 114, 104),  # coral
    (130, 201, 30),   # green
    (88, 190, 230),   # blue
    (255, 198, 92),   # amber
    (193, 129, 255),  # purple
    (109, 217, 180),  # teal
    (255, 154, 162),  # pink
    (255, 211, 105),  # yellow
]

# Demo paragraph (edit this to try your own)
PARAGRAPH = (
    "Natural language processing breaks text into tokens. "
    "Sometimes a single word becomes multiple subword tokens, "
    "especially for rare or compound words like 'tokenization' or 'hyper-parameters'."
)

# -----------------------------
# Helpers
# -----------------------------

def wrap_words(text: str) -> List[str]:
    # Simple word split preserving punctuation
    return text.split()


def layout_multiline(surface, text, font, color, x, y, max_width, line_gap=6):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    yy = y
    rects = []
    for line in lines:
        surf = font.render(line, True, color)
        r = surf.get_rect(topleft=(x, yy))
        surface.blit(surf, r)
        rects.append((line, r))
        yy += surf.get_height() + line_gap
    return rects


def draw_center_text(surface, text, font, color, y):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(W // 2, y))
    surface.blit(surf, rect)
    return rect


def rounded_rect(surface, rect: pygame.Rect, color: Tuple[int, int, int], radius=10, width=0):
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)


def token_boxes(surface, tokens: List[str], font, center_y: int, hpad=16, vpad=10, gap=10):
    # Compute total width to center all tokens
    token_surfs = [font.render(t, True, FG) for t in tokens]
    rects = []
    widths = [s.get_width() + 2 * hpad for s in token_surfs]
    heights = [s.get_height() + 2 * vpad for s in token_surfs]
    total_w = sum(widths) + gap * (len(tokens) - 1)
    x = (W - total_w) // 2
    for i, (surf, w, h) in enumerate(zip(token_surfs, widths, heights)):
        color = PALETTE[i % len(PALETTE)]
        r = pygame.Rect(x, center_y - h // 2, w, h)
        # Soft filled background
        fill = (*color[:3],)
        # Draw translucent-like effect by blending: simulate via a darker fill
        inner = r.inflate(-2, -2)
        rounded_rect(surface, r, (color[0]//6, color[1]//6, color[2]//6), radius=14, width=0)
        # Border
        rounded_rect(surface, r, color, radius=14, width=2)
        # Text
        tx = r.x + (r.w - surf.get_width()) // 2
        ty = r.y + (r.h - surf.get_height()) // 2
        surface.blit(surf, (tx, ty))
        rects.append(r)
        x += w + gap
    return rects


def highlight_current_word_in_paragraph(surface, paragraph: str, current_index: int, font, x, y, max_width):
    words = paragraph.split(" ")
    # Rebuild with styling by drawing word-by-word and wrapping manually
    cx, cy = x, y
    space_w = font.size(" ")[0]
    line_h = font.get_height() + 6
    for i, w in enumerate(words):
        surf = font.render(w, True, FG if i == current_index else MUTED)
        w_w, w_h = surf.get_size()
        if cx + w_w > x + max_width:
            cx = x
            cy += line_h
        surface.blit(surf, (cx, cy))
        if i == current_index:
            # underline to emphasize the focus word in the paragraph context
            pygame.draw.line(surface, CURSOR, (cx, cy + w_h + 2), (cx + w_w, cy + w_h + 2), 2)
        cx += w_w + space_w

# -----------------------------
# Main
# -----------------------------

def main():
    pygame.init()
    pygame.display.set_caption("NLP Token Visualization — Word → Tokens")
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont(None, 34)
    word_font = pygame.font.SysFont(None, 82)
    token_font = pygame.font.SysFont(None, 44)
    para_font = pygame.font.SysFont(None, 26)

    words = wrap_words(PARAGRAPH)
    # Pre-tokenize all words for speed
    tokenized = [subword_tokenize(w) for w in words]

    idx = 0
    phase = "word"  # or "tokens"
    elapsed = 0.0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                    # manual advance
                    phase = "tokens" if phase == "word" else "word"
                    if phase == "word":
                        idx = (idx + 1) % len(words)
                    elapsed = 0.0
                elif event.key == pygame.K_LEFT:
                    # manual back
                    if phase == "word":
                        idx = (idx - 1) % len(words)
                    else:
                        phase = "word"
                    elapsed = 0.0

        # Auto advance
        if phase == "word" and elapsed >= WORD_PHASE_SECS:
            phase = "tokens"
            elapsed = 0.0
        elif phase == "tokens" and elapsed >= TOKENS_PHASE_SECS:
            phase = "word"
            idx = (idx + 1) % len(words)
            elapsed = 0.0

        # Draw
        screen.fill(BG)

        # Title / legend
        title = "Phase: WORD" if phase == "word" else "Phase: TOKENS (colored surrounds)"
        draw_center_text(screen, title, title_font, FG, 36)

        # Paragraph context at bottom
        margin = 60
        highlight_current_word_in_paragraph(
            screen, PARAGRAPH, idx, para_font, margin, H - 220, W - margin * 2
        )

        # Focus area
        focus_y = H // 2 - 40
        current_word = words[idx]
        if phase == "word":
            # Big word
            rect = draw_center_text(screen, current_word, word_font, FG, focus_y)
            # A subtle halo around the word to suggest a future breakdown
            halo = rect.inflate(40, 24)
            pygame.draw.rect(screen, (60, 80, 120), halo, width=2, border_radius=18)
            # Countdown indicator
            t = max(0.0, WORD_PHASE_SECS - elapsed)
            timer_txt = f"Next: tokens in {t:0.1f}s — press SPACE to toggle"
            draw_center_text(screen, timer_txt, title_font, MUTED, focus_y + 90)
        else:
            toks = tokenized[idx]
            # Show the original word faintly above
            draw_center_text(screen, current_word, title_font, MUTED, focus_y - 70)
            # Tokens with colored surrounds
            token_boxes(screen, toks, token_font, focus_y)
            # Countdown indicator
            t = max(0.0, TOKENS_PHASE_SECS - elapsed)
            timer_txt = f"Next: next word in {t:0.1f}s — ←/→ to step"
            draw_center_text(screen, timer_txt, title_font, MUTED, focus_y + 110)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
