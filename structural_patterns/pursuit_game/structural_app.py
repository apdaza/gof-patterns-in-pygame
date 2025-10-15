# pursuit_fixed.py
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import math, random
from typing import List, Tuple, Optional, Dict
import pygame
from abc import ABC, abstractmethod

Vec2 = pygame.math.Vector2

# ---------------- Adapter ----------------
class InputAdapter:
    def __init__(self):
        self._toggle_pressed = False
        self.toggle = False
        self.left = self.right = self.up = self.down = self.quit = False
    def poll(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_TAB]:
            if not self._toggle_pressed:
                self.toggle = True; self._toggle_pressed = True
            else:
                self.toggle = False
        else:
            self._toggle_pressed = False; self.toggle = False
        self.left  = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        self.right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        self.up    = keys[pygame.K_UP]    or keys[pygame.K_w]
        self.down  = keys[pygame.K_DOWN]  or keys[pygame.K_s]
        self.quit  = keys[pygame.K_ESCAPE]

# ---------------- Bridge (Renderer) ----------------
class Renderer(ABC):
    @abstractmethod
    def circle(self, surf: pygame.Surface, pos: Tuple[int,int], r: int, color): ...
    @abstractmethod
    def polygon(self, surf: pygame.Surface, pts: List[Tuple[int,int]], color): ...
    @abstractmethod
    def rect(self, surf: pygame.Surface, rect: pygame.Rect, color): ...

class FilledRenderer(Renderer):
    def circle(self, surf, pos, r, color): pygame.draw.circle(surf, color, pos, r, 0)
    def polygon(self, surf, pts, color):  pygame.draw.polygon(surf, color, pts, 0)
    def rect(self, surf, rect, color):    pygame.draw.rect(surf, color, rect, 0)

class WireRenderer(Renderer):
    def circle(self, surf, pos, r, color): pygame.draw.circle(surf, color, pos, r, 2)
    def polygon(self, surf, pts, color):  pygame.draw.polygon(surf, color, pts, 2)
    def rect(self, surf, rect, color):    pygame.draw.rect(surf, color, rect, 2)

# ---------------- Composite ----------------
class Node(ABC):
    def __init__(self): self.enabled = True; self.visible = True
    def update(self, dt: float): pass
    def draw(self, surface: pygame.Surface, renderer: Renderer): pass

class Group(Node):
    def __init__(self): super().__init__(); self.children: List[Node] = []
    def add(self, n: Node): self.children.append(n); return n
    def update(self, dt: float):
        if not self.enabled: return
        for c in self.children: c.update(dt)
    def draw(self, surface, renderer):
        if not self.visible: return
        for c in self.children: c.draw(surface, renderer)

# ---------------- Flyweight (tiles) ----------------
class SurfaceFactory:
    _cache: Dict[Tuple[int,int,Tuple[int,int,int]], pygame.Surface] = {}
    @staticmethod
    def tile(size: Tuple[int,int], color: Tuple[int,int,int]):
        key = (size[0], size[1], color)
        surf = SurfaceFactory._cache.get(key)
        if surf is None:
            surf = pygame.Surface(size); surf.fill(color)
            pygame.draw.rect(surf, (0,0,0), surf.get_rect(), 1)
            SurfaceFactory._cache[key] = surf
        return surf

class Arena(Node):
    def __init__(self, cols=32, rows=18, tile=32):
        super().__init__(); self.cols, self.rows, self.tile = cols, rows, tile
        self.palette = [(35,45,70), (42,58,90), (48,66,100)]
        self.rect = pygame.Rect(0,0, cols*tile, rows*tile)
    def draw(self, surface, renderer):
        ts = self.tile
        for y in range(self.rows):
            for x in range(self.cols):
                color = self.palette[(x+y) % len(self.palette)]
                surface.blit(SurfaceFactory.tile((ts, ts), color), (x*ts, y*ts))

# ---------------- Decorator ----------------
class Renderable(Node, ABC):
    @abstractmethod
    def get_rect(self) -> pygame.Rect: ...

class OutlineDecorator(Renderable):
    def __init__(self, inner: Renderable, color=(255,255,255), thickness=2):
        super().__init__(); self.inner, self.color, self.thickness = inner, color, thickness
    def update(self, dt: float): self.inner.update(dt)
    def draw(self, surface, renderer):
        self.inner.draw(surface, renderer)
        r = self.inner.get_rect()
        pygame.draw.rect(surface, self.color, r.inflate(self.thickness*2, self.thickness*2), self.thickness)
    def get_rect(self): return self.inner.get_rect()

# ---------------- Gameplay ----------------
def clamp_vec(v: Vec2, max_len: float) -> Vec2:
    if v.length_squared() > max_len*max_len: v = v.normalize() * max_len
    return v

class Player(Renderable):
    def __init__(self, pos, radius=14, color=(120,210,255)):
        super().__init__(); self.pos=Vec2(pos); self.vel=Vec2(0,0)
        self.radius=radius; self.color=color
        self.max_speed=220.0; self.accel=900.0; self.friction=0.85
        self.bounds = pygame.Rect(0,0,1,1)
    def update_controls(self, inp: InputAdapter, dt: float):
        acc = Vec2(0,0)
        if inp.left: acc.x -= 1
        if inp.right: acc.x += 1
        if inp.up: acc.y -= 1
        if inp.down: acc.y += 1
        if acc.length_squared()>0: acc = acc.normalize()*self.accel*dt
        self.vel += acc; self.vel *= self.friction
        self.vel = clamp_vec(self.vel, self.max_speed)
        self.pos += self.vel * dt
        self.pos.x = max(self.radius, min(self.bounds.width - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(self.bounds.height - self.radius, self.pos.y))
    def draw(self, surf, renderer):
        renderer.circle(surf, (int(self.pos.x), int(self.pos.y)), self.radius, self.color)
        renderer.circle(surf, (int(self.pos.x)+4, int(self.pos.y)-4), 3, (255,255,255))
    def get_rect(self): return pygame.Rect(int(self.pos.x-self.radius), int(self.pos.y-self.radius), self.radius*2, self.radius*2)
    def update(self, dt): pass

class Hunter(Renderable):
    def __init__(self, pos, color=(255,110,90)):
        super().__init__(); self.pos=Vec2(pos); self.vel=Vec2(0,0)
        self.color=color; self.size=18
        self.max_speed=180.0; self.max_force=280.0; self.lookahead_time=0.6
        self.bounds = pygame.Rect(0,0,1,1)
    def pursue(self, target_pos: Vec2, target_vel: Vec2) -> Vec2:
        to_target = target_pos - self.pos
        dist = to_target.length(); speed = self.max_speed if self.max_speed>1e-5 else 1.0
        t = min(self.lookahead_time, dist / speed)
        predicted = target_pos + target_vel * t
        desired = predicted - self.pos
        if desired.length_squared()>0: desired = desired.normalize()*self.max_speed
        steer = desired - self.vel
        if steer.length_squared()>self.max_force*self.max_force:
            steer = steer.normalize()*self.max_force
        return steer
    def update_ai(self, player: Player, dt: float):
        force = self.pursue(player.pos, player.vel)
        self.vel += force * dt / max(1.0, self.max_force) * self.max_speed
        self.vel = clamp_vec(self.vel, self.max_speed)
        self.pos += self.vel * dt
        self.pos.x = max(self.size, min(self.bounds.width - self.size, self.pos.x))
        self.pos.y = max(self.size, min(self.bounds.height - self.size, self.pos.y))
    def draw(self, surf, renderer):
        forward = self.vel.normalize() if self.vel.length_squared()>1 else Vec2(1,0)
        left = Vec2(-forward.y, forward.x)
        p1 = self.pos + forward * self.size
        p2 = self.pos - forward * (self.size*0.7) + left * (self.size*0.6)
        p3 = self.pos - forward * (self.size*0.7) - left * (self.size*0.6)
        pts = [(int(p1.x),int(p1.y)), (int(p2.x),int(p2.y)), (int(p3.x),int(p3.y))]
        renderer.polygon(surf, pts, self.color)
    def get_rect(self): s=self.size; return pygame.Rect(int(self.pos.x-s), int(self.pos.y-s), s*2, s*2)
    def update(self, dt): pass

# ---------------- Proxy (improved) ----------------
class LazyHunterProxy(Renderable):
    """
    Improved: placeholder drifts toward player; realizes when close OR on-screen.
    """
    def __init__(self, spawn_pos: Tuple[int,int], activation_dist=520, drift_speed=60):
        super().__init__()
        self.pos = Vec2(spawn_pos)
        self.activation_dist2 = activation_dist*activation_dist
        self.drift_speed = drift_speed
        self._real: Optional[Hunter] = None
        self._placeholder_color = (180, 180, 180)
    def _realize(self):
        if self._real is None:
            self._real = Hunter(tuple(self.pos))
            print("[LazyHunterProxy] Hunter realized at", (int(self.pos.x), int(self.pos.y)))
    def update_ai(self, player: Player, dt: float, screen_rect: pygame.Rect):
        # light drift toward player even as a placeholder
        if self._real is None:
            dirv = (player.pos - self.pos)
            if dirv.length_squared() > 1:
                dirv = dirv.normalize() * self.drift_speed * dt
                self.pos += dirv
        # realize if near player or within/near screen
        near_player = (player.pos - self.pos).length_squared() <= self.activation_dist2
        near_screen = screen_rect.inflate(120,120).collidepoint(int(self.pos.x), int(self.pos.y))
        if near_player or near_screen:
            self._realize()
        if self._real:
            self._real.pos = Vec2(self.pos)  # carry over position
            self._real.bounds = player.bounds
            self._real.update_ai(player, dt)
    def draw(self, surf, renderer):
        if self._real: self._real.draw(surf, renderer)
        else:          renderer.circle(surf, (int(self.pos.x), int(self.pos.y)), 6, self._placeholder_color)
    def get_rect(self):
        if self._real: return self._real.get_rect()
        return pygame.Rect(int(self.pos.x-6), int(self.pos.y-6), 12, 12)
    def update(self, dt): pass

# ---------------- Facade ----------------
class GameApp:
    def __init__(self, width=960, height=540):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pursuit (fixed) — See the hunters!")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 22)

        self.input = InputAdapter()
        self.filled, self.wire = FilledRenderer(), WireRenderer()
        self.renderer: Renderer = self.filled

        self.scene = Group()
        self.arena = self.scene.add(Arena(cols=width//32, rows=height//32, tile=32))

        self.player = Player((width*0.5, height*0.5))
        self.player.bounds = pygame.Rect(0,0,width,height)
        self.player_node = self.scene.add(OutlineDecorator(self.player, (255,255,255), 2))

        # Spawn proxies just outside edges (visible soon), and some inside
        self.hunters: List[LazyHunterProxy] = []
        margin = 12
        edge_offsets = [-margin, height+margin]
        for _ in range(8):
            side = random.choice(["top","bottom","left","right"])
            if side == "top":    pos = (random.randint(0,width), -margin)
            elif side == "bottom": pos = (random.randint(0,width), height+margin)
            elif side == "left": pos = (-margin, random.randint(0,height))
            else:                 pos = (width+margin, random.randint(0,height))
            proxy = LazyHunterProxy(pos, activation_dist=520, drift_speed=random.randint(60,110))
            self.hunters.append(proxy); self.scene.add(proxy)
        # Few start already inside
        for _ in range(4):
            pos = (random.randint(80, width-80), random.randint(80, height-80))
            proxy = LazyHunterProxy(pos, activation_dist=420, drift_speed=random.randint(40,90))
            self.hunters.append(proxy); self.scene.add(proxy)

        self.running = True
        self.score = 0.0

    def toggle_renderer(self):
        self.renderer = self.wire if isinstance(self.renderer, FilledRenderer) else self.filled

    def update(self, dt: float):
        self.input.poll()
        if self.input.quit: self.running = False
        if self.input.toggle: self.toggle_renderer()

        self.player.update_controls(self.input, dt)
        screen_rect = self.screen.get_rect()
        for h in self.hunters:
            h.update_ai(self.player, dt, screen_rect)

        self.scene.update(dt)
        self.score += dt

        # collision check
        prect = self.player.get_rect()
        for h in self.hunters:
            if h.get_rect().colliderect(prect):
                self.running = False; break

    def draw_radar(self):
        # simple radar in top-left
        r = pygame.Rect(8, 8, 120, 80)
        pygame.draw.rect(self.screen, (0,0,0), r, 1)
        # map world to radar
        w, h = self.screen.get_width(), self.screen.get_height()
        def map_pos(v: Vec2):
            return (r.x + int((v.x / w) * (r.width-6)) + 3,
                    r.y + int((v.y / h) * (r.height-6)) + 3)
        # player
        px, py = map_pos(self.player.pos); pygame.draw.circle(self.screen, (120,210,255), (px,py), 3)
        # hunters (real or proxy)
        for hnt in self.hunters:
            pos = hnt._real.pos if hnt._real else hnt.pos
            hx, hy = map_pos(pos)
            pygame.draw.circle(self.screen, (255,120,100), (hx,hy), 2)

    def draw(self):
        self.screen.fill((15,18,26))
        self.scene.draw(self.screen, self.renderer)
        self.draw_radar()
        lines = [
            "PURSUIT: Avoid the hunters!",
            "[WASD/Arrows] move | [TAB] toggle (Filled/Wireframe) | [ESC] quit",
            "Hunters now drift toward you and realize near screen/you. Radar shows all blips.",
            f"Score: {self.score:0.1f}s"
        ]
        y = 96
        for s in lines:
            text = self.font.render(s, True, (235,235,235))
            self.screen.blit(text, (8, y)); y += 20
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: self.running = False
            self.update(dt); self.draw()
        # Game over splash
        self.screen.fill((12,12,12))
        msg = self.font.render(f"Game Over — survived {self.score:0.1f}s (press any key)", True, (240,240,240))
        self.screen.blit(msg, msg.get_rect(center=self.screen.get_rect().center))
        pygame.display.flip()
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type in (pygame.KEYDOWN, pygame.QUIT): waiting = False
        pygame.quit()

if __name__ == "__main__":
    GameApp().run()
