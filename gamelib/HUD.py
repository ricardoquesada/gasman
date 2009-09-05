from cocos.layer import *
from cocos.text import *
from cocos.actions import *

import pyglet
from pyglet.gl import *

# locals
from state import state
import levels

class ScoreLayer( Layer ): 
    def __init__(self):
        w,h = director.get_window_size()
        super( ScoreLayer, self).__init__()

        # transparent layer
        self.add( ColorLayer(32,32,32,200, width=w, height=48),z=-1 )

        self.position = (0,h-48)

        self.score=  Label('Score:', font_size=36,
                font_name='Edit Undo Line BRK',
                color=(255,255,255,255),
                anchor_x='left',
                anchor_y='bottom')
        self.score.position=(0,0)
        self.add( self.score)

        self.farts = Label('Farts:', font_size=36,
                font_name='Edit Undo Line BRK',
                color=(255,255,255,255),
                anchor_x='left',
                anchor_y='bottom')
        self.farts.position=(250,0)
        self.add( self.farts)

        self.lives= Label('Lives:', font_size=36,
                font_name='Edit Undo Line BRK',
                color=(255,255,255,255),
                anchor_x='left',
                anchor_y='bottom')
        self.lives.position=(480,0)
        self.add( self.lives)

        self.lvl=  Label('Lvl:', font_size=36,
                font_name='Edit Undo Line BRK',
                color=(255,255,255,255),
                anchor_x='left',
                anchor_y='bottom')
        self.lvl.position=(660,0)
        self.add( self.lvl)

    def draw(self):
        super( ScoreLayer, self).draw()
        self.score.element.text = 'Score:%d' % state.score 
        self.lives.element.text = 'Lives:%d' % state.lives
        self.farts.element.text = 'Farts:%d' % state.farts

        lvl = state.level_idx or 0
        self.lvl.element.text = 'Lvl:%d' % lvl
        

class MessageLayer( Layer ):
    def show_message( self, msg, callback=None ):

        w,h = director.get_window_size()

        self.msg = Label( msg,
            font_size=42,
            font_name='Edit Undo Line BRK',
            color=(64,64,64,255),
            anchor_y='center',
            anchor_x='center' )
        self.msg.position=(w/2.0, h)

        self.msg2 = Label( msg,
            font_size=42,
            font_name='Edit Undo Line BRK',
            color=(255,255,255,255),
            anchor_y='center',
            anchor_x='center' )
        self.msg2.position=(w/2.0+2, h+2)

        self.add( self.msg, z=1 )
        self.add( self.msg2, z=0 )

        actions = Accelerate(MoveBy( (0,-h/2.0), duration=0.5)) + \
                    Delay(1) +  \
                    Accelerate(MoveBy( (0,-h/2.0), duration=0.5)) + \
                    Hide()

        if callback:
            actions += CallFunc( callback )

        self.msg.do( actions )
        self.msg2.do( actions )

class HUD( Layer ):
    def __init__( self ):
        super( HUD, self).__init__()
        self.add( ScoreLayer() )
        self.add( MessageLayer(), name='msg' )

    def show_message( self, msg, callback = None ):
        self.get('msg').show_message( msg, callback )

    def show_level_name( self ):
        name = '%d: %s' % ( state.level_idx, levels.get_level_name( state.level_idx) )
        self.show_message( name )

    def level_complete( self ):
        self.show_message('WELL DONE!')

    def level_over( self ):
        self.show_message('GAME OVER')
