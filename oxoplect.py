"""
PC Robots -tyylinen simppeli Pygame-simulaatio
- N_AGENTS = 6
- Jokaisella agentilla on "sandbox code bubble" joka sisältää energiaa
- Energia jaetaan kolmen toiminnon kesken: move, self-repair, generate (greenfield)
- Jokainen kierros (round) agentti valitsee 1/3 toiminnoista ja käyttää poolista energiaa
- Toiminnot:
    * MOVE: liikuttaa agenttia, kuluttaa move_pool energiaa
    * REPAIR: käyttää repair_pool energiaa parantaakseen health:ia
    * GENERATE: käyttää generate_pool energiaa synnyttämään greenfield-tokenin
- Greenfield-tokenit voi poimia (collect) ja ne antavat energiaa takaisin agentille
- Simulaatio on vuoropohjainen: 
  paina välilyöntiä (Space) siirtyäksesi seuraavaan kierrokseen

Robottien elämisen maalit (boidance)
- I  pysy elossa
- II ole toisille hyödyksi
- III käytä hieman energiaa aina siihen että opit paremmin 
- IV ota vastuu itsestäsi; siis siitä että olet itsenäinen
- V (optionaalinen) miten lisätään yhteisvastuullisuus eli yhteiskunta
- VI altruismin käsite bota-yhteiskunnassa
- liike on riski, ja teko myös; teko voi olla toisen botin mendaus
- Opitun vaaliminen repositoryssa; perusta repo. Kuka saa commit:aa? 
- oppimiseen tarvitaan liikettä ja tekoja! 
- "taudit" eli tautien konsepti, exogenous risk
- sodat, tai kahina, resurssikilvat
- Ei vielä: ehdotukset ja politiikka: miten eri heimot voivat kommunikoida? 
- tee siis tekoja, kunhan se ei vaaranna tai sodi vastaan ^ aiempia periaatteita
- reflektoi numpy-funktiolla mitä on tapahtunut elämässäsi! 
- oppimisen perusteet selitetty auki, ja nivelletään se ML (machine learning) 
- bottien uskomukset; miten eri botit uskovat toisiansa? 
- vagingossa jaettu väärää tietoa
- mieti, jaatko opit myös toisaalle? Eli strategiointi. Miksi botti strategioisi? 
- oppimisen strategia on annettu väärin (vahingossa!)
- miten vastuun otto väärästä annetusta opetuksesta? Onko sinänsä 
  mitään penaltya vielä väärästä vihjeestä?


Käyttö:
pip install pygame
python pc_robots_pygame.py

Kommentit: tämä on kevyt PoC; toivottavasti auttaa alkuun.
"""


#
# Haluatko, että robotit odottavat käskyäsi?
# sitten automaattinen simulaatio, jatkuva-aikainen.
odotetaan=True  # True => paina Välilyöntiä (Spacebar) jotta simulaatio etenee


import pygame
import random
import math
from collections import deque

# --- Asetukset ---
WIDTH, HEIGHT = 1000, 700
FPS = 60
N_AGENTS = 43
AGENT_RADIUS = 18
BUBBLE_RADIUS = 36

#
#
ROUND_TIME = 0  # 0 = turn-based : advance a round, by pressing <spacebar>

# 
#
MOVE_COST_PER_UNIT = 0.6
REPAIR_HEALTH_PER_ENERGY = 1.2
GENERATE_COST = 6  # base cost from generate_pool to spawn token

# How long tokens live in the game. They disappear if no one
# takes them. A "greenfield" token is like energy, it is a 
# battery bank sorts of .  
GREENFIELD_LIFETIME = 25  # kierrosta
GREENFIELD_ENERGY = 8

FONT_SIZE = 14

# Värit
WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
GRAY = (200, 200, 200)

AGENT_COLORS = [
    (200, 60, 60), (60, 160, 60), (60, 110, 200), (180, 120, 40), (140, 60, 160), (60, 180, 160)
]

# --- Avustavat funktiot ---


# CLAMP is not ceil, floor or average
# Clamp keeps a value within a given range a...b
# So clamp(v, a, b) → leaves *v* unchanged if it’s in range, but forces it to be exactly *a* or *b* if it’s outside the range.
#
def clamp(v, a, b):
    return max(a, min(b, v))

#
# --- Luokat ---
class GreenFieldToken:
    def __init__(self, pos, owner_id=None):
        self.x, self.y = pos
        self.owner_id = owner_id
        self.lifetime = GREENFIELD_LIFETIME

    def update(self):
        self.lifetime -= 1

    def draw(self, surf):
        alpha = clamp(int(255 * (self.lifetime / GREENFIELD_LIFETIME)), 30, 255)
        s = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(s, (100, 230, 130, alpha), (7, 7), 6)
        surf.blit(s, (self.x - 7, self.y - 7))

class Agent:
    def __init__(self, idx, x, y):
        self.id = idx
        self.x = x
        self.y = y
        self.col = AGENT_COLORS[idx % len(AGENT_COLORS)]
        self.health = 80
        self.max_health = 100
        self.bubble_energy = 30.0  # kokonaisenergia sandbox-kuplassa
        # Energiapoolit: summa <= bubble_energy (jaetaan dynaamisesti)
        self.move_pool = 10.0
        self.repair_pool = 10.0
        self.generate_pool = 10.0
        # Behavior / stats
        self.action = None
        self.alive = True
        # Simple cooldown for generate (estää spämmiä)
        self.generate_cooldown = 0
        # Buffs (esim. generate voi antaa pienen tehokkuusboostin)
        self.efficiency_buff = 0.0

    def balance_pools(self):
        # Tasapainota poolit niin että niiden summa on bubble_energy
        s = self.move_pool + self.repair_pool + self.generate_pool
        if s <= 0:
            # equally distribute
            p = self.bubble_energy / 3.0
            self.move_pool = self.repair_pool = self.generate_pool = p
            return
        scale = self.bubble_energy / s
        self.move_pool *= scale
        self.repair_pool *= scale
        self.generate_pool *= scale

    def slight_mutate_allocations(self):
        # Pieni stokastinen muutos poolien jakoihin — simuloi oppimista/eksploraatiota
        # 
        for attr in ['move_pool', 'repair_pool', 'generate_pool']:
            delta = random.uniform(-1.2, 1.2)
            setattr(self, attr, max(0.0, getattr(self, attr) + delta))
        self.balance_pools()

    def decide_action(self, world):
        # Yksinkertainen heuristiikka:
        # - jos health alhainen ja repair_pool > threshold -> REPAIR
        # - jos generate_pool > threshold ja cooldown==0 -> GENERATE
        # - muuten MOVE
        # satunnainen elementti
        choices = []
        # probability weights: influenced by pool sizes
        total = self.move_pool + self.repair_pool + self.generate_pool + 1e-6
        # normalize to probabilities
        p_move = self.move_pool / total
        p_repair = self.repair_pool / total
        p_generate = self.generate_pool / total
        r = random.random()
        # bias towards repair if health low
        if self.health < self.max_health * 0.5 and self.repair_pool > 1:
            r2 = random.random()
            if r2 < 0.6:
                self.action = 'REPAIR'
                return
        if self.generate_cooldown <= 0 and self.generate_pool > 1 and random.random() < p_generate:
            self.action = 'GENERATE'
            return
        # otherwise pick by probabilities
        if r < p_move:
            self.action = 'MOVE'
        elif r < p_move + p_repair:
            self.action = 'REPAIR'
        else:
            self.action = 'GENERATE'

    def perform_action(self, world):
        # Returns log/tokens produced for UI
        log = ''
        if not self.alive:
            return 'dead'
        if self.action == 'MOVE':
            energy = min(self.move_pool, self.bubble_energy * 0.6)
            # compute movement distance from energy and efficiency
            dist = energy * (1.0 + self.efficiency_buff) * 2.0
            # random direction
            ang = random.random() * 2 * math.pi
            dx = math.cos(ang) * dist
            dy = math.sin(ang) * dist
            # Use "clamp()" here to keep the bots within a area
            # Be very careful. Clamping is a known method,
            # but sometimes when it is used in a 
            # You primarily need to understand towards 'which' 
            # a clamping returns the overflown value.
            # So as to not make the clamp() act against the 
            # meaning. It might throw out completely a agent, if
            # it was interpreted in a wrong way.   
            self.x = clamp(self.x + dx, AGENT_RADIUS, WIDTH - AGENT_RADIUS)
            self.y = clamp(self.y + dy, AGENT_RADIUS, HEIGHT - AGENT_RADIUS)
            self.move_pool -= energy
            log = f'MOVE - used {energy:.1f} energy, dist {dist:.1f}'
        elif self.action == 'REPAIR':
            energy = min(self.repair_pool, self.bubble_energy * 0.8)
            heal = energy * REPAIR_HEALTH_PER_ENERGY * (1.0 + self.efficiency_buff * 0.5)
            self.health = clamp(self.health + heal, 0, self.max_health)
            self.repair_pool -= energy
            log = f'REPAIR - used {energy:.1f}, healed {heal:.1f}'
        elif self.action == 'GENERATE':
            energy = min(self.generate_pool, self.bubble_energy * 0.9)
            # require minimum cost to actually spawn
            if energy >= GENERATE_COST and self.generate_cooldown <= 0:
                # spawn token near agent
                angle = random.random() * 2 * math.pi
                rx = clamp(self.x + math.cos(angle) * (BUBBLE_RADIUS + 12), 10, WIDTH - 10)
                ry = clamp(self.y + math.sin(angle) * (BUBBLE_RADIUS + 12), 10, HEIGHT - 10)
                world.spawn_token((rx, ry), owner_id=self.id)
                # take cost
                self.generate_pool -= GENERATE_COST
                # leftover energy is partially returned to bubble
                leftover = max(0.0, energy - GENERATE_COST)
                self.generate_pool -= leftover * 0.0
                # set cooldown
                self.generate_cooldown = 2 + random.randint(0, 2)
                # small chance to get an efficiency buff
                if random.random() < 0.25:
                    self.efficiency_buff += 0.02
                log = f'GENERATE - spawned token, used {GENERATE_COST:.1f}'
            else:
                # Not enough energy; try to convert energy to small repair instead
                converted = energy * 0.4
                self.repair_pool += converted
                self.generate_pool -= energy
                log = f'GENERATE failed - converted {converted:.1f} to repair pool'
        else:
            log = 'NOOP'

        # Ensure pools non-negative and rebalance to bubble energy
        #
        #
        self.move_pool = max(0.0, self.move_pool)
        self.repair_pool = max(0.0, self.repair_pool)
        self.generate_pool = max(0.0, self.generate_pool)
        # small passive energy drain from bubble
        drain = 0.2
        self.bubble_energy = max(0.0, self.bubble_energy - drain)
        # cooldown decrement
        self.generate_cooldown = max(0, self.generate_cooldown - 1)
        # small entropy in allocations
        self.slight_mutate_allocations()
        # agent dies if health 0 or 
        # if bubble is empty and there is no repair pool 
        if self.health <= 0 or (self.bubble_energy <= 0 and self.repair_pool < 0.1 and self.move_pool < 0.1):
            self.alive = False
        return log

    def collect_token_if_near(self, token):
        if not self.alive:
            return False
        d2 = (self.x - token.x) ** 2 + (self.y - token.y) ** 2
        if d2 <= (AGENT_RADIUS + 10) ** 2:
            # collect
            self.bubble_energy += GREENFIELD_ENERGY * (1.0 + self.efficiency_buff)
            # give small boost to pools
            bonus = GREENFIELD_ENERGY * 0.4
            self.move_pool += bonus * 0.4
            self.repair_pool += bonus * 0.3
            self.generate_pool += bonus * 0.3
            return True
        return False

    def draw(self, surf, font):
        # draw bubble (semi transparent)
        s = pygame.Surface((BUBBLE_RADIUS * 2, BUBBLE_RADIUS * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (180, 200, 255, 45), (BUBBLE_RADIUS, BUBBLE_RADIUS), BUBBLE_RADIUS)
        surf.blit(s, (self.x - BUBBLE_RADIUS, self.y - BUBBLE_RADIUS))
        # agent
        pygame.draw.circle(surf, self.col, (int(self.x), int(self.y)), AGENT_RADIUS)
        pygame.draw.circle(surf, BLACK, (int(self.x), int(self.y)), AGENT_RADIUS, 2)
        # health bar
        hw = 36
        hh = 6
        hx = int(self.x - hw / 2)
        hy = int(self.y - AGENT_RADIUS - 12)
        pygame.draw.rect(surf, GRAY, (hx, hy, hw, hh))
        pygame.draw.rect(surf, (60, 200, 80), (hx, hy, int(hw * (self.health / self.max_health)), hh))
        pygame.draw.rect(surf, BLACK, (hx, hy, hw, hh), 1)
        # bubble energy text
        e_text = font.render(f'E:{self.bubble_energy:.0f}', True, BLACK)
        surf.blit(e_text, (self.x - e_text.get_width() / 2, self.y + AGENT_RADIUS + 4))
        # draw three small bars representing pools underneath
        bar_w = 40
        by = int(self.y + AGENT_RADIUS + 24)
        mx = int(self.x - bar_w / 2)
        total = max(1e-6, self.move_pool + self.repair_pool + self.generate_pool)
        # move (left) - red
        w1 = int(bar_w * (self.move_pool / total))
        pygame.draw.rect(surf, (200, 80, 80), (mx, by, w1, 6))
        # repair (middle) - green
        w2 = int(bar_w * (self.repair_pool / total))
        pygame.draw.rect(surf, (80, 200, 100), (mx + w1, by, w2, 6))
        # generate (right) - cyan
        w3 = int(bar_w * (self.generate_pool / total))
        pygame.draw.rect(surf, (80, 200, 200), (mx + w1 + w2, by, w3, 6))
        # small label
        idtxt = font.render(f'A{self.id}', True, BLACK)
        surf.blit(idtxt, (self.x - idtxt.get_width() / 2, hy - 18))

class World:
    def __init__(self):
        self.agents = []
        self.tokens = []
        self.round = 0
        self.logs = deque(maxlen=8)

    def spawn_agents(self, n):
        for i in range(n):
            x = random.randint(50, WIDTH - 50)
            y = random.randint(80, HEIGHT - 80)
            self.agents.append(Agent(i, x, y))

    # 
    def spawn_token(self, pos, owner_id=None):
        self.tokens.append(GreenFieldToken(pos, owner_id=owner_id))

    # 
    def next_round(self):
        self.round += 1
        self.logs.appendleft(f'--- Round {self.round} ---')
        # each agent decides
        for a in self.agents:
            if not a.alive:
                continue
            a.decide_action(self)
            log = a.perform_action(self)
            self.logs.appendleft(f'A{a.id}: {log}')
        # tokens update and possible pickup
        for t in list(self.tokens):
            t.update()
            if t.lifetime <= 0:
                self.tokens.remove(t)
                continue
            # check collisions
            for a in self.agents:
                if a.collect_token_if_near(t):
                    self.logs.appendleft(f'A{a.id} collected token +{GREENFIELD_ENERGY}')
                    try:
                        self.tokens.remove(t)
                    except ValueError:
                        pass
                    break
        # small regeneration: if agent has some generate_pool they regain small bubble energy
        for a in self.agents:
            if not a.alive:
                continue
            # passive recharge from generate_pool
            recharge = a.generate_pool * 0.02
            a.bubble_energy += recharge
            # clamp
            a.bubble_energy = min(a.bubble_energy, 120)

    def draw(self, surf, font):
        # draw tokens
        for t in self.tokens:
            t.draw(surf)
        # draw agents
        for a in self.agents:
            a.draw(surf, font)
        # logs
        lx = WIDTH - 300
        ly = 10
        pygame.draw.rect(surf, (245, 245, 250), (lx - 6, ly - 6, 306, 160))
        pygame.draw.rect(surf, BLACK, (lx - 6, ly - 6, 306, 160), 1)
        for i, msg in enumerate(list(self.logs)):
            txt = font.render(msg, True, BLACK)
            surf.blit(txt, (lx, ly + i * 18))

# --- Pygame loop ---

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('PC Robots - sandbox sim (turn-based)')
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('consolas', FONT_SIZE)

    world = World()
    world.spawn_agents(N_AGENTS)
    # spawn a few initial greenfields
    for _ in range(3):
        world.spawn_token((random.randint(60, WIDTH-60), random.randint(80, HEIGHT-80)))

    running = True
    info = [
        'Space = next round | R = reset | Esc = quit',
        'Agents: move / repair / generate (split energy pools in bubble)',
    ]

    while running:
        #
        # 
        if odotetaan:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        world.next_round()
                    elif event.key == pygame.K_r:
                        world = World()
                        world.spawn_agents(N_AGENTS)
        else:
            world.next_round()

        screen.fill(WHITE)
        # draw header
        header = font.render('PC Robots - Sandbox Sim (Turn-based)', True, BLACK)
        screen.blit(header, (10, 8))
        for i, s in enumerate(info):
            t = font.render(s, True, BLACK)
            screen.blit(t, (10, 30 + i * 18))

        world.draw(screen, font)

        # draw agents summary on left
        sx = 10
        sy = HEIGHT - 140
        pygame.draw.rect(screen, (250, 250, 250), (sx - 6, sy - 6, 360, 128))
        pygame.draw.rect(screen, BLACK, (sx - 6, sy - 6, 360, 128), 1)
        for i, a in enumerate(world.agents):
            st = f'A{a.id}: E{int(a.bubble_energy)} HP{int(a.health)} act:{a.action or "-"}'
            st2 = f' pools M{int(a.move_pool)} R{int(a.repair_pool)} G{int(a.generate_pool)}'
            txt = font.render(st + st2, True, BLACK)
            screen.blit(txt, (sx, sy + i * 16))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == '__main__':
    main()

