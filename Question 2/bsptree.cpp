#include <GL/glut.h>
#include <vector>
#include <iostream>
#include <cmath>

// Simple 2D Vector
struct Vec2 {
    float x, y;
};

// Triangle structure
struct Triangle {
    Vec2 a, b, c;
    int id;
};

// Line equation: ax + by + c = 0
struct Plane {
    float a, b, c;
};

// Global data for the demo
std::vector<Triangle> triangles;
std::vector<Plane> splittingPlanes;

// Function to create a plane (line) from two points
Plane fromTwoPoints(Vec2 p1, Vec2 p2) {
    float dx = p2.x - p1.x;
    float dy = p2.y - p1.y;
    float nx = -dy;
    float ny = dx;
    float len = sqrt(nx * nx + ny * ny);
    nx /= len; ny /= len;
    return { nx, ny, -(nx * p1.x + ny * p1.y) };
}

void init() {
    glClearColor(1.0, 1.0, 1.0, 1.0); // White background
    glMatrixMode(GL_PROJECTION);
    gluOrtho2D(-2, 8, -2, 8); // Set coordinate system

    // Setup Case: Minimum Extra Triangles
    Triangle t1 = { {0,0}, {2,0}, {1,2}, 1 };
    Triangle t2 = { {4,0}, {6,0}, {5,2}, 2 };
    
    triangles.push_back(t1);
    triangles.push_back(t2);

    // In a BSP build, the first triangle's edge becomes the split plane
    splittingPlanes.push_back(fromTwoPoints(t1.a, t1.b));
}

void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // 1. Draw Triangles (Blue)
    glColor3f(0.0, 0.5, 1.0);
    for (const auto& tri : triangles) {
        glBegin(GL_TRIANGLES);
            glVertex2f(tri.a.x, tri.a.y);
            glVertex2f(tri.b.x, tri.b.y);
            glVertex2f(tri.c.x, tri.c.y);
        glEnd();
        
        // Outline for clarity
        glColor3f(0.0, 0.0, 0.0);
        glBegin(GL_LINE_LOOP);
            glVertex2f(tri.a.x, tri.a.y);
            glVertex2f(tri.b.x, tri.b.y);
            glVertex2f(tri.c.x, tri.c.y);
        glEnd();
        glColor3f(0.0, 0.5, 1.0);
    }

    // 2. Draw Splitting Planes (Dashed Red Lines)
    glEnable(GL_LINE_STIPPLE);
    glLineStipple(1, 0xF0F0); 
    glColor3f(1.0, 0.0, 0.0);
    glLineWidth(2.0);

    for (const auto& p : splittingPlanes) {
        glBegin(GL_LINES);
            // Draw a long line based on the plane equation ax + by + c = 0
            if (abs(p.b) > 0.001) {
                glVertex2f(-2, (-p.a * -2 - p.c) / p.b);
                glVertex2f(8, (-p.a * 8 - p.c) / p.b);
            } else { // Vertical line
                glVertex2f(-p.c / p.a, -2);
                glVertex2f(-p.c / p.a, 8);
            }
        glEnd();
    }
    glDisable(GL_LINE_STIPPLE);

    glFlush();
}

int main(int argc, char** argv) {
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB);
    glutInitWindowSize(600, 600);
    glutCreateWindow("BSP Minimum Split Visualisation");
    init();
    glutDisplayFunc(display);
    glutMainLoop();
    return 0;
}