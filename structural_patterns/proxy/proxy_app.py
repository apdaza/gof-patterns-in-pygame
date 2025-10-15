import pygame, random, time
from abc import ABC, abstractmethod

# =========================
# Config
# =========================
WIDTH, HEIGHT = 1000, 560
GROUND_Y = HEIGHT - 80
FPS = 60

BG = (18, 22, 26)
GROUND = (40, 46, 56)
WHITE = (235, 235, 235)
CYAN = (90, 220, 220)
YELLOW = (255, 210, 90)
BLUE = (80, 140, 255)

GRAVITY = 1500.0
MOVE_SPEED = 320.0
JUMP_POWER = 560.0

# =========================
# Subject interface
# =========================
class Texture(ABC):
    @abstractmethod
    def draw(self, surface: pygame.Surface, x: int, y: int) -> None: ...
    @abstractmethod
    def update(self, dt: float) -> None: ...
    @abstractmethod
    def is_loaded(self) -> bool: ...

# =========================
# RealSubject: heavy texture
# =========================
class RealTexture(Texture):
    """
    Simulates heavy loading in __init__ (blocking) when blocking=True.
    Generates a big starry gradient surface once, then draws it fast.
    """
    def __init__(self, w: int, h: int, blocking: bool = True):
        if blocking:
            # Simulate a costly load (decode PNG, generate large surface, etc.)
            time.sleep(1.0)  # <-- causes a visible stutter if used directly
        self.surface = self._generate_surface(w, h)
        self._loaded = True

    def _generate_surface(self, w, h) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # gradient
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(30 + 20 * (1 - t))
            g = int(40 + 30 * (1 - t))
            b = int(70 + 80 * t)
            pygame.draw.line(surf, (r, g, b, 255), (0, y), (w, y))
        # stars / blobs
        for _ in range(900):
            x = random.randint(0, w - 1)
            y = random.randint(0, h - 1)
            color = (220 + random.randint(-20, 20),) * 3
            surf.set_at((x, y), (*color[:3], 200))
        # a big soft blob (nebula)
        for _ in range(60):
            rx = random.randint(0, w)
            ry = random.randint(0, h)
            rad = random.randint(16, 70)
            alpha = random.randint(30, 80)
            blob = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(blob, (90, 140, 255, alpha), (rad, rad), rad)
            surf.blit(blob, (rx - rad, ry - rad), special_flags=pygame.BLEND_PREMULTIPLIED)
        return surf

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        surface.blit(self.surface, (x, y))

    def update(self, dt: float) -> None:
        pass

    def is_loaded(self) -> bool:
        return self._loaded

# =========================
# Proxy: non-blocking placeholder → then swap to RealTexture
# =========================
class ProxyTexture(Texture):
    """
    Virtual Proxy:
      - Starts light and draws a placeholder.
      - After LOAD_DELAY seconds, it builds the real texture WITHOUT blocking the loop.
        (We simulate delay with a timer, then instantiate RealTexture(blocking=False)).
    """
    LOAD_DELAY = 1.2

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self._real: RealTexture | None = None
        self._timer = 0.0
        self._loading_started = False
        # tiny spinner state
        self._spin = 0

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        if self._real and self._real.is_loaded():
            self._real.draw(surface, x, y)
            return

        # draw placeholder card with spinner
        placeholder = pygame.Surface((self.w, self.h))
        placeholder.fill((24, 28, 36))
        pygame.draw.rect(placeholder, (70, 80, 96), placeholder.get_rect(), width=3, border_radius=8)

        font = pygame.font.SysFont("consolas", 20)
        text = font.render("Loading big background (via Proxy)...", True, (210, 210, 210))
        placeholder.blit(text, (16, 16))

        # spinner
        cx, cy = self.w // 2, self.h // 2
        for i in range(8):
            ang = (i + self._spin) * 0.8
            r = 26 + i * 2
            px = int(cx + r * 0.9 * pygame.math.Vector2(1, 0).rotate_rad(ang).x)
            py = int(cy + r * 0.9 * pygame.math.Vector2(1, 0).rotate_rad(ang).y)
            alpha = 60 + i * 20
            pygame.draw.circle(placeholder, (90, 160, 255, min(255, alpha)), (px, py), 4)
        self._spin = (self._spin + 1) % 8

        surface.blit(placeholder, (x, y))

    def update(self, dt: float) -> None:
        if self._real and self._real.is_loaded():
            return
        self._timer += dt
        if self._timer >= self.LOAD_DELAY and not self._loading_started:
            # Instantiate the real texture WITHOUT blocking (skip sleep).
            self._real = RealTexture(self.w, self.h, blocking=False)
            self._loading_started = True

    def is_loaded(self) -> bool:
        return self._real is not None and self._real.is_loaded()

# =========================
# Simple player to make it feel like a game
# =========================
class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.w, self.h = 48, 64
        self.vx, self.vy = 0.0, 0.0
        self.on_ground = False
        self.facing = 1

    def rect(self): return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, dt, keys):
        ax = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: ax -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: ax += 1
        self.vx = ax * MOVE_SPEED
        if ax != 0: self.facing = 1 if ax > 0 else -1

        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = -JUMP_POWER; self.on_ground = False

        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y + self.h >= GROUND_Y:
            self.y = GROUND_Y - self.h
            self.vy = 0.0
            self.on_ground = True

        self.x = max(0, min(self.x, WIDTH - self.w))

    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, BLUE, r, border_radius=10)
        eye = (r.centerx + self.facing*10, r.top + 18)
        pygame.draw.circle(surf, WHITE, eye, 3)

# =========================
# HUD / helpers
# =========================
def draw_ground(surf):
    pygame.draw.rect(surf, GROUND, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, (70, 80, 94), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)

def draw_hud(surf, using_proxy: bool, bg_visible: bool, bg_loaded: bool):
    font = pygame.font.SysFont("consolas", 18)
    lines = [
        "Proxy Pattern demo — Virtual Proxy for a heavy background texture",
        f"Mode: {'Proxy (non-blocking)' if using_proxy else 'Direct Real (blocking on creation)'}",
        f"Background visible: {'YES' if bg_visible else 'NO'}   Loaded: {'YES' if bg_loaded else 'NO'}",
        "Controls: A/D move, SPACE jump | P toggle proxy | V toggle background | ESC quit",
    ]
    y = 10
    for i, t in enumerate(lines):
        c = WHITE if i == 0 else (210, 210, 210)
        surf.blit(font.render(t, True, c), (10, y)); y += 20

# =========================
# Main
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Proxy Pattern with pygame — Virtual Proxy for heavy texture")
    clock = pygame.time.Clock()

    player = Player(140, GROUND_Y - 64)

    # Two ways to access the big background: direct RealTexture vs ProxyTexture
    real_bg = None
    proxy_bg = ProxyTexture(WIDTH, GROUND_Y)
    using_proxy = True
    bg_visible = True

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: running = False
                elif e.key == pygame.K_p:
                    using_proxy = not using_proxy
                elif e.key == pygame.K_v:
                    bg_visible = not bg_visible
                elif e.key == pygame.K_r and not using_proxy:
                    # (Optional) force re-create the real bg for testing hitch
                    real_bg = None

        keys = pygame.key.get_pressed()
        player.update(dt, keys)

        # Update proxy (non-blocking)
        proxy_bg.update(dt)

        # If using direct RealTexture and needed, create it ON DEMAND (this blocks ~1s)
        if not using_proxy and bg_visible and real_bg is None:
            real_bg = RealTexture(WIDTH, GROUND_Y, blocking=True)

        # Render
        screen.fill(BG)

        # Background (either proxy or real)
        if bg_visible:
            if using_proxy:
                proxy_bg.draw(screen, 0, 0)
                bg_loaded = proxy_bg.is_loaded()
            else:
                if real_bg:
                    real_bg.draw(screen, 0, 0)
                bg_loaded = real_bg is not None
        else:
            bg_loaded = False

        draw_ground(screen)
        player.draw(screen)
        draw_hud(screen, using_proxy, bg_visible, bg_loaded)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
