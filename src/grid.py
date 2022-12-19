import numpy as np
from PIL import Image
from enum import IntEnum

from .piet import PietColor

class Direction(IntEnum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

DXY = [(0, -1), (1, 0), (0, 1), (-1, 0)]

class PietPainter:
    def __init__(self, grid, x, y):
        self.__grid = grid
        self.__x = x
        self.__y = y
        self.__direction = Direction.RIGHT
    
    def get_x(self):
        return self.__x
    def get_y(self):
        return self.__y
    def get_xy(self):
        return self.__x, self.__y

    def move_to(self, x=None, y=None):
        if x is not None:
            self.__x = x
        if y is not None:
            self.__y = y
        return self
    
    def move(self, dx, dy):
        self.__x += dx
        self.__y += dy
        return self
    
    def forward(self, amount=1):
        dx, dy = DXY[self.__direction]
        self.__x += dx * amount
        self.__y += dy * amount
        return self
    
    def turn_right(self):
        self.__direction = (self.__direction + 1) % 4
        return self
    
    def turn_left(self):
        self.__direction = (self.__direction - 1) % 4
        return self
    
    def face(self, direction):
        self.__direction = direction
        return self
    
    def paint(self, commands):
        if isinstance(commands, str):
            commands = commands.split()
        color = self.__grid.get(self.__x, self.__y)
        if color == PietColor.BLACK:
            raise Exception("Cannot paint over black")
        if color == PietColor.WHITE:
            color = PietColor.LIGHT_RED
            self.__grid.insert(self.__x, self.__y, color)
        for i in range(len(commands) + 1):
            color_in_grid = self.__grid.get(self.__x, self.__y)
            if color_in_grid != color and color_in_grid != PietColor.WHITE:
                print("Warning: overwriting non-white color")
            self.__grid.insert(self.__x, self.__y, color)
            if i < len(commands):
                self.forward()
                color = getattr(color, commands[i])
        return self
    
    def dot(self, color="black"):
        self.__grid.insert(self.__x, self.__y, color)
        return self
    
    def dots(self, dxys, color="black"):
        ox, oy = self.__x, self.__y
        for dx, dy in dxys:
            self.move_to(ox + dx, oy + dy)
            self.dot(color)
        self.move_to(ox, oy)
        return self

    def dots_str(self, pattern, colors="black"):
        dxys = {}
        if isinstance(colors, str):
            colors = colors.split()
        if isinstance(pattern, str):
            pattern = pattern.strip("\r\n").splitlines()
        origin = (0, 0)
        for y, row in enumerate(pattern):
            for x, c in enumerate(row):
                if c == "O":
                    origin = (x, y)
                if c.isdigit():
                    num = int(c)
                    dxys[num] = dxys.get(num, []) + [(x, y)]
        ox, oy = self.__x, self.__y
        self.move(-origin[0], -origin[1])
        for num, color in enumerate(colors):
            points = dxys.get(num, [])
            if not points:
                print("Warning: no points for color", color)
            self.dots(points, color)
        self.move_to(ox, oy)
        return self


class PietGrid:
    def __init__(self):
        self.__grid = {}

    def insert(self, x, y, color):
        if isinstance(color, str):
            color = PietColor[color.upper()]
        self.__grid[(x, y)] = color
        return self
    
    def get(self, x, y):
        return self.__grid.get((x, y), PietColor.WHITE)
    
    def get_painter(self, x=0, y=0) -> PietPainter:
        return PietPainter(self, x, y)
    
    def get_max_x(self):
        return max(x for x, _ in self.__grid.keys())
    
    def get_max_y(self, x = None):
        if isinstance(x, int):
            x = (x,)
        return max(ky for kx, ky in self.__grid.keys() if x is None or kx in x)

    def get_size(self):
        return self.get_max_x() + 1, self.get_max_y() + 1
    
    def get_rgb_grid(self):
        width, height = self.get_size()
        rgb_grid = []
        for y in range(height):
            rgb_row = []
            for x in range(width):
                rgb_row.append(self.get(x, y).rgb)
            rgb_grid.append(rgb_row)
        return rgb_grid
    
    def get_image(self):
        return Image.fromarray(np.asarray(self.get_rgb_grid(), dtype=np.uint8), "RGB")
    
    def is_noop_path(self, sx, sy, direction, ex=None, ey=None):
        cx, cy = sx, sy
        dx, dy = DXY[direction]
        while cx != ex and cy != ey:
            nx, ny = cx + dx, cy + dy
            cp = self.get(cx, cy)
            np = self.get(nx, ny)
            if cp == PietColor.BLACK or np == PietColor.BLACK:
                return False
            if cp != PietColor.WHITE and np != PietColor.WHITE:
                return False
            cx, cy = nx, ny
        return True

def grid_main():
    STOPPER = "00O00\n01110\n00000"
    grid = PietGrid()
    painter = grid.get_painter()
    painter.paint(["push", "not", "push", "duplicate", "add", "duplicate", "duplicate", "add", "duplicate", "out_number", "duplicate", "add", "add", "out_char", "push", "pointer"])
    painter.turn_right().forward(5).dots_str(STOPPER, "black light_red")


    img = grid.get_image()
    img.save("grid.png")
    scale_amount = 10
    img = img.resize((img.width * scale_amount, img.height * scale_amount), Image.Resampling.NEAREST)
    img.save("grid_scaled.png")

if __name__ == "__main__":
    grid_main()
