import pygame, random, math
from dataclasses import dataclass
from typing import List, Tuple

# =========================
# Config
# =========================
WIDTH, HEIGHT = 900, 540
GROUND_Y = HEIGHT - 80
FPS = 60

BG = (20, 24, 28)
GROUND = (48, 54, 62)
WHITE = (230, 230, 230)
BLUE = (80, 140, 255)
RED = (240, 90, 80)
YELLOW = (255, 210, 90)
CYAN = (100, 220, 220)
GREEN = (80, 200, 120)

# =========================
# Subsystems (hidden behind the Facade)
# =========================
class Camera:
    """Very small camera with screen shake."""
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.shake_t = 0.0
        self.shake_amp = 0.0

    def update(self, dt: float):
        if self.shake_t > 0:
            self.shake_t -= dt
            self.offset_x = random.randint(-int(self.shake_amp), int(self.shake_amp))
            self.offset_y = random.randint(-int(self.shake_amp), int(self.shake_amp))
        else:
            self.offset_x = self.offset_y = 0

    def shake(self, amp: float, dur: float):
        self.shake_amp = amp
        self.shake_t = max(self.shake_t, dur)

class AudioMixer:
    """Tiny sound wrapper (safe even if mixer not available)."""
    def __init__(self):
        self.enabled = False
        try:
            pygame.mixer.init()
            self.enabled = True
        except Exception:
            self.enabled = False
        self.sounds = {}

    def load_beep(self, name: str, freq: int = 440, ms: int = 120):
        # generate a short beep (fallback if no files)
        if not self.enabled: 
            self.sounds[name] = None
            return
        import numpy as np
        samplerate = 22050
        t = np.linspace(0, ms/1000, int(samplerate*ms/1000), False)
        wave = (0.5 * np.sin(2*math.pi*freq*t)).astype(np.float32)
        snd = pygame.sndarray.make_sound((wave*32767).astype("int16"))
        self.sounds[name] = snd

    def play(self, name: str):
        snd = self.sounds.get(name)
        if self.enabled and snd:
            snd.play()

@dataclass
class Particle:
    x: float; y: float; vx: float; vy: float; life: float; col: Tuple[int,int,int]; size: int

class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def burst(self, x: float, y: float, n: int, base_col: Tuple[int,int,int]):
        for _ in range(n):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(80, 320)
            vx, vy = math.cos(ang)*spd, math.sin(ang)*spd
            life = random.uniform(0.3, 0.8)
            size = random.randint(2, 5)
            col = tuple(max(0, min(255, c + random.randint(-30, 30))) for c in base_col)
            self.particles.append(Particle(x, y, vx, vy, life, col, size))

    def update(self, dt: float):
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vy += 500 * dt  # gravity
                alive.append(p)
        self.particles = alive

    def draw(self, surf: pygame.Surface, cam: Camera):
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p.life / 0.8))))
            s = pygame.Surface((p.size, p.size), pygame.SRCALPHA)
            s.fill((*p.col, alpha))
            surf.blit(s, (int(p.x + cam.offset_x), int(p.y + cam.offset_y)))

class HUD:
    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 18)
        self.score = 0
        self.toast = ""
        self.toast_t = 0.0

    def add_score(self, pts: int):
        self.score += pts

    def notify(self, text: str, secs: float = 1.2):
        self.toast = text
        self.toast_t = secs

    def update(self, dt: float):
        if self.toast_t > 0: self.toast_t -= dt

    def draw(self, surf: pygame.Surface):
        surf.blit(self.font.render(f"Score: {self.score}", True, WHITE), (10, 10))
        if self.toast_t > 0:
            msg = self.font.render(self.toast, True, YELLOW)
            surf.blit(msg, (WIDTH//2 - msg.get_width()//2, 10))

class FXLibrary:
    """Predefined color themes for effects."""
    EXPLOSION = RED
    HIT = YELLOW
    SPARK = CYAN

# =========================
# FACADE
# =========================
class GameFXFacade:
    """
    Facade that simplifies complex multi-system interactions:
      - particles (explosion/hit/sparks)
      - camera shake
      - audio cues
      - HUD (score/toast)
    Client code calls one method; facade coordinates subsystems.
    """
    def __init__(self, camera: Camera, particles: ParticleSystem, audio: AudioMixer, hud: HUD):
        self.cam = camera
        self.ps = particles
        self.audio = audio
        self.hud = hud

        # Prepare simple beeps (if mixer available)
        self.audio.load_beep("shoot", 880, 70)
        self.audio.load_beep("explosion", 200, 140)

    # High-level, domain-specific API
    def on_shoot(self, x, y):
        self.ps.burst(x, y, 8, FXLibrary.SPARK)
        self.audio.play("shoot")

    def on_enemy_destroyed(self, x, y, points: int = 100):
        self.ps.burst(x, y, 40, FXLibrary.EXPLOSION)
        self.cam.shake(amp=6, dur=0.25)
        self.audio.play("explosion")
        self.hud.add_score(points)
        self.hud.notify("+{}!".format(points))

    def update(self, dt: float):
        self.cam.update(dt)
        self.ps.update(dt)
        self.hud.update(dt)

    def draw(self, surf: pygame.Surface):
        self.ps.draw(surf, self.cam)
        self.hud.draw(surf)

# =========================
# Tiny game entities
# =========================
class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w, self.h = 48, 64
        self.vx, self.vy = 0.0, 0.0
        self.on_ground = True
        self.facing = 1

    def rect(self): return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, dt, keys):
        ax = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: ax -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: ax += 1
        self.vx = ax * 320
        if ax != 0: self.facing = 1 if ax > 0 else -1

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            # small hop so bullets have some arc reference
            self.vy = -420
            self.on_ground = False

        # physics
        self.vy += 1500 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y + self.h >= GROUND_Y:
            self.y = GROUND_Y - self.h
            self.vy = 0
            self.on_ground = True
        self.x = max(0, min(self.x, WIDTH - self.w))

    def draw(self, surf: pygame.Surface, cam: Camera):
        r = self.rect().move(cam.offset_x, cam.offset_y)
        pygame.draw.rect(surf, BLUE, r, border_radius=10)
        eye = (r.centerx + self.facing*10, r.top + 18)
        pygame.draw.circle(surf, WHITE, eye, 3)

class Bullet:
    def __init__(self, x, y, dirx):
        self.x, self.y = x, y
        self.vx = 520 * dirx
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        if self.x < -20 or self.x > WIDTH + 20:
            self.alive = False

    def rect(self): return pygame.Rect(int(self.x)-4, int(self.y)-2, 8, 4)

    def draw(self, surf: pygame.Surface, cam: Camera):
        pygame.draw.rect(surf, YELLOW, self.rect().move(cam.offset_x, cam.offset_y), border_radius=2)

class Target:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = 16
        self.alive = True
        self.base_x = x
        self.t = random.uniform(0, 3)

    def update(self, dt):
        self.t += dt
        self.x = self.base_x + math.sin(self.t*2)*40

    def rect(self): return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r*2, self.r*2)

    def draw(self, surf: pygame.Surface, cam: Camera):
        pygame.draw.circle(surf, RED, (int(self.x + cam.offset_x), int(self.y + cam.offset_y)), self.r)
        pygame.draw.circle(surf, WHITE, (int(self.x + cam.offset_x), int(self.y + cam.offset_y)), max(2, self.r//3), 2)

# =========================
# Helpers
# =========================
def draw_ground(surf, cam: Camera):
    pygame.draw.rect(surf, GROUND, (0 + cam.offset_x, GROUND_Y + cam.offset_y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, (70, 76, 84), (0 + cam.offset_x, GROUND_Y + cam.offset_y), (WIDTH + cam.offset_x, GROUND_Y + cam.offset_y), 2)

def draw_hint(surf):
    font = pygame.font.SysFont("consolas", 18)
    lines = [
        "Facade Pattern demo — one call triggers particles + camera shake + sound + HUD",
        "Move: A/D or Left/Right | Shoot: SPACE | ESC: quit",
    ]
    y = 10
    for i, t in enumerate(lines):
        c = WHITE if i == 0 else (210,210,210)
        surf.blit(font.render(t, True, c), (12, y)); y += 20

# =========================
# Main
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Facade Pattern with pygame — GameFX Facade")
    clock = pygame.time.Clock()

    # Subsystems
    camera = Camera()
    particles = ParticleSystem()
    audio = AudioMixer()
    hud = HUD()

    # The Facade wrapping all those subsystems
    fx = GameFXFacade(camera, particles, audio, hud)

    player = Player(120, GROUND_Y - 64)
    bullets: List[Bullet] = []
    targets: List[Target] = [Target(500 + i*90, GROUND_Y - 100 - (i%2)*40) for i in range(4)]

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE: running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                # Shoot: create bullet & call a simple facade hook
                dirx = 1 if player.facing >= 0 else -1
                b = Bullet(player.rect().centerx + dirx*28, player.rect().centery - 10, dirx)
                bullets.append(b)
                fx.on_shoot(b.x, b.y)

        keys = pygame.key.get_pressed()
        player.update(dt, keys)
        for b in bullets: b.update(dt)
        for t in targets: t.update(dt)

        # collisions bullet vs targets
        for b in bullets:
            if not b.alive: continue
            br = b.rect()
            for t in targets:
                if t.alive and br.colliderect(t.rect()):
                    t.alive = False
                    b.alive = False
                    fx.on_enemy_destroyed(t.x, t.y, points=100)

        # cleanup
        bullets = [b for b in bullets if b.alive]
        targets = [t for t in targets if t.alive] or targets  # respawn if all dead
        if all(not t.alive for t in targets):
            targets = [Target(500 + i*90, GROUND_Y - 100 - (i%2)*40) for i in range(4)]

        # Update facade (updates subsystems)
        fx.update(dt)

        # render
        screen.fill(BG)
        draw_ground(screen, camera)
        for t in targets: t.draw(screen, camera)
        for b in bullets: b.draw(screen, camera)
        player.draw(screen, camera)
        fx.draw(screen)
        draw_hint(screen)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
