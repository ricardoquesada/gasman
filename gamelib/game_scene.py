# std lib
import math
import random

# pyglet
import pyglet
from pyglet.gl import *
from pyglet.window.key import *

# cocos
import cocos
from cocos.director import director
from cocos.sprite import *
from cocos import euclid

# box2d
from Box2D import *

# squirtle
import squirtle
import squirtle_cocos_adaptor as sqa

# locals
from primitives import *
from state import state
import levels
import soundex
import data
import svg_box2d_parser

from box2d_callbacks import *
from settings import fwSettings

PTM_RATIO = 52
TORQUE_FORCE = 25
JUMP_IMPULSE = 15

class GameLayer(cocos.layer.Layer):

    is_event_handler = True     #: enable pyglet's events
   
    def __init__(self):
        super(GameLayer,self).__init__()

        self.schedule( self.main_loop)

        self.init_events()
        self.init_sounds()
        self.init_physics()
        self.init_sprites()
        self.init_background()
        self.init_game_state()


    #
    # IMAGES
    #
    def init_background( self ):
        self.background = squirtle.SVG( data.filepath("pedoman-character2.svg") )

    #
    # GAME STATE
    #
    def init_game_state( self ):
        self.state = state

    #
    # SOUNDS
    #
    def init_sounds( self ):
        self.sounds_coin = soundex.load('crunch_01.mp3')
        self.sounds_powerup = soundex.load('powerup_01.wav')
        self.sounds_fart = soundex.load('fart_01.mp3')

        soundex.set_music('music_01.mp3')
        soundex.play_music()

    #
    # SPRITES
    #
    def init_sprites( self ):

        sprite = sqa.SVG_CacheNode()
        node= sqa.SVGnode( data.filepath("pedoman-character.svg") )
        sprite.add(node)
        self.add( sprite)

#        sprite = Sprite( 'pedoman-character.png' )
#        self.add( sprite )
        self.pedoman_sprite = sprite

        sprite = Sprite( 'pedowoman-character.png' )
        self.add( sprite )
        sprite.position = (200,200)
        self.pedowoman_sprite = sprite

    #
    # PHYSICS
    #
    def init_physics( self ):
        self.points             = []
        self.destroyList        = []
        self.food_places    = []
        settings = fwSettings

        # Box2D Initialization

        win_size = director.get_window_size()
        self.worldAABB = box2d.b2AABB()
        self.worldAABB.lowerBound = (-200,-200)
        self.worldAABB.upperBound = (200,200)
        gravity = (0.0, -10.0)

        doSleep = True
        self.world = box2d.b2World(self.worldAABB, gravity, doSleep)

        self.destructionListener = fwDestructionListener()
        self.boundaryListener = fwBoundaryListener()
        self.contactListener = fwContactListener()
        self.debugDraw = fwDebugDraw(PTM_RATIO)          # 1 meter == 10 pixels
        self.debugDraw.batch = pyglet.graphics.Batch()
    
        self.destructionListener.test = self
        self.boundaryListener.test = self
        self.contactListener.test = self
        
        self.world.SetDestructionListener(self.destructionListener)
        self.world.SetBoundaryListener(self.boundaryListener)
        self.world.SetContactListener(self.contactListener)

        # Set the other settings that aren't contained in the flags
        self.world.SetWarmStarting(settings.enableWarmStarting)
        self.world.SetContinuousPhysics(settings.enableTOI)
        self.world.SetDebugDraw( self.debugDraw )

        # Set the flags based on what the settings show (uses a bitwise or mask)
        flags = 0
        if settings.drawShapes:     flags |= box2d.b2DebugDraw.e_shapeBit
        if settings.drawJoints:     flags |= box2d.b2DebugDraw.e_jointBit
        if settings.drawControllers:flags |= box2d.b2DebugDraw.e_controllerBit
        if settings.drawCoreShapes: flags |= box2d.b2DebugDraw.e_coreShapeBit
        if settings.drawAABBs:      flags |= box2d.b2DebugDraw.e_aabbBit
        if settings.drawOBBs:       flags |= box2d.b2DebugDraw.e_obbBit
        if settings.drawPairs:      flags |= box2d.b2DebugDraw.e_pairBit
        if settings.drawCOMs:       flags |= box2d.b2DebugDraw.e_centerOfMassBit
        self.debugDraw.SetFlags(flags)

        self.setup_physics_world()

    # 
    # physics callbacks
    #
    def BoundaryViolated(self, body):
        self.destroyList.append(body)

    def ShapeDestroyed(self, joint):
        pass

    def JointDestroyed(self, joint):
        pass


    def physics_game_cb(self, body, values):

        list_values = values.split(',')
        for keypair in list_values:
            key,value = keypair.split('=')
            if key=='sprite' and value=='food':
                self.food_places.append( body )

    def setup_physics_world( self ):

        parser = svg_box2d_parser.SVGBox2dParser( self.world, 'level0.svg', ratio=PTM_RATIO, callback=self.physics_game_cb)
        parser.parse()

        # create Pedo Man
        bd = box2d.b2BodyDef()
        bd.position = (15,1)
        bd.angularDamping = 2.0
        bd.linearDamping = 0.1
        body = self.world.CreateBody(bd)
        sd = box2d.b2CircleDef()
        sd.density = 1.0
        sd.radius = 0.5
        sd.friction = 0.95
        sd.restitution = 0.7
        body.CreateShape(sd)
        body.SetMassFromShapes()
        self.pedoman_body = body


        # food places
#        for i in range(10):
#            bd = box2d.b2BodyDef()
#            bd.position = (i*1.53,10)
#            body = self.world.CreateBody(bd)
#            sd = box2d.b2CircleDef()
#            sd.density = 0.0000001
#            sd.radius = 0.5
#            sd.friction = 0.00001
#            sd.restitution = 0.00001
#            body.CreateShape(sd)
#            body.SetMassFromShapes()
#            self.food_places.append( body )

    #
    # MAIN LOOP
    #
    def main_loop(self, dt):
        #
        # check collision detection
        #
        self.check_collision_detection()
        # Reset the collision points
        self.points = []

        #
        # Physics main loop
        #
        # Prepare for simulation. Typically we use a time step of 1/60 of a
        # second (60Hz) and 10 velocity/8 position iterations. This provides a 
        # high quality simulation in most game scenarios.
#        timeStep = dt
        timeStep = 1.0 / 60
        vel_iters, pos_iters = 10, 8

        # It is generally best to keep the time step and iterations fixed.
        self.world.Step(timeStep, vel_iters, pos_iters)
        self.world.Validate()

        #
        # cleanup
        #
        # Destroy bodies that have left the world AABB (can be removed if not using pickling)
        for obj in self.destroyList:
            self.world.DestroyBody(obj)
        self.destroyList = []

        #
        # update sprites based on physics bodies / shapes
        #
        self.update_sprite_positions()

    def check_collision_detection( self ):

        # Traverse the contact results. Destroy bodies that
        # are touching heavier bodies.
        body_pairs = [(p.shape1.GetBody(), p.shape2.GetBody()) for p in self.points]
        
        for body1, body2 in body_pairs:
            if ( (body1 in self.food_places or body2 in self.food_places) and \
                (body1 == self.pedoman_body or body2 == self.pedoman_body ) ):
                    self.food_eat( body1, body2 )


    def food_eat( self, body1, body2 ):
        shape = self.pedoman_body.shapeList[0]

        # destroy food
        food_body = body1
        if body2 in self.food_places:
            food_body = body2
        self.destroyList.append( food_body )
        self.food_places.remove( food_body )

        self.state.coins += 1

        if self.state.coins % 10 == 0:
            self.sounds_powerup.play()
            self.state.farts += 1

            # new radius
            sd = box2d.b2CircleDef()
            sd.density = 1.0
            sd.radius = shape.GetRadius() + 0.5
            sd.friction = 0.95
            sd.restitution = 0.7
            self.pedoman_body.CreateShape(sd)
#                    self.pedoman_body.SetMassFromShapes()

            # destroy old shape
            self.pedoman_body.DestroyShape( shape )

        else:
            self.sounds_coin.play()

                    

    def update_sprite_positions( self ):
        # position
        position = self.pedoman_body.position
        position = (position.x * PTM_RATIO, position.y * PTM_RATIO)
        self.pedoman_sprite.position = position
        shape = self.pedoman_body.shapeList[0]
        self.pedoman_sprite.scale = ( shape.radius * 2)     # scale 1 == 1 meter

        # angle
        angle = self.pedoman_body.angle
        angle = math.degrees( angle )
        self.pedoman_sprite.rotation = -angle


    #
    # DRAW
    #
    def draw( self ):
        super(GameLayer, self).draw()

        glPushMatrix()
        self.transform()
        self.debugDraw.batch.draw()

        self.background.draw( *self.position )
        glPopMatrix()

        # clean used batch
        self.debugDraw.batch = pyglet.graphics.Batch()

    #
    # EVENTS
    #
    def init_events( self ):
        self.keys_pressed = set()

    def update_keys(self):
        torque = 0
        for key in self.keys_pressed:
            if key == LEFT:
                torque += TORQUE_FORCE
            elif key == RIGHT:
                torque -= TORQUE_FORCE

            if torque != 0:
                self.pedoman_body.ApplyTorque( torque )

    def on_key_press (self, key, modifiers):
        if key == Z:
            if self.state.farts > 0 :
                self.state.farts -= 1
                self.state.player_state = state.PLAYER_FARTING
                body = self.pedoman_body
#                f = (0.0, JUMP_IMPULSE)
                f = body.GetWorldVector((0.0, JUMP_IMPULSE))
                p = body.GetWorldPoint((0.0, 0.0))
                body.ApplyImpulse(f, p)
                self.sounds_fart.play()
            return True
        elif key in (LEFT, RIGHT):
            self.keys_pressed.add(key)
            self.update_keys()
            return True 
        return False 

    def on_key_release (self, key, modifiers):
        if key in (LEFT, RIGHT):
            try:
                self.keys_pressed.remove(key)
                self.update_keys()
            except KeyError:
                self.keys_pressed = set()
            return True 
        return False 

    def on_text_motion(self, motion):
        if motion in ( MOTION_UP, MOTION_DOWN, MOTION_LEFT, MOTION_RIGHT ):
            self.update_keys()
            return True
        return False

    def on_mouse_drag( self, x, y, dx, dy, buttons, modifiers ):
        (x,y) = director.get_virtual_coordinates(x,y)
        x,y = self.position
        self.position = (x+dx, y+dy)

    def on_mouse_scroll( self, x, y, dx, dy ):
        if dy > 0:
            diff = 1.1
        else:
            diff = 0.9
        self.scale *= diff


def get_game_scene():
    state.reset()

    s = cocos.scene.Scene()
    gameModel = GameLayer()
    gameModel.scale = 1
    s.add( gameModel, z=0 )
    return s
