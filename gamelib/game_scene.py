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
import HUD
import gameover
from box2d_callbacks import *
from settings import fwSettings
import gradient_layer

PTM_RATIO = 52
TORQUE_FORCE = 15
JUMP_IMPULSE = 8

class GameLayer(cocos.layer.Layer):

    is_event_handler = True     #: enable pyglet's events
   
    def __init__(self):
        super(GameLayer,self).__init__()

        self.schedule( self.main_loop)
        self.schedule_interval( self.show_level, 0.5 )

        self.init_background()
        self.init_game_state()
        self.init_events()
        self.init_sounds()
        self.init_sprites()
        self.init_physics()

        self.HUD_delegate = None

    def show_level( self, dt ):
        self.unschedule( self.show_level )
        self.HUD_delegate.show_level_name()
        self.state.state = state.STATE_PLAY

    #
    # IMAGES
    #
    def init_background( self ):
        self.with_background = True
        name = levels.get_level_filename( state.level_idx )
        name = name.split('.')[0]
        name = '%s.png' % name
        try:
            background = Sprite( name )
            background.image_anchor = (0,0)
            self.add( background )
        except Exception:
            self.with_background = False

        r1 = random.random() * 0.2 + 0.9 
        r2 = random.random() * 0.2 + 0.9 
        r3 = random.random() * 0.2 + 0.9 
        r4 = random.random() * 0.2 + 0.9 
        gradient = gradient_layer.GradientLayer( 
            (175*r1,203*r1,240*r1,255),
            (181*r2,68*r2,32*r2,255),
            (32*r3,143*r3,168*r3,255),
            (63*r4,32*r4,12*r4,255)
            )
        self.add( gradient, z=-10)
        

    #
    # GAME STATE
    #
    def init_game_state( self ):
        self.state = state

    #
    # SOUNDS
    #
    def init_sounds( self ):
        self.sounds_coin = soundex.load('sounds/crunch_01.mp3')
        self.sounds_powerup = soundex.load('sounds/powerup_01.wav')
        self.sounds_farts = []
        self.sounds_farts.append( soundex.load('sounds/fart_01.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_02.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_03.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_04.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_05.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_06.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_08.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_09.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_10.mp3') )
        self.sounds_farts.append( soundex.load('sounds/fart_11.mp3') )
        self.sounds_level_complete = soundex.load('sounds/level_complete_01.mp3')
        self.sounds_ouch = soundex.load('sounds/ouch_01.wav')
        self.sounds_argh = soundex.load('sounds/scream_01.mp3')

        soundex.set_music('music_01.mp3')
        soundex.play_music()

    #
    # SPRITES
    #
    def init_sprites( self ):

        sprite = sqa.SVG_CacheNode()
        node= sqa.SVGnode( data.filepath("sprites/gasman-character.svg") )
        sprite.add(node)
        self.add( sprite)
        self.gasman_sprite = sprite

        sprite = sqa.SVG_CacheNode()
        node= sqa.SVGnode( data.filepath("sprites/gaswoman-character.svg") )
        sprite.add(node)
        self.add( sprite)
        self.gaswoman_sprite = sprite

    #
    # PHYSICS
    #
    def init_physics( self ):
        self.points             = []
        self.destroyList        = []
        self.food_places        = []
        self.bad_guys           = []
        self.deadly_places      = []
        settings = fwSettings

        # Box2D Initialization

        win_size = director.get_window_size()
        self.worldAABB = box2d.b2AABB()
        self.worldAABB.lowerBound = (-30,-30)
        self.worldAABB.upperBound = (45,41)
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

        if not self.with_background:
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
            if key=='sprite':
                if value=='food':
                    self.food_places.append( body )
                    shape = body.shapeList[0]
                    body.DestroyShape(shape)
                    sd = box2d.b2CircleDef()
                    sd.radius = 0.2
                    sd.isSensor = True
                    body.CreateShape(sd)
                    body.SetMassFromShapes()
                    sprite = Sprite('sprites/bean-man.png')
                    self.add( sprite )
                    body.userData = sprite

                elif value=='bad_guy':
                    self.bad_guys.append( body )
                    shape = body.shapeList[0]
                    sd = box2d.b2CircleDef()
                    sd.radius = 0.5
                    sd.friction = shape.friction
                    sd.restitution = shape.restitution
                    sd.density = shape.density
                    body.DestroyShape(shape)
                    body.CreateShape(sd)
                    body.SetMassFromShapes()

                    sprite = sqa.SVG_CacheNode()
                    node= sqa.SVGnode( data.filepath("sprites/badguy-character.svg") )
                    sprite.add(node)
                    self.add( sprite)
                    body.userData = sprite

                elif value=='gasman':
                    self.gasman_body = body
                    body.userData = self.gasman_sprite
                    shape = body.shapeList[0]
                    body.DestroyShape(shape)
                    sd = box2d.b2CircleDef()
                    sd.radius = 0.5
                    sd.density = 1
                    sd.friction = 1
                    sd.restitution = 0.2
                    body.CreateShape(sd)
                    body.SetMassFromShapes()

                elif value=='gaswoman':
                    self.gaswoman_body = body
                    body.userData = self.gaswoman_sprite
                    shape = body.shapeList[0]
                    sd = box2d.b2CircleDef()
                    sd.radius = 0.5
                    sd.density = 1
                    sd.friction = 1
                    sd.restitution = shape.restitution
                    body.CreateShape(sd)

                    body.DestroyShape(shape)

                    body.SetMassFromShapes()

                elif value=='game_over':
                    self.deadly_places.append( body )


    def setup_physics_world( self ):

        level_name = levels.get_level_filename( self.state.level_idx )
        parser = svg_box2d_parser.SVGBox2dParser( self.world, level_name, ratio=PTM_RATIO, callback=self.physics_game_cb)
        parser.parse()

        # create Gas Man
#        bd = box2d.b2BodyDef()
#        bd.position = (15,1)
#        bd.angularDamping = 2.0
#        bd.linearDamping = 0.1
#        body = self.world.CreateBody(bd)
#        sd = box2d.b2CircleDef()
#        sd.density = 1.0
#        sd.radius = 0.5
#        sd.friction = 0.95
#        sd.restitution = 0.7
#        body.CreateShape(sd)
#        body.SetMassFromShapes()
#        self.gasman_body = body


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
        
        for pair in body_pairs:
            body1 = pair[0]
            body2 = pair[1]
            if ( (body1 in self.food_places or body2 in self.food_places) and \
                (body1 == self.gasman_body or body2 == self.gasman_body ) ):
                    self.food_eat( body1, body2 )
            elif ( self.gasman_body in pair and self.gaswoman_body in pair):
                self.collision_gasman_gaswoman()
            elif ( self.gasman_body in pair and (body1 in self.deadly_places or body2 in self.deadly_places ) ):
                self.collision_gasman_deadly()
            elif ( self.gasman_body in pair and (body1 in self.bad_guys or body2 in self.bad_guys ) ):
                self.collision_gasman_badguy()

    def collision_gasman_gaswoman( self ):
        if self.state.state == state.STATE_PLAY:
            self.state.state = state.STATE_WIN
            self.state.score += 10
            self.sounds_level_complete.play()
            self.HUD_delegate.level_complete()
            self.schedule_interval( self.level_next_async, 1.5 )

    def collision_gasman_deadly( self ):
        if self.state.state == state.STATE_PLAY:
            self.sounds_argh.play()
            self.state.lives -= 1
            if self.state.lives == 0:
                self.state.state = state.STATE_OVER
                self.parent.add( gameover.GameOver( win=False) , z=10 )
            else:
                self.level_replay()

    def collision_gasman_badguy( self ):
        if self.state.state == state.STATE_PLAY:
            self.sounds_ouch.play()
            self.state.lives -= 1
            if self.state.lives == 0:
                self.state.state = state.STATE_OVER
                self.parent.add( gameover.GameOver( win=False) , z=10 )
            else:
                self.level_replay()

    def food_eat( self, body1, body2 ):
        shape = self.gasman_body.shapeList[0]

        # destroy food
        food_body = body1
        if body2 in self.food_places:
            food_body = body2

        self.remove( food_body.userData )
        self.destroyList.append( food_body )
        self.food_places.remove( food_body )

        self.state.coins += 1
        self.state.score += 3

        if self.state.coins % 10 == 0:
            self.sounds_powerup.play()
            self.state.farts += 1

            # new radius
#            sd = box2d.b2CircleDef()
#            sd.density = shape.density
#            sd.radius = shape.GetRadius() + 0.2
#            sd.friction = shape.friction
#            sd.restitution = shape.restitution
#            self.gasman_body.CreateShape(sd)
#            self.gasman_body.SetMassFromShapes()

            # destroy old shape
#            self.gasman_body.DestroyShape( shape )

        else:
            self.sounds_coin.play()

                    

    def update_sprite_positions( self ):
        # position


        for body in self.world.bodyList:
            sprite = body.userData
            if isinstance( sprite, cocos.cocosnode.CocosNode):
                position = body.position
                position = (position.x * PTM_RATIO, position.y * PTM_RATIO)
                sprite.position = position
                shape = body.shapeList[0]
                sprite.scale = ( shape.radius * 2)     # scale 1 == 1 meter

                # angle
                angle = body.angle
                angle = math.degrees( angle )
                sprite.rotation = -angle

    #
    # DRAW
    #
    def draw( self ):
        super(GameLayer, self).draw()

        glPushMatrix()
        self.transform()
        self.debugDraw.batch.draw()

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
                self.gasman_body.ApplyTorque( torque )

    def on_key_press (self, key, modifiers):
        if self.state.state == state.STATE_PLAY:
            if key == UP or key == SPACE:
                if self.state.farts > 0 :
                    self.state.farts -= 1
                    body = self.gasman_body
#                f = (0.0, JUMP_IMPULSE)
                    f = body.GetWorldVector((0.0, JUMP_IMPULSE))
                    p = body.GetWorldPoint((0.0, 0.0))
                    body.ApplyImpulse(f, p)
                    random.choice( self.sounds_farts ).play()
                return True
            elif key in (LEFT, RIGHT):
                self.keys_pressed.add(key)
                self.update_keys()
                return True 
            elif key == R:
                self.level_restart()
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
        if self.state.state == state.STATE_PLAY:
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

    #
    # level management
    #
    def level_new( self ):
        scene = self.parent
        hud = scene.get('hud')
        scene.remove( 'ctrl' )
        gameModel = GameLayer()
        gameModel.HUD_delegate = hud
        scene.add( gameModel, z=1, name='ctrl')

    def level_replay( self ):
        state.replay()
        self.level_new()

    def level_restart( self ):
        state.reset()
        self.level_new()

    def level_next( self ):
        if state.level_idx == len( levels.levels) -1:
            self.parent.add( gameover.GameOver( win=True) , z=10 )
        else:
            state.level_idx += 1
            self.level_new()
            state.set_level( state.level_idx )


    def level_next_async( self, dt ):
        self.unschedule( self.level_next_async )
        self.level_next()

def get_game_scene():
    state.reset()

    s = cocos.scene.Scene()
    gameModel = GameLayer()
    s.add( gameModel, z=1, name='ctrl')

    hud = HUD.HUD()
    s.add( hud, z=10, name='hud' )

    gameModel.HUD_delegate = hud

    return s
