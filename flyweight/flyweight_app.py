import pygame
import random
from dataclasses import dataclass
from typing import Dict, Tuple

# =========================
# Config
# =========================
WIDTH, HEIGHT = 1000, 600
BG = (18, 20, 24)
HUD = (215, 215, 215)
FPS = 60

# =========================
# Flyweight: intrinsic, shared state
# =========================
class ParticleFlyweight:
    """
    Intrinsic state (shared):
      - shape: "circle" | "square"
      - size: int
      - color: (r,g,b)
      - pre-rendered Surface for fast blits
    """
    def __init__(self, shape: str, size: int, color: Tuple[int,int,int]):
        self.shape = shape
        self.size = size
        self.color = color

        # Pre-render a small sprite surface (with alpha) we can blit many times
        s = size * 2  # draw centered, so make room
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        if shape == "circle":
            pygame.draw.circle(surf, color, (s//2, s//2), size)
        else:  # square
            pygame.draw.rect(surf, color, (0, 0, s, s), border_radius=max(4, size//3))
        self.sprite = surf
        self.offset = (s//2, s//2)  # to draw centered

    def draw(self, screen: pygame.Surface, x: float, y: float, alpha: int = 255):
        """Blit centered. Optionally modulate alpha without reallocating the sprite."""
        if alpha >= 255:
            screen.blit(self.sprite, (int(x - self.offset[0]), int(y - self.offset[1])))
        else:
            temp = self.sprite.copy()
            temp.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(temp, (int(x - self.offset[0]), int(y - self.offset[1])))

# =========================
# Flyweight Factory
# =========================
class ParticleFlyweightFactory:
    """
    Caches flyweights by (shape, size, color) key.
    """
    def __init__(self):
        self._pool: Dict[Tuple[str, int, Tuple[int,int,int]], ParticleFlyweight] = {}

    def get(self, shape: str, size: int, color: Tuple[int,int,int]) -> ParticleFlyweight:
        key = (shape, size, color)
        fw = self._pool.get(key)
        if fw is None:
            fw = ParticleFlyweight(shape, size, color)
            self._pool[key] = fw
        return fw

    def count(self) -> int:
        return len(self._pool)

# =========================
# Particle: extrinsic state only
# =========================
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    alpha: int
    fw_key: Tuple[str, int, Tuple[int,int,int]]  # reference key to shared flyweight

    def update(self, dt: float):
        self.x = (self.x + self.vx * dt) % WIDTH
        self.y = (self.y + self.vy * dt) % HEIGHT
        # optional twinkle
        self.alpha = max(90, min(255, self.alpha + random.randint(-10, 10)))

    def draw(self, screen: pygame.Surface, factory: ParticleFlyweightFactory):
        shape, size, color = self.fw_key
        fw = factory.get(shape, size, color)
        fw.draw(screen, self.x, self.y, alpha=self.alpha)

# =========================
# Demo helpers
# =========================
STYLES = [
    ("circle", 3,  (135, 206, 235)),  # skyblue small
    ("circle", 5,  (255, 215,   0)),  # gold medium
    ("square", 6,  (255, 99,   71)),  # tomato medium
    ("square", 4,  (144, 238, 144)),  # lightgreen small
    ("circle", 8,  (221, 160, 221)),  # plum large
]

def random_particle() -> Particle:
    shape, size, color = random.choice(STYLES)
    speed = random.uniform(30, 180)
    angle = random.uniform(0, 6.28318)
    vx = speed * 0.8 * (1 if random.random() < 0.5 else -1) * random.random()
    vy = speed * 0.8 * (1 if random.random() < 0.5 else -1) * random.random()
    return Particle(
        x=random.uniform(0, WIDTH),
        y=random.uniform(0, HEIGHT),
        vx=vx, vy=vy,
        alpha=random.randint(120, 255),
        fw_key=(shape, size, color)
    )

def batch_add(particles, n: int, preset_idx: int = None):
    for _ in range(n):
        if preset_idx is None:
            p = random_particle()
        else:
            shape, size, color = STYLES[preset_idx % len(STYLES)]
            speed = random.uniform(40, 160)
            vx = random.uniform(-speed, speed)
            vy = random.uniform(-speed, speed)
            p = Particle(
                x=random.uniform(0, WIDTH),
                y=random.uniform(0, HEIGHT),
                vx=vx, vy=vy,
                alpha=random.randint(130, 255),
                fw_key=(shape, size, color)
            )
        particles.append(p)

def draw_hud(screen, factory: ParticleFlyweightFactory, particles_count: int, fps_now: float):
    font = pygame.font.SysFont("consolas", 18)
    lines = [
        "Flyweight Pattern demo — many particles sharing intrinsic state (shape/size/color sprite)",
        f"Particles: {particles_count:,}    Flyweights in cache: {factory.count()}    FPS: {fps_now:5.1f}",
        "SPACE: +1000 random  |  1/2/3: +250 of preset types  |  C: clear  |  ESC: quit",
        "Flyweight = shared sprite per (shape,size,color). Particles only keep position/velocity (extrinsic)."
    ]
    y = 10
    for i, t in enumerate(lines):
        color = HUD if i == 0 else (200, 200, 200)
        screen.blit(font.render(t, True, color), (10, y))
        y += 20

# =========================
# Main
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Flyweight Pattern with pygame — shared particle sprites")
    clock = pygame.time.Clock()

    factory = ParticleFlyweightFactory()
    particles: list[Particle] = []

    # start with a few thousand to show performance
    batch_add(particles, 2000)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    batch_add(particles, 1000)
                elif e.key == pygame.K_1:
                    batch_add(particles, 250, preset_idx=0)  # skyblue small circles
                elif e.key == pygame.K_2:
                    batch_add(particles, 250, preset_idx=2)  # tomato squares
                elif e.key == pygame.K_3:
                    batch_add(particles, 250, preset_idx=4)  # plum large circles
                elif e.key == pygame.K_c:
                    particles.clear()

        # Update
        for p in particles:
            p.update(dt)

        # Render
        screen.fill(BG)
        for p in particles:
            p.draw(screen, factory)

        draw_hud(screen, factory, len(particles), clock.get_fps())
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
