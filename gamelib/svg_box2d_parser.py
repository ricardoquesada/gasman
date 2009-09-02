
from Box2D import *
import data
import cocos
import squirtle
import math

from xml.dom.minidom import parse, parseString



class SVGBox2dParser( object ):

    def __init__( self, world, level, ratio=52 ):
        self.world = world
        self.level = level
        self.ratio = ratio

        self.svg_size = b2Vec2(0,0)


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
            if child.nodeName == 'rect':
                self.parse_rect( child )
            elif child.nodeName == 'path':
                self.parse_path( child )
            elif child.nodeName == 'g':
                self.parse_group( child )

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

        bd=b2BodyDef()
        bd.angle = -angle
        bd.position = b2Vec2(rel_pos.x, rel_pos.y)
#        bd.position = b2Vec2(rel_pos.x + width/2, rel_pos.y+height/2)
#        bd.position = b2Vec2(0,0)
        body = self.world.CreateBody(bd)
        body.CreateShape(sd)

        if not self.static_physics:
            body.SetMassFromShapes()

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

            radius = math.sqrt( rx * ry ) / self.ratio

            sd=b2CircleDef()
            sd.radius = radius
            bd=b2BodyDef()
            bd.position = rel_pos
            body = self.world.CreateBody(bd)
            body.CreateShape(sd)

    def parse_group( self, node ):
        pass


    def parse_transform( self, s ):
        s = str(s)
        matrix = squirtle.Matrix( s )
        return matrix
