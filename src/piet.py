from enum import Enum

PIET_COMMANDS = {
    "push": (0, 1),
    "pop": (0, 2),
    "add": (1, 0),
    "subtract": (1, 1),
    "multiply": (1, 2),
    "divide": (2, 0),
    "mod": (2, 1),
    "not": (2, 2),
    "greater": (3, 0),
    "pointer": (3, 1),
    "switch": (3, 2),
    "duplicate": (4, 0),
    "roll": (4, 1),
    "in_number": (4, 2),
    "in_char": (5, 0),
    "out_number": (5, 1),
    "out_char": (5, 2)
}

class PietColor(Enum):
    LIGHT_RED = 0xffc0c0
    RED = 0xff0000
    DARK_RED = 0xc00000

    LIGHT_YELLOW = 0xffffc0
    YELLOW = 0xffff00
    DARK_YELLOW = 0xc0c000

    LIGHT_GREEN = 0xc0ffc0
    GREEN = 0x00ff00
    DARK_GREEN = 0x00c000

    LIGHT_CYAN = 0xc0ffff
    CYAN = 0x00ffff
    DARK_CYAN = 0x00c0c0

    LIGHT_BLUE = 0xc0c0ff
    BLUE = 0x0000ff
    DARK_BLUE = 0x0000c0

    LIGHT_MAGENTA = 0xffc0ff
    MAGENTA = 0xff00ff
    DARK_MAGENTA = 0xc000c0

    WHITE = 0xffffff
    BLACK = 0x000000

    @staticmethod
    def shift(color, hue_shift, light_shift):
        all_colors = list(PietColor)
        index = all_colors.index(color)

        new_index = (index + (hue_shift % 6) * 3) % 18
        current_light_shift = new_index % 3
        new_index += -current_light_shift + (current_light_shift + light_shift) % 3

        return all_colors[new_index]
    
    @staticmethod
    def assign_all_properties():
        for color in PietColor:
            for command in PIET_COMMANDS:
                hue_shift, light_shift = PIET_COMMANDS[command]
                setattr(color, command, PietColor.shift(color, hue_shift, light_shift))
                setattr(color, f"backwards_{command}", PietColor.shift(color, -hue_shift, -light_shift))

    @property
    def rgb(self):
        return (
            (self.value & 0xff0000) >> 16,
            (self.value & 0x00ff00) >> 8,
            (self.value & 0x0000ff)
        )

PietColor.assign_all_properties()

def piet_main():
    print(PietColor.LIGHT_RED.rgb)

if __name__ == "__main__":
    piet_main()
