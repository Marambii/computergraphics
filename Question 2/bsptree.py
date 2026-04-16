"""
BSP Tree Implementation — Computer Graphics
Demonstrates:
  1. Building a BSP tree from a list of triangles
  2. Counting how many extra triangles are created by plane splits
  3. Showing minimum extra triangles = 0 when planes align with polygons

Each Triangle is represented as 3 vertices in 2D (x, y) for simplicity.
The "splitting plane" in 2D is a splitting line.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

@dataclass
class Vec2:
    x: float
    y: float

    def __sub__(self, other): return Vec2(self.x - other.x, self.y - other.y)
    def __add__(self, other): return Vec2(self.x + other.x, self.y + other.y)
    def scale(self, t):       return Vec2(self.x * t, self.y * t)
    def dot(self, other):     return self.x * other.x + self.y * other.y


@dataclass
class Triangle:
    """Triangle defined by 3 vertices; carries an id for tracking."""
    a: Vec2
    b: Vec2
    c: Vec2
    id: int = 0

    def vertices(self):
        return [self.a, self.b, self.c]

    def centroid(self) -> Vec2:
        return Vec2((self.a.x + self.b.x + self.c.x) / 3,
                    (self.a.y + self.b.y + self.c.y) / 3)


@dataclass
class Plane:
    """
    Line in 2D: ax + by + c = 0  (normalised so that a^2+b^2=1)
    sign of evaluate(p) tells which side point p is on.
    """
    a: float
    b: float
    c: float

    @classmethod
    def from_two_points(cls, p: Vec2, q: Vec2) -> "Plane":
        dx, dy = q.x - p.x, q.y - p.y
        # Normal is perpendicular to (dx, dy)
        nx, ny = -dy, dx
        length = math.hypot(nx, ny)
        if length < 1e-9:
            raise ValueError("Degenerate plane (identical points)")
        nx, ny = nx / length, ny / length
        c = -(nx * p.x + ny * p.y)
        return cls(nx, ny, c)

    def evaluate(self, p: Vec2) -> float:
        """Positive = front, negative = back, ~0 = on plane."""
        return self.a * p.x + self.b * p.y + self.c

    def classify(self, p: Vec2, eps: float = 1e-6) -> str:
        d = self.evaluate(p)
        if d > eps:  return "front"
        if d < -eps: return "back"
        return "on"

    def intersect_segment(self, p: Vec2, q: Vec2) -> Optional[Vec2]:
        """Return intersection point of segment PQ with this plane, or None."""
        dp, dq = self.evaluate(p), self.evaluate(q)
        if dp * dq >= 0:
            return None          # same side — no crossing
        t = dp / (dp - dq)
        return p + (q - p).scale(t)


# ---------------------------------------------------------------------------
# Triangle classifier + splitter
# ---------------------------------------------------------------------------

EPSILON = 1e-6


def classify_triangle(tri: Triangle, plane: Plane) -> str:
    """
    Returns one of: 'front', 'back', 'on', 'straddling'
    A triangle straddles if its vertices are on both sides.
    """
    sides = {plane.classify(v) for v in tri.vertices()}
    sides.discard("on")
    if not sides:       return "on"
    if len(sides) == 1: return sides.pop()
    return "straddling"


def split_triangle(tri: Triangle, plane: Plane, next_id: list) -> tuple[list, list]:
    """
    Split a straddling triangle into front and back fragment lists.
    Returns (front_triangles, back_triangles).
    Extra triangles created = (total output triangles) - 1.
    """
    verts   = tri.vertices()
    classes = [plane.classify(v) for v in verts]

    front_pts = []
    back_pts  = []

    for i in range(3):
        curr, curr_cls = verts[i], classes[i]
        nxt,  nxt_cls  = verts[(i + 1) % 3], classes[(i + 1) % 3]

        if curr_cls != "back":
            front_pts.append(curr)
        if curr_cls != "front":
            back_pts.append(curr)

        # Edge crosses the plane → add intersection to both sides
        if (curr_cls == "front" and nxt_cls == "back") or \
           (curr_cls == "back"  and nxt_cls == "front"):
            pt = plane.intersect_segment(curr, nxt)
            if pt:
                front_pts.append(pt)
                back_pts.append(pt)

    def polygon_to_triangles(pts, color_id):
        """Fan-triangulate a convex polygon."""
        tris = []
        for i in range(1, len(pts) - 1):
            new_id = next_id[0]; next_id[0] += 1
            tris.append(Triangle(pts[0], pts[i], pts[i + 1], new_id))
        return tris

    front_tris = polygon_to_triangles(front_pts, next_id)
    back_tris  = polygon_to_triangles(back_pts,  next_id)
    return front_tris, back_tris


# ---------------------------------------------------------------------------
# BSP Node
# ---------------------------------------------------------------------------

@dataclass
class BSPNode:
    plane:       Optional[Plane]    = None
    triangles:   list               = field(default_factory=list)   # coplanar
    front:       Optional["BSPNode"] = None
    back:        Optional["BSPNode"] = None


# ---------------------------------------------------------------------------
# BSP Builder
# ---------------------------------------------------------------------------

class BSPTree:
    def __init__(self):
        self.root          = None
        self.splits_count  = 0      # extra triangles added due to splits
        self.next_id       = [1000] # mutable counter

    def build(self, triangles: list[Triangle]) -> BSPNode:
        self.root = self._build(triangles)
        return self.root

    def _build(self, triangles: list[Triangle]) -> Optional[BSPNode]:
        if not triangles:
            return None

        # Choose the first triangle's plane as the splitting plane (simple heuristic)
        node = BSPNode()
        splitter = triangles[0]
        node.plane = Plane.from_two_points(splitter.a, splitter.b)

        front_list, back_list = [], []
        # The splitter goes into the coplanar list
        node.triangles.append(splitter)

        for tri in triangles[1:]:   # skip the splitter (index 0)
            status = classify_triangle(tri, node.plane)
            if status == "on":
                node.triangles.append(tri)
            elif status == "front":
                front_list.append(tri)
            elif status == "back":
                back_list.append(tri)
            else:  # straddling — must split
                ft, bt = split_triangle(tri, node.plane, self.next_id)
                extra = (len(ft) + len(bt)) - 1   # one became n
                self.splits_count += extra
                front_list.extend(ft)
                back_list.extend(bt)

        node.front = self._build(front_list)
        node.back  = self._build(back_list)
        return node

    def count_nodes(self, node: Optional[BSPNode] = None) -> int:
        if node is None:
            node = self.root
        count, stack = 0, [node]
        while stack:
            n = stack.pop()
            if n is None: continue
            count += 1
            stack.append(n.front)
            stack.append(n.back)
        return count

    def count_all_triangles(self, node: Optional[BSPNode] = None) -> int:
        if node is None:
            node = self.root
        count, stack = 0, [node]
        while stack:
            n = stack.pop()
            if n is None: continue
            count += len(n.triangles)
            stack.append(n.front)
            stack.append(n.back)
        return count

    def back_to_front(self, camera: Vec2,
                      node: Optional[BSPNode] = None) -> list[Triangle]:
        """Painter's algorithm traversal: yields triangles back-to-front."""
        if node is None:
            node = self.root
        result = []
        self._btf(camera, node, result)
        return result

    def _btf(self, camera: Vec2, node: Optional[BSPNode], result: list):
        if node is None or node.plane is None:
            return
        side = node.plane.classify(camera)
        if side != "back":
            self._btf(camera, node.back,  result)
            result.extend(node.triangles)
            self._btf(camera, node.front, result)
        else:
            self._btf(camera, node.front, result)
            result.extend(node.triangles)
            self._btf(camera, node.back,  result)


# ---------------------------------------------------------------------------
# Demo: CASE 1 — non-aligned planes → splits happen
# ---------------------------------------------------------------------------

def demo_with_splits():
    print("=" * 60)
    print("CASE 1: Triangles where splits occur")
    print("=" * 60)

    # Four triangles arranged so they straddle each other's planes
    triangles = [
        Triangle(Vec2(0, 0),  Vec2(4, 0),  Vec2(2, 3),  id=1),
        Triangle(Vec2(1, -1), Vec2(1, 4),  Vec2(3, 2),  id=2),  # will straddle
        Triangle(Vec2(-1, 1), Vec2(5, 1),  Vec2(2, 4),  id=3),
        Triangle(Vec2(0, 2),  Vec2(4, 2),  Vec2(2, -1), id=4),
    ]

    tree = BSPTree()
    tree.build(triangles)

    n = len(triangles)
    extra = tree.splits_count
    total = n + extra

    print(f"Input triangles N          = {n}")
    print(f"Extra triangles from splits= {extra}")
    print(f"Total triangles in tree    = {total}")
    print(f"BSP nodes                  = {tree.count_nodes()}")
    print()
    print(f"MINIMUM extra = 0 (if planes are aligned with polygons)")
    print(f"THIS CASE extra = {extra} (planes cut across other triangles)")


# ---------------------------------------------------------------------------
# Demo: CASE 2 — polygon-aligned planes → ZERO extra triangles
# ---------------------------------------------------------------------------

def demo_minimum_zero():
    print()
    print("=" * 60)
    print("CASE 2: Planes aligned with polygons → 0 extra triangles")
    print("=" * 60)

    # Triangles that tile a plane without overlap — no triangle
    # will ever straddle another triangle's edge plane
    triangles = [
        Triangle(Vec2(0, 0), Vec2(2, 0), Vec2(1, 2), id=1),
        Triangle(Vec2(2, 0), Vec2(4, 0), Vec2(3, 2), id=2),
        Triangle(Vec2(4, 0), Vec2(6, 0), Vec2(5, 2), id=3),
        Triangle(Vec2(6, 0), Vec2(8, 0), Vec2(7, 2), id=4),
    ]

    tree = BSPTree()
    tree.build(triangles)

    n = len(triangles)
    extra = tree.splits_count
    total = n + extra

    print(f"Input triangles N          = {n}")
    print(f"Extra triangles from splits= {extra}")
    print(f"Total triangles in tree    = {total}")
    print(f"BSP nodes                  = {tree.count_nodes()}")


# ---------------------------------------------------------------------------
# Demo: CASE 3 — Minimum formula analysis
# ---------------------------------------------------------------------------

def demo_formula():
    print()
    print("=" * 60)
    print("MINIMUM EXTRA TRIANGLES — THEORETICAL ANALYSIS")
    print("=" * 60)
    print("""
Given N triangles:

  Minimum extra triangles = 0
  ─────────────────────────────────────────────────
  Achievable when every splitting plane chosen at
  each BSP node is coplanar with one of the input
  triangles, so no triangle ever straddles a plane.

  Worst case extra triangles = O(N²)
  ─────────────────────────────────────────────────
  Each of N-1 splitting planes can in the worst case
  cut every remaining triangle, producing:
      (N-1) + (N-2) + … + 1 = N(N-1)/2  extra pieces.

  For N triangles:
""")
    print(f"  {'N':>5}  {'min extra':>10}  {'worst case extra':>18}  {'worst total':>12}")
    print(f"  {'-'*5}  {'-'*10}  {'-'*18}  {'-'*12}")
    for n in [1, 2, 4, 8, 16, 32, 64]:
        worst = n * (n - 1) // 2
        print(f"  {n:>5}  {'0':>10}  {worst:>18}  {n + worst:>12}")


# ---------------------------------------------------------------------------
# Visualise back-to-front traversal
# ---------------------------------------------------------------------------

def demo_traversal():
    print()
    print("=" * 60)
    print("PAINTER'S ALGORITHM — back-to-front traversal order")
    print("=" * 60)

    triangles = [
        Triangle(Vec2(0, 0), Vec2(2, 0), Vec2(1, 2), id=1),
        Triangle(Vec2(2, 0), Vec2(4, 0), Vec2(3, 2), id=2),
        Triangle(Vec2(4, 0), Vec2(6, 0), Vec2(5, 2), id=3),
    ]

    tree = BSPTree()
    tree.build(triangles)

    camera = Vec2(3, 10)   # camera above the scene
    order  = tree.back_to_front(camera)
    print(f"Camera position: ({camera.x}, {camera.y})")
    print(f"Draw order (back → front): {[t.id for t in order]}")
    print("(Triangles drawn in this order will composite correctly)")


# ---------------------------------------------------------------------------
# Run all demos
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_with_splits()
    demo_minimum_zero()
    demo_formula()
    demo_traversal()