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

# locals
from primitives import *
from state import state
import levels
import soundex

from box2d_callbacks import *
from settings import fwSettings


class GameLayer(cocos.layer.Layer):

    def __init__(self):
        super(GameLayer,self).__init__()

        self.schedule( self.step )

        self.init_physics()


    def init_physics( self ):
        self.points             = []
        self.destroyList        = []
        settings = fwSettings

        # Box2D Initialization

        win_size = director.get_window_size()
        self.worldAABB = box2d.b2AABB()
        self.worldAABB.lowerBound = (-200,-200)
        self.worldAABB.upperBound = (200,200)
        gravity = (0.0, -10.0)
#        gravity = (0.0, 0.0)

        doSleep = True
        self.world = box2d.b2World(self.worldAABB, gravity, doSleep)

        self.destructionListener = fwDestructionListener()
        self.boundaryListener = fwBoundaryListener()
        self.contactListener = fwContactListener()
        self.debugDraw = fwDebugDraw(10)          # 1 meter == 32 pixels
        self.debugDraw.batch = pyglet.graphics.Batch()

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

    def setup_physics_world( self ):
        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(50.0, 20.0)

        bd=box2d.b2BodyDef() 
        bd.position = (0.0, -20.0)
        ground = self.world.CreateBody(bd) 
        ground.CreateShape(sd)

        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(13.0, 0.25)

        bd=box2d.b2BodyDef() 
        bd.position = (-4.0, 22.0)
        bd.angle = -0.25

        ground = self.world.CreateBody(bd) 
        ground.CreateShape(sd)

        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(0.25, 1.0)

        bd=box2d.b2BodyDef() 
        bd.position = (10.5, 19.0)

        ground = self.world.CreateBody(bd) 
        ground.CreateShape(sd)

        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(13.0, 0.25)

        bd=box2d.b2BodyDef() 
        bd.position = (4.0, 14.0)
        bd.angle = 0.25

        ground = self.world.CreateBody(bd) 
        ground.CreateShape(sd)

        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(0.25, 1.0)

        bd=box2d.b2BodyDef() 
        bd.position = (-10.5, 11.0)

        ground = self.world.CreateBody(bd) 
        ground.CreateShape(sd)

        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(13.0, 0.25)

        bd=box2d.b2BodyDef() 
        bd.position = (-4.0, 6.0)
        bd.angle = -0.25

        ground = self.world.CreateBody(bd) 
        ground.CreateShape(sd)

        sd=box2d.b2PolygonDef() 
        sd.SetAsBox(0.5, 0.5)
        sd.density = 25.0

        friction = [0.75, 0.5, 0.35, 0.1, 0.0]

        for i in range(5):
            bd=box2d.b2BodyDef() 
            bd.position = (-15.0 + 4.0 * i, 28.0)
            body = self.world.CreateBody(bd) 

            sd.friction = friction[i]
            body.CreateShape(sd)
            body.SetMassFromShapes()


    def step(self, dt):
        # Prepare for simulation. Typically we use a time step of 1/60 of a
        # second (60Hz) and 10 velocity/8 position iterations. This provides a 
        # high quality simulation in most game scenarios.
#        timeStep = dt
        timeStep = 1.0 / 60
        vel_iters, pos_iters = 10, 8

        # Instruct the world to perform a single step of simulation. It is
        # generally best to keep the time step and iterations fixed.
        self.world.Step(timeStep, vel_iters, pos_iters)
        self.world.Validate()

        # Destroy bodies that have left the world AABB (can be removed if not using pickling)
        for obj in self.destroyList:
            self.world.DestroyBody(obj)
        self.destroyList = []

    def draw( self ):
        super(GameLayer, self).draw()
        self.debugDraw.batch.draw()

        # clean used batch
#        self.debugDraw.batch = pyglet.graphics.Batch()
        self.debugDraw.batch = pyglet.graphics.Batch()

class ControlLayer( cocos.layer.Layer ):

    is_event_handler = True     #: enable pyglet's events
   
    def __init__(self, model):
        super(ControlLayer,self).__init__()
        self.model = model

        self.keys_pressed = set()

    def update_keys(self):
        v = euclid.Vector2( 0, 0)
        
        for key in self.keys_pressed:
            if key == LEFT:
                v += (-1,0)
            elif key == RIGHT:
                v += (1,0)
            elif key == UP:
                v += (0,1)
            elif key == DOWN:
                v += (0,-1)

        v = v.normalize()
        v = v * 50

    def on_key_press (self, key, modifiers):
        if state.state == state.STATE_PLAY:
            if key in (LEFT, RIGHT, UP, DOWN):
                self.keys_pressed.add(key)
                self.update_keys()
                return True 
        return False 

    def on_key_release (self, key, modifiers):
        if state.state == state.STATE_PLAY:
            if key in (LEFT, RIGHT, UP, DOWN):
                try:
                    self.keys_pressed.remove(key)
                    self.update_keys()
                except KeyError:
                    self.keys_pressed = set()
                return True 
        return False 

    def on_text_motion(self, motion):
        if state.state == state.STATE_PLAY:
            if motion in ( MOTION_UP, MOTION_DOWN, MOTION_LEFT, MOTION_RIGHT ):
                self.update_keys()
                return True
        return False


def get_game_scene():
    state.reset()

    s = cocos.scene.Scene()
    gameModel = GameLayer()
    s.add( gameModel, z=0 )
    s.add( ControlLayer( gameModel), z=0, name='ctrl' )
    return s
