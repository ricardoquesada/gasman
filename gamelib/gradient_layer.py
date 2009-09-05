
import cocos
from cocos.layer import *
from cocos.director import *

import pyglet
from pyglet.gl import *

class GradientLayer(Layer):
    """Creates a layer of a certain color.
    The color shall be specified in the format (r,g,b,a).
    
    For example, to create green layer::
    
        l = ColorLayer(0, 255, 0, 0 )

    The size and position can be changed, for example::

        l = ColorLayer( 0, 255,0,0, width=200, height=400)
        l.position = (50,50)

    """
    def __init__(self, bl, br, tl, tr, width=None, height=None):
        super(Layer, self).__init__()
        self._batch = pyglet.graphics.Batch()
        self._vertex_list = None
        self._bl = map(int, bl)
        self._br = map(int, br)
        self._tl = map(int, tl)
        self._tr = map(int, tr)

        self.width = width
        self.height = height
        
        w,h = director.get_window_size()
        if not self.width:
            self.width = w
        if not self.height:
            self.height = h

    def on_enter(self):
        super(Layer, self).on_enter()
        x, y = self.width, self.height
        ox, oy = 0, 0
        
        self._vertex_list = self._batch.add(4, pyglet.gl.GL_QUADS, None,
            ('v2i', ( ox, oy,
                      ox, oy + y,
                      ox+x, oy+y, 
                      ox+x, oy)),
            'c4B')

        self._update_color()

    def on_exit(self):
        super(Layer, self).on_exit()
        self._vertex_list.delete()
        self._vertex_list = None

    def draw(self):
        super(Layer, self).draw()
        glPushMatrix()
        self.transform()
        glTranslatef( 
                -self.children_anchor_x, 
                -self.children_anchor_y,
                 0 )
        glPushAttrib(GL_CURRENT_BIT)
        self._batch.draw()
        glPopAttrib()
        glPopMatrix()

    def _update_color(self):
        if self._vertex_list:
            r1, g1, b1, a1 = self._bl
            r2, g2, b2, a2 = self._br
            r3, g3, b3, a3 = self._tr
            r4, g4, b4, a4 = self._tl
            self._vertex_list.colors[:] = [
                        r1, g1, b1, a1,
                        r2, g2, b2, a2,
                        r3, g3, b3, a3,
                        r4, g4, b4, a4,
            ] 

    def _set_opacity(self, opacity):
        self._opacity = opacity
        self._update_color()

    opacity = property(lambda self: self._opacity, _set_opacity,
                       doc='''Blend opacity.

    This property sets the alpha component of the colour of the layer's
    vertices.  This allows the layer to be drawn with fractional opacity,
    blending with the background.

    An opacity of 255 (the default) has no effect.  An opacity of 128 will
    make the sprite appear translucent.

    :type: int
    ''')

    def _set_color(self, bl, br, tl, tr):
        self._bl = map(int, bl)
        self._br = map(int, br)
        self._tl = map(int, tl)
        self._tr = map(int, tr)
        self._update_color()

    color = property(lambda self: self._rgb, _set_color,
                       doc='''Blend color.

    This property sets the color of the layer's vertices. This allows the
    layer to be drawn with a color tint.
    
    The color is specified as an RGB tuple of integers ``(red, green, blue)``.
    Each color component must be in the range 0 (dark) to 255 (saturated).
    
    :type: (int, int, int)
    ''')
