
# This code is so you can run the samples without installing the package

#python
import random
import math

#cocos + pyglet
import cocos
from cocos.director import director
from cocos.layer import *
from cocos.scene import Scene
from cocos.scenes.transitions import *
from cocos.actions import *
from cocos.sprite import *
from cocos.menu import *
from cocos.text import *

import pyglet
from pyglet import gl, font
from pyglet.window import key

# squirtle
import squirtle
import squirtle_cocos_adaptor as sqa

#locals
import soundex
import state
import levels
import hiscore
import gradient_layer
import data
import menu_scene


FONT_NAME_TITLE = "Gas Huffer Phat"
FONT_NAME_MENU = "Gas"

COLOR_WHITE = (255,255,255,255)
class IntroLayer( Layer ):

    is_event_handler = True     #: enable pyglet's events

    def __init__(self):
        super( IntroLayer, self ).__init__()

        w,h = director.get_window_size()
        self.font_title = {}

        # you can override the font that will be used for the title and the items
        self.font_title['font_name'] = FONT_NAME_TITLE
        self.font_title['font_size'] = 26
#        self.font_title['color'] = (204,164,164,255)
        self.font_title['color'] = COLOR_WHITE
        self.font_title['anchor_y'] ='top'
        self.font_title['anchor_x'] ='right'
        title = Label('A SOUND LOVE STORY', **self.font_title )
        title.position=(w-10,34)
        self.add(title,z=1)

        self.sound_fart = soundex.load('sounds/fart_01.mp3')

        self.schedule_interval( self.gasman_appear, 0.1 )

        sprite = sqa.SVG_CacheNode()
        node= sqa.SVGnode( data.filepath("sprites/gasman-character.svg") )
        sprite.add(node)
        self.add( sprite)
        self.gasman_sprite = sprite
        self.gasman_sprite.position = (-50, 200)


    def gasman_appear( self, dt ):
        self.unschedule( self.gasman_appear )
        self.gasman_sprite.do( MoveBy( (450,0), duration=2 ) )
        self.gasman_sprite.do( RotateBy(360*3, duration=2 ) + CallFunc( self.dialog ) ) 

    def dialog( self ):
        sprite = Sprite('intro.png')
        sprite.anchor_image = (0,0)
        sprite.opacity = 0
        sprite.do( FadeIn(0.5) )
        self.add( sprite, name='intro' )
        sprite.position = (500,350)

        self.gasman_sprite.do(
                    Delay(4) +
                    CallFunc( self.remove_intro) +
                    (CallFunc( self.play_sound ) | Accelerate( MoveBy( (0,500), 1 ) )) +
                    CallFunc( self.call_menu_scene )
                    )

    def remove_intro( self ):
        sprite = self.get('intro')
        sprite.do( FadeOut(0.5) )

    def play_sound( self ):
        self.sound_fart.play()

    def call_menu_scene( self ):
        s = menu_scene.get_menu_scene()
        director.replace( FadeTransition( s, 1 ) )

    def on_key_press (self, k, modifiers):
        if k == key.ESCAPE:
            self.call_menu_scene()
            return True
        return False

def get_intro_scene():

    scene = Scene()
    scene.add( IntroLayer() )

    return scene
