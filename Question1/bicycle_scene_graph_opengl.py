"""
Bicycle Scene Graph — OpenGL + GLFW (Python)
=============================================
Demonstrates a scene graph where a bicycle is built from hierarchical nodes.
Each node has its own local transform (translate / rotate / scale), and
transforms cascade from parent to child automatically.

Scene Graph Structure
---------------------
World
└── Bicycle (translates across screen, bobs up/down)
    ├── Frame         (static relative to bicycle)
    │   ├── Seat Post
    │   │   └── Seat
    │   └── Handlebar Post
    │       └── Handlebars
    ├── Rear Wheel    (spins, drives chain)
    │   ├── Rim
    │   ├── Spokes  ×8
    │   └── Hub
    ├── Front Wheel   (spins, same rate as rear)
    │   ├── Rim
    │   ├── Spokes  ×8
    │   └── Hub
    └── Drivetrain
        ├── Chainring  (spins with pedals)
        │   ├── Crank L
        │   │   └── Pedal L
        │   └── Crank R
        │       └── Pedal R
        └── Chain      (drawn as dotted arc, links front and rear)

Controls
--------
  SPACE     — pause / resume animation
  R         — reset to start
  ESC / Q   — quit
  ← / →     — change bicycle speed
  +/-       — zoom in/out

Requirements (install with pip)
--------------------------------
  pip install pyglfw PyOpenGL PyOpenGL_accelerate

Run
---
  python bicycle_scene_graph_opengl.py
"""

import sys
import math
import glfw
from OpenGL.GL import *

# ─────────────────────────────────────────────────────────────────────────────
# MATH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def mat_identity():
    """Return a 4×4 identity matrix as a flat list (column-major for OpenGL)."""
    return [
        1,0,0,0,
        0,1,0,0,
        0,0,1,0,
        0,0,0,1,
    ]

def mat_translate(tx, ty):
    m = mat_identity()
    m[12] = tx
    m[13] = ty
    return m

def mat_rotate_z(angle_deg):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    m = mat_identity()
    m[0]  =  c;  m[4]  = -s
    m[1]  =  s;  m[5]  =  c
    return m

def mat_scale(sx, sy):
    m = mat_identity()
    m[0]  = sx
    m[5]  = sy
    return m

def mat_mul(A, B):
    """Multiply two 4×4 column-major matrices."""
    R = [0.0] * 16
    for row in range(4):
        for col in range(4):
            R[col*4 + row] = sum(A[k*4 + row] * B[col*4 + k] for k in range(4))
    return R

def mat_compose(*matrices):
    """Compose a chain of matrices: result = M0 × M1 × M2 × …"""
    result = mat_identity()
    for m in matrices:
        result = mat_mul(result, m)
    return result

# ─────────────────────────────────────────────────────────────────────────────
# SCENE GRAPH NODE
# ─────────────────────────────────────────────────────────────────────────────

class SceneNode:
    """
    One node in the scene graph.

    Each node stores:
      • local_transform  — the transform *relative to its parent*
      • children         — list of child SceneNodes
      • draw_fn          — optional callable(world_matrix) that draws geometry

    Rendering is a recursive DFS:
      render(parent_world_matrix)
        world = parent_world_matrix × local_transform
        draw_fn(world)               # draw this node's geometry
        for child in children:
            child.render(world)      # pass combined matrix down
    """

    def __init__(self, name="node", draw_fn=None):
        self.name            = name
        self.local_transform = mat_identity()   # set each frame by the app
        self.children        = []
        self.draw_fn         = draw_fn          # callable or None

    def add_child(self, child):
        self.children.append(child)
        return child          # allows chaining

    def render(self, parent_world=None):
        if parent_world is None:
            parent_world = mat_identity()

        # Cascade: world = parent_world × my_local
        world = mat_mul(parent_world, self.local_transform)

        # Push combined matrix and draw
        glPushMatrix()
        glLoadMatrixf(world)
        if self.draw_fn:
            self.draw_fn()
        glPopMatrix()

        # Recurse into children — they receive the combined world matrix
        for child in self.children:
            child.render(world)


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING PRIMITIVES  (pure GL 1.x immediate mode — widely supported)
# ─────────────────────────────────────────────────────────────────────────────

def draw_circle(cx, cy, r, segments=48, filled=True):
    if filled:
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
    else:
        glBegin(GL_LINE_LOOP)
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()

def draw_line(x1, y1, x2, y2, width=1.0):
    glLineWidth(width)
    glBegin(GL_LINES)
    glVertex2f(x1, y1)
    glVertex2f(x2, y2)
    glEnd()

def draw_rect(cx, cy, w, h, angle_deg=0.0):
    """Axis-aligned filled rectangle centred at (cx, cy)."""
    glPushMatrix()
    glTranslatef(cx, cy, 0)
    glRotatef(angle_deg, 0, 0, 1)
    hw, hh = w / 2, h / 2
    glBegin(GL_QUADS)
    glVertex2f(-hw, -hh)
    glVertex2f( hw, -hh)
    glVertex2f( hw,  hh)
    glVertex2f(-hw,  hh)
    glEnd()
    glPopMatrix()

def draw_spoke(angle_deg, r):
    """Draw one wheel spoke from centre outward."""
    a = math.radians(angle_deg)
    glBegin(GL_LINES)
    glVertex2f(0, 0)
    glVertex2f(r * math.cos(a), r * math.sin(a))
    glEnd()

def draw_chain_arc(x_rear, x_front, y, r_chain):
    """Approximate the drive chain as two horizontal lines + arcs."""
    glLineWidth(1.5)
    glColor3f(0.3, 0.3, 0.3)
    # Top strand
    glBegin(GL_LINES)
    glVertex2f(x_rear,  y + r_chain)
    glVertex2f(x_front, y + r_chain)
    glEnd()
    # Bottom strand
    glBegin(GL_LINES)
    glVertex2f(x_rear,  y - r_chain)
    glVertex2f(x_front, y - r_chain)
    glEnd()

def draw_text_label(text, x, y, scale=0.0008):
    """Render a simple bitmap string at (x,y) in world space."""
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(scale, scale, 1)
    for ch in text:
        from OpenGL.GLUT import glutStrokeCharacter, GLUT_STROKE_MONO_ROMAN
        glutStrokeCharacter(GLUT_STROKE_MONO_ROMAN, ord(ch))
    glPopMatrix()


# ─────────────────────────────────────────────────────────────────────────────
# BICYCLE SCENE GRAPH BUILDER
# ─────────────────────────────────────────────────────────────────────────────

# Bicycle geometry constants (in "bicycle units", ~1 unit = wheel radius)
WHEEL_R      = 0.18     # wheel outer radius
WHEEL_INNER  = 0.14     # rim inner radius
HUB_R        = 0.025    # hub radius
CHAINRING_R  = 0.055    # chainring sprocket radius
CRANK_LEN    = 0.07     # crank arm length
PEDAL_W      = 0.04     # pedal width
PEDAL_H      = 0.012    # pedal height
SPOKE_COUNT  = 8        # spokes per wheel
WHEELBASE    = 0.44     # horizontal distance between wheel centres
BOTTOM_BRKT  = -0.02    # bottom bracket height relative to wheel centres
SEAT_X       = -0.14    # seat post x offset from rear axle
SEAT_H       = 0.22     # seat post height above bottom bracket
STEM_X       =  0.18    # handlebar stem x offset from front axle


def build_wheel_node(name, color_rim, color_tire, color_hub):
    """Return a SceneNode subtree for one wheel (origin = axle centre)."""

    root = SceneNode(name)

    # Tyre (outermost dark ring)
    def draw_tyre():
        glColor3f(0.15, 0.15, 0.15)
        draw_circle(0, 0, WHEEL_R, 64, filled=True)
        glColor3f(0.22, 0.22, 0.22)
        draw_circle(0, 0, WHEEL_R, 64, filled=False)

    # Rim
    def draw_rim():
        glColor3f(*color_rim)
        draw_circle(0, 0, WHEEL_INNER, 64, filled=True)

    # Spokes
    def draw_spokes():
        glColor3f(0.6, 0.6, 0.65)
        glLineWidth(1.2)
        for i in range(SPOKE_COUNT):
            draw_spoke(i * (360 / SPOKE_COUNT), WHEEL_INNER)

    # Hub
    def draw_hub():
        glColor3f(*color_hub)
        draw_circle(0, 0, HUB_R, 20, filled=True)

    root.add_child(SceneNode(name + "_tyre",   draw_tyre))
    root.add_child(SceneNode(name + "_rim",    draw_rim))
    root.add_child(SceneNode(name + "_spokes", draw_spokes))
    root.add_child(SceneNode(name + "_hub",    draw_hub))
    return root


def build_scene_graph():
    """
    Construct the full bicycle scene graph and return:
      (world_node, bicycle_node, rear_wheel_node, front_wheel_node,
       chainring_node, crank_l_node, crank_r_node)
    so the main loop can update their local_transforms each frame.
    """

    # ── World root ───────────────────────────────────────────────
    world = SceneNode("world")

    # ── Bicycle root ─────────────────────────────────────────────
    bicycle = SceneNode("bicycle")
    world.add_child(bicycle)

    # ── Frame ────────────────────────────────────────────────────
    def draw_frame():
        glLineWidth(3.5)
        glColor3f(0.13, 0.45, 0.90)   # classic blue

        rx, ry = -WHEELBASE / 2, 0    # rear axle (local coords)
        fx, fy =  WHEELBASE / 2, 0    # front axle

        # Bottom bracket position
        bbx = rx + SEAT_X * 0 + 0.00  # centred between axles, slightly rear
        bby = BOTTOM_BRKT

        # Rear axle → bottom bracket
        draw_line(rx, ry, bbx, bby, 3.5)
        # Bottom bracket → front axle
        draw_line(bbx, bby, fx, fy, 3.5)
        # Bottom bracket → top of seat post base
        sp_base_x = rx + 0.06
        sp_base_y = bby
        sp_top_y  = bby + SEAT_H * 0.7
        draw_line(sp_base_x, sp_base_y, sp_base_x, sp_top_y, 3.5)
        # Top tube: seat post top → handlebar stem base
        stem_base_x = fx - 0.04
        stem_base_y = sp_top_y - 0.01
        draw_line(sp_base_x, sp_top_y, stem_base_x, stem_base_y, 3.0)
        # Front fork: front axle → stem base
        draw_line(fx, fy, stem_base_x, stem_base_y, 3.5)
        # Chain stay: rear axle → bottom bracket
        draw_line(rx, ry, bbx, bby, 3.0)

    frame = SceneNode("frame", draw_frame)
    bicycle.add_child(frame)

    # ── Seat post + seat ─────────────────────────────────────────
    def draw_seat_post():
        glColor3f(0.08, 0.08, 0.08)
        draw_rect(0, SEAT_H * 0.5, 0.012, SEAT_H)

    def draw_seat():
        glColor3f(0.1, 0.1, 0.1)
        # Saddle shape: flat ellipse
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0, 0)
        for i in range(33):
            a = math.pi * i / 32      # half ellipse
            x = 0.10 * math.cos(a + math.pi / 2)
            y = 0.018 * math.sin(a + math.pi / 2)
            glVertex2f(x - 0.01, y)
        glEnd()

    seat_post = SceneNode("seat_post", draw_seat_post)
    seat_post.local_transform = mat_translate(-WHEELBASE / 2 + 0.06, BOTTOM_BRKT)
    frame.add_child(seat_post)

    seat = SceneNode("seat", draw_seat)
    seat.local_transform = mat_translate(0, SEAT_H)
    seat_post.add_child(seat)

    # ── Handlebar post + bars ────────────────────────────────────
    def draw_stem():
        glColor3f(0.55, 0.55, 0.60)
        draw_rect(0, SEAT_H * 0.38, 0.012, SEAT_H * 0.75)

    def draw_handlebars():
        glColor3f(0.55, 0.55, 0.60)
        glLineWidth(3.0)
        # Horizontal bar
        draw_line(-0.07, 0, 0.07, 0, 3.0)
        # Drop-bar curves (simple arcs)
        for side in (-1, 1):
            for i in range(20):
                pass   # simplified: just vertical drops
            draw_line(side * 0.07, 0, side * 0.07, -0.04, 2.5)

    stem = SceneNode("stem", draw_stem)
    stem.local_transform = mat_translate(WHEELBASE / 2 - 0.04, BOTTOM_BRKT)
    frame.add_child(stem)

    handlebars = SceneNode("handlebars", draw_handlebars)
    handlebars.local_transform = mat_translate(0, SEAT_H * 0.75)
    stem.add_child(handlebars)

    # ── Rear wheel ───────────────────────────────────────────────
    rear_wheel = build_wheel_node(
        "rear_wheel",
        color_rim  = (0.75, 0.75, 0.80),
        color_tire = (0.15, 0.15, 0.15),
        color_hub  = (0.50, 0.50, 0.55),
    )
    rear_wheel.local_transform = mat_translate(-WHEELBASE / 2, 0)
    bicycle.add_child(rear_wheel)

    # ── Front wheel ──────────────────────────────────────────────
    front_wheel = build_wheel_node(
        "front_wheel",
        color_rim  = (0.75, 0.75, 0.80),
        color_tire = (0.15, 0.15, 0.15),
        color_hub  = (0.50, 0.50, 0.55),
    )
    front_wheel.local_transform = mat_translate(WHEELBASE / 2, 0)
    bicycle.add_child(front_wheel)

    # ── Drivetrain ───────────────────────────────────────────────
    def draw_chainring():
        glColor3f(0.70, 0.65, 0.20)    # golden chainring
        draw_circle(0, 0, CHAINRING_R, 40, filled=False)
        glLineWidth(2.5)
        draw_circle(0, 0, CHAINRING_R, 40, filled=False)

    def draw_cassette():
        glColor3f(0.60, 0.55, 0.18)
        draw_circle(0, 0, CHAINRING_R * 0.55, 30, filled=False)

    def draw_chain():
        glColor3f(0.25, 0.25, 0.25)
        r = CHAINRING_R * 0.98
        # Top and bottom strands of chain
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex2f(0, r)
        glVertex2f(WHEELBASE, r)   # rear → front (offset in drivetrain space)
        glEnd()
        glBegin(GL_LINES)
        glVertex2f(0, -r)
        glVertex2f(WHEELBASE, -r)
        glEnd()

    drivetrain = SceneNode("drivetrain")
    drivetrain.local_transform = mat_translate(-WHEELBASE / 2 + 0.11, BOTTOM_BRKT)
    bicycle.add_child(drivetrain)

    chainring = SceneNode("chainring", draw_chainring)
    drivetrain.add_child(chainring)

    # Cassette sits at the rear wheel hub
    cassette = SceneNode("cassette", draw_cassette)
    cassette.local_transform = mat_translate(0, 0)   # same origin as drivetrain for chain
    drivetrain.add_child(cassette)

    # Chain (visual arc)
    chain = SceneNode("chain", draw_chain)
    drivetrain.add_child(chain)

    # ── Cranks & pedals ──────────────────────────────────────────
    def draw_crank():
        glColor3f(0.35, 0.35, 0.40)
        draw_rect(CRANK_LEN / 2, 0, CRANK_LEN, 0.014)

    def draw_pedal():
        glColor3f(0.15, 0.15, 0.15)
        draw_rect(0, 0, PEDAL_W, PEDAL_H)

    crank_r = SceneNode("crank_r", draw_crank)        # right (near side)
    chainring.add_child(crank_r)

    crank_l = SceneNode("crank_l", draw_crank)        # left (opposite, 180°)
    chainring.add_child(crank_l)

    pedal_r = SceneNode("pedal_r", draw_pedal)
    pedal_r.local_transform = mat_translate(CRANK_LEN, 0)
    crank_r.add_child(pedal_r)

    pedal_l = SceneNode("pedal_l", draw_pedal)
    pedal_l.local_transform = mat_translate(CRANK_LEN, 0)
    crank_l.add_child(pedal_l)

    return (world, bicycle, rear_wheel, front_wheel,
            chainring, crank_r, crank_l)


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATION STATE
# ─────────────────────────────────────────────────────────────────────────────

class AnimState:
    def __init__(self):
        self.paused       = False
        self.time         = 0.0
        self.speed        = 0.6      # bicycle forward speed (world units/sec)
        self.bike_x       = -0.6     # current x position of bicycle
        self.wheel_angle  = 0.0      # cumulative wheel rotation (degrees)
        self.zoom         = 1.0
        self.bg_scroll    = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# HUD / LABEL DRAWING  (uses GL lines to avoid GLUT dependency)
# ─────────────────────────────────────────────────────────────────────────────

def draw_legend(state):
    """Draw a simple on-screen legend in clip space [-1,1]."""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(-1, 1, -1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Semi-transparent background panel
    glColor4f(0.0, 0.0, 0.05, 0.7)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glBegin(GL_QUADS)
    glVertex2f(-1.0, -1.0)
    glVertex2f(-0.45, -1.0)
    glVertex2f(-0.45, -0.48)
    glVertex2f(-1.0, -0.48)
    glEnd()
    glDisable(GL_BLEND)

    # Color key boxes
    entries = [
        ((0.13, 0.45, 0.90), "Frame"),
        ((0.75, 0.75, 0.80), "Wheels / Rim"),
        ((0.70, 0.65, 0.20), "Chainring"),
        ((0.35, 0.35, 0.40), "Cranks"),
        ((0.15, 0.15, 0.15), "Tyres / Pedals"),
    ]
    bx, by = -0.97, -0.52
    for (r, g, b), label in entries:
        glColor3f(r, g, b)
        bw, bh = 0.045, 0.028
        glBegin(GL_QUADS)
        glVertex2f(bx,      by)
        glVertex2f(bx + bw, by)
        glVertex2f(bx + bw, by + bh)
        glVertex2f(bx,      by + bh)
        glEnd()
        by -= 0.076

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_ground():
    """Scrolling ground line."""
    glColor3f(0.25, 0.22, 0.18)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex2f(-2.0, -WHEEL_R)
    glVertex2f( 2.0, -WHEEL_R)
    glEnd()


def draw_background(scroll):
    """Simple scenery: sky gradient boxes + scrolling ground marks."""
    # Sky
    glBegin(GL_QUADS)
    glColor3f(0.53, 0.81, 0.98)
    glVertex2f(-2, -1)
    glVertex2f( 2, -1)
    glColor3f(0.18, 0.52, 0.85)
    glVertex2f( 2,  1)
    glVertex2f(-2,  1)
    glEnd()

    # Ground band
    glColor3f(0.28, 0.52, 0.20)
    glBegin(GL_QUADS)
    glVertex2f(-2, -1.0)
    glVertex2f( 2, -1.0)
    glVertex2f( 2, -WHEEL_R)
    glVertex2f(-2, -WHEEL_R)
    glEnd()

    # Road marks
    glColor3f(0.85, 0.82, 0.72)
    glLineWidth(1.5)
    spacing = 0.25
    for i in range(-12, 13):
        x = (i * spacing - scroll % spacing)
        draw_line(x, -WHEEL_R, x + 0.06, -WHEEL_R, 2.5)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Init GLFW ────────────────────────────────────────────────
    if not glfw.init():
        sys.exit("Failed to initialise GLFW")

    WIDTH, HEIGHT = 1000, 600
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)

    window = glfw.create_window(WIDTH, HEIGHT, "Bicycle Scene Graph — OpenGL", None, None)
    if not window:
        glfw.terminate()
        sys.exit("Failed to create GLFW window")

    glfw.make_context_current(window)
    glfw.swap_interval(1)   # vsync

    # ── Build scene graph ────────────────────────────────────────
    (world, bicycle, rear_wheel, front_wheel,
     chainring, crank_r, crank_l) = build_scene_graph()

    state = AnimState()

    # ── Input callbacks ──────────────────────────────────────────
    def on_key(win, key, scancode, action, mods):
        if action not in (glfw.PRESS, glfw.REPEAT):
            return
        if key == glfw.KEY_SPACE:
            state.paused = not state.paused
        elif key in (glfw.KEY_ESCAPE, glfw.KEY_Q):
            glfw.set_window_should_close(win, True)
        elif key == glfw.KEY_R:
            state.time        = 0.0
            state.bike_x      = -0.6
            state.wheel_angle = 0.0
            state.bg_scroll   = 0.0
        elif key == glfw.KEY_RIGHT:
            state.speed = min(state.speed + 0.1, 2.0)
        elif key == glfw.KEY_LEFT:
            state.speed = max(state.speed - 0.1, 0.05)
        elif key in (glfw.KEY_EQUAL, glfw.KEY_KP_ADD):
            state.zoom = min(state.zoom + 0.1, 3.0)
        elif key in (glfw.KEY_MINUS, glfw.KEY_KP_SUBTRACT):
            state.zoom = max(state.zoom - 0.1, 0.3)

    glfw.set_key_callback(window, on_key)

    # ── OpenGL setup ─────────────────────────────────────────────
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    prev_time = glfw.get_time()

    # ── Render loop ──────────────────────────────────────────────
    while not glfw.window_should_close(window):
        glfw.poll_events()

        # Delta time
        now  = glfw.get_time()
        dt   = now - prev_time
        prev_time = now
        dt = min(dt, 0.05)   # clamp to avoid spiral of death on lag

        # ── Update animation ──────────────────────────────────
        if not state.paused:
            state.time       += dt
            state.bike_x     += state.speed * dt
            state.bg_scroll  += state.speed * dt
            # Wheel rotation: circumference = 2π·r, so angle per unit = 1/r radians
            deg_per_unit      = math.degrees(1.0 / WHEEL_R)
            state.wheel_angle += state.speed * dt * deg_per_unit
            # Loop bicycle back to left when it exits right
            if state.bike_x > 1.2:
                state.bike_x = -1.2

        # Bob amplitude
        bob_y = math.sin(state.time * 4.5) * 0.003

        # ── Update scene graph transforms ─────────────────────
        # World is fixed
        world.local_transform = mat_identity()

        # Bicycle: translate across screen + vertical bob
        bicycle.local_transform = mat_compose(
            mat_translate(state.bike_x, bob_y),
            mat_scale(state.zoom, state.zoom),
        )

        # Rear wheel: fixed relative to bicycle (local offset set at build time)
        # — we update its rotation each frame
        rear_wheel.local_transform = mat_compose(
            mat_translate(-WHEELBASE / 2, 0),
            mat_rotate_z(-state.wheel_angle),   # negative = forward roll
        )

        # Front wheel: same rotation
        front_wheel.local_transform = mat_compose(
            mat_translate(WHEELBASE / 2, 0),
            mat_rotate_z(-state.wheel_angle),
        )

        # Chainring: spins at ~3× wheel rate (gear ratio)
        crank_angle = state.wheel_angle * 1.8
        chainring.local_transform = mat_compose(
            mat_translate(0, 0),   # already positioned by drivetrain node
            mat_rotate_z(crank_angle),
        )

        # Crank R is at 0°, crank L is 180° opposite
        crank_r.local_transform = mat_identity()    # inherits chainring rotation
        crank_l.local_transform = mat_rotate_z(180)

        # Pedals stay horizontal in world space (counter-rotate to cancel parent spin)
        # This gives a realistic "pedal stays flat" effect
        for pedal_node in [crank_r.children[0], crank_l.children[0]]:
            pedal_node.local_transform = mat_compose(
                mat_translate(CRANK_LEN, 0),
                mat_rotate_z(-crank_angle),   # cancels parent rotation
            )

        # ── Render ────────────────────────────────────────────
        w, h = glfw.get_framebuffer_size(window)
        glViewport(0, 0, w, h)
        glClear(GL_COLOR_BUFFER_BIT)

        # Projection: orthographic, aspect-corrected
        aspect = w / h if h > 0 else 1.0
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-aspect, aspect, -1, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Background (drawn in world space, not affected by zoom)
        draw_background(state.bg_scroll)
        draw_ground()

        # ── Traverse & render the scene graph ─────────────────
        world.render()

        # HUD legend
        draw_legend(state)

        # On-screen text info (approximate, using GL lines via mini bitmap font)
        # (We skip full GLUT text to avoid extra dependency — speed shown in title)
        title = (f"Bicycle Scene Graph  |  Speed: {state.speed:.1f}  |  "
                 f"Zoom: {state.zoom:.1f}x  |  "
                 f"{'⏸ PAUSED' if state.paused else '▶ RUNNING'}  |  "
                 f"SPACE=pause  ←/→=speed  +/-=zoom  R=reset  Q=quit")
        glfw.set_window_title(window, title)

        glfw.swap_buffers(window)

    glfw.terminate()


if __name__ == "__main__":
    main()