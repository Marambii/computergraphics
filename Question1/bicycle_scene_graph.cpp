/*
 * ============================================================
 *  Bicycle Scene Graph  —  C++ / OpenGL (Legacy) + GLFW 3
 *  Compatible: MSVC (Visual Studio), GCC, Clang
 * ============================================================
 *
 *  Build — Visual Studio (Developer Command Prompt)
 *  ─────────────────────────────────────────────────
 *  1. Download GLFW "Windows pre-compiled binaries" from https://www.glfw.org/download.html
 *     Extract to e.g. C:\libs\glfw
 *  2. In a Developer Command Prompt:
 *     cl /std:c++17 /EHsc /D_USE_MATH_DEFINES ^
 *        /I "C:\libs\glfw\include" ^
 *        bicycle_scene_graph.cpp ^
 *        /link /LIBPATH:"C:\libs\glfw\lib-vc2022" glfw3.lib opengl32.lib glu32.lib
 *
 *  Build — GCC / MinGW / MSYS2
 *  ─────────────────────────────────────────────────
 *  pacman -S mingw-w64-x86_64-glfw
 *  g++ -std=c++17 -D_USE_MATH_DEFINES bicycle_scene_graph.cpp ^
 *      -lglfw3 -lopengl32 -lglu32 -lm -o bicycle.exe
 *
 *  Build — Linux
 *  ─────────────
 *  sudo apt install libglfw3-dev libgl-dev
 *  g++ -std=c++17 bicycle_scene_graph.cpp -lglfw -lGL -lGLU -lm -o bicycle
 *
 *  Build — macOS
 *  ─────────────
 *  brew install glfw
 *  g++ -std=c++17 bicycle_scene_graph.cpp -lglfw -framework OpenGL -o bicycle
 *
 *  Controls
 *  ────────
 *   SPACE        pause / resume
 *   R            reset
 *   LEFT/RIGHT   change speed
 *   + / -        zoom in / out
 *   ESC / Q      quit
 * ============================================================
 */

 /* Must come FIRST so <cmath> exposes M_PI on Windows */
#ifndef _USE_MATH_DEFINES
#  define _USE_MATH_DEFINES
#endif

#include <cmath>
#include <cstring>
#include <algorithm>
#include <functional>
#include <memory>
#include <sstream>
#include <iomanip>
#include <string>
#include <vector>

#include <GLFW/glfw3.h>

#if defined(_WIN32)
#  include <windows.h>
#  include <GL/glu.h>
#elif defined(__APPLE__)
#  include <OpenGL/glu.h>
#else
#  include <GL/glu.h>
#endif

/* Portable PI guarantee */
#ifndef M_PI
#  define M_PI 3.14159265358979323846
#endif

/* GL_MULTISAMPLE is core GL 1.3; guard for old Windows SDK headers */
#ifndef GL_MULTISAMPLE
#  define GL_MULTISAMPLE 0x809D
#endif

/* ============================================================
   GEOMETRY CONSTANTS
   ============================================================ */
static const float WHEEL_R = 0.18f;
static const float WHEEL_INNER = 0.14f;
static const float HUB_R = 0.022f;
static const float CHAINRING_R = 0.055f;
static const float CRANK_LEN = 0.072f;
static const float PEDAL_W = 0.040f;
static const float PEDAL_H = 0.012f;
static const int   SPOKE_COUNT = 8;
static const float WHEELBASE = 0.44f;
static const float BB_Y = -0.02f;

/* ============================================================
   MATH HELPERS
   ============================================================ */

static inline float toRad(float deg)
{
    return deg * static_cast<float>(M_PI) / 180.0f;
}

/* ============================================================
   DRAWING PRIMITIVES  (GL 1.x immediate mode)
   ============================================================ */

static void drawCircle(float cx, float cy, float r, int segs, bool filled)
{
    glBegin(filled ? GL_TRIANGLE_FAN : GL_LINE_LOOP);
    if (filled) glVertex2f(cx, cy);
    for (int i = 0; i <= segs; ++i) {
        float a = 2.0f * static_cast<float>(M_PI)
            * static_cast<float>(i) / static_cast<float>(segs);
        glVertex2f(cx + r * cosf(a), cy + r * sinf(a));
    }
    glEnd();
}

static void drawLine(float x1, float y1, float x2, float y2, float lw)
{
    glLineWidth(lw);
    glBegin(GL_LINES);
    glVertex2f(x1, y1);
    glVertex2f(x2, y2);
    glEnd();
}

static void drawRect(float cx, float cy, float w, float h)
{
    float hw = w * 0.5f, hh = h * 0.5f;
    glBegin(GL_QUADS);
    glVertex2f(cx - hw, cy - hh);
    glVertex2f(cx + hw, cy - hh);
    glVertex2f(cx + hw, cy + hh);
    glVertex2f(cx - hw, cy + hh);
    glEnd();
}

static void drawSpoke(float angleDeg, float r)
{
    float a = toRad(angleDeg);
    glBegin(GL_LINES);
    glVertex2f(0.0f, 0.0f);
    glVertex2f(r * cosf(a), r * sinf(a));
    glEnd();
}

/* ============================================================
   SCENE NODE
   ============================================================

   The SceneNode is the building block of the scene graph.

   Each node stores:
     localTransform[16]  — 4x4 column-major matrix, relative to parent
     children            — child nodes
     drawFn              — geometry callback (empty = no geometry)

   render(parentWorld):
     1.  world = parentWorld x localTransform   (cascade)
     2.  glLoadMatrix(world) + drawFn()          (draw)
     3.  recurse into children with 'world'      (propagate)

   Result: every descendant's world position is automatically
   correct when you move the root.
   ============================================================ */

struct SceneNode
{
    std::string  name;
    float        localTransform[16];
    std::vector<std::shared_ptr<SceneNode>> children;
    std::function<void()> drawFn;

    explicit SceneNode(const std::string& n = "node") : name(n)
    {
        setIdentity();
    }

    void setIdentity()
    {
        for (int i = 0; i < 16; ++i)
            localTransform[i] = (i % 5 == 0) ? 1.0f : 0.0f;
    }

    void setTranslate(float tx, float ty)
    {
        setIdentity();
        localTransform[12] = tx;
        localTransform[13] = ty;
    }

    void setRotateZ(float deg)
    {
        float a = toRad(deg);
        float c = cosf(a), s = sinf(a);
        setIdentity();
        localTransform[0] = c;  localTransform[4] = -s;
        localTransform[1] = s;  localTransform[5] = c;
    }

    /* Combined translate * rotateZ in one call */
    void setTranslateRotateZ(float tx, float ty, float deg)
    {
        float a = toRad(deg);
        float c = cosf(a), s = sinf(a);
        setIdentity();
        localTransform[0] = c;   localTransform[4] = -s;
        localTransform[1] = s;   localTransform[5] = c;
        localTransform[12] = tx;   localTransform[13] = ty;
    }

    /* Uniform scale + translate (used for bicycle zoom) */
    void setScaleTranslate(float sc, float tx, float ty)
    {
        setIdentity();
        localTransform[0] = sc;
        localTransform[5] = sc;
        localTransform[10] = sc;
        localTransform[12] = tx;
        localTransform[13] = ty;
    }

    std::shared_ptr<SceneNode> addChild(std::shared_ptr<SceneNode> child)
    {
        children.push_back(child);
        return child;
    }

    /* Multiply two 4x4 column-major matrices: R = A * B */
    static void matMul(const float* A, const float* B, float* R)
    {
        for (int row = 0; row < 4; ++row)
            for (int col = 0; col < 4; ++col) {
                float sum = 0.0f;
                for (int k = 0; k < 4; ++k)
                    sum += A[k * 4 + row] * B[col * 4 + k];
                R[col * 4 + row] = sum;
            }
    }

    /* Recursive render — cascades parent transform to all descendants */
    void render(const float* parentWorld = nullptr) const
    {
        float world[16];
        if (parentWorld)
            matMul(parentWorld, localTransform, world);
        else
            memcpy(world, localTransform, sizeof(world));

        glPushMatrix();
        glLoadMatrixf(world);
        if (drawFn) drawFn();
        glPopMatrix();

        for (size_t i = 0; i < children.size(); ++i)
            children[i]->render(world);
    }
};

/* ============================================================
   BUILD WHEEL SUB-GRAPH
   ============================================================ */

static std::shared_ptr<SceneNode> buildWheel(
    const std::string& nameStr,
    float rR, float rG, float rB,
    float hR, float hG, float hB)
{
    auto root = std::make_shared<SceneNode>(nameStr);

    /* Tyre */
    {
        auto n = std::make_shared<SceneNode>(nameStr + "_tyre");
        n->drawFn = []() {
            glColor3f(0.14f, 0.14f, 0.14f);
            drawCircle(0, 0, WHEEL_R, 64, true);
            glColor3f(0.24f, 0.24f, 0.24f);
            glLineWidth(1.4f);
            drawCircle(0, 0, WHEEL_R, 64, false);
            };
        root->addChild(n);
    }

    /* Rim */
    {
        float r = rR, g = rG, b = rB;
        auto n = std::make_shared<SceneNode>(nameStr + "_rim");
        n->drawFn = [r, g, b]() {
            glColor3f(r, g, b);
            drawCircle(0, 0, WHEEL_INNER, 64, true);
            };
        root->addChild(n);
    }

    /* Spokes */
    {
        auto n = std::make_shared<SceneNode>(nameStr + "_spokes");
        n->drawFn = []() {
            glColor3f(0.62f, 0.62f, 0.68f);
            glLineWidth(1.1f);
            for (int i = 0; i < SPOKE_COUNT; ++i)
                drawSpoke(static_cast<float>(i) * (360.0f / SPOKE_COUNT), WHEEL_INNER);
            };
        root->addChild(n);
    }

    /* Inner disc */
    {
        float r = rR * 0.55f, g = rG * 0.55f, b = rB * 0.55f;
        auto n = std::make_shared<SceneNode>(nameStr + "_inner");
        n->drawFn = [r, g, b]() {
            glColor3f(r, g, b);
            drawCircle(0, 0, HUB_R * 3.5f, 32, true);
            };
        root->addChild(n);
    }

    /* Hub */
    {
        float r = hR, g = hG, b = hB;
        auto n = std::make_shared<SceneNode>(nameStr + "_hub");
        n->drawFn = [r, g, b]() {
            glColor3f(r, g, b);
            drawCircle(0, 0, HUB_R, 20, true);
            };
        root->addChild(n);
    }

    return root;
}

/* ============================================================
   BICYCLE SCENE GRAPH
   ============================================================ */

struct BicycleGraph {
    std::shared_ptr<SceneNode> world;
    std::shared_ptr<SceneNode> bicycle;
    std::shared_ptr<SceneNode> rearWheel;
    std::shared_ptr<SceneNode> frontWheel;
    std::shared_ptr<SceneNode> chainring;
    std::shared_ptr<SceneNode> crankR;
    std::shared_ptr<SceneNode> crankL;
    std::shared_ptr<SceneNode> pedalR;
    std::shared_ptr<SceneNode> pedalL;
};

static BicycleGraph buildBicycle()
{
    BicycleGraph g;

    g.world = std::make_shared<SceneNode>("world");
    g.bicycle = std::make_shared<SceneNode>("bicycle");
    g.world->addChild(g.bicycle);

    /* Key positions relative to bicycle root */
    float rax = -WHEELBASE * 0.5f;
    float fax = WHEELBASE * 0.5f;
    float bbx = rax + 0.13f;
    float bby = BB_Y;
    float spx = bbx;
    float sptop = bby + 0.21f;
    float stemx = fax - 0.04f;
    float stemtop = sptop - 0.01f;

    /* ── Frame node ── */
    {
        auto frame = std::make_shared<SceneNode>("frame");

        /* Capture geometry values by value for the lambda */
        float _rax = rax, _fax = fax, _bbx = bbx, _bby = bby;
        float _spx = spx, _sptop = sptop, _stemx = stemx, _stemtop = stemtop;

        frame->drawFn = [_rax, _fax, _bbx, _bby, _spx, _sptop, _stemx, _stemtop]()
            {
                glColor3f(0.13f, 0.47f, 0.90f);
                drawLine(_rax, 0.0f, _bbx, _bby, 3.8f);
                drawLine(_spx, _bby, _spx, _sptop, 3.8f);
                drawLine(_spx, _sptop, _stemx, _stemtop, 3.2f);
                drawLine(_stemx, _stemtop - 0.04f, _bbx, _bby, 3.2f);
                drawLine(_fax, 0.0f, _stemx, _stemtop - 0.04f, 3.8f);
                glColor3f(0.10f, 0.38f, 0.78f);
                drawLine(_spx, _sptop, _rax, 0.0f, 2.2f);
            };
        g.bicycle->addChild(frame);

        /* Seat post */
        {
            auto sp = std::make_shared<SceneNode>("seat_post");
            sp->drawFn = []() {
                glColor3f(0.20f, 0.20f, 0.22f);
                drawRect(0.0f, 0.06f, 0.012f, 0.12f);
                };
            sp->setTranslate(spx, sptop - 0.10f);
            frame->addChild(sp);

            /* Saddle */
            auto saddle = std::make_shared<SceneNode>("saddle");
            saddle->drawFn = []() {
                glColor3f(0.10f, 0.10f, 0.10f);
                float piF = static_cast<float>(M_PI);
                glBegin(GL_TRIANGLE_FAN);
                glVertex2f(0.0f, 0.012f);
                for (int i = 0; i <= 32; ++i) {
                    float t = piF * static_cast<float>(i) / 32.0f;
                    float x = 0.09f * cosf(t + piF * 0.5f) - 0.01f;
                    float y = 0.017f * sinf(t + piF * 0.5f);
                    glVertex2f(x, y);
                }
                glEnd();
                };
            saddle->setTranslate(0.0f, 0.12f);
            sp->addChild(saddle);
        }

        /* Stem + handlebars */
        {
            auto stem = std::make_shared<SceneNode>("stem");
            stem->drawFn = []() {
                glColor3f(0.58f, 0.58f, 0.62f);
                drawRect(0.0f, 0.07f, 0.012f, 0.14f);
                };
            stem->setTranslate(stemx, stemtop - 0.04f);
            frame->addChild(stem);

            auto bars = std::make_shared<SceneNode>("handlebars");
            bars->drawFn = []() {
                glColor3f(0.55f, 0.55f, 0.60f);
                drawLine(-0.075f, 0.0f, 0.075f, 0.0f, 3.0f);
                drawLine(-0.075f, 0.0f, -0.075f, -0.042f, 2.5f);
                drawLine(0.075f, 0.0f, 0.075f, -0.042f, 2.5f);
                glColor3f(0.20f, 0.20f, 0.20f);
                drawCircle(-0.068f, -0.012f, 0.010f, 12, true);
                drawCircle(0.068f, -0.012f, 0.010f, 12, true);
                };
            bars->setTranslate(0.0f, 0.14f);
            stem->addChild(bars);
        }

        /* Bottom bracket + drivetrain */
        {
            auto bb = std::make_shared<SceneNode>("bottom_bracket");
            bb->setTranslate(bbx, bby);
            frame->addChild(bb);

            g.chainring = std::make_shared<SceneNode>("chainring");
            {
                float chainDx = rax - bbx;
                float cr = CHAINRING_R;
                g.chainring->drawFn = [chainDx, cr]()
                    {
                        glColor3f(0.78f, 0.68f, 0.18f);
                        glLineWidth(2.8f);
                        drawCircle(0.0f, 0.0f, cr, 40, false);
                        glLineWidth(1.2f);
                        drawCircle(0.0f, 0.0f, cr * 0.55f, 30, false);
                        glColor3f(0.55f, 0.50f, 0.15f);
                        drawCircle(0.0f, 0.0f, cr * 0.22f, 12, true);

                        float cassR = cr * 0.52f;
                        glColor3f(0.28f, 0.28f, 0.30f);
                        glLineWidth(2.0f);
                        glBegin(GL_LINES);
                        glVertex2f(0.0f, cr);    glVertex2f(chainDx, cassR);
                        glVertex2f(0.0f, -cr);    glVertex2f(chainDx, -cassR);
                        glEnd();

                        glColor3f(0.65f, 0.58f, 0.18f);
                        glLineWidth(1.6f);
                        glPushMatrix();
                        glTranslatef(chainDx, 0.0f, 0.0f);
                        drawCircle(0.0f, 0.0f, cassR, 24, false);
                        glPopMatrix();
                    };
            }
            bb->addChild(g.chainring);

            /* Crank R (right, inherits chainring rotation) */
            g.crankR = std::make_shared<SceneNode>("crank_r");
            g.crankR->drawFn = []() {
                glColor3f(0.38f, 0.38f, 0.42f);
                drawRect(CRANK_LEN * 0.5f, 0.0f, CRANK_LEN, 0.014f);
                };
            g.chainring->addChild(g.crankR);

            /* Pedal R */
            g.pedalR = std::make_shared<SceneNode>("pedal_r");
            g.pedalR->drawFn = []() {
                glColor3f(0.15f, 0.15f, 0.16f);
                drawRect(0.0f, 0.0f, PEDAL_W, PEDAL_H);
                };
            g.pedalR->setTranslate(CRANK_LEN, 0.0f);
            g.crankR->addChild(g.pedalR);

            /* Crank L (left, always 180 deg opposite) */
            g.crankL = std::make_shared<SceneNode>("crank_l");
            g.crankL->drawFn = []() {
                glColor3f(0.38f, 0.38f, 0.42f);
                drawRect(CRANK_LEN * 0.5f, 0.0f, CRANK_LEN, 0.014f);
                };
            g.crankL->setRotateZ(180.0f);
            g.chainring->addChild(g.crankL);

            /* Pedal L */
            g.pedalL = std::make_shared<SceneNode>("pedal_l");
            g.pedalL->drawFn = []() {
                glColor3f(0.15f, 0.15f, 0.16f);
                drawRect(0.0f, 0.0f, PEDAL_W, PEDAL_H);
                };
            g.pedalL->setTranslate(CRANK_LEN, 0.0f);
            g.crankL->addChild(g.pedalL);
        }
    }

    /* Rear wheel */
    g.rearWheel = buildWheel("rear_wheel",
        0.76f, 0.76f, 0.80f,
        0.52f, 0.52f, 0.56f);
    g.rearWheel->setTranslate(-WHEELBASE * 0.5f, 0.0f);
    g.bicycle->addChild(g.rearWheel);

    /* Front wheel */
    g.frontWheel = buildWheel("front_wheel",
        0.76f, 0.76f, 0.80f,
        0.52f, 0.52f, 0.56f);
    g.frontWheel->setTranslate(WHEELBASE * 0.5f, 0.0f);
    g.bicycle->addChild(g.frontWheel);

    return g;
}

/* ============================================================
   ANIMATION STATE
   ============================================================ */

struct AnimState {
    bool  paused;
    float time;
    float speed;
    float bikeX;
    float wheelAngle;
    float bgScroll;
    float zoom;

    AnimState()
        : paused(false), time(0.0f), speed(0.55f),
        bikeX(-0.80f), wheelAngle(0.0f), bgScroll(0.0f), zoom(1.0f)
    {
    }
};

/* ============================================================
   BACKGROUND + GROUND
   ============================================================ */

static void drawBackground(float scroll)
{
    glBegin(GL_QUADS);
    glColor3f(0.55f, 0.82f, 0.98f); glVertex2f(-2.0f, -1.0f); glVertex2f(2.0f, -1.0f);
    glColor3f(0.20f, 0.54f, 0.86f); glVertex2f(2.0f, 1.0f);  glVertex2f(-2.0f, 1.0f);
    glEnd();

    glColor3f(0.30f, 0.54f, 0.22f);
    glBegin(GL_QUADS);
    glVertex2f(-2.0f, -1.0f);   glVertex2f(2.0f, -1.0f);
    glVertex2f(2.0f, -WHEEL_R); glVertex2f(-2.0f, -WHEEL_R);
    glEnd();

    glColor3f(0.82f, 0.80f, 0.70f);
    float spacing = 0.26f;
    float offset = fmodf(scroll, spacing);
    for (int i = -15; i <= 15; ++i) {
        float x = static_cast<float>(i) * spacing - offset;
        drawLine(x, -WHEEL_R, x + 0.065f, -WHEEL_R, 2.0f);
    }
}

static void drawGround()
{
    glColor3f(0.24f, 0.22f, 0.18f);
    drawLine(-2.0f, -WHEEL_R, 2.0f, -WHEEL_R, 2.2f);
}

/* ============================================================
   LEGEND OVERLAY
   ============================================================ */

static void drawLegend()
{
    glMatrixMode(GL_PROJECTION);
    glPushMatrix(); glLoadIdentity(); glOrtho(-1, 1, -1, 1, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix(); glLoadIdentity();

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glColor4f(0.0f, 0.02f, 0.08f, 0.68f);
    glBegin(GL_QUADS);
    glVertex2f(-1.00f, -1.00f); glVertex2f(-0.46f, -1.00f);
    glVertex2f(-0.46f, -0.40f); glVertex2f(-1.00f, -0.40f);
    glEnd();
    glDisable(GL_BLEND);

    struct Swatch { float r, g, b; };
    static const Swatch sw[] = {
        {0.13f, 0.47f, 0.90f},
        {0.76f, 0.76f, 0.80f},
        {0.78f, 0.68f, 0.18f},
        {0.38f, 0.38f, 0.42f},
        {0.14f, 0.14f, 0.14f},
    };
    float bx = -0.96f, by = -0.44f;
    for (int i = 0; i < 5; ++i) {
        glColor3f(sw[i].r, sw[i].g, sw[i].b);
        glBegin(GL_QUADS);
        glVertex2f(bx, by);
        glVertex2f(bx + 0.046f, by);
        glVertex2f(bx + 0.046f, by + 0.028f);
        glVertex2f(bx, by + 0.028f);
        glEnd();
        by -= 0.074f;
    }

    glPopMatrix();
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
}

/* ============================================================
   KEYBOARD CALLBACK
   ============================================================ */

static AnimState* gState = nullptr;

static void keyCallback(GLFWwindow* window,
    int key, int /*scan*/, int action, int /*mods*/)
{
    if ((action != GLFW_PRESS && action != GLFW_REPEAT) || !gState) return;
    switch (key) {
    case GLFW_KEY_SPACE:
        gState->paused = !gState->paused; break;
    case GLFW_KEY_R:
        gState->time = 0.0f; gState->bikeX = -0.80f;
        gState->wheelAngle = 0.0f; gState->bgScroll = 0.0f; break;
    case GLFW_KEY_RIGHT:
        gState->speed = (std::min)(gState->speed + 0.10f, 2.0f); break;
    case GLFW_KEY_LEFT:
        gState->speed = (std::max)(gState->speed - 0.10f, 0.05f); break;
    case GLFW_KEY_EQUAL:
    case GLFW_KEY_KP_ADD:
        gState->zoom = (std::min)(gState->zoom + 0.10f, 3.0f); break;
    case GLFW_KEY_MINUS:
    case GLFW_KEY_KP_SUBTRACT:
        gState->zoom = (std::max)(gState->zoom - 0.10f, 0.30f); break;
    case GLFW_KEY_ESCAPE:
    case GLFW_KEY_Q:
        glfwSetWindowShouldClose(window, GLFW_TRUE); break;
    default: break;
    }
}

/* ============================================================
   MAIN
   ============================================================ */

int main()
{
    if (!glfwInit()) return -1;

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 2);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 1);
    glfwWindowHint(GLFW_SAMPLES, 4);

    GLFWwindow* window = glfwCreateWindow(
        1100, 640, "Bicycle Scene Graph  -  OpenGL / GLFW", nullptr, nullptr);
    if (!window) { glfwTerminate(); return -1; }

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    BicycleGraph scene = buildBicycle();

    AnimState state;
    gState = &state;
    glfwSetKeyCallback(window, keyCallback);

    glEnable(GL_MULTISAMPLE);
    glEnable(GL_LINE_SMOOTH);
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    /* Rotation rate: full circle per wheel circumference */
    float degPerUnit = 180.0f / (static_cast<float>(M_PI) * WHEEL_R);

    double prevTime = glfwGetTime();

    while (!glfwWindowShouldClose(window))
    {
        glfwPollEvents();

        double now = glfwGetTime();
        float  dt = static_cast<float>(now - prevTime);
        prevTime = now;
        if (dt > 0.05f) dt = 0.05f;

        /* Update animation */
        if (!state.paused) {
            state.time += dt;
            state.bikeX += state.speed * dt;
            state.bgScroll += state.speed * dt;
            state.wheelAngle += state.speed * dt * degPerUnit;
            if (state.bikeX > 1.25f) state.bikeX = -1.25f;
        }

        float bob = sinf(state.time * 4.6f) * 0.0028f;

        /* ── Update scene graph transforms ──
           Only the nodes whose transforms changed need updating.
           All descendants stay correct automatically.           */

        scene.bicycle->setScaleTranslate(state.zoom, state.bikeX, bob);

        float wa = -state.wheelAngle;
        scene.rearWheel->setTranslateRotateZ(-WHEELBASE * 0.5f, 0.0f, wa);
        scene.frontWheel->setTranslateRotateZ(WHEELBASE * 0.5f, 0.0f, wa);

        float ca = state.wheelAngle * 1.8f;   /* 1.8x gear ratio */
        scene.chainring->setRotateZ(ca);

        scene.crankL->setRotateZ(180.0f);      /* always opposite crankR */

        /* Pedals counter-rotate to stay horizontal — parent-cancel trick */
        scene.pedalR->setTranslateRotateZ(CRANK_LEN, 0.0f, -ca);
        scene.pedalL->setTranslateRotateZ(CRANK_LEN, 0.0f, -ca);

        /* Render */
        int fbW = 0, fbH = 0;
        glfwGetFramebufferSize(window, &fbW, &fbH);
        glViewport(0, 0, fbW, fbH);
        glClearColor(0.53f, 0.82f, 0.98f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        float aspect = (fbH > 0)
            ? (static_cast<float>(fbW) / static_cast<float>(fbH))
            : 1.0f;
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-aspect, aspect, -1.0, 1.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        drawBackground(state.bgScroll);
        drawGround();

        /* ── Scene graph traversal ── */
        scene.world->render();

        drawLegend();

        std::ostringstream oss;
        oss << "Bicycle Scene Graph  |  "
            << (state.paused ? "PAUSED" : "RUNNING")
            << "  |  Speed: " << std::fixed << std::setprecision(2) << state.speed
            << "  |  Zoom: " << std::fixed << std::setprecision(1) << state.zoom
            << "x  |  SPACE=pause  Arrows=speed  +/-=zoom  R=reset  Q=quit";
        glfwSetWindowTitle(window, oss.str().c_str());

        glfwSwapBuffers(window);
    }

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}