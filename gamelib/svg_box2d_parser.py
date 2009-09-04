
from Box2D import *
import data
import cocos
import squirtle
import math

from xml.dom.minidom import parse, parseString

DEFAULT_FRICTION = 1
DEFAULT_RESTITUTION = 0.2
DEFAULT_DENSITY = 1

class SVGBox2dParser( object ):

    def __init__( self, world, level, ratio=30, callback=None ):
        self.world = world
        self.level = level
        self.ratio = ratio
        self.callback = callback

        self.svg_size = b2Vec2(0,0)


        self.current_body = None
        self.static_physics = True
#        self.transform = squirtle.Matrix([1,0,0,-1,0,0])
        self.transform = squirtle.Matrix([1,0,0,1,0,0])


    def parse( self ):
        dom1 = parse( data.filepath( self.level) )
        main = dom1.getElementsByTagName("svg")[0]
        groups = main.getElementsByTagName("g")

        width = main.getAttribute('width')
        height = main.getAttribute('height')
        self.svg_size = b2Vec2( float(width), float(height) )

        for group in groups:
            self.parse_main_group( group )


    def parse_main_group( self, group ):
        label = group.getAttribute('inkscape:label')

        if label.startswith('physics:'):
            array = label.split(':')
            if array[1] == 'static':
                self.static_physics = True
            else:
                self.static_physics = False

            transform = group.getAttribute('transform')
            oldTransform = self.transform
            self.transform = self.transform * self.parse_transform( transform )

            self.parse_elements( group )

            self.transform = oldTransform


    def parse_elements( self, group ):
        for child in group.childNodes:
            body = None
            supported = ['rect','path','g']
            if child.nodeName in supported:
                if child.nodeName == 'rect':
                    body = self.parse_rect( child )
                elif child.nodeName == 'path':
                    body = self.parse_path( child )
                elif child.nodeName == 'g':
                    body = self.parse_group( child )
                self.apply_callback( child, body )

    def parse_rect( self, node ):
        width = float( node.getAttribute('width') )
        height = float( node.getAttribute('height') )
        x = float( node.getAttribute('x') )
        y = float( node.getAttribute('y') )
        transform = node.getAttribute('transform')

        matrix = self.transform * self.parse_transform( transform )

        identity = squirtle.Matrix()
        identity.values[4] = x
        identity.values[5] = y

        matrix = matrix * identity

        rel_pos = b2Vec2( matrix.values[4], matrix.values[5] )
        rel_pos.y = self.svg_size.y - rel_pos.y
        rel_pos.y -= height
        rel_pos /= self.ratio

        angle = math.asin( -matrix.values[2] )

        width /= self.ratio
        height /= self.ratio

#        vertices = (
#                    (rel_pos.x,         rel_pos.y + height ),
#                    (rel_pos.x,         rel_pos.y),
#                    (rel_pos.x + width, rel_pos.y),
#                    (rel_pos.x + width, rel_pos.y + height ),
#                    )
#
#        sd=b2EdgeChainDef()
#        sd.setVertices(vertices)


        sd=b2PolygonDef()
        sd.SetAsBox(width/2,height/2,(width/2,height/2),0)
        self.apply_physics_properties_to_shape( node, sd ) 

        if not self.current_body:
            bd = b2BodyDef()
            bd.angle = -angle
            bd.position = b2Vec2(rel_pos.x, rel_pos.y)
            body = self.world.CreateBody(bd)
        else:
            body = self.current_body

        body.CreateShape(sd)

        self.apply_physics_properties_to_body( body ) 

        return body

    def parse_path( self, node ):
        subtype = node.getAttribute('sodipodi:type')
        if subtype == 'arc':
            cx = float( node.getAttribute('sodipodi:cx') )
            cy = float( node.getAttribute('sodipodi:cy') )
            rx = float( node.getAttribute('sodipodi:rx') )
            ry = float( node.getAttribute('sodipodi:ry') )
            transform = node.getAttribute('transform')

            matrix = self.transform * self.parse_transform( transform )

            identity = squirtle.Matrix()
            identity.values[4] = cx
            identity.values[5] = cy
            matrix = matrix * identity

            rel_pos = b2Vec2( matrix.values[4], matrix.values[5] )
            rel_pos.y = self.svg_size.y - rel_pos.y
            rel_pos /= self.ratio

            scale_x = matrix.values[0]
            scale_y = matrix.values[3]
            radius = math.sqrt( rx * scale_x * ry * scale_y ) / self.ratio

            sd=b2CircleDef()
            sd.radius = radius
            self.apply_physics_properties_to_shape( node, sd ) 
            if not self.current_body:
                bd=b2BodyDef()
                bd.position = rel_pos
                body = self.world.CreateBody(bd)
            else:
                body = self.current_body
            body.CreateShape(sd)
            self.apply_physics_properties_to_body( body )

        return body

    def parse_group( self, node ):
        transform = node.getAttribute('transform')
        matrix = self.parse_transform( transform )

        old_transform = self.transform
        self.transform = self.transform * matrix

        bd = b2BodyDef()
        bd.position = b2Vec2( self.transform.values[4], self.transform.values[5] )
        self.current_body = self.world.CreateBody(bd)

        self.parse_elements( node )

        self.current_body = None

        self.transform = old_transform

        return self.current_body


    def parse_transform( self, s ):
        s = str(s)
        matrix = squirtle.Matrix( s )
        return matrix


    def cast_value( self, value ):
        value = value.lower()

        # is bool
        if value in ['true','false']:
            if value == 'true':
                return True
            return False

        # then it is a float or a int (string is not supported)
        f = float( value )
        i = int (value )

        # integer ?
        if f == i:
            return i
        # nope, float
        return f

    def apply_physics_properties_to_shape( self, node, shape ):

        shape.restitution = DEFAULT_RESTITUTION
        shape.density = DEFAULT_DENSITY
        shape.friction = DEFAULT_FRICTION

        data = node.getAttribute('physics_shape' )

        if data:
            keyvalues = data.split(',')
            for keyvalue in keyvalues:
                key,value = keyvalue.split('=')
                value = self.cast_value( value )
                setattr( shape, key, value )


    def apply_physics_properties_to_body( self, body ):
        if not self.static_physics:
            body.SetMassFromShapes()

    def apply_callback( self, node, body ):
        game_data = node.getAttribute('game_data')
        if game_data and self.callback:
            self.callback( body, game_data )
