import tkinter as tk

class BSPVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("BSP Tree: Minimum Additions (N=2, Added=0)")
        
        self.canvas = tk.Canvas(root, width=600, height=400, bg="black")
        self.canvas.pack()

        # 1. Draw Coordinate Grid (like your screenshot)
        for i in range(0, 600, 50):
            self.canvas.create_line(i, 0, i, 400, fill="#222")
            self.canvas.create_line(0, i, 600, i, fill="#222")

        # 2. Define N=2 Triangles (Green and Blue)
        # Positioned so they do NOT straddle the center line
        tri1 = [100, 100, 200, 100, 150, 200] # Left side
        tri2 = [400, 200, 500, 200, 450, 300] # Right side
        
        self.canvas.create_polygon(tri1, outline="lime", fill="", width=2)
        self.canvas.create_polygon(tri2, outline="cyan", fill="", width=2)

        # 3. Draw the Partitioning Plane (The Splitter)
        # We pick X = 300 as the splitter
        self.canvas.create_line(300, 0, 300, 400, fill="red", dash=(5,5), width=2)
        
        # 4. Logic Display
        info_text = (
            "Total Triangles (N): 2\n"
            "Splitter: Red Dashed Line\n"
            "Triangles Straddling Plane: 0\n"
            "Triangles Added: 0 (Minimum Case)"
        )
        self.canvas.create_text(150, 350, text=info_text, fill="white", justify="left")

if __name__ == "__main__":
    root = tk.Tk()
    app = BSPVisualizer(root)
    root.mainloop()