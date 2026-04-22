from graphviz import Digraph

dot = Digraph(
    name='BicycleSceneGraph',
    comment='Bicycle Scene Graph',
    format='png'
)

dot.attr(
    rankdir='TB',
    bgcolor='#0f0f14',
    fontname='Helvetica Neue',
    fontcolor='#e8e4d9',
    pad='0.6',
    nodesep='0.55',
    ranksep='0.75',
    splines='ortho',
)

# Node style defaults
dot.attr('node',
    fontname='Helvetica Neue',
    fontsize='11',
    style='filled,rounded',
    penwidth='0',
    margin='0.18,0.10',
)

dot.attr('edge',
    color='#3a3a4a',
    penwidth='1.5',
    arrowsize='0.7',
    arrowhead='vee',
)

# ── Color palette ──
C_ROOT   = ('#7c6af5', '#e8e4d9', '#4a3fb5')   # fill, font, border
C_MAJOR  = ('#1d6b5c', '#a8f0df', '#0f4a3d')   # frame, fork, handlebars, saddle
C_WHEEL  = ('#4a1d6b', '#d4a8f0', '#2d0f4a')   # wheels
C_MINOR  = ('#6b3a1d', '#f0c8a8', '#4a250f')   # components
C_LEAF   = ('#1a2840', '#7ab3e0', '#0d1a2a')   # leaf parts

def node(g, name, label, transform, color_triple):
    fill, font, border = color_triple
    g.node(name,
        label=f'<<B>{label}</B><BR/><FONT POINT-SIZE="9" COLOR="{font}">{transform}</FONT>>',
        fillcolor=fill,
        fontcolor=font,
        color=border,
        penwidth='1.5',
    )

# ── ROOT ──
node(dot, 'world', 'World Root', 'identity', C_ROOT)

# ── BICYCLE ──
node(dot, 'bicycle', 'Bicycle', 'translate(0, 0, 0)', C_MAJOR)

# ── MAIN COMPONENTS ──
node(dot, 'frame',       'Frame',        'identity',              C_MAJOR)
node(dot, 'front_fork',  'Front Fork',   'translate(0.55, 0, 0)', C_MAJOR)
node(dot, 'handlebars',  'Handlebars',   'translate(0, 0.6, 0)',  C_MAJOR)
node(dot, 'saddle_post', 'Saddle Post',  'translate(-0.2,0.3,0)', C_MAJOR)
node(dot, 'rear_wheel',  'Rear Wheel',   'translate(-0.55,0, 0)', C_WHEEL)
node(dot, 'front_wheel', 'Front Wheel',  'translate(0.55, 0, 0)', C_WHEEL)

# ── SADDLE ──
node(dot, 'saddle', 'Saddle', 'translate(0, 0.2, 0)', C_MINOR)

# ── DRIVETRAIN ──
node(dot, 'drivetrain',  'Drivetrain',   'translate(-0.1,0,0)',   C_MINOR)
node(dot, 'chainring',   'Chainring',    'rotate(θ_crank)',       C_LEAF)
node(dot, 'crank_l',     'Crank L',      'rotate(0°)',            C_LEAF)
node(dot, 'crank_r',     'Crank R',      'rotate(180°)',          C_LEAF)
node(dot, 'pedal_l',     'Pedal L',      'translate(-0.15,0,0)',  C_LEAF)
node(dot, 'pedal_r',     'Pedal R',      'translate(0.15, 0, 0)', C_LEAF)
node(dot, 'chain',       'Chain',        'follows sprockets',     C_LEAF)
node(dot, 'cassette',    'Cassette',     'rotate(θ_wheel)',       C_LEAF)

# ── WHEEL PARTS ──
node(dot, 'rim_r',   'Rim',    'identity',   C_LEAF)
node(dot, 'spokes_r','Spokes', 'radial(36)', C_LEAF)
node(dot, 'tire_r',  'Tire',   'scale(1.05)',C_LEAF)
node(dot, 'hub_r',   'Hub',    'identity',   C_LEAF)

node(dot, 'rim_f',   'Rim',    'identity',   C_LEAF)
node(dot, 'spokes_f','Spokes', 'radial(36)', C_LEAF)
node(dot, 'tire_f',  'Tire',   'scale(1.05)',C_LEAF)
node(dot, 'hub_f',   'Hub',    'identity',   C_LEAF)

# ── HANDLEBAR PARTS ──
node(dot, 'grips',   'Grips',       'translate(±0.3,0,0)', C_LEAF)
node(dot, 'brake_l', 'Brake Lever L','translate(-0.25,0,0)',C_LEAF)
node(dot, 'brake_r', 'Brake Lever R','translate(0.25, 0,0)',C_LEAF)

# ── EDGES ──
edges = [
    ('world',       'bicycle'),
    ('bicycle',     'frame'),
    ('bicycle',     'rear_wheel'),
    ('bicycle',     'front_wheel'),
    ('frame',       'front_fork'),
    ('frame',       'saddle_post'),
    ('frame',       'drivetrain'),
    ('front_fork',  'front_wheel'),
    ('saddle_post', 'saddle'),
    ('handlebars',  'grips'),
    ('handlebars',  'brake_l'),
    ('handlebars',  'brake_r'),
    ('front_fork',  'handlebars'),
    ('drivetrain',  'chainring'),
    ('drivetrain',  'chain'),
    ('drivetrain',  'cassette'),
    ('chainring',   'crank_l'),
    ('chainring',   'crank_r'),
    ('crank_l',     'pedal_l'),
    ('crank_r',     'pedal_r'),
    ('rear_wheel',  'rim_r'),
    ('rear_wheel',  'spokes_r'),
    ('rear_wheel',  'tire_r'),
    ('rear_wheel',  'hub_r'),
    ('front_wheel', 'rim_f'),
    ('front_wheel', 'spokes_f'),
    ('front_wheel', 'tire_f'),
    ('front_wheel', 'hub_f'),
    ('hub_r',       'cassette'),
]

for src, dst in edges:
    dot.edge(src, dst)

out = dot.render('C:/Users/user/Documents/ComputerGraphics/bicycle_scene_graph (1)', cleanup=True)
print(f'Saved: {out}')
