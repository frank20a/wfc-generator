from asyncio import QueueEmpty
from msilib.schema import CheckBox
from tkinter import *
# from tkinter.ttk import *
import numpy as np
import os, sys, json, random
from PIL import Image, ImageTk, ImageDraw
from time import time

# Constants
# ========================================================
R = 0
L = 2
T = 3
B = 1
OPP = {R: L, L: R, T: B, B: T}

# Classes
# ========================================================

class Tile:
    def __init__(self, img, name, slots):
        self.img = img
        self.tkimg = ImageTk.PhotoImage(img)
        self.name = name
        self.slots = slots
   
class Pack:
    def __init__(self, pack_name):
        path = os.path.join(os.getcwd(), "packs", pack_name)
        with open(os.path.join(path, 'pack.json')) as f:
            j = json.load(f)
            
        self.name = j['pack_name']
        self.tiles_width = j['tiles_width']
        self.tiles_height = j['tiles_height']
        self.tiles = {}
        
        for tile in j['tiles']:
            img = Image.open(os.path.join(path, tile['filename']))
                             
            for i in range(4):
                if i in tile['rotations']:
                    t = Tile(img, f'{tile["filename"].split(".")[0]}_{i}', tile['slots'])
                    self.tiles[t.name] = t
                img = img.rotate(-90, expand=True)
                tile['slots'] = [tile['slots'][-1]] + tile['slots'][:-1]
                
        try:
            self.compatible = j['compatible_slots']
        except:
            self.compatible = [[i, i] for i in range(15)]
    
    def __str__(self) -> str:
        return f'{self.name} ({", ".join(self.tiles.keys())})'
    
    def get_from_name(self, name: str) -> Tile:
        return self.tiles[name]
    
    def tile_list(self) -> list:
        return list(self.tiles.keys())
    
    def is_compatible(self, one, other, direction) -> bool:
        if type(one) is not Tile: 
            one = self.get_from_name(one)
            
        if type(other) is not Tile:
            other = self.get_from_name(other)
        
        return ([one.slots[OPP[direction]], other.slots[direction]] in self.compatible) or ([other.slots[direction], one.slots[OPP[direction]]] in self.compatible)
    
    def is_any_compatible(self, one, others, direction) -> bool:
        for other in others:
            if self.is_compatible(one, other, direction):
                return True
        return False
    
    def __int__(self):
        return len(self.tiles)
    
class App(Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.minsize(600, 400)
        self.maxsize(600, 400)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.title("Wave Function Collapse: Map Generator - by @frank20a")
        
        top = Frame(self)
        
        # Sidebar
        sidebar = Frame(top, bg='grey')
        
        self.pack_string = Entry(sidebar, width=20)
        self.pack_string.pack(side=TOP, padx=10, pady=10)
        
        Button(sidebar, text="Start WFC", command=self.on_start_wfc).pack(side=TOP, padx=10, pady=10)
        
        tmp = Frame(sidebar, bg='grey')
        Label(tmp, text="X:", bg='grey').pack(side=LEFT)
        self.x = Entry(tmp, width=5)
        self.x.insert(END, '20')
        self.x.pack(side=LEFT, padx=2)
        Label(tmp, text="Y:", bg='grey').pack(side=LEFT)
        self.y = Entry(tmp, width=5)
        self.y.insert(END, '20')
        self.y.pack(side=LEFT, padx=2)
        tmp.pack(side=TOP, padx=10, pady=10)
        
        self.outflag = IntVar()
        Checkbutton(sidebar, text="Output frames:", variable=self.outflag).pack(side=LEFT)
        
        sidebar.pack(side=LEFT, fill=BOTH)
        
        # Canvas
        self.canvas = Canvas(top, bg='#a0ff8f')
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Console
        top.pack(side=TOP, fill=BOTH, expand=True)
        self.console = Text(self, height=4, state=DISABLED)
        self.console.pack(side=TOP, fill=X)
        
        self.collapsed = 0
        self.w, self.h = 0, 0
        self.board = []
        self.pack = None
        self.__running__ = True
        self.__generating__ = False
        self.__outfolder__ = None
    
    def rand_collapse(self, x, y):
        index = y * self.w + x
        self.sort_board_position()
        
        if self.board[index]['collapsed']:
            return
        try:
            # for i in range(1000 * int(self.pack)):
            #     tmp = random.choice(self.board[index]['candidates'])
                
            #     # V A R I E M A I   na ftiajw to index error poy baraei to is_any_compatible sta bounds tou board
            #     try:
            #         if self.pack.is_any_compatible(tmp, self.board[y * self.w + x-1]['candidates'], L) and self.pack.is_any_compatible(tmp, self.board[y * self.w + x+1]['candidates'], R) and self.pack.is_any_compatible(tmp, self.board[(y-1) * self.w + x]['candidates'], T) and self.pack.is_any_compatible(tmp, self.board[(y+1) * self.w + x]['candidates'], B):
            #             self.board[index]['candidates'] = [tmp]
            #             break
            #     except IndexError:
            #         self.board[index]['candidates'] = [tmp]
            #         break
            # else:
            #     tmp = random.choice(self.board[index]['candidates'])
            #     self.board[index]['candidates'] = [tmp]
            tmp = random.choice(self.board[index]['candidates'])
            self.board[index]['candidates'] = [tmp]
        except IndexError:
            print(x, y, index, self.board[index])
        self.board[index]['collapsed'] = True
        self.propagate(self.board[index]['x'], self.board[index]['y'])
                
    def cout(self, msg):
        self.console.config(state=NORMAL)
        self.console.insert(END, '\n' + msg)
        self.console.config(state=DISABLED)
        self.console.see(END)

    def sort_board_collapsed(self):
        self.board.sort(key=lambda t: -float('inf') if t['collapsed'] else float('inf'))
        
    def sort_board_position(self):
        self.board.sort(key=lambda t: t['y'] * self.w + t['x'])
        
    def sort_board_entropy(self):
        self.board.sort(key=lambda t: len(t['candidates']) if not t['collapsed'] else float('inf'))
    
    def propagate_part(self, x, y, xx, yy, dir) -> bool:
        if self.board[yy * self.w + xx]['collapsed'] or len(self.board[yy * self.w + xx]['candidates']) < 2:
            return False
        
        q = []
        for cand2 in self.board[yy * self.w + xx]['candidates']:
            c = 0
            for cand1 in self.board[y * self.w + x]['candidates']:
                if not self.pack.is_compatible(cand1, cand2, dir):
                    c += 1

            if c == len(self.board[y * self.w + x]['candidates']):
                q.append(cand2)

        if len(q) > 0:
            for cand in q:
                self.board[yy * self.w + xx]['candidates'].remove(cand)
            if len(self.board[yy * self.w + xx]['candidates']) < 2:
                return False
            return True

        return False
    
    def propagate(self, x: int, y: int, queue: list = [], visited: list = [], depth: int = 0):
        self.sort_board_position()
        
        if len(self.board[y * self.w + x]['candidates']) == int(self.pack):
            if len(queue) > 0:
                self.propagate(queue[0][0], queue[0][1], queue[1:], visited, depth + 1)
            return
        if (x, y) not in visited:
            visited.append((x, y))
            
        try: 
            if x > 0 and self.propagate_part(x, y, x - 1, y, L):
                if (x - 1, y) not in queue:
                    queue.append((x - 1, y))
                    # visited.append((x - 1, y))
        except IndexError as e:
            print(e)
            input(f" LEFT {x} {y}")

        try:
            if x < self.w - 1 and self.propagate_part(x, y, x + 1, y, R):
                if (x + 1, y) not in queue:
                    queue.append((x + 1, y))
                    # visited.append((x + 1, y))
        except IndexError as e:
            print(e)
            input(f" RIGHT {x} {y}")
        
        try:
            if y > 0 and self.propagate_part(x, y, x, y - 1, T):
                if (x, y - 1) not in queue:
                    queue.append((x, y - 1))
                    # visited.append((x, y - 1))
        except IndexError as e:
            print(e)
            input(f" TOP {x} {y}")
        
        try:
            if y < self.h - 1 and self.propagate_part(x, y, x, y + 1, B):
                if (x, y + 1) not in queue:
                    queue.append((x, y + 1))
                    # visited.append((x, y + 1))
        except IndexError as e:
            print(e)
            input(f" BOTTOM {x} {y}")
            
        if len(queue) > 0:
            self.propagate(queue[0][0], queue[0][1], queue[1:], visited, depth + 1)
        # else:
        #     print(f"{depth}")
    
    def update(self):
        if self.__generating__:
            self.sort_board_entropy()
                      
            if self.board[0]['collapsed']:
                self.__generating__ = False
                self.cout("Finished")
            else:
                if len(self.board[0]['candidates']) == 1:
                    self.board[0]["collapsed"] = True
                    self.propagate(self.board[0]['x'], self.board[0]['y'])
                else:
                    i = 1
                    tmp = len(self.board[0]['candidates'])
                    while len(self.board[i]['candidates']) == tmp:
                        i += 1
                    
                    c = random.randint(0, i-1)
                    self.rand_collapse(self.board[c]['x'], self.board[c]['y'])
        
        
            self.draw()
        
        super().update()
    
    def draw(self):
        self.sort_board_entropy()
        
        if self.__outfolder__ is not None or self.board[0]['collapsed']:
            output = Image.new("RGB", ((self.w + 1) * self.pack.tiles_width, (self.h+1) * self.pack.tiles_height), (0,0,0))
            
        self.canvas.delete(ALL)
        for x in range(self.w + 1):
            self.canvas.create_line(x * self.pack.tiles_width, 0 * self.pack.tiles_height, x * self.pack.tiles_width, self.h * self.pack.tiles_height, fill="black")
        for y in range(self.h + 1):
            self.canvas.create_line(0 * self.pack.tiles_width, y * self.pack.tiles_height, self.w * self.pack.tiles_width, y * self.pack.tiles_height, fill="black")
            
        for tile in self.board:
            if tile is not None:
                if tile['collapsed']:
                    try:
                        self.canvas.create_image(int((tile['x'] + .5) * self.pack.tiles_width), int((tile['y'] + .5) * self.pack.tiles_height), image=self.pack.get_from_name(tile['candidates'][0]).tkimg)
                        
                        if self.__outfolder__ is not None or self.board[0]['collapsed']: 
                            output.paste(self.pack.get_from_name(tile['candidates'][0]).img, (int((tile['x'] + .5) * self.pack.tiles_width), int((tile['y'] + .5) * self.pack.tiles_height)))
                    except IndexError as e:
                        print(e)
                else:
                    self.canvas.create_text(int((tile['x'] + .5) * self.pack.tiles_width), int((tile['y'] + .5) * self.pack.tiles_height), fill="darkblue", font="Times 10",
                        text=str(len(tile['candidates'])))
                    
        if self.__generating__:
            if self.__outfolder__ is not None:
                output.save(os.path.join(os.getcwd(), self.__outfolder__, f'{self.__iter__}.png'))
            if self.board[0]['collapsed']:
                output.save(os.path.join(os.getcwd(), f'{int(time())}.png'))
                self.cout(f'Saved as {int(time())}.png')
            self.__iter__ += 1
    
    def on_start_wfc(self):        
        # Get Pack
        pack = self.pack_string.get()
        if pack == "":
            self.cout("No pack selected")
            return
        try:
            self.pack = Pack(pack)
            self.cout(f'Pack loaded: {self.pack}')
        except (FileNotFoundError, ) as e:
            self.cout(f'Error: {e}')
            return
        
        # Get Dimensions
        try:
            self.w, self.h = int(self.x.get()), int(self.y.get())
        except (ValueError, ) as e:
            self.cout(f"Can't get board size: {e}")
            return
        
        sys.setrecursionlimit(self.w * self.h)
        self.minsize(self.w * self.pack.tiles_width + 150, self.h * self.pack.tiles_height + 70)
        self.maxsize(self.w * self.pack.tiles_width + 150, self.h * self.pack.tiles_height + 70)
        
        self.cout(f'Starting WFC - Board size: {self.w}x{self.h}')
        self.board = [{'x': x, 'y': y, 'candidates': self.pack.tile_list(), 'collapsed': False} for y in range(self.h) for x in range(self.w)]
        self.rand_collapse(random.randint(0, self.w - 1), random.randint(0, self.h - 1))
        if self.outflag.get():
            self.__outfolder__ = str(int(time()))
            os.mkdir(os.path.join(os.getcwd(), self.__outfolder__))
        else:
            self.__outfolder__ = None
        self.__iter__ = 0
        self.__generating__ = True
        
    def mainloop(self):
        while self.__running__:
            self.update()
        self.cleanup()
    
    def on_close(self):
        self.__running__ = False
        super().quit()
        self.destroy()
    
    def cleanup(self):
        pass
                
                
if __name__ == '__main__':
    app = App()
    app.mainloop()       