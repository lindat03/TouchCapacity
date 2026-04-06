"""
WISHING JAR — Laptop Visualizer (v3)

State flow:
  IDLE      (0) — black, waiting
  RUBBING   (1) — yellow flicker while touch held, chime sounds
                  must hold 3 continuous seconds to reach READY
  READY     (2) — blue glow, different sound signals jar is ready
  GRANTING  (3) — random color flashes + new sound, 3s then back to READY

Requirements:
    pip install pyserial pygame

Change SERIAL_PORT to match your machine:
    Mac:     /dev/cu.usbserial-XXXX
    Windows: COM3
    Linux:   /dev/ttyUSB0
"""

import serial
import pygame
import random
import math
import sys
import os
import time

# ── CONFIG ──────────────────────────────────────────────────
SERIAL_PORT = "/dev/cu.wchusbserial56230319291"   # ← change this
BAUD_RATE   = 115200
WIDTH       = 700
HEIGHT      = 700
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio")


# ── STATES ──────────────────────────────────────────────────
IDLE      = 0
RUBBING   = 1
READY     = 2
GRANTING  = 3

STATE_LABELS = {
    IDLE:     "",
    RUBBING:  "awakening...",
    READY:    "speak your wish",
    GRANTING: "wish granted",
}

# ── PALETTE ─────────────────────────────────────────────────
BG          = (6,   3,  14)
YELLOW      = (255, 200,  30)
AMBER       = (255, 140,   0)
BLUE        = ( 30, 110, 255)
BLUE_PALE   = (140, 190, 255)
WHITE       = (255, 255, 255)


# ════════════════════════════════════════════════════════════
#  PARTICLE
# ════════════════════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color, speed=2.0, size=3, life=60):
        angle    = random.uniform(0, math.pi * 2)
        spd      = random.uniform(0.5, speed)
        self.x   = float(x) + random.uniform(-12, 12)
        self.y   = float(y) + random.uniform(-12, 12)
        self.dx  = math.cos(angle) * spd
        self.dy  = math.sin(angle) * spd
        self.col = color
        self.sz  = size
        self.lf  = life
        self.mx  = life

    def update(self):
        self.x  += self.dx
        self.y  += self.dy
        self.dy += 0.025
        self.lf -= 1

    def draw(self, surf):
        r = max(1, int(self.sz * self.lf / self.mx))
        pygame.draw.circle(surf, self.col, (int(self.x), int(self.y)), r)

    def alive(self):
        return self.lf > 0


# ════════════════════════════════════════════════════════════
#  ORB — central glow mirroring the TTGO screen
# ════════════════════════════════════════════════════════════
class Orb:
    def __init__(self, cx, cy):
        self.cx        = cx
        self.cy        = cy
        self.color     = (0, 0, 0)
        self.tgt_color = (0, 0, 0)
        self.radius    = 0.0
        self.tgt_rad   = 0.0

    def set_state(self, s):
        if s == IDLE:
            self.tgt_color = (0, 0, 0)
            self.tgt_rad   = 0
        elif s == RUBBING:
            self.tgt_color = YELLOW
            self.tgt_rad   = 110
        elif s == READY:
            self.tgt_color = BLUE
            self.tgt_rad   = 100
        elif s == GRANTING:
            self.tgt_color = WHITE
            self.tgt_rad   = 150

    def randomize_color(self):
        # Called every frame during GRANTING
        self.tgt_color = (
            random.randint(80, 255),
            random.randint(80, 255),
            random.randint(80, 255),
        )

    def update(self, t, state, rubbed):
        ease = 0.08
        self.radius = self.radius + (self.tgt_rad - self.radius) * ease
        self.color  = tuple(
            int(self.color[i] + (self.tgt_color[i] - self.color[i]) * ease)
            for i in range(3)
        )

        # Per-state modulation of the draw color
        if state == IDLE:
            self._draw_col = (0, 0, 0)
            self._draw_rad = 0

        elif state == RUBBING:
            if rubbed:
                # Flicker: random brightness, alternate yellow/amber
                br  = random.uniform(0.55, 1.0)
                col = random.choice([YELLOW, AMBER])
                self._draw_col = tuple(int(c * br) for c in col)
                self._draw_rad = int(self.radius) + random.randint(-10, 10)
            else:
                self._draw_col = (0, 0, 0)
                self._draw_rad = 0

        elif state == READY:
            pulse = (math.sin(t * 0.00071 * math.pi) + 1.0) / 2.0
            br    = 0.65 + pulse * 0.35
            self._draw_col = tuple(int(c * br) for c in BLUE)
            self._draw_rad = int(self.radius)

        elif state == GRANTING:
            self._draw_col = self.color
            self._draw_rad = int(self.radius) + random.randint(-15, 15)

    def draw(self, surf):
        r = max(0, self._draw_rad)
        c = self._draw_col
        if r < 2:
            return

        # Glow rings
        for i in range(6, 0, -1):
            gr   = r + i * 22
            ga   = max(0, int(35 / i))
            gsurf = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (*c, ga), (gr + 2, gr + 2), gr)
            surf.blit(gsurf, (self.cx - gr - 2, self.cy - gr - 2))

        # Core
        csurf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(csurf, (*c, 220), (r + 2, r + 2), r)
        surf.blit(csurf, (self.cx - r - 2, self.cy - r - 2))

        # Highlight
        hx = self.cx - int(r * 0.28)
        hy = self.cy - int(r * 0.28)
        hr = max(1, int(r * 0.15))
        hs = pygame.Surface((hr * 2 + 2, hr * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(hs, (255, 255, 255, 160), (hr + 1, hr + 1), hr)
        surf.blit(hs, (hx - hr - 1, hy - hr - 1))


# ════════════════════════════════════════════════════════════
#  SOUND MANAGER
# ════════════════════════════════════════════════════════════
class SoundManager:
    def __init__(self):
        self.sounds  = {}
        self.chime_t = 0
        self._load("chime",   "chime.wav")
        self._load("ready",   "ready.wav")
        self._load("granted", "granted.wav")

    def _load(self, name, fname):
        fpath = os.path.join(SCRIPT_DIR, fname)
        if os.path.exists(fpath):
            try:
                self.sounds[name] = pygame.mixer.Sound(fpath)
                print(f"  Loaded: {fname}")
            except Exception as e:
                print(f"  Could not load {fname}: {e}")
        else:
            print(f"  Missing: {fpath} — check file is in src/")

    def play(self, name, loop=False):
        if name in self.sounds:
            self.sounds[name].play(loops=-1 if loop else 0)

    def stop(self, name):
        if name in self.sounds:
            self.sounds[name].stop()

    def stop_all(self):
        pygame.mixer.stop()

    def tick_chime(self, t, rubbed):
        if rubbed and t > self.chime_t:
            self.play("chime")
            self.chime_t = t + 600

# ════════════════════════════════════════════════════════════
#  SERIAL
# ════════════════════════════════════════════════════════════
def connect_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected: {SERIAL_PORT}")
        return ser
    except Exception as e:
        print(f"Serial not found ({e}) — demo mode")
        print("Press 1/2/3/4 to simulate states, ESC to quit")
        return None

def read_serial(ser):
    try:
        if ser and ser.in_waiting:
            line  = ser.readline().decode("utf-8", errors="ignore").strip()
            parts = line.split(",")
            if len(parts) == 3:
                return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        pass
    return None


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wishing Jar")
    clock  = pygame.time.Clock()

    try:
        font_label = pygame.font.SysFont("Georgia", 26, italic=True)
        font_sub   = pygame.font.SysFont("Georgia", 14, italic=True)
    except Exception:
        font_label = pygame.font.SysFont(None, 26)
        font_sub   = pygame.font.SysFont(None, 14)

    cx, cy    = WIDTH // 2, HEIGHT // 2
    orb       = Orb(cx, cy)
    sounds    = SoundManager()
    ser       = connect_serial()
    particles = []

    current_state = IDLE
    last_state    = -1
    rubbed        = False
    t             = 0   # ms elapsed

    stars = [
        (random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.3, 1.0))
        for _ in range(110)
    ]

    def spawn(n, col, speed=2.5, size=3, life=55):
        for _ in range(n):
            particles.append(Particle(cx, cy, col, speed=speed, size=size, life=life))

    def on_enter(s):
        """Called once when state changes."""
        sounds.stop_all()
        orb.set_state(s)
        if s == IDLE:
            pass
        elif s == RUBBING:
            # Chime sounds handled per-frame in tick_chime
            spawn(15, YELLOW, speed=3, size=4, life=50)
        elif s == READY:
            sounds.play("ready", loop=True)
            spawn(25, BLUE_PALE, speed=1.5, size=2, life=90)
        elif s == GRANTING:
            sounds.play("granted")
            spawn(80, WHITE, speed=6, size=4, life=80)
            for _ in range(3):
                col = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
                spawn(20, col, speed=4, size=3, life=60)

    # ── Main loop ────────────────────────────────────────────
    running = True
    while running:
        dt = clock.tick(60)
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: current_state = IDLE
                if event.key == pygame.K_2: current_state = RUBBING
                if event.key == pygame.K_3: current_state = READY
                if event.key == pygame.K_4: current_state = GRANTING
                if event.key == pygame.K_ESCAPE: running = False

        # Serial
        data = read_serial(ser)
        if data:
            current_state, rubbed_int, lid_int = data
            rubbed = bool(rubbed_int)
        else:
            # In demo mode, simulate rubbing when key 2 held
            keys   = pygame.key.get_pressed()
            rubbed = bool(keys[pygame.K_2])

        # State change
        if current_state != last_state:
            on_enter(current_state)
            last_state = current_state

        # Per-state continuous effects
        if current_state == RUBBING:
            sounds.tick_chime(t, rubbed)
            if rubbed and random.random() < 0.45:
                spawn(3, random.choice([YELLOW, AMBER]), speed=2.5, size=3, life=38)

        elif current_state == READY:
            if random.random() < 0.2:
                angle = random.uniform(0, math.pi * 2)
                r     = random.uniform(60, 160)
                particles.append(
                    Particle(cx + math.cos(angle) * r,
                             cy + math.sin(angle) * r,
                             BLUE_PALE, speed=0.4, size=2,
                             life=random.randint(30, 70))
                )

        elif current_state == GRANTING:
            orb.randomize_color()
            if random.random() < 0.6:
                col = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
                spawn(4, col, speed=4, size=3, life=40)

        # ── Draw ──────────────────────────────────────────────
        screen.fill(BG)

        # Stars (dim in GRANTING so flashes pop)
        star_opacity = 0.3 if current_state == GRANTING else 1.0
        for sx, sy, b in stars:
            tw  = 0.5 + 0.5 * math.sin(t * 0.001 + sx * 0.05)
            val = int(140 * b * tw * star_opacity)
            if val > 5:
                pygame.draw.circle(screen, (val, val, val), (sx, sy), 1)

        # Full-screen flash overlay for GRANTING
        if current_state == GRANTING:
            fc = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((*fc, 180))
            screen.blit(flash_surf, (0, 0))

        # Orb
        orb.update(t, current_state, rubbed)
        orb.draw(screen)

        # Particles
        particles[:] = [p for p in particles if p.alive()]
        for p in particles:
            p.update()
            p.draw(screen)

        # State label
        label_text = STATE_LABELS.get(current_state, "")
        if label_text:
            label_col = {
                RUBBING:  (255, 210,  60),
                READY:    ( 80, 160, 255),
                GRANTING: (255, 255, 255),
            }.get(current_state, WHITE)
            lbl = font_label.render(label_text, True, label_col)
            screen.blit(lbl, lbl.get_rect(center=(cx, HEIGHT - 80)))

        # Progress hint during RUBBING
        if current_state == RUBBING and rubbed:
            sub = font_sub.render("hold to awaken...", True, (200, 160, 60))
            screen.blit(sub, sub.get_rect(center=(cx, HEIGHT - 54)))

        # Demo hint
        hint = font_sub.render("1=idle  2=rub  3=ready  4=grant  |  ESC quit",
                               True, (50, 45, 70))
        screen.blit(hint, (10, HEIGHT - 18))

        pygame.display.flip()

    pygame.quit()
    if ser:
        ser.close()
    sys.exit()


if __name__ == "__main__":
    main()
