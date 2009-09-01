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

PTM_RATIO = 52
TORQUE_FORCE = 25
JUMP_IMPULSE = 5

class GameLayer(cocos.layer.Layer):

    def __init__(self):
        super(GameLayer,self).__init__()

        self.schedule( self.step )

        self.init_physics()
        self.init_sprites()

    def init_sprites( self ):
        sprite = Sprite( 'pedoman-character.png' )
        self.add( sprite )
        sprite.position = (200,200)
        self.pedoman_sprite = sprite

    def init_physics( self ):
        self.points             = []
        self.destroyList        = []
        self.shitting_places    = []
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
    # callbacks
    #
    def BoundaryViolated(self, body):
        self.destroyList.append(body)

    def ShapeDestroyed(self, joint):
        pass

    def JointDestroyed(self, joint):
        pass

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

        # falling boxes
#        friction = [0.75, 0.5, 0.35, 0.1, 0.0]
#
#        for i in range(5):
#            bd=box2d.b2BodyDef() 
#            bd.position = (-15.0 + 4.0 * i, 28.0)
#            body = self.world.CreateBody(bd) 
#
#            sd.friction = friction[i]
#            body.CreateShape(sd)
#            body.SetMassFromShapes()

        # create Pedo Man
        bd = box2d.b2BodyDef()
        bd.position = (18,0)
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


        # shitting places
        for i in range(10):
            bd = box2d.b2BodyDef()
            bd.position = (i*1.5,0)
            body = self.world.CreateBody(bd)
            sd = box2d.b2CircleDef()
            sd.density = 0.0000001
            sd.radius = 0.5
            sd.friction = 0.00001
            sd.restitution = 0.00001
            body.CreateShape(sd)
            body.SetMassFromShapes()
            self.shitting_places.append( body )

    def step(self, dt):

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
            if ( (body1 in self.shitting_places or body2 in self.shitting_places) and \
                (body1 == self.pedoman_body or body2 == self.pedoman_body ) ):
                    shape = self.pedoman_body.shapeList[0]

                    # new radius
                    sd = box2d.b2CircleDef()
                    sd.density = 1.0
                    sd.radius = shape.GetRadius() + 0.05
                    sd.friction = 0.95
                    sd.restitution = 0.7
                    self.pedoman_body.CreateShape(sd)
#                    self.pedoman_body.SetMassFromShapes()

                    # destroy old shape
                    self.pedoman_body.DestroyShape( shape )

                    # destroy shitting
                    shit_body = body1
                    if body2 in self.shitting_places:
                        shit_body = body2
                    self.destroyList.append( shit_body )
                    self.shitting_places.remove( shit_body )

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

    def draw( self ):
        super(GameLayer, self).draw()

        glPushMatrix()
        self.transform()
        self.debugDraw.batch.draw()
        glPopMatrix()

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
       
        torque = 0
        for key in self.keys_pressed:
            if key == LEFT:
                torque += TORQUE_FORCE
            elif key == RIGHT:
                torque -= TORQUE_FORCE

            if torque != 0:
                self.model.pedoman_body.ApplyTorque( torque )


    def on_mouse_drag( self, x, y, dx, dy, buttons, modifiers ):
        (x,y) = director.get_virtual_coordinates(x,y)
        x,y = self.model.position
        self.model.position = (x+dx, y+dy)

    def on_key_press (self, key, modifiers):
        if key == UP:
            body = self.model.pedoman_body
            f = (0.0, JUMP_IMPULSE)
            p = body.GetWorldPoint((0.0, 0.0))
            body.ApplyImpulse(f, p)
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


def get_game_scene():
    state.reset()

    s = cocos.scene.Scene()
    gameModel = GameLayer()
    gameModel.scale = 0.4
    s.add( gameModel, z=0 )
    s.add( ControlLayer( gameModel), z=0, name='ctrl' )
    return s
