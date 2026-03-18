import pygame
import math
import random

pygame.init()

s = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Cloth Simulation")
W, H = s.get_width(), s.get_height()
clock = pygame.time.Clock()

# --- Cloth settings ---
COLS = 55
ROWS = 35
SPACING = 14
START_X = (W - (COLS - 1) * SPACING) // 2
START_Y = 100
DAMPING = 0.98
CONSTRAINT_ITERATIONS = 5
TEAR_DISTANCE = SPACING * 2.8

# --- Sim state ---
gravity = 0.5
wind_x = 0.0
wind_y = 0.0
wind_enabled = False
wind_turbulence = False
turbulence_timer = 0

# --- Modes ---
MODE_HOLD = "HOLD"
MODE_TEAR = "TEAR"
mode = MODE_HOLD

# --- Colors ---
BG            = (8, 8, 16)
PIN_COLOR     = (255, 215, 0)
HOLD_CURSOR   = (80, 180, 255)
TEAR_CURSOR   = (255, 70, 70)
HUD_COLOR     = (180, 180, 200)
ACTIVE_COLOR  = (100, 255, 180)
INACTIVE_COLOR= (80, 80, 100)

# ─────────────────────────────────────────
# Multi-point grab state
# Each entry: { point, offset_x, offset_y, offset_angle, offset_dist }
grabbed_points = []   # list of dicts
grab_cx = 0.0         # grab centre X when mouse-down
grab_cy = 0.0         # grab centre Y when mouse-down
grab_radius = 60      # influence radius for grab
prev_mx = 0
prev_my = 0
drag_angle = 0.0      # accumulated rotation angle
# ─────────────────────────────────────────


class Point:
    def __init__(self, x, y, pinned=False):
        self.x = x
        self.y = y
        self.px = x
        self.py = y
        self.pinned = pinned

    def update(self, grav, wx, wy):
        if self.pinned:
            return
        vx = (self.x - self.px) * DAMPING
        vy = (self.y - self.py) * DAMPING
        self.px = self.x
        self.py = self.y
        self.x += vx + wx
        self.y += vy + wy + grav

    def constrain(self):
        self.x = max(0, min(W, self.x))
        self.y = max(0, min(H, self.y))


class Stick:
    def __init__(self, p0, p1):
        self.p0 = p0
        self.p1 = p1
        self.length = math.hypot(p0.x - p1.x, p0.y - p1.y)
        self.active = True

    def update(self):
        if not self.active:
            return
        dx = self.p1.x - self.p0.x
        dy = self.p1.y - self.p0.y
        dist = math.hypot(dx, dy) or 0.0001
        if dist > TEAR_DISTANCE:
            self.active = False
            return
        diff = (dist - self.length) / dist * 0.5
        ox = dx * diff
        oy = dy * diff
        if not self.p0.pinned:
            self.p0.x += ox
            self.p0.y += oy
        if not self.p1.pinned:
            self.p1.x -= ox
            self.p1.y -= oy


def build_cloth():
    pts = []
    stks = []
    for row in range(ROWS):
        row_pts = []
        for col in range(COLS):
            x = START_X + col * SPACING
            y = START_Y + row * SPACING
            pinned = (row == 0 and col % 5 == 0)
            row_pts.append(Point(x, y, pinned))
        pts.append(row_pts)
    for row in range(ROWS):
        for col in range(COLS - 1):
            stks.append(Stick(pts[row][col], pts[row][col + 1]))
    for row in range(ROWS - 1):
        for col in range(COLS):
            stks.append(Stick(pts[row][col], pts[row + 1][col]))
    return pts, stks


points, sticks = build_cloth()


# ─────────────────────────────────────────
# Grab helpers
# ─────────────────────────────────────────
def begin_grab(mx, my):
    """Record all points within grab_radius and their polar offsets from cursor."""
    global grab_cx, grab_cy, drag_angle, grabbed_points
    grab_cx, grab_cy = float(mx), float(my)
    drag_angle = 0.0
    grabbed_points = []
    for row in points:
        for p in row:
            dx = p.x - mx
            dy = p.y - my
            dist = math.hypot(dx, dy)
            if dist <= grab_radius:
                ang = math.atan2(dy, dx)
                # weight: 1 at centre, 0 at edge (smooth falloff)
                weight = 1.0 - (dist / grab_radius) ** 0.5
                grabbed_points.append({
                    "point":   p,
                    "dist":    dist,
                    "angle":   ang,   # polar angle relative to grab centre
                    "weight":  weight,
                })


def apply_grab(mx, my, delta_angle):
    """Move grabbed points so they follow cursor translation + rotation."""
    for g in grabbed_points:
        p = g["point"]
        if p.pinned:
            continue
        # new polar angle = original + accumulated rotation
        new_ang = g["angle"] + delta_angle
        # target position = cursor + rotated offset
        target_x = mx + math.cos(new_ang) * g["dist"]
        target_y = my + math.sin(new_ang) * g["dist"]
        # blend: full weight at centre, softer at edge
        w = g["weight"]
        p.x = p.x + (target_x - p.x) * w
        p.y = p.y + (target_y - p.y) * w
        p.px = p.x
        p.py = p.y


def cut_sticks_at(mx, my, radius=35):
    for stick in sticks:
        if not stick.active:
            continue
        mid_x = (stick.p0.x + stick.p1.x) / 2
        mid_y = (stick.p0.y + stick.p1.y) / 2
        if math.hypot(mid_x - mx, mid_y - my) < radius:
            stick.active = False


def get_stick_color(stick):
    dist = math.hypot(stick.p1.x - stick.p0.x, stick.p1.y - stick.p0.y)
    stretch = dist / stick.length
    if stretch < 1.2:
        return (0, 220, 140)
    elif stretch < 1.8:
        t = (stretch - 1.2) / 0.6
        return (int(255 * t), int(220 - 120 * t), 50)
    else:
        return (255, 50, 50)


# ─────────────────────────────────────────
# HUD
# ─────────────────────────────────────────
def draw_button(surf, rect, label, active, font):
    color = ACTIVE_COLOR if active else INACTIVE_COLOR
    pygame.draw.rect(surf, color, rect, 2 if active else 1, border_radius=6)
    txt = font.render(label, True, color)
    surf.blit(txt, (rect.x + rect.w // 2 - txt.get_width() // 2,
                    rect.y + rect.h // 2 - txt.get_height() // 2))


def draw_hud(surf, font_sm, font_md):
    px, py = 16, 16
    lh = 22
    hold_rect = pygame.Rect(px, py, 120, 32)
    tear_rect = pygame.Rect(px + 130, py, 120, 32)
    draw_button(surf, hold_rect, "[ H ]  HOLD", mode == MODE_HOLD, font_sm)
    draw_button(surf, tear_rect, "[ T ]  TEAR", mode == MODE_TEAR, font_sm)

    y = py + 48
    items = [
        (f"[ G ]  Gravity     {gravity:+.1f}", gravity != 0),
        (f"[ W ]  Wind        {'ON ' if wind_enabled else 'OFF'}  wx={wind_x:+.1f}", wind_enabled),
        (f"[ U ]  Turbulence  {'ON' if wind_turbulence else 'OFF'}", wind_turbulence),
        (f"[ +/- ] Grab radius  {grab_radius}", True),
    ]
    for label, active in items:
        surf.blit(font_sm.render(label, True, ACTIVE_COLOR if active else HUD_COLOR), (px, y))
        y += lh

    y += 4
    for h in ["↑ ↓   gravity", "← →   wind", "R   reset", "ESC quit"]:
        surf.blit(font_sm.render(h, True, (90, 90, 120)), (px, y))
        y += lh

    # badge
    badge_color = HOLD_CURSOR if mode == MODE_HOLD else TEAR_CURSOR
    icon = "✦" if mode == MODE_HOLD else "✂"
    desc = "drag to grab & rotate cloth" if mode == MODE_HOLD else "drag to cut cloth"
    badge = font_md.render(f"{icon}  {'HOLD' if mode == MODE_HOLD else 'TEAR'} MODE  —  {desc}", True, badge_color)
    surf.blit(badge, (W // 2 - badge.get_width() // 2, 16))

    # wind arrow
    if wind_enabled:
        ax, ay = W - 80, 60
        pygame.draw.circle(surf, (40, 40, 70), (ax, ay), 28)
        pygame.draw.circle(surf, (60, 60, 100), (ax, ay), 28, 1)
        angle = math.atan2(wind_y, wind_x) if (wind_x or wind_y) else 0
        ex = int(ax + math.cos(angle) * 22)
        ey = int(ay + math.sin(angle) * 22)
        pygame.draw.line(surf, HOLD_CURSOR, (ax, ay), (ex, ey), 2)
        pygame.draw.circle(surf, HOLD_CURSOR, (ex, ey), 4)
        surf.blit(font_sm.render("WIND", True, HOLD_CURSOR),
                  (ax - font_sm.size("WIND")[0] // 2, ay + 34))

    return hold_rect, tear_rect


# ─────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────
font_sm = pygame.font.SysFont("monospace", 15)
font_md = pygame.font.SysFont("monospace", 17, bold=True)

holding      = False
hold_rect    = pygame.Rect(16, 16, 120, 32)
tear_rect    = pygame.Rect(146, 16, 120, 32)
drag_angle   = 0.0
last_vec     = None   # (dx, dy) from grab centre to cursor — used to detect rotation

pygame.mouse.set_visible(False)   # we draw our own cursor

running = True
while running:
    mx, my = pygame.mouse.get_pos()
    mouse_buttons = pygame.mouse.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r:
                points, sticks = build_cloth()
                holding = False
                grabbed_points.clear()
            if event.key == pygame.K_h:
                mode = MODE_HOLD
            if event.key == pygame.K_t:
                mode = MODE_TEAR
            if event.key == pygame.K_w:
                wind_enabled = not wind_enabled
                if not wind_enabled:
                    wind_x = wind_y = 0.0
            if event.key == pygame.K_u:
                wind_turbulence = not wind_turbulence
            if event.key == pygame.K_UP:
                gravity = round(min(gravity + 0.1, 3.0), 2)
            if event.key == pygame.K_DOWN:
                gravity = round(max(gravity - 0.1, -1.5), 2)
            if event.key == pygame.K_RIGHT and wind_enabled:
                wind_x = round(min(wind_x + 0.2, 4.0), 2)
            if event.key == pygame.K_LEFT and wind_enabled:
                wind_x = round(max(wind_x - 0.2, -4.0), 2)
            if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                grab_radius = min(grab_radius + 5, 150)
            if event.key == pygame.K_MINUS:
                grab_radius = max(grab_radius - 5, 15)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hold_rect.collidepoint(mx, my):
                mode = MODE_HOLD
            elif tear_rect.collidepoint(mx, my):
                mode = MODE_TEAR
            elif mode == MODE_HOLD:
                begin_grab(mx, my)
                holding = True
                drag_angle = 0.0
                last_vec = None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            holding = False
            grabbed_points.clear()
            last_vec = None

    # ── Rotation detection ──
    # Compare angle from grab-centre to current cursor vs previous frame
    delta_angle = 0.0
    if holding and grabbed_points:
        cur_vec = (mx - grab_cx, my - grab_cy)
        cur_dist = math.hypot(*cur_vec)
        if cur_dist > 5 and last_vec is not None:
            prev_dist = math.hypot(*last_vec)
            if prev_dist > 5:
                # signed angle between last_vec and cur_vec
                cross = last_vec[0] * cur_vec[1] - last_vec[1] * cur_vec[0]
                dot   = last_vec[0] * cur_vec[0] + last_vec[1] * cur_vec[1]
                delta_angle = math.atan2(cross, dot)
        last_vec = cur_vec
        drag_angle += delta_angle

    # ── Apply grab ──
    if holding and grabbed_points:
        apply_grab(mx, my, drag_angle)

    # ── Tear mode ──
    if mouse_buttons[0] and mode == MODE_TEAR:
        if not hold_rect.collidepoint(mx, my) and not tear_rect.collidepoint(mx, my):
            cut_sticks_at(mx, my)

    # ── Turbulence ──
    if wind_enabled and wind_turbulence:
        turbulence_timer += 1
        if turbulence_timer % 6 == 0:
            wind_x = max(-4.0, min(4.0, wind_x + random.uniform(-0.3, 0.3)))
            wind_y = max(-1.0, min(1.0, wind_y + random.uniform(-0.15, 0.15)))

    active_wx = wind_x if wind_enabled else 0.0
    active_wy = wind_y if wind_enabled else 0.0

    # ── Physics (skip grabbed points) ──
    grabbed_set = {g["point"] for g in grabbed_points}
    for row in points:
        for p in row:
            if p not in grabbed_set:
                p.update(gravity, active_wx, active_wy)
            p.constrain()

    for _ in range(CONSTRAINT_ITERATIONS):
        for stick in sticks:
            stick.update()

    # ── Draw ──
    s.fill(BG)

    # dot grid
    for gx in range(0, W, 44):
        for gy in range(0, H, 44):
            pygame.draw.circle(s, (18, 18, 32), (gx, gy), 1)

    # cloth
    for stick in sticks:
        if stick.active:
            pygame.draw.line(s, get_stick_color(stick),
                             (int(stick.p0.x), int(stick.p0.y)),
                             (int(stick.p1.x), int(stick.p1.y)), 1)

    # pins
    for row in points:
        for p in row:
            if p.pinned:
                pygame.draw.circle(s, PIN_COLOR, (int(p.x), int(p.y)), 5)
                pygame.draw.circle(s, (255, 255, 220), (int(p.x), int(p.y)), 2)

    # highlight grabbed cluster
    if holding and grabbed_points:
        for g in grabbed_points:
            p = g["point"]
            alpha = int(180 * g["weight"])
            col = (alpha, int(alpha * 0.9), 255)
            pygame.draw.circle(s, col, (int(p.x), int(p.y)), 3)
        # draw rotation arc to show spin
        if abs(drag_angle) > 0.05:
            arc_r = int(grab_radius * 0.6)
            arc_rect = pygame.Rect(int(grab_cx) - arc_r, int(grab_cy) - arc_r,
                                   arc_r * 2, arc_r * 2)
            start_a = -drag_angle
            end_a   = 0.0
            if start_a > end_a:
                start_a, end_a = end_a, start_a
            try:
                pygame.draw.arc(s, (100, 200, 255, 120), arc_rect,
                                start_a, end_a, 1)
            except Exception:
                pass

    # ── Custom cursor ──
    cursor_color = HOLD_CURSOR if mode == MODE_HOLD else TEAR_CURSOR

    if mode == MODE_TEAR:
        # Scissor cross
        pygame.draw.circle(s, cursor_color, (mx, my), 35, 1)
        pygame.draw.line(s, TEAR_CURSOR, (mx - 8, my - 8), (mx + 8, my + 8), 2)
        pygame.draw.line(s, TEAR_CURSOR, (mx + 8, my - 8), (mx - 8, my + 8), 2)
    else:
        # Grab cursor — shows influence radius
        pygame.draw.circle(s, (*HOLD_CURSOR, 60), (mx, my), grab_radius, 1)
        if holding:
            # spinning arrow around centre
            ang = drag_angle
            for i in range(4):
                a = ang + i * math.pi / 2
                x1 = int(mx + math.cos(a) * (grab_radius - 6))
                y1 = int(my + math.sin(a) * (grab_radius - 6))
                x2 = int(mx + math.cos(a) * (grab_radius + 6))
                y2 = int(my + math.sin(a) * (grab_radius + 6))
                pygame.draw.line(s, HOLD_CURSOR, (x1, y1), (x2, y2), 2)
            pygame.draw.circle(s, (255, 255, 100), (mx, my), 5)
        else:
            # idle grab cursor
            pygame.draw.circle(s, HOLD_CURSOR, (mx, my), 5, 1)
            for i in range(4):
                a = i * math.pi / 2
                pygame.draw.line(s,
                                 HOLD_CURSOR,
                                 (int(mx + math.cos(a) * 8), int(my + math.sin(a) * 8)),
                                 (int(mx + math.cos(a) * 14), int(my + math.sin(a) * 14)), 2)

    # HUD
    hold_rect, tear_rect = draw_hud(s, font_sm, font_md)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
