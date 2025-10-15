import pygame
from dataclasses import dataclass
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
YELLOW = (255, 210, 70)
CYAN = (80, 220, 220)
RED = (235, 80, 70)
GRAY = (140, 140, 140)

SPEED = 300.0          # horizontal px/s
JUMP_POWER = 560.0     # initial upward vel
GRAVITY = 1500.0       # px/s^2
DASH_SPEED = 820.0
DASH_COOLDOWN = 0.9    # seconds

# =========================
# Command data the Character (adaptee) understands
# =========================
@dataclass
class Command:
    move: int            # -1, 0, +1 (left/idle/right)
    jump_pressed: bool   # True only on the frame the jump is triggered
    dash_pressed: bool   # True only on the frame the dash is triggered

# =========================
# Target interface (what client code expects)
# Concrete adapters translate inputs to Command
# =========================
class InputAdapter(ABC):
    @abstractmethod
    def poll(self, character_rect: pygame.Rect) -> Command:
        """Translate the current input state to a Character Command."""
        ...

    @abstractmethod
    def name(self) -> str:
        ...

# =========================
# Adaptee: Character only knows Commands
# =========================
class Character:
    def __init__(self, x, y):
        self.w = 48
        self.h = 64
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1         # 1 right, -1 left
        self.on_ground = False
        self.color = BLUE
        self.dash_cd = 0.0      # cooldown timer

        # little squash effect on jump/dash
        self.squash = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def apply(self, cmd: Command, dt: float):
        # Horizontal movement (arcade: set velocity from command)
        self.vx = SPEED * cmd.move
        if cmd.move != 0:
            self.facing = 1 if cmd.move > 0 else -1

        # Jump
        if cmd.jump_pressed and self.on_ground:
            self.vy = -JUMP_POWER
            self.on_ground = False
            self.squash = 0.25

        # Dash (simple burst; respects cooldown)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        if cmd.dash_pressed and self.dash_cd <= 0.0:
            self.vx = self.facing * DASH_SPEED
            # tiny upward nudge if grounded (feels nice)
            if self.on_ground:
                self.vy = -JUMP_POWER * 0.25
                self.on_ground = False
            self.dash_cd = DASH_COOLDOWN
            self.squash = 0.35

        # Gravity + integrate
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Ground collision
        if self.y + self.h >= GROUND_Y:
            self.y = GROUND_Y - self.h
            self.vy = 0.0
            self.on_ground = True

        # Clamp to screen (x)
        self.x = max(0, min(self.x, WIDTH - self.w))

        # relax squash
        self.squash *= (1.0 - min(1.0, 6.0 * dt))

    def draw(self, surf: pygame.Surface):
        r = self.rect()
        # squash-stretch around center
        sx = 1.0 + self.squash * 0.6
        sy = 1.0 - self.squash * 0.6
        w = max(1, int(self.w * sx))
        h = max(1, int(self.h * sy))
        cx, cy = r.center
        rect = pygame.Rect(int(cx - w/2), int(cy - h/2), w, h)

        pygame.draw.rect(surf, self.color, rect, border_radius=10)
        # facing indicator
        eye = (rect.centerx + self.facing*10, rect.centery - 10)
        pygame.draw.circle(surf, WHITE, eye, 3)
        # cooldown bar
        if self.dash_cd > 0:
            pct = 1.0 - min(1.0, self.dash_cd / DASH_COOLDOWN)
            bar_w = 40
            pygame.draw.rect(surf, GRAY, (rect.centerx - bar_w//2, rect.top - 8, bar_w, 4), border_radius=2)
            pygame.draw.rect(surf, YELLOW, (rect.centerx - bar_w//2, rect.top - 8, int(bar_w * pct), 4), border_radius=2)

# =========================
# Concrete Adapter: Keyboard
# =========================
class KeyboardAdapter(InputAdapter):
    def __init__(self):
        # edge detection for jump/dash
        self.prev_jump = False
        self.prev_dash = False

    def name(self) -> str:
        return "KeyboardAdapter (←/→/A/D, SPACE jump, SHIFT dash)"

    def poll(self, character_rect: pygame.Rect) -> Command:
        keys = pygame.key.get_pressed()
        move = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move += 1

        jump_now = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        dash_now = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]

        # edge (pressed this frame)
        jump_pressed = jump_now and not self.prev_jump
        dash_pressed = dash_now and not self.prev_dash

        self.prev_jump = jump_now
        self.prev_dash = dash_now

        return Command(move=move, jump_pressed=jump_pressed, dash_pressed=dash_pressed)

# =========================
# Concrete Adapter: Mouse
#  - Move: hold Left Mouse -> move toward cursor (left/right)
#  - Jump: Right Mouse click (edge)
#  - Dash: Left Mouse click (edge) while not holding
# =========================
class MouseAdapter(InputAdapter):
    def __init__(self):
        self.prev_lmb = False
        self.prev_rmb = False

    def name(self) -> str:
        return "MouseAdapter (move toward cursor; RMB jump; LMB dash)"

    def poll(self, character_rect: pygame.Rect) -> Command:
        mx, my = pygame.mouse.get_pos()
        lmb, _, rmb = pygame.mouse.get_pressed(num_buttons=3)

        # Decide horizontal move by cursor relative to character center
        cx = character_rect.centerx
        move = 0
        if lmb:  # while holding LMB, follow cursor horizontally
            if mx > cx + 6:
                move = +1
            elif mx < cx - 6:
                move = -1

        # Edge detection for clicks
        jump_pressed = (rmb and not self.prev_rmb)
        dash_pressed = (lmb and not self.prev_lmb)

        self.prev_lmb = lmb
        self.prev_rmb = rmb

        return Command(move=move, jump_pressed=jump_pressed, dash_pressed=dash_pressed)

# =========================
# Helper UI
# =========================
def draw_ground(surf):
    pygame.draw.rect(surf, GROUND, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(surf, (70, 76, 84), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)

def draw_hint(surf, adapter_name):
    font = pygame.font.SysFont("consolas", 18)
    lines = [
        "Adapter Pattern demo — same Character, different input adapters",
        f"Active: {adapter_name}",
        "TAB: switch adapter",
        "Keyboard: ←/→ or A/D, SPACE jump, SHIFT dash",
        "Mouse: hold LMB to move toward cursor, RMB jump, LMB click dash",
        "ESC: quit",
    ]
    y = 10
    for i, t in enumerate(lines):
        c = WHITE if i < 2 else (200, 200, 200)
        surf.blit(font.render(t, True, c), (12, y))
        y += 20

# =========================
# Main
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Adapter Pattern with pygame — Keyboard / Mouse controls")
    clock = pygame.time.Clock()

    player = Character(140, GROUND_Y - 64)

    adapters = [KeyboardAdapter(), MouseAdapter()]
    active_idx = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_TAB:
                active_idx = (active_idx + 1) % len(adapters)
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        adapter = adapters[active_idx]
        cmd = adapter.poll(player.rect())
        player.apply(cmd, dt)

        # Render
        screen.fill(BG)
        draw_ground(screen)
        player.draw(screen)

        # Crosshair for mouse control (optional)
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(screen, CYAN, (mx, my), 4)
        pygame.draw.circle(screen, CYAN, (mx, my), 12, 1)

        draw_hint(screen, adapter.name())
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
