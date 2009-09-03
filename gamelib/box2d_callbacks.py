#
# Based on pyglet_main from PyBox2d
#
"""
"""

import pyglet
from pyglet import gl
import Box2D as box2d
from settings import fwSettings
from pyglet_keymapper import *
import math

class fwDestructionListener(box2d.b2DestructionListener):
    """
    The destruction listener callback:
    "SayGoodbye" is called when a joint or shape is deleted.
    """
    test = None
    def __init__(self):
        super(fwDestructionListener, self).__init__()

    def SayGoodbye(self, object):
        if isinstance(object, box2d.b2Joint):
            if self.test.mouseJoint==object:
                self.test.mouseJoint=None
            else:
                self.test.JointDestroyed(object)
        elif isinstance(object, box2d.b2Shape):
            self.test.ShapeDestroyed(object)

class fwBoundaryListener(box2d.b2BoundaryListener):
    """
    The boundary listener callback:
    Violation is called when the specified body leaves the world AABB.
    """
    test = None
    def __init__(self):
        super(fwBoundaryListener, self).__init__()

    def Violation(self, body):
        # So long as it's not the user-created bomb, let the test know that
        # the specific body has left the world AABB
#        if self.test.bomb != body:
        self.test.BoundaryViolated(body)

class fwContactTypes:
    """
    Acts as an enum, holding the types necessary for contacts:
    Added, persisted, and removed
    """
    contactUnknown = 0
    contactAdded = 1
    contactPersisted = 2
    contactRemoved = 3

class fwContactPoint:
    """
    Structure holding the necessary information for a contact point.
    All of the information is copied from the contact listener callbacks.
    """
    shape1 = None
    shape2 = None
    normal = None
    position = None
    velocity = None
    id  = box2d.b2ContactID()
    state = 0

class fwContactListener(box2d.b2ContactListener):
    """
    Handles all of the contact states passed in from Box2D.

    """
    test = None
    def __init__(self):
        super(fwContactListener, self).__init__()

    def handleCall(self, state, point):
        if not self.test: return

        cp          = fwContactPoint()
        cp.shape1   = point.shape1
        cp.shape2   = point.shape2
        cp.position = point.position.copy()
        cp.normal   = point.normal.copy()
        cp.id       = point.id
        cp.state    = state
        self.test.points.append(cp)

    def Add(self, point):
        self.handleCall(fwContactTypes.contactAdded, point)

    def Persist(self, point):
        self.handleCall(fwContactTypes.contactPersisted, point)

    def Remove(self, point):
        self.handleCall(fwContactTypes.contactRemoved, point)

class grBlended (pyglet.graphics.Group):
    """
    This pyglet rendering group enables blending.
    """
    def set_state(self):
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    def unset_state(self):
        gl.glDisable(gl.GL_BLEND)

class grPointSize (pyglet.graphics.Group):
    """
    This pyglet rendering group sets a specific point size.
    """
    def __init__(self, size=4.0):
        super(grPointSize, self).__init__()
        self.size = size
    def set_state(self):
        gl.glPointSize(self.size)
    def unset_state(self):
        gl.glPointSize(1.0)

class grText(pyglet.graphics.Group):
    """
    This pyglet rendering group sets the proper projection for
    displaying text when used.
    """
    window = None
    def __init__(self, window=None):
        super(grText, self).__init__()
        self.window = window

    def set_state(self):
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.gluOrtho2D(0, self.window.width, 0, self.window.height)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

    def unset_state(self):
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

class fwDebugDraw(box2d.b2DebugDraw):
    """
    This debug draw class accepts callbacks from Box2D (which specifies what to draw)
    and handles all of the rendering.

    If you are writing your own game, you likely will not want to use debug drawing.
    Debug drawing, as its name implies, is for debugging.
    """
#    blended = grBlended()
    blended = None
    circle_segments = 16
    surface = None
    circle_cache_tf = {} # triangle fan (inside)
    circle_cache_ll = {} # line loop (border)
    def __init__(self, p2m_ratio=1):
        super(fwDebugDraw, self).__init__()

        self.batch = None
        self.p2m_ratio = p2m_ratio

    def triangle_fan(self, vertices):
        """
        in: vertices arranged for gl_triangle_fan ((x,y),(x,y)...)
        out: vertices arranged for gl_triangles (x,y,x,y,x,y...)
        """
        out = []
        for i in range(1, len(vertices)-1):
            # 0,1,2   0,2,3  0,3,4 ..
            out.extend( vertices[0  ] )
            out.extend( vertices[i  ] )
            out.extend( vertices[i+1] )
        return len(out) / 2, out

    def line_loop(self, vertices):
        """
        in: vertices arranged for gl_line_loop ((x,y),(x,y)...)
        out: vertices arranged for gl_lines (x,y,x,y,x,y...)
        """
        out = []
        for i in range(0, len(vertices)-1):
            # 0,1  1,2  2,3 ... len-1,len  len,0
            out.extend( vertices[i  ] )
            out.extend( vertices[i+1] )
        
        out.extend( vertices[len(vertices)-1] )
        out.extend( vertices[0] )

        return len(out)/2, out

    def _getLLCircleVertices(self, radius, points):
        """
        Get the line loop-style vertices for a given circle.
        Drawn as lines.

        "Line Loop" is used as that's how the C++ code draws the
        vertices, with lines going around the circumference of the
        circle (GL_LINE_LOOP).

        This returns 'points' amount of lines approximating the 
        border of a circle.

        (x1, y1, x2, y2, x3, y3, ...)
        """
        ret = []
        step = 2*math.pi/points
        n = 0
        for i in range(0, points):
            ret.append( (math.cos(n) * radius, math.sin(n) * radius ) )
            n += step
            ret.append( (math.cos(n) * radius, math.sin(n) * radius ) )
        return ret

    def _getTFCircleVertices(self, radius, points):
        """
        Get the triangle fan-style vertices for a given circle.
        Drawn as triangles.

        "Triangle Fan" is used as that's how the C++ code draws the
        vertices, with triangles originating at the center of the
        circle, extending around to approximate a filled circle
        (GL_TRIANGLE_FAN).

        This returns 'points' amount of lines approximating the 
        circle.

        (a1, b1, c1, a2, b2, c2, ...)
        """
        ret = []
        step = 2*math.pi/points
        n = 0
        for i in range(0, points):
            ret.append( (0.0, 0.0) )
            ret.append( (math.cos(n) * radius, math.sin(n) * radius ) )
            n += step
            ret.append( (math.cos(n) * radius, math.sin(n) * radius ) )
        return ret

    def getCircleVertices(self, center, radius, points):
        """
        Returns the triangles that approximate the circle and
        the lines that border the circles edges, given
        (center, radius, points).

        Caches the calculated LL/TF vertices, but recalculates
        based on the center passed in.

        TODO: As of this point, there's only one point amount,
        so the circle cache ignores it when storing. Could cause 
        some confusion if you're using multiple point counts as
        only the first stored point-count for that radius will
        show up.

        Returns: (tf_vertices, ll_vertices)
        """
        if radius not in self.circle_cache_tf.keys():
            self.circle_cache_tf[radius]=self._getTFCircleVertices(radius,points)
            self.circle_cache_ll[radius]=self._getLLCircleVertices(radius,points)

        ret_tf, ret_ll = [], []

        for x, y in self.circle_cache_tf[radius]:
            ret_tf.extend( (x+center.x, y+center.y) )
        for x, y in self.circle_cache_ll[radius]:
            ret_ll.extend( (x+center.x, y+center.y) )
        return ret_tf, ret_ll

    def DrawCircle(self, center, radius, color):
        """
        Draw an unfilled circle given center, radius and color.
        """
        center *= self.p2m_ratio
        radius *= self.p2m_ratio
        unused, ll_vertices = self.getCircleVertices( center, radius, self.circle_segments)
        ll_count = len(ll_vertices)/2

        self.batch.add(ll_count, gl.GL_LINES, None,
            ('v2f', ll_vertices),
            ('c4f', [color.r, color.g, color.b, 1.0] * (ll_count)))

    def DrawSolidCircle(self, center, radius, axis, color):
        """
        Draw an filled circle given center, radius, axis (of orientation) and color.
        """
        center *= self.p2m_ratio
        radius *= self.p2m_ratio
        tf_vertices, ll_vertices = self.getCircleVertices( center, radius, self.circle_segments)
        tf_count, ll_count = len(tf_vertices) / 2, len(ll_vertices) / 2

        self.batch.add(tf_count, gl.GL_TRIANGLES, self.blended,
            ('v2f', tf_vertices),
            ('c4f', [0.5 * color.r, 0.5 * color.g, 0.5 * color.b, 0.5] * (tf_count)))

        self.batch.add(ll_count, gl.GL_LINES, None,
            ('v2f', ll_vertices),
            ('c4f', [color.r, color.g, color.b, 1.0] * (ll_count)))

        p = center + radius * axis
        self.batch.add(2, gl.GL_LINES, None,
            ('v2f', (center.x, center.y, p.x, p.y)),
            ('c3f', [1.0, 0.0, 0.0] * 2))

    def DrawPolygon(self, vertices, vertexCount, color):
        """
        Draw a wireframe polygon given the world vertices (tuples) with the specified color.
        """
        new_vertices = []
        for i in range( vertexCount ):
            new_vertices.append( (vertices[i][0] * self.p2m_ratio, vertices[i][1] * self.p2m_ratio) )

        vertices = new_vertices

        ll_count, ll_vertices = self.line_loop(vertices)

        self.batch.add(ll_count, gl.GL_LINES, None,
            ('v2f', ll_vertices),
            ('c4f', [color.r, color.g, color.b, 1.0] * (ll_count)))

    def DrawSolidPolygon(self, vertices, vertexCount, color):
        """
        Draw a wireframe polygon given the world vertices (tuples) with the specified color.
        """
        new_vertices = []
        for i in range( vertexCount ):
            new_vertices.append( (vertices[i][0] * self.p2m_ratio, vertices[i][1] * self.p2m_ratio) )

        vertices = new_vertices
        tf_count, tf_vertices = self.triangle_fan(vertices)

        self.batch.add(tf_count, gl.GL_TRIANGLES, self.blended,
            ('v2f', tf_vertices),
            ('c4f', [0.5 * color.r, 0.5 * color.g, 0.5 * color.b, 0.5] * (tf_count)))

        ll_count, ll_vertices = self.line_loop(vertices)

        self.batch.add(ll_count, gl.GL_LINES, None,
            ('v2f', ll_vertices),
            ('c4f', [color.r, color.g, color.b, 1.0] * (ll_count)))

    def DrawSegment(self, p1, p2, color):
        """
        Draw the line segment from p1-p2 with the specified color.
        """
        p1.x *= self.p2m_ratio
        p1.y *= self.p2m_ratio
        p2.x *= self.p2m_ratio
        p2.y *= self.p2m_ratio
        self.batch.add(2, gl.GL_LINES, None,
            ('v2f', (p1.x, p1.y, p2.x, p2.y)),
            ('c3f', [color.r, color.g, color.b]*2))

    def DrawXForm(self, xf):
        """
        Draw the transform xf on the screen
        """
        print 'DrawXForm without ratio'
        p1 = xf.position
        k_axisScale = 0.4
        p2 = p1 + k_axisScale * xf.R.col1
        p3 = p1 + k_axisScale * xf.R.col2

        self.batch.add(3, gl.GL_LINES, None,
            ('v2f', (p1.x, p1.y, p2.x, p2.y, p1.x, p1.y, p3.x, p3.y)),
            ('c3f', [1.0, 0.0, 0.0] * 2 + [0.0, 1.0, 0.0] * 2))

    def DrawPoint(self, p, size, color):
        """
        Draw a single point at point p given a point size and color.
        """
        p.x *= self.p2m_ratio
        p.y *= self.p2m_ratio
        self.batch.add(1, gl.GL_POINTS, grPointSize(size),
            ('v2f', (p.x, p.y)),
            ('c3f', [color.r, color.g, color.b]))
        
    def DrawAABB(self, aabb, color):
        """
        Draw a wireframe around the AABB with the given color.
        """
        print 'DrawAABB without ratio'
        self.debugDraw.batch.add(8, gl.GL_LINES, None,
            ('v2f', (aabb.lowerBound.x, aabb.lowerBound.y, abb.upperBound.x, aabb.lowerBound.y, 
                abb.upperBound.x, aabb.lowerBound.y, aabb.upperBound.x, aabb.upperBound.y,
                aabb.upperBound.x, aabb.upperBound.y, aabb.lowerBound.x, aabb.upperBound.y,
                aabb.lowerBound.x, aabb.upperBound.y, aabb.lowerBound.x, aabb.lowerBound.y)),
            ('c3f', [color.r, color.g, color.b] * 8))
