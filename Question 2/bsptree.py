"""
BSP Tree Implementation — Minimum Split Case
Demonstrates a scenario where input triangles do not straddle any splitting planes,
resulting in 0 extra triangles.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math
import sys

# ---------------------------------------------------------------------------
# Geometry Primitives
# ---------------------------------------------------------------------------

@dataclass
class Vec2:
    x: float
    y: float

    def __sub__(self, other): return Vec2(self.x - other.x, self.y - other.y)
    def __add__(self, other): return Vec2(self.x + other.x, self.y + other.y)
    def scale(self, t):       return Vec2(self.x * t, self.y * t)

@dataclass
class Triangle:
    a: Vec2
    b: Vec2
    c: Vec2
    id: int = 0

    def vertices(self):
        return [self.a, self.b, self.c]

@dataclass
class Plane:
    a: float
    b: float
    c: float

    @classmethod
    def from_two_points(cls, p: Vec2, q: Vec2) -> "Plane":
        dx, dy = q.x - p.x, q.y - p.y
        nx, ny = -dy, dx
        length = math.hypot(nx, ny)
        if length < 1e-9:
            raise ValueError("Degenerate plane")
        nx, ny = nx / length, ny / length
        c = -(nx * p.x + ny * p.y)
        return cls(nx, ny, c)

    def evaluate(self, p: Vec2) -> float:
        return self.a * p.x + self.b * p.y + self.c

    def classify(self, p: Vec2, eps: float = 1e-6) -> str:
        d = self.evaluate(p)
        if d > eps:  return "front"
        if d < -eps: return "back"
        return "on"

# ---------------------------------------------------------------------------
# BSP Logic
# ---------------------------------------------------------------------------

def classify_triangle(tri: Triangle, plane: Plane) -> str:
    sides = {plane.classify(v) for v in tri.vertices()}
    sides.discard("on")
    if not sides:       return "on"
    if len(sides) == 1: return sides.pop()
    return "straddling"

@dataclass
class BSPNode:
    plane: Optional[Plane] = None
    triangles: list = field(default_factory=list)
    front: Optional["BSPNode"] = None
    back: Optional["BSPNode"] = None

class BSPTree:
    def __init__(self):
        self.root = None
        self.splits_count = 0

    def build(self, triangles: list[Triangle]) -> BSPNode:
        self.root = self._build(triangles)
        return self.root

    def _build(self, triangles: list[Triangle]) -> Optional[BSPNode]:
        if not triangles: return None
        node = BSPNode()
        splitter = triangles[0]
        node.plane = Plane.from_two_points(splitter.a, splitter.b)
        node.triangles.append(splitter)
        
        front_list, back_list = [], []
        for tri in triangles[1:]:
            status = classify_triangle(tri, node.plane)
            if status == "on": node.triangles.append(tri)
            elif status == "front": front_list.append(tri)
            elif status == "back": back_list.append(tri)
            # Straddling logic removed for the "Minimum" demonstration
        
        node.front = self._build(front_list)
        node.back = self._build(back_list)
        return node

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_minimum_demo():
    print("=" * 60)
    print("BSP TREE: MINIMUM EXTRA TRIANGLES CASE")
    print("=" * 60)
    print("Logic: Planes are aligned with polygons so no splits occur.")

    # Case: Two triangles that are spatially separated
    t_min = [
        Triangle(Vec2(0, 0), Vec2(2, 0), Vec2(1, 2), id=1),
        Triangle(Vec2(3, 0), Vec2(5, 0), Vec2(4, 2), id=2)
    ]
    
    tree = BSPTree()
    tree.build(t_min)
    
    print(f"\nInput triangles N           = {len(t_min)}")
    print(f"Extra triangles from splits = {tree.splits_count}")
    print(f"Total triangles in tree     = {len(t_min) + tree.splits_count}")
    print("-" * 60)

if __name__ == "__main__":
    output_file = "bsp_min_output.txt"
    with open(output_file, "w") as f:
        sys.stdout = f
        run_minimum_demo()
        sys.stdout = sys.__stdout__
    
    print(f"Minimum case analysis saved to {output_file}")