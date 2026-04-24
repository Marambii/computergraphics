import matplotlib
matplotlib.use('Agg')  # disables GUI backend

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from bsptree import BSPTree, Triangle, Vec2, BSPNode # Assumes your code is in bsptree.py

def visualize_bsp(node: BSPNode, ax, depth=0, x_range=(-2, 12), y_range=(-7, 12)):
    """Recursively plots the BSP splitting lines and triangles."""
    if node is None:
        return

    # 1. Draw the triangles stored at this node (coplanar triangles)
    for tri in node.triangles:
        polygon = plt.Polygon([(tri.a.x, tri.a.y), (tri.b.x, tri.b.y), (tri.c.x, tri.c.y)],
                              closed=True, fill=True, facecolor='lightblue', 
                              edgecolor='blue', alpha=0.5, label=f"Tri {tri.id}" if depth == 0 else "")
        ax.add_patch(polygon)
        # Add ID label at centroid
        cx, cy = (tri.a.x + tri.b.x + tri.c.x)/3, (tri.a.y + tri.b.y + tri.c.y)/3
        ax.text(cx, cy, str(tri.id), fontsize=9, fontweight='bold')

    # 2. Draw the splitting plane (the line)
    if node.plane:
        # Calculate line endpoints based on the plot boundaries
        # ax + by + c = 0  =>  y = (-ax - c) / b
        a, b, c = node.plane.a, node.plane.b, node.plane.c
        
        if abs(b) > 1e-6:
            x_pts = [x_range[0], x_range[1]]
            y_pts = [(-a * x - c) / b for x in x_pts]
        else: # Vertical line
            x_pts = [-c / a, -c / a]
            y_pts = [y_range[0], y_range[1]]
            
        ax.plot(x_pts, y_pts, '--', color='red', alpha=0.7, linewidth=1.5, label="Split Plane" if depth == 0 else "")

    # 3. Recurse
    visualize_bsp(node.front, ax, depth + 1, x_range, y_range)
    visualize_bsp(node.back, ax, depth + 1, x_range, y_range)

def run_visual_demo():
    # Setup the same triangles from Case 1
    triangles = [
        Triangle(Vec2(0, 0), Vec2(10, 0), Vec2(5, 10), id=1),
        Triangle(Vec2(0, 5), Vec2(10, 5), Vec2(5, -5), id=2)
    ]

    tree = BSPTree()
    tree.build(triangles)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-2, 12)
    ax.set_ylim(-7, 12)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_title("BSP Tree Visualization: Splitting & Partitioning")

    visualize_bsp(tree.root, ax)
    
    # Create a legend but remove duplicate labels
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper right')

    plt.savefig("output.png")

if __name__ == "__main__":
    run_visual_demo()