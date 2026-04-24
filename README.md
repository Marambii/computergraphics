# Computer Graphics Data Structures
## Group 3
## SCT211-0024/2023 & SCT211-0433/2023
## Nevean Adhiambo
## Baruch Marambi


In computer graphics, efficiently managing spatial data, object relationships, and geometric primitives is critical for real-time rendering and physical simulation.  

This technical report outlines three foundational data structures:

- Binary Space Partitioning (BSP) Trees  
- Scene Graphs  
- Triangular Meshes  

---

## 1. Binary Space Partitioning (BSP) Trees

### Definition
A BSP tree is a hierarchical, recursive decomposition of *n-dimensional space* into convex sets using hyperplanes.  

In 3D graphics, these hyperplanes are 2D planes used to divide space into **front** and **back** regions.

### Implementation Details

- **Recursive Partitioning**  
  A root polygon is selected as the partitioning plane. Other polygons are classified as:
  - In front of the plane  
  - Behind the plane  

- **Tree Structure**  
  - Internal nodes → partitioning planes  
  - Leaf nodes → convex regions or polygons  

- **Spatial Sorting**  
  Traversing the tree based on the viewer’s position enables correct rendering order:
  - Back-to-front  
  - Front-to-back  

### Primary Use Cases

- **Visibility Determination**  
  Solves the *Hidden Surface Problem* by rendering objects in correct depth order  

- **Collision Detection**  
  Efficiently determines intersections in complex environments  

---

## 2. Scene Graphs

### Definition
A Scene Graph is a hierarchical structure (tree or graph) that organizes the logical and spatial relationships in a scene.

It defines **parent-child relationships** for transformations and attributes.

### Implementation Details

- **Node Types**
  - Transformation Nodes (position, rotation, scale)  
  - Geometry Nodes (meshes)  
  - Property Nodes (materials, lighting)  

- **Transformation Inheritance**  
  A child node’s global transformation is computed as:
