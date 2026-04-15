import pygame
import numpy as np
import math
import random
import time
from dataclasses import dataclass
from typing import List, Optional
from copy import deepcopy

# screen dimensions and a few global constants
W, H = 1280, 800

# color palette for the whole app
C = {
    "bg":         (8,  12, 16),
    "panel":      (12, 16, 22),
    "border":     (25, 38, 55),
    "accent":     (0,  220, 255),
    "accent_dim": (0,  100, 120),
    "warn":       (255, 80,  50),
    "text":       (180, 200, 215),
    "text_dim":   (55,  80,  95),
    "text_bright":(230, 245, 255),
    "obs_fill":   (20,  35,  55),
    "obs_edge":   (40,  70,  105),
    "obs_sel":    (0,   180, 220),
    "path":       (0,   220, 255),
    "path_dim":   (0,   80,  100),
    "drone":      (255, 220, 80),
    "start":      (0,   220, 255),
    "goal":       (255, 80,  50),
    "waypoint":   (255, 170, 0),
    "vtx_used":   (0,   255, 120),
    "vtx_unused": (255, 60,  60),
    "grid":       (14,  22,  30),
    "sky_top":    (6,   10,  20),
    "sky_bot":    (10,  20,  30),
    "gnd_top":    (10,  22,  12),
    "gnd_bot":    (6,   12,   8),
}

FPS = 60
SIDEBAR_W = 230
ANIM_STEPS = 240

# tiny math helpers to keep the rest of the code readable
def v2(x, y):       return np.array([x, y], dtype=float)
def v3(x, y, z):    return np.array([x, y, z], dtype=float)
def norm(v):
    l = np.linalg.norm(v)
    return v / l if l > 1e-9 else v * 0
def dist2(a, b):    return float(np.linalg.norm(a - b))
def dist3(a, b):    return float(np.linalg.norm(a - b))
def cross2(a, b):   return float(a[0]*b[1] - a[1]*b[0])


# ─── 2D geometry helpers ──────────────────────────────────────────────────────

def segs_cross(p1, p2, p3, p4) -> bool:
    """true only for strict interior crossing — grazing at endpoints does not count"""
    d1 = p2 - p1; d2 = p4 - p3
    denom = cross2(d1, d2)
    if abs(denom) < 1e-9:
        return False
    t = cross2(p3 - p1, d2) / denom
    u = cross2(p3 - p1, d1) / denom
    return 1e-9 < t < 1-1e-9 and 1e-9 < u < 1-1e-9

def pt_strictly_in(verts, pt) -> bool:
    """strict interior test — boundary is NOT considered inside"""
    n = len(verts)
    for i in range(n):
        a, b = verts[i], verts[(i+1) % n]
        if cross2(b - a, pt - a) <= 1e-9:
            return False
    return True

def seg_blocked_by(verts, p1, p2) -> bool:
    """true if the segment p1->p2 is obstructed by this polygon"""
    if pt_strictly_in(verts, p1) or pt_strictly_in(verts, p2):
        return True
    n = len(verts)
    return any(segs_cross(p1, p2, verts[i], verts[(i+1) % n]) for i in range(n))


# convex polygon class used for all 2D obstacles
@dataclass
class ConvexPoly:
    cx: float
    cy: float
    sides: int
    rx: float
    ry: float
    angle: float = 0.0

    @property
    def verts(self) -> List[np.ndarray]:
        # generate vertices evenly spaced around an ellipse, rotated by self.angle
        pts = []
        for i in range(self.sides):
            a = self.angle + i * 2 * math.pi / self.sides
            pts.append(v2(self.cx + self.rx * math.cos(a),
                          self.cy + self.ry * math.sin(a)))
        return pts

    def aabb(self):
        vs = self.verts
        xs = [v[0] for v in vs]; ys = [v[1] for v in vs]
        return min(xs), max(xs), min(ys), max(ys)

    def blocked_by(self, p1, p2) -> bool:
        return seg_blocked_by(self.verts, p1, p2)

    def strictly_contains(self, pt) -> bool:
        return pt_strictly_in(self.verts, pt)


# ─── 2D TLD algorithm ─────────────────────────────────────────────────────────

def path_len_2d(pts):
    return sum(dist2(pts[i], pts[i+1]) for i in range(len(pts)-1))

def visible_waypoints_2d(poly: ConvexPoly, ps: np.ndarray,
                          all_polys: List[ConvexPoly], offset=1.2,
                          stats: dict = None) -> List[np.ndarray]:
    """
    For each vertex of the blocking polygon, compute the outward bisector of
    the two edges meeting at that corner and nudge along it. This guarantees the
    waypoint sits cleanly outside the corner rather than just radially offset,
    which means the straight line ps->wp actually clears the polygon surface.
    Only waypoints that are directly visible from ps (unblocked by any polygon)
    are returned.

    stats: optional dict with keys 'detected' and 'approached' to accumulate counts.
    """
    candidates = []
    verts = poly.verts
    n = len(verts)
    all_verts = [p.verts for p in all_polys]

    for i in range(n):
        # every vertex is a candidate that we "detect"
        if stats is not None:
            stats['detected'] += 1

        v = verts[i]
        prev_v = verts[(i - 1) % n]
        next_v = verts[(i + 1) % n]
        # outward bisector: sum of the two normalised edge directions away from adjacent verts
        e1 = v - prev_v; e2 = v - next_v
        l1 = np.linalg.norm(e1); l2 = np.linalg.norm(e2)
        if l1 < 1e-9 or l2 < 1e-9:
            if stats is not None:
                stats['unused_pts'].append(v.copy())
            continue
        bisect = e1 / l1 + e2 / l2
        bl = np.linalg.norm(bisect)
        if bl < 1e-9:
            # degenerate 180-degree corner — use edge perpendicular instead
            bisect = np.array([-e1[1], e1[0]]) / l1
        else:
            bisect = bisect / bl
        wp = v + bisect * offset
        # skip if essentially at the same spot as ps (prevents self-loop)
        if dist2(wp, ps) < 0.3:
            if stats is not None:
                stats['unused_pts'].append(wp.copy())
            continue
        # skip if it landed inside any polygon
        if any(pt_strictly_in(pv, wp) for pv in all_verts):
            if stats is not None:
                stats['unused_pts'].append(wp.copy())
            continue
        # only keep if ps->wp is clear of every polygon
        if not any(seg_blocked_by(pv, ps, wp) for pv in all_verts):
            # this vertex is actually reachable — count it as "approached"
            if stats is not None:
                stats['approached'] += 1
                stats['used_pts'].append(wp.copy())
            candidates.append(wp)
        else:
            if stats is not None:
                stats['unused_pts'].append(wp.copy())
    return candidates

def tld_2d(ps, pg, polys: List[ConvexPoly], depth=0, max_depth=16,
           stats: dict = None):
    if stats is None:
        stats = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}
    if depth > max_depth:
        return [ps, pg], stats
    # check whether anything blocks the straight line at all
    if not any(p.blocked_by(ps, pg) for p in polys):
        return [ps, pg], stats
    # collect the single best visible waypoint from each blocking obstacle,
    # then pick the top 2 overall.
    per_obs_best = []
    for p in polys:
        if not p.blocked_by(ps, pg):
            continue
        cands = visible_waypoints_2d(p, ps, polys, offset=1.2, stats=stats)
        if cands:
            cands.sort(key=lambda w: dist2(w, ps) + dist2(w, pg))
            per_obs_best.append(cands[0])
    if not per_obs_best:
        return [ps, pg], stats
    per_obs_best.sort(key=lambda w: dist2(w, ps) + dist2(w, pg))
    candidates = per_obs_best[:2]
    best, best_l = None, math.inf
    for wp in candidates:
        L, _ = tld_2d(ps, wp, polys, depth+1, max_depth, stats)
        R, _ = tld_2d(wp, pg, polys, depth+1, max_depth, stats)
        combined = L + R[1:]
        l = path_len_2d(combined)
        if l < best_l:
            best_l = l; best = combined
    return (best if best else [ps, pg]), stats


# ─── 3D geometry helpers ──────────────────────────────────────────────────────

def seg_intersects_cuboid(p1, p2, obs) -> bool:
    """slab method AABB intersection, works well for axis-aligned boxes"""
    d = p2 - p1
    tmin, tmax = 1e-6, 1-1e-6
    for lo, hi, o, dd in [
        (obs.x0, obs.x1, p1[0], d[0]),
        (obs.y0, obs.y1, p1[1], d[1]),
        (obs.z0, obs.z1, p1[2], d[2]),
    ]:
        if abs(dd) < 1e-9:
            if o < lo or o > hi:
                return False
        else:
            t1, t2 = (lo-o)/dd, (hi-o)/dd
            if t1 > t2: t1, t2 = t2, t1
            tmin = max(tmin, t1); tmax = min(tmax, t2)
            if tmin > tmax:
                return False
    return tmin < tmax

def pt_in_cuboid(p, obs, margin=0.05) -> bool:
    return (obs.x0+margin < p[0] < obs.x1-margin and
            obs.y0+margin < p[1] < obs.y1-margin and
            obs.z0+margin < p[2] < obs.z1-margin)


# cuboid class used for all 3D obstacles
@dataclass
class Cuboid:
    cx: float
    cy: float
    elev: float   # how high off the ground the bottom face sits
    w: float
    d: float
    h: float

    @property
    def x0(self): return self.cx - self.w/2
    @property
    def x1(self): return self.cx + self.w/2
    @property
    def y0(self): return self.cy - self.d/2
    @property
    def y1(self): return self.cy + self.d/2
    @property
    def z0(self): return self.elev
    @property
    def z1(self): return self.elev + self.h

    @property
    def verts(self) -> List[np.ndarray]:
        # 8 corners, bottom face first then top face
        x0,x1,y0,y1,z0,z1 = self.x0,self.x1,self.y0,self.y1,self.z0,self.z1
        return [
            v3(x0,y0,z0), v3(x1,y0,z0), v3(x1,y1,z0), v3(x0,y1,z0),
            v3(x0,y0,z1), v3(x1,y0,z1), v3(x1,y1,z1), v3(x0,y1,z1),
        ]

    # pairs of vertex indices that form each edge
    EDGES = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]


# ─── 3D TLD using the plane-intersection extension ────────────────────────────

def path_len_3d(pts):
    return sum(dist3(pts[i], pts[i+1]) for i in range(len(pts)-1))


def visible_waypoints_3d(obs: Cuboid, ps: np.ndarray,
                          all_obs: List[Cuboid], margin=0.8,
                          stats: dict = None) -> List[np.ndarray]:
    """
    nudge each of the 8 corners of the blocking cuboid outward in XY, then
    keep only those the drone can actually reach from ps without clipping anything.

    Uses progressive margin nudging: if the initial margin places the waypoint
    inside an adjacent obstacle (common in building clusters), try larger margins
    (2×, 3×, 4×) to push the waypoint clear.

    stats: optional dict with keys 'detected' and 'approached' to accumulate counts.
    """
    candidates = []
    for vt in obs.verts:
        # every corner is a detected vertex candidate
        if stats is not None:
            stats['detected'] += 1

        horiz = vt[:2] - np.array([obs.cx, obs.cy])
        l = np.linalg.norm(horiz)
        away = horiz / l if l > 1e-9 else np.array([0., 1.])

        # try progressively larger margins to clear adjacent obstacles
        wp = None
        for mult in (1, 2, 3, 4):
            trial = vt.copy()
            trial[:2] += away * (margin * mult)
            if trial[2] < 0:
                continue
            if dist3(trial, ps) < 0.3:
                continue
            if not any(pt_in_cuboid(trial, o) for o in all_obs):
                wp = trial
                break

        if wp is None:
            if stats is not None:
                stats['unused_pts'].append(vt.copy())
            continue

        # only keep if ps->wp is actually clear of every obstacle
        if not any(seg_intersects_cuboid(ps, wp, o) for o in all_obs):
            # reachable — count as approached
            if stats is not None:
                stats['approached'] += 1
                stats['used_pts'].append(wp.copy())
            candidates.append(wp)
        else:
            if stats is not None:
                stats['unused_pts'].append(wp.copy())
    return candidates

def _repair_collisions_3d(path, obstacles, max_iters=8):
    """Post-process a TLD path: fix any residual collision segments by
    inserting fly-over waypoints above the tallest obstacle."""
    if len(obstacles) == 0:
        return path
    ceil_z = max(o.z1 for o in obstacles) + 2.0
    for _ in range(max_iters):
        fixed = [path[0]]
        had_collision = False
        for i in range(len(path) - 1):
            hit = next((o for o in obstacles
                        if seg_intersects_cuboid(path[i], path[i+1], o)), None)
            if hit is not None:
                had_collision = True
                # insert two fly-over waypoints: above the start and end of
                # the colliding segment so the drone ascends, flies over, descends
                up_start = v3(path[i][0], path[i][1], ceil_z)
                up_end   = v3(path[i+1][0], path[i+1][1], ceil_z)
                fixed.append(up_start)
                fixed.append(up_end)
            fixed.append(path[i+1])
        path = fixed
        if not had_collision:
            break
    return path

def tld_3d(ps, pg, obstacles: List[Cuboid], depth=0, max_depth=14,
           stats: dict = None):
    if stats is None:
        stats = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}
    if depth > max_depth:
        return [ps, pg], stats

    # find ALL blocking obstacles along ps→pg
    blockers = [o for o in obstacles if seg_intersects_cuboid(ps, pg, o)]
    if not blockers:
        return [ps, pg], stats

    # try each blocker until one yields usable corner-based waypoints;
    # progressive margin nudging inside visible_waypoints_3d handles
    # the case where the default margin lands inside adjacent buildings
    candidates = []
    for blocking in blockers:
        candidates = visible_waypoints_3d(blocking, ps, obstacles, margin=0.8,
                                          stats=stats)
        if candidates:
            break

    # fly-over fallback: when ALL blockers' corners are unreachable (very
    # tight cluster), ascend above the tallest obstacle — the recursion
    # will route from the elevated waypoint back down to pg.
    # Only at shallow depth to prevent repeated fly-over attempts.
    if not candidates and depth < 3:
        max_z = max(o.z1 for o in obstacles) + 1.5
        above_ps = v3(ps[0], ps[1], max_z)
        if not any(pt_in_cuboid(above_ps, ob) for ob in obstacles):
            candidates.append(above_ps)
            if stats is not None:
                stats['detected'] += 1
                stats['approached'] += 1
                stats['used_pts'].append(above_ps.copy())

    if not candidates:
        return [ps, pg], stats

    candidates.sort(key=lambda w: dist3(w, ps) + dist3(w, pg))
    # limit branching at deeper recursion levels to avoid exponential
    # blowup in tight building clusters: full search at top, greedy deeper
    if depth >= 3:
        candidates = candidates[:1]
    elif depth >= 1:
        candidates = candidates[:3]

    best, best_l = None, math.inf
    for wp in candidates:
        L, _ = tld_3d(ps, wp, obstacles, depth+1, max_depth, stats)
        R, _ = tld_3d(wp, pg, obstacles, depth+1, max_depth, stats)
        combined = L + R[1:]
        l = path_len_3d(combined)
        if l < best_l:
            best_l = l; best = combined

    result = best if best else [ps, pg]

    # at the top level, guarantee no collisions remain by repairing any
    # segments the recursive solver could not resolve (e.g. max-depth hit)
    if depth == 0:
        result = _repair_collisions_3d(result, obstacles)

    return result, stats


# ─── path interpolation helpers for smooth animation ─────────────────────────

def interp_path_2d(pts, t):
    total = path_len_2d(pts)
    if total < 1e-9: return pts[0].copy()
    target = total * max(0, min(1, t))
    acc = 0.0
    for i in range(1, len(pts)):
        seg = dist2(pts[i-1], pts[i])
        if acc + seg >= target:
            u = (target - acc) / seg
            return pts[i-1] + u * (pts[i] - pts[i-1])
        acc += seg
    return pts[-1].copy()

def interp_path_3d(pts, t):
    total = path_len_3d(pts)
    if total < 1e-9: return pts[0].copy()
    target = total * max(0, min(1, t))
    acc = 0.0
    for i in range(1, len(pts)):
        seg = dist3(pts[i-1], pts[i])
        if acc + seg >= target:
            u = (target - acc) / seg
            return pts[i-1] + u * (pts[i] - pts[i-1])
        acc += seg
    return pts[-1].copy()

def look_dir_3d(pts, t):
    # returns the forward direction the drone is facing at animation time t
    if len(pts) < 2: return v3(1, 0, 0)
    total = path_len_3d(pts)
    target = total * max(0, min(1, t))
    acc = 0.0
    for i in range(1, len(pts)):
        seg = dist3(pts[i-1], pts[i])
        if acc + seg >= target:
            return norm(pts[i] - pts[i-1])
        acc += seg
    return norm(pts[-1] - pts[-2])

def slerp_dirs(a, b, t):
    # smoothly interpolate between two direction vectors using slerp
    a = norm(a); b = norm(b)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    # if they are nearly the same direction, just lerp
    if dot > 0.9999:
        return norm(a + t * (b - a))
    angle = math.acos(dot)
    sin_angle = math.sin(angle)
    return (math.sin((1 - t) * angle) / sin_angle) * a + (math.sin(t * angle) / sin_angle) * b

def get_altitude_change_points(pts):
    """
    Returns a list of (position, z_level, color_index) for every waypoint
    where the drone changes altitude (or the start/end points).
    These are the locations where we draw a square horizontal plane.
    """
    if not pts or len(pts) < 2:
        return []
    result = []
    # always include the start
    result.append((pts[0].copy(), float(pts[0][2]), 0))
    for i in range(1, len(pts) - 1):
        prev_z = float(pts[i-1][2])
        curr_z = float(pts[i][2])
        next_z = float(pts[i+1][2])
        # include if altitude changed coming in OR is about to change going out
        if abs(prev_z - curr_z) > 0.05 or abs(curr_z - next_z) > 0.05:
            result.append((pts[i].copy(), curr_z, i))
    # always include the end
    result.append((pts[-1].copy(), float(pts[-1][2]), len(pts)-1))
    return result


def build_turn_schedule(pts):
    """
    returns a list of (travel_fraction, turn_duration) events, one per waypoint.
    travel_fraction is how far along the total path length the waypoint sits.
    turn_duration controls how long the turn-in-place pause lasts (in anim time units).
    """
    if len(pts) < 3:
        return []
    total = path_len_3d(pts)
    if total < 1e-9:
        return []
    schedule = []
    acc = 0.0
    for i in range(1, len(pts) - 1):
        acc += dist3(pts[i-1], pts[i])
        frac = acc / total
        # compute the turn angle so sharper turns get more time
        dir_in  = norm(pts[i]   - pts[i-1])
        dir_out = norm(pts[i+1] - pts[i])
        dot = float(np.clip(np.dot(dir_in, dir_out), -1.0, 1.0))
        angle_rad = math.acos(dot)
        # scale turn duration: 90 deg takes 0.3 anim-time units, 180 deg takes 0.6
        turn_dur = (angle_rad / math.pi) * 0.6
        schedule.append((frac, turn_dur, dir_in, dir_out))
    return schedule


# ─── camera projection functions ──────────────────────────────────────────────

def proj_fp(p, drone_pos, look, up, W, H, fov=320):
    # first-person projection from the drone's perspective
    right = np.cross(look, up)
    rel = p - drone_pos
    x = float(np.dot(rel, right))
    y = float(np.dot(rel, up))
    z = float(np.dot(rel, look))
    if z < 0.05:
        return None
    sx = W//2 + int((x/z)*fov)
    sy = H//2 - int((y/z)*fov)
    return (sx, sy, z)


# ─── reusable UI drawing helpers ──────────────────────────────────────────────

def draw_text(surf, text, pos, font, color, align="left"):
    img = font.render(text, True, color)
    x, y = pos
    if align == "center":
        x -= img.get_width() // 2
    elif align == "right":
        x -= img.get_width()
    surf.blit(img, (x, y))

def draw_rect_border(surf, rect, color, width=1, radius=4):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)

def draw_rect_fill(surf, rect, color, radius=4):
    pygame.draw.rect(surf, color, rect, border_radius=radius)

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))


class Button:
    def __init__(self, rect, label, primary=False, danger=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.primary = primary
        self.danger = danger
        self.hovered = False

    def draw(self, surf, font):
        if self.primary:
            bg = C["accent"] if not self.hovered else tuple(min(255,v+30) for v in C["accent"])
            fg = C["bg"]
        elif self.danger:
            bg = C["warn"] if not self.hovered else tuple(min(255,v+30) for v in C["warn"])
            fg = C["text_bright"]
        else:
            bg = C["border"] if self.hovered else C["panel"]
            fg = C["text"]
        draw_rect_fill(surf, self.rect, bg, radius=4)
        draw_rect_border(surf, self.rect, C["border"], 1, radius=4)
        draw_text(surf, self.label, (self.rect.centerx, self.rect.centery - 6),
                  font, fg, align="center")

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class Slider:
    def __init__(self, rect, label, val, vmin, vmax, step=0.1, integer=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.val = val
        self.vmin = vmin
        self.vmax = vmax
        self.step = step
        self.integer = integer
        self.dragging = False

    def draw(self, surf, font_sm):
        val_str = str(int(self.val)) if self.integer else f"{self.val:.1f}"
        draw_text(surf, self.label, (self.rect.x, self.rect.y), font_sm, C["text_dim"])
        draw_text(surf, val_str, (self.rect.right, self.rect.y), font_sm, C["accent"], align="right")
        # slider track background
        track_y = self.rect.y + 16
        track_rect = pygame.Rect(self.rect.x, track_y, self.rect.w, 3)
        draw_rect_fill(surf, track_rect, C["border"])
        # filled portion showing current value
        frac = (self.val - self.vmin) / (self.vmax - self.vmin)
        fill_rect = pygame.Rect(self.rect.x, track_y, int(self.rect.w * frac), 3)
        draw_rect_fill(surf, fill_rect, C["accent"])
        # draggable thumb
        tx = self.rect.x + int(self.rect.w * frac)
        pygame.draw.circle(surf, C["accent"], (tx, track_y + 1), 5)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            thumb_y = self.rect.y + 17
            if abs(event.pos[1] - thumb_y) < 10 and self.rect.x <= event.pos[0] <= self.rect.right:
                self.dragging = True
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            frac = (event.pos[0] - self.rect.x) / self.rect.w
            frac = max(0, min(1, frac))
            raw = self.vmin + frac * (self.vmax - self.vmin)
            self.val = round(raw / self.step) * self.step
            self.val = max(self.vmin, min(self.vmax, self.val))
            if self.integer:
                self.val = int(round(self.val))
            return True
        return False


# ─── random environment generators ───────────────────────────────────────────

def gen_polys(n, bounds=(0,100,0,100)):
    x0,x1,y0,y1 = bounds
    obs = []
    for _ in range(n * 10):
        if len(obs) >= n: break
        cx = x0+10 + random.random()*(x1-x0-20)
        cy = y0+10 + random.random()*(y1-y0-20)
        sides = random.randint(3, 7)
        rx = 4 + random.random()*9
        ry = 3 + random.random()*9
        ang = random.random()*math.pi
        o = ConvexPoly(cx, cy, sides, rx, ry, ang)
        xlo,xhi,ylo,yhi = o.aabb()
        # discard if it clips the boundary
        if xlo < x0+2 or xhi > x1-2 or ylo < y0+2 or yhi > y1-2: continue
        # keep the start and goal corners clear
        if cx < x0+14 and cy < y0+14: continue
        if cx > x1-14 and cy > y1-14: continue
        obs.append(o)
    return obs

def gen_cuboids(n):
    obs = []
    for _ in range(n * 10):
        if len(obs) >= n: break
        cx = 4 + random.random()*22
        cy = 4 + random.random()*22
        # occasionally float an obstacle off the ground for extra interest
        elev = random.choice([0,0,0,1+random.random()*3])
        w = 2 + random.random()*5
        d = 2 + random.random()*5
        h = 1 + random.random()*7
        o = Cuboid(cx, cy, elev, w, d, h)
        # keep start and goal corners clear
        if cx < 5 and cy < 5: continue
        if cx > 25 and cy > 25: continue
        overlaps = any(abs(e.cx-cx)<(e.w+w)/2+0.5 and abs(e.cy-cy)<(e.d+d)/2+0.5 for e in obs)
        if not overlaps:
            obs.append(o)
    return obs


def draw_altitude_planes(surf, alt_points, proj_fn, half_size=3.5):
    """
    For each altitude-change waypoint draw a square horizontal plane centred
    on that point. The plane is always axis-aligned and square in world space.
    half_size controls how big the square is (world units).
    """
    if not alt_points:
        return
    plane_colors = [
        (0,   220, 255),   # cyan
        (255, 160,   0),   # amber
        (0,   255, 120),   # green
        (255,  60, 200),   # magenta
        (100, 200, 255),   # light blue
        (255, 220,  60),   # yellow
    ]
    for pos, z_lev, idx in alt_points:
        col = plane_colors[idx % len(plane_colors)]
        cx, cy = float(pos[0]), float(pos[1])
        # four corners of the square at this altitude
        corners = [
            v3(cx - half_size, cy - half_size, z_lev),
            v3(cx + half_size, cy - half_size, z_lev),
            v3(cx + half_size, cy + half_size, z_lev),
            v3(cx - half_size, cy + half_size, z_lev),
        ]
        sc = [proj_fn(c) for c in corners]
        if any(p is None for p in sc):
            continue
        pts2d = [(int(p[0]), int(p[1])) for p in sc]
        try:
            # filled semi-transparent interior
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(tmp, (*col, 55), pts2d)
            surf.blit(tmp, (0, 0))
            # solid border
            pygame.draw.polygon(surf, col, pts2d, 2)
            # dot at the centre
            cp = proj_fn(pos)
            if cp:
                pygame.draw.circle(surf, col, (int(cp[0]), int(cp[1])), 4)
                pygame.draw.circle(surf, (255,255,255), (int(cp[0]), int(cp[1])), 4, 1)
        except Exception:
            pass


def draw_three_views(screen, fonts, path, cuboids, ps, pg, stats=None):
    """
    Popup showing top, side-X and side-Y views of the completed path.
    Square altitude-change planes are drawn at every waypoint where z changes.
    stats: optional dict with 'detected' and 'approached' vertex counts.
    Press any key or click to close.
    """
    f_md, f_sm, _ = fonts
    PW, PH = 940, 640
    popup = pygame.Surface((PW, PH))

    # four quadrant layout
    VW = PW // 2 - 12
    VH = PH // 2 - 32
    WORLD_XY = 30.0
    WORLD_Z  = 14.0
    SXY = VW / WORLD_XY
    SZ  = VH / WORLD_Z

    alt_pts = get_altitude_change_points(path)
    plane_colors = [
        (0,220,255),(255,160,0),(0,255,120),(255,60,200),(100,200,255),(255,220,60)
    ]

    # view origin offsets (top-left corner of each sub-view)
    OX = [(8, 28), (PW//2+8, 28), (8, PH//2+28), (PW//2+8, PH//2+28)]

    def to_top(wx, wy):
        return int(wx*SXY), int(wy*SXY)

    def to_sx(wx, wz):   # X horizontal, Z vertical (flipped so 0 is bottom)
        return int(wx*SXY), int(VH - wz*SZ)

    def to_sy(wy, wz):   # Y horizontal, Z vertical
        return int(wy*SXY), int(VH - wz*SZ)

    popup.fill(C["bg"])

    # panel dividers
    pygame.draw.line(popup, C["border"], (PW//2, 0), (PW//2, PH), 1)
    pygame.draw.line(popup, C["border"], (0, PH//2), (PW, PH//2), 1)

    labels = ["TOP VIEW (X·Y)", "SIDE VIEW (X·Z)", "SIDE VIEW (Y·Z)", "LEGEND"]
    for i, lbl in enumerate(labels):
        draw_text(popup, lbl, (OX[i][0], OX[i][0]//40 + 8), f_sm, C["accent_dim"])

    # ── draw grid, obstacles and path in each of the three views ──
    for view_idx, (ox, oy) in enumerate(OX[:3]):
        # grid
        for gi in range(0, 31, 5):
            if view_idx == 0:
                x = to_top(gi,0)[0]; y = to_top(0,gi)[1]
                pygame.draw.line(popup, C["grid"], (ox+x, oy), (ox+x, oy+VH), 1)
                pygame.draw.line(popup, C["grid"], (ox, oy+y), (ox+VW, oy+y), 1)
            else:
                h_fn = to_sx if view_idx==1 else to_sy
                hx = h_fn(gi,0)[0]
                pygame.draw.line(popup, C["grid"], (ox+hx, oy), (ox+hx, oy+VH), 1)
        for gz in range(0, 15, 2):
            if view_idx > 0:
                h_fn = to_sx if view_idx==1 else to_sy
                hy = h_fn(0,gz)[1]
                pygame.draw.line(popup, C["grid"], (ox, oy+hy), (ox+VW, oy+hy), 1)
                draw_text(popup, f"{gz}m", (ox-1, oy+hy-6), f_sm, C["text_dim"])

        # obstacles
        for obs in cuboids:
            if view_idx == 0:
                x0,y0 = to_top(obs.x0, obs.y0)
                rw,rh = int(obs.w*SXY), int(obs.d*SXY)
                pygame.draw.rect(popup, C["obs_fill"], (ox+x0, oy+y0, rw, rh))
                pygame.draw.rect(popup, C["obs_edge"], (ox+x0, oy+y0, rw, rh), 1)
            elif view_idx == 1:
                x0,z1 = to_sx(obs.x0, obs.z1); x1,z0 = to_sx(obs.x1, obs.z0)
                rw,rh = x1-x0, z0-z1
                if rw>0 and rh>0:
                    pygame.draw.rect(popup, C["obs_fill"], (ox+x0, oy+z1, rw, rh))
                    pygame.draw.rect(popup, C["obs_edge"], (ox+x0, oy+z1, rw, rh), 1)
            else:
                y0,z1 = to_sy(obs.y0, obs.z1); y1,z0 = to_sy(obs.y1, obs.z0)
                rw,rh = y1-y0, z0-z1
                if rw>0 and rh>0:
                    pygame.draw.rect(popup, C["obs_fill"], (ox+y0, oy+z1, rw, rh))
                    pygame.draw.rect(popup, C["obs_edge"], (ox+y0, oy+z1, rw, rh), 1)

        # altitude-change square planes
        hs = 3.0   # half-size of each square in world units
        for pos, z_lev, cidx in alt_pts:
            col = plane_colors[cidx % len(plane_colors)]
            cx_, cy_ = float(pos[0]), float(pos[1])
            if view_idx == 0:
                # top view: filled square footprint at (cx,cy)
                x0,y0 = to_top(cx_-hs, cy_-hs)
                x1,y1 = to_top(cx_+hs, cy_+hs)
                rw,rh = x1-x0, y1-y0
                if rw>0 and rh>0:
                    tmp = pygame.Surface((rw,rh), pygame.SRCALPHA)
                    tmp.fill((*col, 55))
                    popup.blit(tmp, (ox+x0, oy+y0))
                    pygame.draw.rect(popup, col, (ox+x0, oy+y0, rw, rh), 2)
                    # dot at centre
                    cx2,cy2 = to_top(cx_, cy_)
                    pygame.draw.circle(popup, col, (ox+cx2, oy+cy2), 4)
            elif view_idx == 1:
                # side-X: horizontal line at z_lev spanning ±hs in X
                x0,zy = to_sx(cx_-hs, z_lev); x1,_ = to_sx(cx_+hs, z_lev)
                lw = max(2, x1-x0)
                pygame.draw.line(popup, col, (ox+x0, oy+zy), (ox+x0+lw, oy+zy), 3)
                # small square indicator
                cx2,cy2 = to_sx(cx_, z_lev)
                pygame.draw.rect(popup, col, (ox+cx2-4, oy+cy2-4, 8, 8), 0)
                pygame.draw.rect(popup, (255,255,255), (ox+cx2-4, oy+cy2-4, 8, 8), 1)
            else:
                # side-Y: horizontal line at z_lev spanning ±hs in Y
                y0,zy = to_sy(cy_-hs, z_lev); y1,_ = to_sy(cy_+hs, z_lev)
                lw = max(2, y1-y0)
                pygame.draw.line(popup, col, (ox+y0, oy+zy), (ox+y0+lw, oy+zy), 3)
                cy2,cy3 = to_sy(cy_, z_lev)
                pygame.draw.rect(popup, col, (ox+cy2-4, oy+cy3-4, 8, 8), 0)
                pygame.draw.rect(popup, (255,255,255), (ox+cy2-4, oy+cy3-4, 8, 8), 1)

        # ── vertex markers in popup views ─────────────────────────────────────
        if stats is not None:
            for pt in stats.get('unused_pts', []):
                if view_idx == 0:
                    vx, vy = to_top(pt[0], pt[1])
                elif view_idx == 1:
                    vx, vy = to_sx(pt[0], pt[2])
                else:
                    vx, vy = to_sy(pt[1], pt[2])
                pygame.draw.circle(popup, C["vtx_unused"], (ox+vx, oy+vy), 3)
            for pt in stats.get('used_pts', []):
                if view_idx == 0:
                    vx, vy = to_top(pt[0], pt[1])
                elif view_idx == 1:
                    vx, vy = to_sx(pt[0], pt[2])
                else:
                    vx, vy = to_sy(pt[1], pt[2])
                pygame.draw.circle(popup, C["vtx_used"], (ox+vx, oy+vy), 4)

        # path
        if len(path) > 1:
            for i in range(1, len(path)):
                col = plane_colors[(i-1) % len(plane_colors)]
                a, b = path[i-1], path[i]
                if view_idx == 0:
                    pa = to_top(a[0],a[1]); pb = to_top(b[0],b[1])
                elif view_idx == 1:
                    pa = to_sx(a[0],a[2]); pb = to_sx(b[0],b[2])
                else:
                    pa = to_sy(a[1],a[2]); pb = to_sy(b[1],b[2])
                pygame.draw.line(popup, col,
                                 (ox+pa[0],oy+pa[1]), (ox+pb[0],oy+pb[1]), 2)

        # start / goal markers (only endpoints, no intermediate waypoints)
        for i in (0, len(path)-1):
            p = path[i]
            dot_col = C["start"] if i==0 else C["goal"]
            if view_idx == 0:
                px,py2 = to_top(p[0],p[1])
            elif view_idx == 1:
                px,py2 = to_sx(p[0],p[2])
            else:
                px,py2 = to_sy(p[1],p[2])
            pygame.draw.circle(popup, dot_col, (ox+px, oy+py2), 5)

    # ── legend ──
    ox_l, oy_l = OX[3]
    draw_text(popup, "Coloured square = altitude plane at waypoint", (ox_l, oy_l+10), f_sm, C["text"])
    draw_text(popup, "Each colour = one path segment",               (ox_l, oy_l+26), f_sm, C["text"])
    for i, col in enumerate(plane_colors[:6]):
        pygame.draw.rect(popup, col, (ox_l, oy_l+50+i*20, 14, 14))
        draw_text(popup, f"Segment {i+1}", (ox_l+20, oy_l+50+i*20), f_sm, C["text_dim"])
    pygame.draw.circle(popup, C["start"],   (ox_l+7, oy_l+178), 5)
    draw_text(popup, "Start",  (ox_l+18, oy_l+173), f_sm, C["text_dim"])
    pygame.draw.circle(popup, C["goal"],    (ox_l+7, oy_l+193), 5)
    draw_text(popup, "Goal",   (ox_l+18, oy_l+188), f_sm, C["text_dim"])
    pygame.draw.circle(popup, C["vtx_used"], (ox_l+7, oy_l+208), 4)
    draw_text(popup, "Used vertex",  (ox_l+18, oy_l+203), f_sm, C["vtx_used"])
    pygame.draw.circle(popup, C["vtx_unused"], (ox_l+7, oy_l+223), 3)
    draw_text(popup, "Unused vertex",(ox_l+18, oy_l+218), f_sm, C["vtx_unused"])

    # ── vertex stats in popup ──
    if stats is not None:
        det  = stats.get('detected', 0)
        appr = stats.get('approached', 0)
        vs_y = oy_l + 240
        pygame.draw.line(popup, C["border"], (ox_l, vs_y), (ox_l + VW, vs_y), 1)
        draw_text(popup, f"Used {stats.get('approached',0)} / {stats.get('detected',0)} vertices",
                  (ox_l, vs_y + 6), f_sm, C["accent"])
        if det > 0:
            bar_w = VW - 8
            bar_rect = pygame.Rect(ox_l, vs_y + 22, bar_w, 6)
            fill_w = int(bar_w * appr / det)
            draw_rect_fill(popup, bar_rect, C["border"], radius=3)
            draw_rect_fill(popup, pygame.Rect(ox_l, vs_y + 22, fill_w, 6), C["accent"], radius=3)

    draw_text(popup, "Press any key or click to close",
              (ox_l, PH - 36), f_sm, C["accent"])

    # blit dimmed background + popup
    sw, sh = screen.get_size()
    dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
    dim.fill((0,0,0,160))
    screen.blit(dim, (0,0))
    px2 = (sw-PW)//2; py2 = (sh-PH)//2
    pygame.draw.rect(screen, C["panel"], (px2, py2-26, PW, 26))
    draw_text(screen, "PATH ANALYSIS  —  altitude change planes + 3 views",
              (px2+10, py2-20), f_sm, C["accent"])
    screen.blit(popup, (px2, py2))
    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.QUIT):
                waiting = False


def draw_drone_icon(surf, cx, cy, color, size=10):
    # four arms with a small rotor circle at each tip
    for a in range(4):
        ang = a * math.pi/2 + math.pi/4
        ex = int(cx + math.cos(ang)*size)
        ey = int(cy + math.sin(ang)*size)
        pygame.draw.line(surf, color, (int(cx), int(cy)), (ex, ey), 2)
        pygame.draw.circle(surf, color, (ex, ey), 3)


# ─── 2D simulation screen ─────────────────────────────────────────────────────

class Sim2D:
    WORLD = (0, 100, 0, 100)
    PS = v2(3, 3)
    PG = v2(97, 97)
    CANVAS_X = SIDEBAR_W
    CANVAS_W = H   # square canvas so world units map cleanly
    CANVAS_H = H
    SCALE = H / 100.0

    def __init__(self, screen, fonts, on_back=None):
        self.screen = screen
        self.f_md, self.f_sm, self.f_lg = fonts
        self.on_back = on_back   # callback to return to the home screen
        self.polys: List[ConvexPoly] = []
        self.selected: Optional[int] = None
        self.path: Optional[List[np.ndarray]] = None
        self.anim_t = 0.0
        self.animating = False
        self.log: List[str] = []
        self.drag_start = None   # stores (mouse_x, mouse_y, orig_cx, orig_cy) when dragging
        # vertex stats from last TLD run
        self.last_stats: dict = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}

        # lay out all the sidebar controls
        sx = 12
        self.btn_back  = Button((sx, 14, SIDEBAR_W-24, 24), "BACK TO MENU")
        self.sl_num    = Slider((sx, 55, SIDEBAR_W-24, 20), "OBSTACLES", 6, 2, 14, 1, integer=True)
        self.btn_regen = Button((sx, 88, SIDEBAR_W-24, 26), "RANDOMIZE ALL")
        self.sl_sides  = Slider((sx, 166, SIDEBAR_W-24, 20), "SIDES", 4, 3, 8, 1, integer=True)
        self.sl_rx     = Slider((sx, 201, SIDEBAR_W-24, 20), "WIDTH (RX)", 6, 1, 20, 0.5)
        self.sl_ry     = Slider((sx, 236, SIDEBAR_W-24, 20), "HEIGHT (RY)", 6, 1, 20, 0.5)
        self.sl_rot    = Slider((sx, 271, SIDEBAR_W-24, 20), "ROTATION", 0, 0, 6.28, 0.05)
        self.btn_del   = Button((sx, 304, 90, 24), "DELETE", danger=True)
        self.btn_run   = Button((sx, H-120, SIDEBAR_W-24, 32), "RUN TLD", primary=True)
        self.btn_reset = Button((sx, H-80,  SIDEBAR_W-24, 26), "RESET DRONE")
        self.btn_replay= Button((sx, H-46,  SIDEBAR_W-24, 26), "REPLAY ANIMATION")

        self.regenerate()

    def regenerate(self):
        n = int(self.sl_num.val)
        self.polys = gen_polys(n)
        self.selected = None
        self.path = None
        self.anim_t = 0.0
        self.animating = False
        self.last_stats = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}

    def world_to_canvas(self, wx, wy):
        cx = self.CANVAS_X + wx * self.SCALE
        cy = wy * self.SCALE
        return int(cx), int(cy)

    def canvas_to_world(self, cx, cy):
        return (cx - self.CANVAS_X) / self.SCALE, cy / self.SCALE

    def run_tld(self):
        t0 = time.time()
        stats = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}
        self.path, stats = tld_2d(self.PS.copy(), self.PG.copy(), self.polys,
                                  stats=stats)
        dt = (time.time()-t0)*1000
        self.last_stats = stats
        self.anim_t = 0.0
        self.animating = True
        self.add_log(f"Done  {len(self.path)} pts  {dt:.1f}ms")
        self.add_log(f"Length: {path_len_2d(self.path):.2f} units")
        self.add_log(f"Vtx detected: {stats['detected']}  approached: {stats['approached']}")

    def add_log(self, msg):
        self.log = self.log[-6:] + [msg]

    def reset_drone(self):
        # wipe the computed path and return the drone to start without touching the obstacles
        self.path = None
        self.anim_t = 0.0
        self.animating = False
        self.add_log("Drone reset to start")

    def update_sel_sliders(self):
        # sync the sliders to match the currently selected obstacle
        if self.selected is None: return
        p = self.polys[self.selected]
        self.sl_sides.val = p.sides
        self.sl_rx.val = p.rx
        self.sl_ry.val = p.ry
        self.sl_rot.val = p.angle

    def apply_sel_sliders(self):
        # push slider values back into the selected obstacle
        if self.selected is None: return
        p = self.polys[self.selected]
        p.sides = int(self.sl_sides.val)
        p.rx = self.sl_rx.val
        p.ry = self.sl_ry.val
        p.angle = self.sl_rot.val

    def handle_event(self, event):
        # shape editing sliders only apply when something is selected
        for sl in [self.sl_sides, self.sl_rx, self.sl_ry, self.sl_rot]:
            if sl.handle(event):
                self.apply_sel_sliders()

        if self.sl_num.handle(event):
            self.regenerate()

        if self.btn_back.handle(event) and self.on_back:  self.on_back()
        if self.btn_regen.handle(event):  self.regenerate()
        if self.btn_run.handle(event):    self.run_tld()
        if self.btn_reset.handle(event):  self.reset_drone()
        if self.btn_replay.handle(event): self.anim_t = 0.0; self.animating = True

        if self.selected is not None and self.btn_del.handle(event):
            self.polys.pop(self.selected)
            self.selected = None

        # canvas mouse: click to select and start drag
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if mx > self.CANVAS_X:
                wx, wy = self.canvas_to_world(mx, my)
                pt = v2(wx, wy)
                hit = -1
                for i in range(len(self.polys)-1, -1, -1):
                    if self.polys[i].strictly_contains(pt):
                        hit = i; break
                if hit >= 0:
                    self.selected = hit
                    self.drag_start = (mx, my, self.polys[hit].cx, self.polys[hit].cy)
                    self.update_sel_sliders()
                else:
                    self.selected = None
                    self.drag_start = None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag_start = None

        if event.type == pygame.MOUSEMOTION and self.drag_start:
            mx, my = event.pos
            dx = (mx - self.drag_start[0]) / self.SCALE
            dy = (my - self.drag_start[1]) / self.SCALE
            self.polys[self.selected].cx = self.drag_start[2] + dx
            self.polys[self.selected].cy = self.drag_start[3] + dy

    def update(self, dt):
        if self.animating and self.path:
            self.anim_t += dt / (ANIM_STEPS / FPS)
            if self.anim_t >= 1.0:
                self.anim_t = 1.0
                self.animating = False

    def draw(self):
        surf = self.screen
        surf.fill(C["bg"])

        # sidebar panel
        pygame.draw.rect(surf, C["panel"], (0, 0, SIDEBAR_W, H))
        pygame.draw.line(surf, C["border"], (SIDEBAR_W, 0), (SIDEBAR_W, H), 1)

        self.btn_back.draw(surf, self.f_sm)
        draw_text(surf, "TLD 2D", (SIDEBAR_W-50, 18), self.f_sm, C["accent"])
        draw_text(surf, "drag obstacles to move", (12, H-16), self.f_sm, C["text_dim"])

        self.sl_num.draw(surf, self.f_sm)
        self.btn_regen.draw(surf, self.f_sm)

        if self.selected is not None:
            pygame.draw.line(surf, C["border"], (8, 135), (SIDEBAR_W-8, 135), 1)
            draw_text(surf, f"SELECTED  [{self.selected}]", (12, 140), self.f_sm, C["accent"])
            self.sl_sides.draw(surf, self.f_sm)
            self.sl_rx.draw(surf, self.f_sm)
            self.sl_ry.draw(surf, self.f_sm)
            self.sl_rot.draw(surf, self.f_sm)
            self.btn_del.draw(surf, self.f_sm)

        self.btn_run.draw(surf, self.f_sm)
        self.btn_reset.draw(surf, self.f_sm)
        self.btn_replay.draw(surf, self.f_sm)

        # ── vertex stats panel ────────────────────────────────────────────────
        # shown whenever a path has been computed; positioned in clear sidebar area
        if self.path is not None:
            panel_y = 380
            pygame.draw.line(surf, C["border"], (8, panel_y), (SIDEBAR_W-8, panel_y), 1)
            draw_text(surf, "VERTEX STATS", (12, panel_y + 6), self.f_sm, C["text_dim"])
            det  = self.last_stats.get('detected',  0)
            appr = self.last_stats.get('approached', 0)
            # prominent "Used X / Y vertices" display
            draw_text(surf, f"Used {appr} / {det}",
                      (12, panel_y + 24), self.f_md, C["accent"])
            draw_text(surf, "vertices",
                      (12, panel_y + 42), self.f_md, C["text"])
            # ratio bar
            if det > 0:
                bar_w = SIDEBAR_W - 24
                bar_rect = pygame.Rect(12, panel_y + 62, bar_w, 8)
                fill_w = int(bar_w * appr / det)
                draw_rect_fill(surf, bar_rect, C["border"], radius=3)
                draw_rect_fill(surf, pygame.Rect(12, panel_y + 62, fill_w, 8), C["accent"], radius=3)
                pct = int(100 * appr / det)
                draw_text(surf, f"{pct}% utilisation",
                          (12, panel_y + 76), self.f_sm, C["text_dim"])
            # vertex marker legend
            leg_y = panel_y + 94
            pygame.draw.circle(surf, C["vtx_used"], (22, leg_y + 6), 5)
            draw_text(surf, "Used vertex", (34, leg_y), self.f_sm, C["vtx_used"])
            pygame.draw.circle(surf, C["vtx_unused"], (22, leg_y + 22), 4)
            draw_text(surf, "Unused vertex", (34, leg_y + 16), self.f_sm, C["vtx_unused"])

        # log output in the sidebar (between stats and action buttons)
        log_y = 500
        pygame.draw.line(surf, C["border"], (8, log_y), (SIDEBAR_W-8, log_y), 1)
        draw_text(surf, "LOG", (12, log_y + 4), self.f_sm, C["text_dim"])
        for i, msg in enumerate(self.log[-5:]):
            draw_text(surf, f"> {msg}", (12, log_y + 20 + i*15), self.f_sm, C["accent_dim"])

        # main canvas area
        canvas_rect = pygame.Rect(self.CANVAS_X, 0, self.CANVAS_W, self.CANVAS_H)
        pygame.draw.rect(surf, C["bg"], canvas_rect)

        # background grid
        for i in range(0, 101, 10):
            x, _ = self.world_to_canvas(i, 0); _, y = self.world_to_canvas(0, i)
            pygame.draw.line(surf, C["grid"], (x, 0), (x, H), 1)
            pygame.draw.line(surf, C["grid"], (self.CANVAS_X, y), (self.CANVAS_X + self.CANVAS_W, y), 1)

        # draw each obstacle, highlighted if selected
        for idx, poly in enumerate(self.polys):
            vs = [self.world_to_canvas(v[0], v[1]) for v in poly.verts]
            is_sel = idx == self.selected
            pygame.draw.polygon(surf, C["obs_fill"], vs)
            pygame.draw.polygon(surf, C["obs_sel"] if is_sel else C["obs_edge"], vs, 2 if is_sel else 1)
            if is_sel:
                for v in vs:
                    pygame.draw.circle(surf, C["accent"], v, 4)
            # show the number of sides in the center
            cx, cy = self.world_to_canvas(poly.cx, poly.cy)
            draw_text(surf, str(poly.sides)+"v", (cx-8, cy-5), self.f_sm, C["text_dim"])

        # ── vertex markers on canvas ──────────────────────────────────────────
        if self.path is not None:
            for pt in self.last_stats.get('unused_pts', []):
                px, py = self.world_to_canvas(pt[0], pt[1])
                pygame.draw.circle(surf, C["vtx_unused"], (int(px), int(py)), 4)
                pygame.draw.circle(surf, (0, 0, 0), (int(px), int(py)), 4, 1)
            for pt in self.last_stats.get('used_pts', []):
                px, py = self.world_to_canvas(pt[0], pt[1])
                pygame.draw.circle(surf, C["vtx_used"], (int(px), int(py)), 5)
                pygame.draw.circle(surf, (0, 0, 0), (int(px), int(py)), 5, 1)

        # path drawing: ghost first, then the animated portion on top
        if self.path and len(self.path) > 1:
            ghost_pts = [self.world_to_canvas(p[0], p[1]) for p in self.path]
            pygame.draw.lines(surf, C["path_dim"], False, ghost_pts, 1)

            # build the animated path up to the current animation time
            drone_pos = interp_path_2d(self.path, self.anim_t)
            total = path_len_2d(self.path) * self.anim_t
            acc = 0.0
            anim_pts = [self.world_to_canvas(self.path[0][0], self.path[0][1])]
            for i in range(1, len(self.path)):
                seg = dist2(self.path[i-1], self.path[i])
                if acc + seg >= total:
                    u = (total - acc) / seg if seg > 1e-9 else 0
                    mp = self.path[i-1] + u*(self.path[i]-self.path[i-1])
                    anim_pts.append(self.world_to_canvas(mp[0], mp[1]))
                    break
                acc += seg
                anim_pts.append(self.world_to_canvas(self.path[i][0], self.path[i][1]))
            if len(anim_pts) > 1:
                pygame.draw.lines(surf, C["path"], False, anim_pts, 2)

            # drone icon at current position
            dx, dy = self.world_to_canvas(drone_pos[0], drone_pos[1])
            draw_drone_icon(surf, dx, dy, C["drone"], size=9)

        # start and goal markers
        sx, sy = self.world_to_canvas(self.PS[0], self.PS[1])
        gx, gy = self.world_to_canvas(self.PG[0], self.PG[1])
        pygame.draw.circle(surf, C["start"], (sx, sy), 7)
        pygame.draw.circle(surf, C["goal"],  (gx, gy), 7)
        draw_text(surf, "S", (sx-4, sy-6), self.f_sm, C["bg"])
        draw_text(surf, "G", (gx-4, gy-6), self.f_sm, C["bg"])


# ─── 3D simulation screen ─────────────────────────────────────────────────────

class Sim3D:
    PS = v3(1, 1, 0.5)
    PG = v3(29, 29, 8.0)
    WORLD_SIZE = 30.0

    # the screen is split: sidebar | top view | fp view
    TOP_X = SIDEBAR_W
    TOP_W = (W - SIDEBAR_W) // 2
    TOP_H = H - 30
    FP_X  = SIDEBAR_W + (W - SIDEBAR_W) // 2
    FP_W  = W - FP_X
    FP_H  = H - 30
    SCALE = None  # computed in __init__

    def __init__(self, screen, fonts, on_back=None):
        self.screen = screen
        self.f_md, self.f_sm, self.f_lg = fonts
        self.on_back = on_back   # callback to return to the home screen
        self.TOP_SCALE = self.TOP_W / self.WORLD_SIZE
        self.cuboids: List[Cuboid] = []
        self.selected: Optional[int] = None
        self.path: Optional[List[np.ndarray]] = None
        self.anim_t = 0.0
        self.animating = False
        self.log: List[str] = []
        self.drag_ref = None   # stores (mx, my, cx, cy) while dragging
        self.turn_schedule   = []
        self.disp_planes     = []
        self.show_path_views = False
        self._turning        = False
        self._turn_t         = 0.0
        self._turn_dur       = 0.0
        self._turn_dir_in    = v3(1, 0, 0)
        self._turn_dir_out   = v3(1, 0, 0)
        # vertex stats from last TLD run
        self.last_stats: dict = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}

        # start and goal are instance variables so elevation sliders can move them
        self.ps = v3(1, 1, 0.5)
        self.pg = v3(29, 29, 8.0)

        sx = 12
        self.btn_back    = Button((sx, 14,  SIDEBAR_W-24, 24), "BACK TO MENU")
        self.sl_num      = Slider((sx, 55,  SIDEBAR_W-24, 20), "OBSTACLES", 5, 2, 10, 1, integer=True)
        self.btn_regen   = Button((sx, 88,  SIDEBAR_W-24, 26), "RANDOMIZE ALL")
        # start and goal elevation sliders sit just below randomize
        self.sl_start_z  = Slider((sx, 128, SIDEBAR_W-24, 20), "START ALT", 0.5, 0.0, 12.0, 0.5)
        self.sl_goal_z   = Slider((sx, 163, SIDEBAR_W-24, 20), "GOAL ALT",  8.0, 0.0, 12.0, 0.5)
        # obstacle sliders appear when one is selected (drawn conditionally)
        self.sl_w        = Slider((sx, 210, SIDEBAR_W-24, 20), "LENGTH (W)", 3, 1, 12, 0.5)
        self.sl_d        = Slider((sx, 245, SIDEBAR_W-24, 20), "BREADTH (D)", 3, 1, 12, 0.5)
        self.sl_h        = Slider((sx, 280, SIDEBAR_W-24, 20), "HEIGHT (H)", 3, 0.5, 12, 0.5)
        self.sl_elev     = Slider((sx, 315, SIDEBAR_W-24, 20), "ELEVATION", 0, 0, 8, 0.5)
        self.btn_del     = Button((sx, 350, 90, 24), "DELETE", danger=True)
        self.btn_run     = Button((sx, H-120, SIDEBAR_W-24, 32), "RUN TLD", primary=True)
        self.btn_reset   = Button((sx, H-80,  SIDEBAR_W-24, 26), "RESET DRONE")
        self.btn_replay  = Button((sx, H-46,  SIDEBAR_W-24, 26), "REPLAY ANIMATION")

        # separate surfaces so each view draws independently
        self.top_surf = pygame.Surface((self.TOP_W, self.TOP_H))
        self.fp_surf  = pygame.Surface((self.FP_W,  self.FP_H))

        self.regenerate()

    def regenerate(self):
        n = int(self.sl_num.val)
        self.cuboids = gen_cuboids(n)
        self.selected = None
        self.path = None
        self.anim_t = 0.0
        self.animating = False
        self.turn_schedule   = []
        self.disp_planes     = []
        self.show_path_views = False
        self._turning        = False
        self._turn_t         = 0.0
        self.last_stats      = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}
        # randomise goal elevation to a clean 0.5m step between 1.0 and 11.5
        new_goal_z = round(random.uniform(1.0, 11.5) / 0.5) * 0.5
        self.sl_goal_z.val = new_goal_z
        self._apply_altitude_sliders()

    def run_tld(self):
        t0 = time.time()
        stats = {'detected': 0, 'approached': 0, 'used_pts': [], 'unused_pts': []}
        self.path, stats = tld_3d(self.ps.copy(), self.pg.copy(), self.cuboids,
                                  stats=stats)
        dt = (time.time()-t0)*1000
        self.last_stats = stats
        self.anim_t = 0.0
        self.animating = True
        # build the turn-pause and displacement-plane schedules
        self.turn_schedule      = build_turn_schedule(self.path)           if self.path else []
        self.disp_planes        = get_altitude_change_points(self.path)   if self.path else []
        self.show_path_views    = False   # flips to True when animation finishes
        self.add_log(f"Done  {len(self.path)} pts  {dt:.1f}ms")
        self.add_log(f"Length: {path_len_3d(self.path):.2f}")
        self.add_log(f"Vtx det:{stats['detected']} appr:{stats['approached']}")

    def add_log(self, m): self.log = self.log[-6:] + [m]

    def reset_drone(self):
        # wipe the computed path and return the drone to start without touching the obstacles
        self.path = None
        self.anim_t = 0.0
        self.animating = False
        self.turn_schedule   = []
        self.disp_planes     = []
        self.show_path_views = False
        self._turning        = False
        self._turn_t         = 0.0
        self.add_log("Drone reset to start")

    def update_sel_sliders(self):
        # sync sliders to the selected cuboid's dimensions
        if self.selected is None: return
        c = self.cuboids[self.selected]
        self.sl_w.val = c.w; self.sl_d.val = c.d
        self.sl_h.val = c.h; self.sl_elev.val = c.elev

    def apply_sel_sliders(self):
        # write slider values back into the selected cuboid
        if self.selected is None: return
        c = self.cuboids[self.selected]
        c.w = self.sl_w.val; c.d = self.sl_d.val
        c.h = self.sl_h.val; c.elev = self.sl_elev.val

    def top_canvas_to_world(self, cx, cy):
        # convert a pixel position in the top view back to world coordinates
        return cx / self.TOP_SCALE, cy / self.TOP_SCALE

    def world_to_top(self, wx, wy):
        return int(wx * self.TOP_SCALE), int(wy * self.TOP_SCALE)

    def _apply_altitude_sliders(self):
        # update the live ps/pg vectors whenever the altitude sliders move
        self.ps = v3(1, 1, self.sl_start_z.val)
        self.pg = v3(29, 29, self.sl_goal_z.val)

    def handle_event(self, event):
        for sl in [self.sl_w, self.sl_d, self.sl_h, self.sl_elev]:
            if sl.handle(event): self.apply_sel_sliders()
        if self.sl_start_z.handle(event): self._apply_altitude_sliders()
        if self.sl_goal_z.handle(event):  self._apply_altitude_sliders()
        if self.btn_back.handle(event) and self.on_back:  self.on_back()
        if self.sl_num.handle(event):    self.regenerate()
        if self.btn_regen.handle(event): self.regenerate()
        if self.btn_run.handle(event):   self.run_tld()
        if self.btn_reset.handle(event): self.reset_drone()
        if self.btn_replay.handle(event): self.anim_t=0.0; self.animating=True
        if self.selected is not None and self.btn_del.handle(event):
            self.cuboids.pop(self.selected); self.selected=None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # only respond to clicks inside the top-view panel
            if self.TOP_X <= mx < self.TOP_X + self.TOP_W and 0 <= my < self.TOP_H:
                local_x = mx - self.TOP_X
                wx, wy = self.top_canvas_to_world(local_x, my)
                hit = -1
                for i in range(len(self.cuboids)-1, -1, -1):
                    c = self.cuboids[i]
                    if c.x0 <= wx <= c.x1 and c.y0 <= wy <= c.y1:
                        hit = i; break
                if hit >= 0:
                    self.selected = hit
                    self.drag_ref = (mx, my, self.cuboids[hit].cx, self.cuboids[hit].cy)
                    self.update_sel_sliders()
                else:
                    self.selected = None; self.drag_ref = None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag_ref = None

        if event.type == pygame.MOUSEMOTION and self.drag_ref:
            mx, my = event.pos
            dx = (mx - self.drag_ref[0]) / self.TOP_SCALE
            dy = (my - self.drag_ref[1]) / self.TOP_SCALE
            c = self.cuboids[self.selected]
            c.cx = self.drag_ref[2] + dx
            c.cy = self.drag_ref[3] + dy

    def update(self, dt):
        if not self.animating or not self.path:
            return
        speed = dt / (ANIM_STEPS / FPS)

        # check if we are currently in a turn-pause at any waypoint
        if hasattr(self, "_turning") and self._turning:
            self._turn_t += dt / self._turn_dur
            if self._turn_t >= 1.0:
                # turn complete, resume travelling
                self._turn_t = 1.0
                self._turning = False
            return   # position does not advance while turning

        # advance travel time
        prev_t = self.anim_t
        self.anim_t += speed

        # check if we just crossed a waypoint that has a turn scheduled
        for frac, turn_dur, dir_in, dir_out in (self.turn_schedule if hasattr(self, "turn_schedule") else []):
            if prev_t < frac <= self.anim_t and turn_dur > 0.01:
                # snap anim_t to exactly the waypoint and start turning
                self.anim_t = frac
                self._turning = True
                self._turn_t = 0.0
                self._turn_dur = turn_dur
                self._turn_dir_in = dir_in
                self._turn_dir_out = dir_out
                return

        if self.anim_t >= 1.0:
            self.anim_t = 1.0
            self.animating = False
            self.show_path_views = True   # show the multi-view popup

    def _get_look(self):
        """return the current look direction, accounting for mid-turn interpolation"""
        if not self.path:
            return norm(self.pg - self.ps)
        if hasattr(self, "_turning") and self._turning:
            # ease in-out the rotation so it feels physical
            t = self._turn_t
            t_ease = t * t * (3 - 2 * t)   # smoothstep
            return norm(slerp_dirs(self._turn_dir_in, self._turn_dir_out, t_ease))
        return look_dir_3d(self.path, self.anim_t)

    def draw(self):
        surf = self.screen
        surf.fill(C["bg"])

        drone_pos = interp_path_3d(self.path, self.anim_t) if self.path else self.ps.copy()
        look = self._get_look()
        up = v3(0, 0, 1)

        # sidebar panel
        pygame.draw.rect(surf, C["panel"], (0, 0, SIDEBAR_W, H))
        pygame.draw.line(surf, C["border"], (SIDEBAR_W, 0), (SIDEBAR_W, H), 1)
        self.btn_back.draw(surf, self.f_sm)
        draw_text(surf, "TLD 3D", (SIDEBAR_W-50, 18), self.f_sm, C["accent"])
        draw_text(surf, "click+drag in TOP VIEW", (12, H-16), self.f_sm, C["text_dim"])

        self.sl_num.draw(surf, self.f_sm)
        self.btn_regen.draw(surf, self.f_sm)

        # start and goal altitude sliders are always visible
        pygame.draw.line(surf, C["border"], (8, 118), (SIDEBAR_W-8, 118), 1)
        draw_text(surf, "FLIGHT ALTITUDES", (12, 122), self.f_sm, C["text_dim"])
        self.sl_start_z.draw(surf, self.f_sm)
        self.sl_goal_z.draw(surf, self.f_sm)

        if self.selected is not None:
            pygame.draw.line(surf, C["border"], (8, 196), (SIDEBAR_W-8, 196), 1)
            draw_text(surf, f"OBS  [{self.selected}]", (12, 200), self.f_sm, C["accent"])
            self.sl_w.draw(surf, self.f_sm)
            self.sl_d.draw(surf, self.f_sm)
            self.sl_h.draw(surf, self.f_sm)
            self.sl_elev.draw(surf, self.f_sm)
            self.btn_del.draw(surf, self.f_sm)

        self.btn_run.draw(surf, self.f_sm)
        self.btn_reset.draw(surf, self.f_sm)
        self.btn_replay.draw(surf, self.f_sm)

        # log output in the sidebar (vertex stats moved to the path-analysis popup)
        log_y = 500
        pygame.draw.line(surf, C["border"], (8, log_y), (SIDEBAR_W-8, log_y), 1)
        draw_text(surf, "LOG", (12, log_y + 4), self.f_sm, C["text_dim"])
        for i, msg in enumerate(self.log[-5:]):
            draw_text(surf, f"> {msg}", (12, log_y + 20 + i*15), self.f_sm, C["accent_dim"])

        # vertex marker legend in sidebar (shown when path exists)
        if self.path is not None:
            leg_y = 410
            pygame.draw.line(surf, C["border"], (8, leg_y), (SIDEBAR_W-8, leg_y), 1)
            draw_text(surf, "VERTEX MARKERS", (12, leg_y + 4), self.f_sm, C["text_dim"])
            pygame.draw.circle(surf, C["vtx_used"], (22, leg_y + 24), 5)
            draw_text(surf, "Used vertex", (34, leg_y + 18), self.f_sm, C["vtx_used"])
            pygame.draw.circle(surf, C["vtx_unused"], (22, leg_y + 40), 4)
            draw_text(surf, "Unused vertex", (34, leg_y + 34), self.f_sm, C["vtx_unused"])
            det  = self.last_stats.get('detected', 0)
            appr = self.last_stats.get('approached', 0)
            draw_text(surf, f"Used {appr} / {det} vertices",
                      (12, leg_y + 56), self.f_sm, C["accent"])

        # telemetry bar along the bottom
        pygame.draw.rect(surf, C["panel"], (SIDEBAR_W, H-30, W-SIDEBAR_W, 30))
        pygame.draw.line(surf, C["border"], (SIDEBAR_W, H-30), (W, H-30), 1)
        info = f"POS ({drone_pos[0]:.1f}, {drone_pos[1]:.1f}, {drone_pos[2]:.1f})  |  DST {dist3(drone_pos,self.pg):.1f}m"
        if self.path:
            info += f"  |  PATH {path_len_3d(self.path):.1f}m  |  WPT {len(self.path)}"
        draw_text(surf, info, (SIDEBAR_W+8, H-22), self.f_sm, C["text_dim"])

        # vertical divider between the two view panels
        pygame.draw.line(surf, C["border"], (self.FP_X, 0), (self.FP_X, H-30), 1)

        # top-down view
        top = self.top_surf
        top.fill(C["bg"])
        S = self.TOP_SCALE

        # grid lines
        for i in range(0, 31, 3):
            x, y = int(i*S), int(i*S)
            pygame.draw.line(top, C["grid"], (x, 0), (x, self.TOP_H), 1)
            pygame.draw.line(top, C["grid"], (0, y), (self.TOP_W, y), 1)

        # draw each cuboid as a filled rectangle with a height label
        for idx, c in enumerate(self.cuboids):
            is_sel = idx == self.selected
            rx0, ry0 = self.world_to_top(c.x0, c.y0)
            rw, rh   = int(c.w*S), int(c.d*S)
            pygame.draw.rect(top, C["obs_fill"], (rx0, ry0, rw, rh))
            pygame.draw.rect(top, C["obs_sel"] if is_sel else C["obs_edge"],
                             (rx0, ry0, rw, rh), 2 if is_sel else 1)
            # show elevation and height so floating obstacles are obvious
            draw_text(top, f"e{c.elev:.0f}+{c.h:.0f}",
                      (rx0+2, ry0+2), self.f_sm, C["text_dim"])

        # ── vertex markers on top view ─────────────────────────────────────────
        if self.path is not None:
            for pt in self.last_stats.get('unused_pts', []):
                tx, ty = self.world_to_top(pt[0], pt[1])
                pygame.draw.circle(top, C["vtx_unused"], (int(tx), int(ty)), 3)
                pygame.draw.circle(top, (0, 0, 0), (int(tx), int(ty)), 3, 1)
            for pt in self.last_stats.get('used_pts', []):
                tx, ty = self.world_to_top(pt[0], pt[1])
                pygame.draw.circle(top, C["vtx_used"], (int(tx), int(ty)), 4)
                pygame.draw.circle(top, (0, 0, 0), (int(tx), int(ty)), 4, 1)

        # path projected onto the ground plane
        if self.path and len(self.path) > 1:
            ghost = [self.world_to_top(p[0], p[1]) for p in self.path]
            pygame.draw.lines(top, C["path_dim"], False, ghost, 1)
            total = path_len_3d(self.path) * self.anim_t
            acc = 0.0
            anim_pts = [self.world_to_top(self.path[0][0], self.path[0][1])]
            for i in range(1, len(self.path)):
                seg = dist3(self.path[i-1], self.path[i])
                if acc + seg >= total:
                    u = (total-acc)/seg if seg>1e-9 else 0
                    mp = self.path[i-1]+u*(self.path[i]-self.path[i-1])
                    anim_pts.append(self.world_to_top(mp[0], mp[1]))
                    break
                acc += seg
                anim_pts.append(self.world_to_top(self.path[i][0], self.path[i][1]))
            if len(anim_pts) > 1:
                pygame.draw.lines(top, C["path"], False, anim_pts, 2)
        # drone, start and goal markers
        dx, dy = self.world_to_top(drone_pos[0], drone_pos[1])
        draw_drone_icon(top, dx, dy, C["drone"], 7)
        sx, sy = self.world_to_top(self.ps[0], self.ps[1])
        gx, gy = self.world_to_top(self.pg[0], self.pg[1])
        pygame.draw.circle(top, C["start"], (sx, sy), 6)
        pygame.draw.circle(top, C["goal"],  (gx, gy), 6)
        draw_text(top, "S", (sx-4, sy-6), self.f_sm, C["bg"])
        draw_text(top, "G", (gx-4, gy-6), self.f_sm, C["bg"])
        # show the altitude of start and goal next to their markers
        draw_text(top, f"z{self.ps[2]:.1f}", (sx+8, sy-6), self.f_sm, C["start"])
        draw_text(top, f"z{self.pg[2]:.1f}", (gx+8, gy-6), self.f_sm, C["goal"])
        draw_text(top, "TOP VIEW", (4, 4), self.f_sm, C["text_dim"])

        surf.blit(top, (self.TOP_X, 0))

        # first-person drone eye view
        fp = self.fp_surf
        FW, FH = self.FP_W, self.FP_H

        # sky gradient from dark top to slightly lighter horizon
        for y in range(int(FH*0.55)):
            t = y / (FH*0.55)
            col = lerp_color(C["sky_top"], C["sky_bot"], t)
            pygame.draw.line(fp, col, (0, y), (FW, y))
        # ground gradient
        for y in range(int(FH*0.55), FH):
            t = (y - FH*0.55) / (FH*0.45)
            col = lerp_color(C["gnd_top"], C["gnd_bot"], t)
            pygame.draw.line(fp, col, (0, y), (FW, y))
        # horizon line
        pygame.draw.line(fp, C["border"], (0, int(FH*0.55)), (FW, int(FH*0.55)), 1)

        def fp_proj(p):
            return proj_fp(p, drone_pos, look, up, FW, FH, fov=320)

        # perspective ground grid so the scene feels grounded
        for i in range(0, 31, 2):
            pts_a = [v3(i, j, 0) for j in range(0, 31, 2)]
            pts_b = [v3(j, i, 0) for j in range(0, 31, 2)]
            for pts in [pts_a, pts_b]:
                screen_pts = [fp_proj(p) for p in pts]
                screen_pts = [p for p in screen_pts if p and 0<=p[0]<FW and 0<=p[1]<FH]
                if len(screen_pts) > 1:
                    pygame.draw.lines(fp, (18, 38, 22), False,
                                      [(p[0], p[1]) for p in screen_pts], 1)

        # sort back to front so closer obstacles paint over farther ones
        sorted_obs = sorted(self.cuboids,
                            key=lambda o: -dist3(drone_pos, v3(o.cx, o.cy, (o.z0+o.z1)/2)))

        # face definitions: vertex indices and outward normal for each of the 6 faces
        FACE_DEFS = [
            ([0,1,2,3], v3( 0, 0,-1)),
            ([4,5,6,7], v3( 0, 0, 1)),
            ([0,1,5,4], v3( 0,-1, 0)),
            ([2,3,7,6], v3( 0, 1, 0)),
            ([1,2,6,5], v3( 1, 0, 0)),
            ([0,3,7,4], v3(-1, 0, 0)),
        ]

        light_dir = norm(v3(0.5, 0.5, 1.2))

        for obs in sorted_obs:
            vs = obs.verts
            faces_to_draw = []
            for vi_list, fn in FACE_DEFS:
                # back-face culling: skip faces pointing away from the camera
                to_cam = norm(drone_pos - vs[vi_list[0]])
                if float(np.dot(fn, to_cam)) < -0.1:
                    continue
                pts_3d = [vs[i] for i in vi_list]
                proj_pts = [fp_proj(p) for p in pts_3d]
                if any(p is None for p in proj_pts):
                    continue
                avg_depth = sum(p[2] for p in proj_pts) / len(proj_pts)
                if avg_depth < 0:
                    continue
                light = max(0.15, float(np.dot(fn, light_dir)))
                faces_to_draw.append((avg_depth, proj_pts, light))

            # sort faces by depth within this obstacle too
            faces_to_draw.sort(key=lambda x: -x[0])
            for _, proj_pts, light in faces_to_draw:
                b = int(light * 85)
                col = (b, b+12, b+28)
                screen_pts = [(p[0], p[1]) for p in proj_pts]
                if len(screen_pts) >= 3:
                    try:
                        pygame.draw.polygon(fp, col, screen_pts)
                        pygame.draw.polygon(fp, (35, 65, 110), screen_pts, 1)
                    except:
                        pass

        # draw altitude-change planes as squares in the FP view
        if self.disp_planes:
            draw_altitude_planes(fp, self.disp_planes, fp_proj, half_size=3.5)

        # ── vertex markers in FP view ──────────────────────────────────────────
        if self.path is not None:
            for pt in self.last_stats.get('unused_pts', []):
                pp = fp_proj(pt)
                if pp and 0 <= pp[0] < FW and 0 <= pp[1] < FH:
                    pygame.draw.circle(fp, C["vtx_unused"], (int(pp[0]), int(pp[1])), 3)
            for pt in self.last_stats.get('used_pts', []):
                pp = fp_proj(pt)
                if pp and 0 <= pp[0] < FW and 0 <= pp[1] < FH:
                    pygame.draw.circle(fp, C["vtx_used"], (int(pp[0]), int(pp[1])), 4)

        # draw the full planned path as a faint line in 3D space
        if self.path and len(self.path) > 1:
            path_screen = []
            for pt in self.path:
                pp = fp_proj(pt)
                if pp and 0 <= pp[0] < FW and 0 <= pp[1] < FH:
                    path_screen.append((int(pp[0]), int(pp[1])))
            if len(path_screen) > 1:
                pygame.draw.lines(fp, C["path_dim"], False, path_screen, 1)

            # find the next waypoint ahead and draw a crosshair on it
            total_done = path_len_3d(self.path) * self.anim_t
            acc = 0.0
            next_wp = None
            for i in range(1, len(self.path)):
                seg = dist3(self.path[i-1], self.path[i])
                acc += seg
                if acc > total_done:
                    next_wp = self.path[i]; break


        # goal marker visible in the fp view
        gp = fp_proj(self.pg)
        if gp and 0 <= gp[0] < FW and 0 <= gp[1] < FH:
            pygame.draw.circle(fp, C["goal"], (int(gp[0]), int(gp[1])), 8, 2)
            draw_text(fp, "GOAL", (int(gp[0])+10, int(gp[1])-6), self.f_sm, C["goal"])

        # center crosshair HUD element
        cx2, cy2 = FW//2, FH//2
        pygame.draw.line(fp, (*C["drone"], 120), (cx2-16, cy2), (cx2+16, cy2), 1)
        pygame.draw.line(fp, (*C["drone"], 120), (cx2, cy2-16), (cx2, cy2+16), 1)
        pygame.draw.circle(fp, (*C["drone"], 80), (cx2, cy2), 4, 1)

        # altitude bar on the right edge of the fp view
        bar_x, bar_y, bar_h = FW-20, int(FH*0.2), int(FH*0.6)
        pygame.draw.rect(fp, C["border"], (bar_x, bar_y, 8, bar_h), 1)
        alt_frac = min(1.0, drone_pos[2] / 12.0)
        fill_h = int(bar_h * alt_frac)
        pygame.draw.rect(fp, C["accent_dim"], (bar_x+1, bar_y+bar_h-fill_h, 6, fill_h))
        draw_text(fp, "^Z", (bar_x-6, bar_y-12), self.f_sm, C["text_dim"])

        # HUD telemetry readout
        draw_text(fp, f"ALT {drone_pos[2]:.1f}m", (6, FH-40), self.f_sm, C["accent"])
        draw_text(fp, f"DST {dist3(drone_pos, self.pg):.1f}m", (6, FH-26), self.f_sm, C["accent"])
        draw_text(fp, "DRONE EYE VIEW", (4, 4), self.f_sm, C["text_dim"])

        surf.blit(fp, (self.FP_X, 0))


# ─── home / mode-selection screen ─────────────────────────────────────────────

class HomeScreen:
    def __init__(self, screen, fonts):
        self.screen = screen
        self.f_md, self.f_sm, self.f_lg = fonts
        self.btn_2d = Button((W//2-220, H//2+20, 180, 52), "2D  GROUND ROBOT")
        self.btn_3d = Button((W//2+40,  H//2+20, 180, 52), "3D  AERIAL DRONE", primary=True)
        self.choice = None

    def handle_event(self, event):
        if self.btn_2d.handle(event): self.choice = "2d"
        if self.btn_3d.handle(event): self.choice = "3d"

    def draw(self):
        s = self.screen
        s.fill(C["bg"])
        # subtle background grid so the screen doesn't look empty
        for i in range(0, W, 40):
            pygame.draw.line(s, C["grid"], (i, 0), (i, H), 1)
        for i in range(0, H, 40):
            pygame.draw.line(s, C["grid"], (0, i), (W, i), 1)

        draw_text(s, "TLD PATH PLANNING SIMULATION", (W//2, H//2-110),
                  self.f_lg, C["accent"], align="center")
        draw_text(s, "Tangent Line Decomposition  +  Plane-Intersection Extension  +  ICRA 2025",
                  (W//2, H//2-72), self.f_sm, C["text_dim"], align="center")
        draw_text(s, "Select simulation mode", (W//2, H//2-10),
                  self.f_md, C["text"], align="center")

        self.btn_2d.draw(s, self.f_md)
        self.btn_3d.draw(s, self.f_md)

        draw_text(s, "2D: Convex polygon obstacles   Drag to move   Sliders to reshape + rotate",
                  (W//2, H//2+90), self.f_sm, C["text_dim"], align="center")
        draw_text(s, "3D: Cuboid obstacles with elevation   Drone-eye view + Top view   Plane-Intersection TLD",
                  (W//2, H//2+108), self.f_sm, C["text_dim"], align="center")
        draw_text(s, "ESC  returns to this screen at any time",
                  (W//2, H-22), self.f_sm, C["text_dim"], align="center")


# ─── main game loop ───────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("TLD Path Planning Simulation")
    clock = pygame.time.Clock()

    # try the nice monospace font first, fall back to Courier if unavailable
    try:
        f_sm = pygame.font.SysFont("JetBrains Mono", 11)
        f_md = pygame.font.SysFont("JetBrains Mono", 13)
        f_lg = pygame.font.SysFont("JetBrains Mono", 22)
    except:
        f_sm = pygame.font.SysFont("Courier New", 11)
        f_md = pygame.font.SysFont("Courier New", 13)
        f_lg = pygame.font.SysFont("Courier New", 22)
    fonts = (f_md, f_sm, f_lg)

    home   = HomeScreen(screen, fonts)
    sim_2d: Optional[Sim2D] = None
    sim_3d: Optional[Sim3D] = None
    current = "home"

    # shared helper so both the button and ESC key do the same thing
    def go_back():
        nonlocal current
        current = "home"
        home.choice = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if current != "home":
                    go_back()
                else:
                    running = False

            if current == "home":
                home.handle_event(event)
                if home.choice == "2d":
                    # always recreate so obstacles reset when coming back from menu
                    sim_2d = Sim2D(screen, fonts, on_back=go_back)
                    current = "2d"; home.choice = None
                elif home.choice == "3d":
                    sim_3d = Sim3D(screen, fonts, on_back=go_back)
                    current = "3d"; home.choice = None
            elif current == "2d" and sim_2d:
                sim_2d.handle_event(event)
            elif current == "3d" and sim_3d:
                sim_3d.handle_event(event)

        if current == "home":
            home.draw()
        elif current == "2d" and sim_2d:
            sim_2d.update(dt)
            sim_2d.draw()
        elif current == "3d" and sim_3d:
            sim_3d.update(dt)
            sim_3d.draw()
            # once animation finishes, show the path-analysis popup once
            if sim_3d.show_path_views and sim_3d.path:
                sim_3d.show_path_views = False
                draw_three_views(screen, fonts, sim_3d.path,
                                 sim_3d.cuboids, sim_3d.ps, sim_3d.pg,
                                 stats=sim_3d.last_stats)
                sim_3d.draw()   # redraw sim behind the now-closed popup

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()