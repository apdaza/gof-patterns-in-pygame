import pygame
import random
import math
from typing import List, Protocol, runtime_checkable

# =========================
# Composite Pattern Types
# =========================
@runtime_checkable
class Graphic(Protocol):
    def move(self, dx: int, dy: int) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...
    def add(self, child: "Graphic") -> None: ...
    def remove(self, child: "Graphic") -> None: ...
    def update(self, dt: float, moving: bool, dirx: float, diry: float) -> None: ...

class Square(Graphic):
    def __init__(self, x: int, y: int, size: int = 20, color=(255, 255, 255)):
        self.x = float(x)
        self.y = float(y)
        self.size = size
        self.base_color = color

        # Animation state
        self.squash = 0.0
        self.trail_t = 0.0
        self.jitter_phase = random.random() * 2 * math.pi

        self._dirx = 0.0
        self._diry = 0.0

    def move(self, dx: int, dy: int) -> None:
        # Apply movement + modular wrapping on both axes
        self.x = (self.x + dx) % WIDTH
        self.y = (self.y + dy) % HEIGHT

    def update(self, dt: float, moving: bool, dirx: float, diry: float) -> None:
        target = 1.0 if moving else 0.0
        speed_up = 10.0
        slow_down = 6.0
        rate = speed_up if target > self.squash else slow_down
        self.squash += (target - self.squash) * min(1.0, rate * dt)

        if moving:
            self.jitter_phase += 6.0 * dt
        else:
            self.jitter_phase += 1.0 * dt

        self.trail_t += ((1.0 if moving else 0.0) - self.trail_t) * min(1.0, 6.0 * dt)

        self.squash = max(0.0, min(1.0, self.squash))
        self.trail_t = max(0.0, min(1.0, self.trail_t))

        self._dirx = dirx
        self._diry = diry

    def draw(self, surface: pygame.Surface) -> None:
        s = self.size

        # Stretch factors from squash
        stretch_amt = 0.25 * self.squash  # up to ±25%
        ax = 1.0 + stretch_amt * (abs(self._dirx))
        ay = 1.0 - stretch_amt * (abs(self._dirx))
        bx = 1.0 - stretch_amt * (abs(self._diry))
        by = 1.0 + stretch_amt * (abs(self._diry))

        scale_x = ax * bx
        scale_y = ay * by

        jitter = 0.6 * self.squash
        jx = math.sin(self.jitter_phase + 0.7) * jitter
        jy = math.cos(self.jitter_phase) * jitter

        # Motion trail
        if self.trail_t > 0.01 and (abs(self._dirx) + abs(self._diry) > 0.0):
            steps = 4
            for i in range(1, steps + 1):
                falloff = (steps - i + 1) / (steps + 1)
                alpha = int(90 * self.trail_t * falloff)
                offset_mul = i * 3
                tx = self.x - self._dirx * offset_mul
                ty = self.y - self._diry * offset_mul
                self._draw_scaled_rect(surface, tx, ty, scale_x, scale_y,
                                       (self.base_color[0], self.base_color[1], self.base_color[2], alpha))

        # Main body
        self._draw_scaled_rect(surface, self.x + jx, self.y + jy, scale_x, scale_y, (*self.base_color, 255))

    def _draw_scaled_rect(self, surface: pygame.Surface, x: float, y: float, sx: float, sy: float, color_rgba):
        w = max(1, int(self.size * sx))
        h = max(1, int(self.size * sy))

        # Center around the original top-left's center
        cx = x + self.size / 2.0
        cy = y + self.size / 2.0
        rect = pygame.Rect(int(cx - w / 2.0), int(cy - h / 2.0), w, h)

        if color_rgba[3] < 255:
            temp = pygame.Surface((w, h), pygame.SRCALPHA)
            temp.fill(color_rgba)
            surface.blit(temp, rect.topleft)
        else:
            pygame.draw.rect(surface, color_rgba[:3], rect)

    def add(self, child: "Graphic") -> None:
        raise NotImplementedError("Cannot add to a leaf")

    def remove(self, child: "Graphic") -> None:
        raise NotImplementedError("Cannot remove from a leaf")

class Group(Graphic):
    def __init__(self, *children: Graphic):
        self.children: List[Graphic] = list(children)

    def move(self, dx: int, dy: int) -> None:
        for c in self.children:
            c.move(dx, dy)

    def update(self, dt: float, moving: bool, dirx: float, diry: float) -> None:
        for c in self.children:
            c.update(dt, moving, dirx, diry)

    def draw(self, surface: pygame.Surface) -> None:
        for c in self.children:
            c.draw(surface)

    def add(self, child: Graphic) -> None:
        self.children.append(child)

    def remove(self, child: Graphic) -> None:
        self.children.remove(child)

# =========================
# Demo / Game Setup
# =========================
WIDTH, HEIGHT = 800, 600
BG_COLOR = (18, 20, 24)
FPS = 60
SPEED = 5

def make_random_square(area_w: int, area_h: int, size: int = 20) -> Square:
    x = random.randint(0, max(0, area_w - size))
    y = random.randint(0, max(0, area_h - size))
    color = random.choice([
        (255, 99, 71),    # tomato
        (135, 206, 235),  # skyblue
        (144, 238, 144),  # lightgreen
        (255, 215, 0),    # gold
        (221, 160, 221),  # plum
        (255, 182, 193),  # lightpink
    ])
    return Square(x, y, size, color)

def build_population() -> Group:
    cluster_a = Group(*[make_random_square(WIDTH//3, HEIGHT//3) for _ in range(10)])
    cluster_b = Group(*[make_random_square(WIDTH//3, HEIGHT//3) for _ in range(10)])
    cluster_c = Group(*[make_random_square(WIDTH//3, HEIGHT//3) for _ in range(10)])

    cluster_b.move(WIDTH//3, HEIGHT//6)
    cluster_c.move(WIDTH//6, HEIGHT//3)

    root = Group()
    root.add(cluster_a)
    root.add(cluster_b)
    root.add(cluster_c)
    return root

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Composite Pattern – Wrap, Animate, Add/Remove")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 22)

    root_group = build_population()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Add square (handle plus on main and numpad; also '=' on some layouts)
                if event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    # Randomly pick a subgroup to add into (if any)
                    subgroups = [c for c in root_group.children if isinstance(c, Group)]
                    if subgroups:
                        choice = random.choice(subgroups)
                        new_sq = make_random_square(WIDTH//3, HEIGHT//3)
                        choice.add(new_sq)
                # Remove square (main and numpad minus)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    subgroups = [c for c in root_group.children if isinstance(c, Group)]
                    # Remove from the first subgroup that still has children
                    for sg in subgroups:
                        if sg.children:
                            sg.remove(sg.children[-1])
                            break

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]:  dx -= SPEED
        if keys[pygame.K_RIGHT]: dx += SPEED
        if keys[pygame.K_UP]:    dy -= SPEED
        if keys[pygame.K_DOWN]:  dy += SPEED

        moving = (dx != 0 or dy != 0)
        mag = math.hypot(dx, dy) or 1.0
        dirx, diry = (dx / mag, dy / mag)

        if moving:
            root_group.move(dx, dy)

        root_group.update(dt, moving, dirx, diry)

        # Render
        screen.fill(BG_COLOR)
        root_group.draw(screen)

        hint_lines = [
            "Arrows: move ALL squares (composite) — wraps at screen edges",
            "+ / - : add / remove squares (random subgroup)",
            "ESC: quit",
        ]
        for i, text in enumerate(hint_lines):
            screen.blit(font.render(text, True, (205, 205, 205)), (12, 12 + i*20))

        pygame.display.flip()

        if keys[pygame.K_ESCAPE]:
            running = False

    pygame.quit()

if __name__ == "__main__":
    main()
