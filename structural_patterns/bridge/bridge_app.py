import pygame
from abc import ABC, abstractmethod
import math

# =========================
# Config
# =========================
WIDTH, HEIGHT = 960, 540
GROUND_Y = HEIGHT - 90
FPS = 60

BG = (20, 24, 28)
GROUND = (46, 52, 60)
WHITE = (240, 240, 240)
BLUE = (70, 130, 255)
GREEN = (70, 200, 120)

GRAVITY = 1500.0
MOVE_SPEED = 320.0
JUMP_POWER = 560.0
FRICTION = 9.0     # horizontal easing when no input

# =========================
# Implementor side of the Bridge
# =========================
class RenderAPI(ABC):
    """Implementor: different drawing styles for actors."""
    @abstractmethod
    def draw_actor(self, surf: pygame.Surface, rect: pygame.Rect, facing: int, base_color: tuple[int,int,int], squash: float) -> None:
        ...

class SolidRenderAPI(RenderAPI):
    def draw_actor(self, surf, rect, facing, base_color, squash):
        pygame.draw.rect(surf, base_color, rect, border_radius=10)
        eye = (rect.centerx + facing*10, rect.centery - 10)
        pygame.draw.circle(surf, WHITE, eye, 3)

class OutlineRenderAPI(RenderAPI):
    def draw_actor(self, surf, rect, facing, base_color, squash):
        pygame.draw.rect(surf, base_color, rect, border_radius=10)
        pygame.draw.rect(surf, WHITE, rect.inflate(8, 8), width=3, border_radius=12)
        eye = (rect.centerx + facing*10, rect.centery - 10)
        pygame.draw.circle(surf, WHITE, eye, 3)

class GlowRenderAPI(RenderAPI):
    def draw_actor(self, surf, rect, facing, base_color, squash):
        # simple halo using translucent layers
        for i in range(1, 5):
            a = max(20, 70 - i*10)
            halo = pygame.Surface(rect.inflate(14+i*8, 14+i*8).size, pygame.SRCALPHA)
            halo.fill((*base_color, a))
            top_left = (rect.centerx - halo.get_width()//2, rect.centery - halo.get_height()//2)
            surf.blit(halo, top_left)
        pygame.draw.rect(surf, base_color, rect, border_radius=10)
        eye = (rect.centerx + facing*10, rect.centery - 10)
        pygame.draw.circle(surf, WHITE, eye, 3)

# =========================
# Abstraction side of the Bridge
# =========================
class Actor:
    """Abstraction: game entity that delegates drawing to a RenderAPI."""
    def __init__(self, x, y, w, h, color, render_api: RenderAPI):
        self.x = float(x); self.y = float(y)
        self.w = w; self.h = h
        self.vx = 0.0; self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.color = color
        self.render_api = render_api
        self.squash = 0.0  # tiny squash on jump/land

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def set_renderer(self, render_api: RenderAPI):
        self.render_api = render_api

    def physics(self, dt: float):
        # gravity + integrate
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # clamp ground
        if self.y + self.h >= GROUND_Y:
            if not self.on_ground and self.vy > 200:
                self.squash = 0.25
            self.y = GROUND_Y - self.h
            self.vy = 0.0
            self.on_ground = True
        else:
            self.on_ground = False

        # clamp to screen X
        self.x = max(0, min(self.x, WIDTH - self.w))

        # relax squash
        self.squash *= (1.0 - min(1.0, 8.0 * dt))

    def draw(self, surf: pygame.Surface):
        # simple squash-stretch
        sx = 1.0 + self.squash * 0.6
        sy = 1.0 - self.squash * 0.6
        w = max(1, int(self.w * sx))
        h = max(1, int(self.h * sy))
        r = self.rect()
        rect = pygame.Rect(r.centerx - w//2, r.centery - h//2, w, h)
        self.render_api.draw_actor(surf, rect, self.facing, self.color, self.squash)

class Player(Actor):
    """Refined Abstraction: controlled by keyboard."""
    def update(self, dt: float, keys):
        ax = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  ax -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: ax += 1.0
        self.vx += ax * MOVE_SPEED * dt
        # friction when no input
        if ax == 0:
            self.vx *= (1.0 - min(1.0, FRICTION * dt))
        # face direction
        if abs(self.vx) > 1: self.facing = 1 if self.vx > 0 else -1
        # jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = -JUMP_POWER
            self.on_ground = False
            self.squash = 0.25
        self.physics(dt)

class NPC(Actor):
    """Refined Abstraction: simple patrol AI."""
    def __init__(self, x, y, w, h, color, render_api: RenderAPI):
        super().__init__(x, y, w, h, color, render_api)
        self.center_x = x
        self.t = 0.0

    def update(self, dt: float, _keys=None):
        self.t += dt
        # cosine patrol around spawn center
        target_x = self.center_x + math.cos(self.t * 0.8) * 180
        # steer toward target
        self.vx += (1 if target_x > self.x else -1) * MOVE_SPEED * 0.6 * dt
        # gentle friction
        self.vx *= (1.0 - min(1.0, (FRICTION*0.6) * dt))
        if abs(self.vx) > 1: self.facing = 1 if self.vx > 0 else -1
        self.physics(dt)

# =========================
# Small helpers
# =========================
def draw_ground(surf):
    pygame.draw.rect(surf, GROUND, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, (70, 76, 84), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)

def draw_hint(surf, player_api_name, npc_api_name):
    font = pygame.font.SysFont("consolas", 18)
    lines = [
        "Bridge Pattern demo — Abstraction: Actor (Player/NPC)  | Implementor: RenderAPI",
        f"Player renderer: {player_api_name}   (1 Solid, 2 Outline, 3 Glow)",
        f"NPC renderer:    {npc_api_name}      (7 Solid, 8 Outline, 9 Glow)",
        "Move: A/D or Left/Right | Jump: SPACE | ESC: quit",
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
    pygame.display.set_caption("Bridge Pattern with pygame — Actor x RenderAPI")
    clock = pygame.time.Clock()

    # Implementors (Renderers)
    solid = SolidRenderAPI()
    outline = OutlineRenderAPI()
    glow = GlowRenderAPI()
    renderers = [solid, outline, glow]
    names = ["SolidRenderAPI", "OutlineRenderAPI", "GlowRenderAPI"]

    # Abstractions (Actors)
    player = Player(160, GROUND_Y - 64, 48, 64, BLUE, renderers[0])
    npc    = NPC  (640, GROUND_Y - 64, 48, 64, GREEN, renderers[1])
    player_idx, npc_idx = 0, 1

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False
            # swap implementors at runtime (Bridge in action)
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1: player_idx = 0; player.set_renderer(renderers[player_idx])
                elif e.key == pygame.K_2: player_idx = 1; player.set_renderer(renderers[player_idx])
                elif e.key == pygame.K_3: player_idx = 2; player.set_renderer(renderers[player_idx])
                elif e.key == pygame.K_7: npc_idx = 0; npc.set_renderer(renderers[npc_idx])
                elif e.key == pygame.K_8: npc_idx = 1; npc.set_renderer(renderers[npc_idx])
                elif e.key == pygame.K_9: npc_idx = 2; npc.set_renderer(renderers[npc_idx])

        keys = pygame.key.get_pressed()
        player.update(dt, keys)
        npc.update(dt)

        # render
        screen.fill(BG)
        draw_ground(screen)
        player.draw(screen)
        npc.draw(screen)
        draw_hint(screen, names[player_idx], names[npc_idx])

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
