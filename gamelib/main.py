'''Game main module.

Contains the entry point used by the run_game.py script.

Feel free to put all your game code here, or in other modules in this "gamelib"
package.
'''

from pyglet.gl import *
import pyglet
import cocos
from cocos.director import director

from game_scene import *
from menu_scene import *

import data

def main():

    pyglet.resource.path.append('data')
    pyglet.resource.reindex()
    font.add_directory('data')
    font.add_directory('data/fonts')

    director.init( width=800, height=600)
    director.set_depth_test(True)

    s = get_menu_scene()
#    s = get_game_scene()
    director.run (s)
