# Copyright (c) 2008, Martin O'Leary
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name(s) of the copyright holders nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""squirtle_core mini-library for SVG rendering to a openGL display list

This module must not depend on the specific python gl flawor,
you must provide a simple gl_backend.py to allow squirtle_core
access to the glXXX and gluXXX functions. (see below examples)
Also, I dont wanted conditional imports to not confuse py2exe.

As a design guide, here goes only functionality that deals with
converting a .svg file into a vertexlist; you must build elsewere
a suitable adaptor that using squirtle_core provides your engine
with the adequate objects. cocos_adaptor and classic_squirtle are
both adaptor examples.

backends examples:

# pyglet backend
from pyglet.gl import *

# cocos backend
from pyglet.gl import *

# pyOpenGL backend
from OpenGL.GL import *
from OpenGL.GLU import *

Tipically you should add the files
  squirtle_core.py #this file
  svg_colors.py # provided with the library
  gl_backend.py # with the apropiate content (see above examples)
  xxx_adaptor.py # cocos_adaptor.py , classic_squirtle.py or your own custom adaptor
to your src dir,
then in your app import xxx_adaptor,probably with a shortname, like
import squirtle_cocos_adaptor as sqa

The concrete classes your app will use comes from the adaptor,not from
this file

"""


from gl_backend import *
from xml.etree.cElementTree import parse as cTree_parse
import re
import math
from ctypes import CFUNCTYPE, POINTER, byref, cast
import sys

from svg_colors import svg_named_colors

tess = gluNewTess()
gluTessNormal(tess, 0, 0, 1)
gluTessProperty(tess, GLU_TESS_WINDING_RULE, GLU_TESS_WINDING_NONZERO)

if sys.platform == 'win32':
    from ctypes import WINFUNCTYPE
    c_functype = WINFUNCTYPE
else:
    c_functype = CFUNCTYPE
    
callback_types = {GLU_TESS_VERTEX: c_functype(None, POINTER(GLvoid)),
                  GLU_TESS_BEGIN: c_functype(None, GLenum),
                  GLU_TESS_END: c_functype(None),
                  GLU_TESS_ERROR: c_functype(None, GLenum),
                  GLU_TESS_COMBINE: c_functype(None, POINTER(GLdouble), POINTER(POINTER(GLvoid)), POINTER(GLfloat), POINTER(POINTER(GLvoid)))}

def set_tess_callback(which):
    def set_call(func):
        cb = callback_types[which](func)
        gluTessCallback(tess, which, cast(cb, CFUNCTYPE(None)))
        return cb
    return set_call
    
BEZIER_POINTS = 10
CIRCLE_POINTS = 24
TOLERANCE = 0.001
def setup_gl():
    """Set various pieces of OpenGL state for better rendering of SVG.
        If the app needs to setup other states, use begin_svg() - end_svg()
        wich preseres the gl state.
    """
    glEnable(GL_LINE_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

def begin_svg():
    """ preserves current gl state, then change to the desired gl state.
        call end_svg() to restore gl state
        """
    #preserve state
    glPushAttrib(GL_COLOR_BUFFER_BIT)
    glPushAttrib(GL_ENABLE_BIT)
    setup_gl()

def end_svg():
    glPopAttrib()
    glPopAttrib()
    
def parse_list(string):
    return re.findall("([A-Za-z]|-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", string)

def parse_style(string):
    sdict = {}
    for item in string.split(';'):
        if ':' in item:
            key, value = item.split(':')
            sdict[key] = value
    return sdict
    
def parse_color(c, default=None):
    if not c:
        return default
    if c == 'none':
        return None
    if c[0] == '#': c = c[1:]
    if c.startswith('url(#'):
        return c[5:-1]
    if c in svg_named_colors:
        r,g,b = svg_named_colors[c]
        return [r,g,b,255]
    try:
        if len(c) == 6:
            r = int(c[0:2], 16)
            g = int(c[2:4], 16)
            b = int(c[4:6], 16)
        elif len(c) == 3:
            r = int(c[0], 16) * 17
            g = int(c[1], 16) * 17
            b = int(c[2], 16) * 17
        else:
            raise Exception("Incorrect length for colour " + str(c) + " length " + str(len(c)))            
        return [r,g,b,255]
    except Exception, ex:
        print 'Exception parsing color', ex
        return None
        
class Matrix(object):
    def __init__(self, string=None):
        self.values = [1, 0, 0, 1, 0, 0] #Identity matrix seems a sensible default
        if isinstance(string, str):
            if string.startswith('matrix('):
                self.values = [float(x) for x in parse_list(string[7:-1])]
            elif string.startswith('translate('):
                x, y = [float(x) for x in parse_list(string[10:-1])]
                self.values = [1, 0, 0, 1, x, y]
            elif string.startswith('scale('):
                sx, sy = [float(x) for x in parse_list(string[6:-1])]
                self.values = [sx, 0, 0, sy, 0, 0]           
        elif string is not None:
            self.values = list(string)
    
    def __call__(self, other):
        return (self.values[0]*other[0] + self.values[2]*other[1] + self.values[4],
                self.values[1]*other[0] + self.values[3]*other[1] + self.values[5])
    
    def inverse(self):
        d = float(self.values[0]*self.values[3] - self.values[1]*self.values[2])
        return Matrix([self.values[3]/d, -self.values[1]/d, -self.values[2]/d, self.values[0]/d,
                       (self.values[2]*self.values[5] - self.values[3]*self.values[4])/d,
                       (self.values[1]*self.values[4] - self.values[0]*self.values[5])/d])

    def __mul__(self, other):
        a, b, c, d, e, f = self.values
        u, v, w, x, y, z = other.values
        return Matrix([a*u + c*v, b*u + d*v, a*w + c*x, b*w + d*x, a*y + c*z + e, b*y + d*z + f])
                               
class TriangulationError(Exception):
    """Exception raised when triangulation of a filled area fails. For internal use only.
    
    """
    pass

class GradientContainer(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.callback_dict = {}

    def call_me_on_add(self, callback, grad_id):
        '''The client wants to know when the gradient with id grad_id gets
        added.  So store this callback for when that happens.
        When the desired gradient is added, the callback will be called
        with the gradient as the first and only argument.
        '''
        cblist = self.callback_dict.get(grad_id, None)
        if cblist == None:
            cblist = [callback]
            self.callback_dict[grad_id] = cblist
            return
        cblist.append(callback)

    def update(self, *args, **kwargs):
        raise NotImplementedError('update not done for GradientContainer')

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)
        callbacks = self.callback_dict.get(key, [])
        for callback in callbacks:
            callback(val)
        
    
class Gradient(object):
    def __init__(self, element, svg):
        self.element = element
        self.stops = {}
        for e in element.getiterator():
            if e.tag.endswith('stop'):
                style = parse_style(e.get('style', ''))
                color = parse_color(e.get('stop-color'))
                if 'stop-color' in style:
                    color = parse_color(style['stop-color'])
                color[3] = int(float(e.get('stop-opacity', '1')) * 255)
                if 'stop-opacity' in style:
                    color[3] = int(float(style['stop-opacity']) * 255)
                self.stops[float(e.get('offset'))] = color
        self.stops = sorted(self.stops.items())
        self.svg = svg
        self.inv_transform = Matrix(element.get('gradientTransform')).inverse()

        inherit = self.element.get('{http://www.w3.org/1999/xlink}href') #need inet ?
        parent = None
        delay_params = False
        if inherit:
            parent_id = inherit[1:]
            parent = self.svg.gradients.get(parent_id, None)
            if parent == None:
                self.svg.gradients.call_me_on_add(self.tardy_gradient_parsed, parent_id)
                delay_params = True
                return
        if not delay_params:
            self.get_params(parent)
        
    def interp(self, pt):
        if not self.stops: return [255, 0, 255, 255]
        t = self.grad_value(self.inv_transform(pt))
        if t < self.stops[0][0]:
            return self.stops[0][1]
        for n, top in enumerate(self.stops[1:]):
            bottom = self.stops[n]
            if t <= top[0]:
                u = bottom[0]
                v = top[0]
                alpha = (t - u)/(v - u)
                return [int(x[0] * (1 - alpha) + x[1] * alpha) for x in zip(bottom[1], top[1])]
        return self.stops[-1][1]

    def get_params(self, parent):
        for param in self.params:
            v = None
            if parent:
                v = getattr(parent, param, None)
            my_v = self.element.get(param)
            if my_v:
                v = float(my_v)
            if v:
                setattr(self, param, v)

    def tardy_gradient_parsed(self, gradient):
        self.get_params(gradient)
        
class LinearGradient(Gradient):
    params = ['x1', 'x2', 'y1', 'y2', 'stops']
    def grad_value(self, pt):
        return ((pt[0] - self.x1)*(self.x2 - self.x1) + (pt[1] - self.y1)*(self.y2 - self.y1)) / ((self.x1 - self.x2)**2 + (self.y1 - self.y2)**2)

class RadialGradient(Gradient):
    params = ['cx', 'cy', 'r', 'stops']

    def grad_value(self, pt):
        return math.sqrt((pt[0] - self.cx) ** 2 + (pt[1] - self.cy) ** 2)/self.r
        


class SVG_pre_render(object):
    """Builds a gl display list from a .svg or .svgz file.
    
        `filename`: str
            The name of the file to be loaded.
        `bezier_points`: int
            The number of line segments into which to subdivide Bezier splines. Defaults to 10.
        `circle_points`: int
            The number of line segments into which to subdivide circular and elliptic arcs. 
            Defaults to 10.

        Usage:
            obj = SVG_pre_render(params).get_result()
            display_list , width, height, min_x, max_x, min_y, max_y = obj.get_result() 
        where:
            display_list: gl display list
            min_x,max_x,min_y,max_y: bounding box for the display list
            width, height : calculated from the bounding box
        
        Usage legacy, for compatibility with squirtle 2.04:
            display_list , width, height = SVG_pre_render(params).get_legacy_result()
        where:
            display_list: gl display list
            width, height : as stored in the .svg file
    """
    def __init__(self, filename, bezier_points=BEZIER_POINTS, circle_points=CIRCLE_POINTS):
        self.bezier_points = bezier_points
        self.circle_points = circle_points
        self.bezier_coefficients = []
        self.gradients = GradientContainer()
        self.filename = filename 
        
        if open(filename, 'rb').read(3) == '\x1f\x8b\x08': #gzip magic numbers
            import gzip
            f = gzip.open(filename, 'rb')
        else:
            f = open(filename, 'rb')
        self.tree = cTree_parse(f) #cElementTree
        self.parse_doc()
        self.disp_list = glGenLists(1)
        glNewList(self.disp_list, GL_COMPILE)
        self.render_slowly()
        glEndList()

    def get_result(self):
        return (self.disp_list, self._width, self._height,
                self.min_x, self.max_x, self.min_y, self.max_y)

    def get_legacy_result(self):
        return self.disp_list, self.width, self.height

        
    # users dont need to call any of the following
    def parse_doc(self):
        self.paths = []
        try:
            self.width = self.parse_float(self.tree._root.get("width", '0'))
        except ValueError:
            #? happens by example when including units, like '12cm'
            self.width = 0
        try:
            #? happens by example when including units, like '12cm'
            self.height = self.parse_float(self.tree._root.get("height", '0'))
        except ValueError:
            self.height = 0
        if self.height:
            self.transform = Matrix([1, 0, 0, -1, 0, self.height])
        else:
            x, y, w, h = (self.parse_float(x) for x in parse_list(self.tree._root.get("viewBox")))
            self.transform = Matrix([1, 0, 0, -1, -x, h + y])
            self.height = h
            self.width = w
        self.opacity = 1.0
        for e in self.tree._root.getchildren():
            try:
                self.parse_element(e)
            except Exception, ex:
                print 'Exception while parsing element', e
                print 'elem: %s'%e
                raise
        self.calc_bounds() # .min_x , .max_x, .min_y , max_y 

    def parse_element(self, e):
        default = object()
#        print 'id:',e.get('id',1)
        self.fill = parse_color(e.get('fill'), default)
        self.stroke = parse_color(e.get('stroke'), default)
        oldopacity = self.opacity
        self.opacity *= float(e.get('opacity', 1))
        fill_opacity = float(e.get('fill-opacity', 1))
        stroke_opacity = float(e.get('stroke-opacity', 1))
        
        oldtransform = self.transform
        self.transform = self.transform * Matrix(e.get('transform'))
        style = e.get('style')
        if style:
            sdict = parse_style(style)
            if 'fill' in sdict:
                self.fill = parse_color(sdict['fill'])
            if 'fill-opacity' in sdict:
                fill_opacity *= float(sdict['fill-opacity'])
            if 'stroke' in sdict:
                self.stroke = parse_color(sdict['stroke'])
            if 'stroke-opacity' in sdict:
                stroke_opacity *= float(sdict['stroke-opacity'])
        if self.fill == default:
            self.fill = [0, 0, 0, 255]
        if self.stroke == default:
            self.stroke = [0, 0, 0, 0]  
        if isinstance(self.stroke, list):
            self.stroke[3] = int(self.opacity * stroke_opacity * self.stroke[3])
        if isinstance(self.fill, list):
            self.fill[3] = int(self.opacity * fill_opacity * self.fill[3])                 
        if isinstance(self.stroke, list) and self.stroke[3] == 0: self.stroke = self.fill #Stroked edges antialias better
        
        if e.tag.endswith('path'):
            #print '*** path begin ***'
            pathdata = e.get('d', '')               
            pathdata = re.findall("([A-Za-z]|-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", pathdata)

            def opcode_follows():
                return len(pathdata)==0 or pathdata[0] in 'MmCcSsAaLlHhZzVv'
                
            def pnext():
                return (float(pathdata.pop(0)), float(pathdata.pop(0)))

            self.new_path()
            opnum = -1
            while pathdata:
                opnum += 1 
                opcode = pathdata.pop(0)
                #print ' opcode:',opcode
                if opcode == 'M':
                    self.set_position(*pnext())
                elif opcode=='m':
                    if opnum==0:
                        self.set_position(*pnext())
                    else:                        
                        self.set_relative_position(*pnext())
                    # if aditional points follow, treat as lineto's
                    while not opcode_follows():
                        x, y = pnext()
                        self.line_to(self.x + x, self.y + y)
                elif opcode == 'C':
                    self.curve_to(*(pnext() + pnext() + pnext()))
                elif opcode == 'c':
                    while 1:
                        mx = self.x
                        my = self.y
                        x1, y1 = pnext()
                        x2, y2 = pnext()
                        x, y = pnext()
                        self.curve_to(mx + x1, my + y1, mx + x2, my + y2, mx + x, my + y)
                        if opcode_follows():
                            break
                elif opcode == 'S':
                    self.curve_to(2 * self.x - self.last_cx, 2 * self.y - self.last_cy, *(pnext() + pnext()))
                elif opcode == 's':
                    mx = self.x
                    my = self.y
                    x1, y1 = 2 * self.x - self.last_cx, 2 * self.y - self.last_cy
                    x2, y2 = pnext()
                    x, y = pnext()
                    
                    self.curve_to(x1, y1, mx + x2, my + y2, mx + x, my + y)
                elif opcode in 'A':
                    rx, ry = pnext()
                    phi = float(pathdata.pop(0))
                    large_arc = int(pathdata.pop(0))
                    sweep = int(pathdata.pop(0))
                    x, y = pnext()
                    self.arc_to(rx, ry, phi, large_arc, sweep, x, y)
                    #? opcode 'A' allow implicit repeats, as 'a' ? 
                elif opcode in 'a':
                    while 1:
                        rx, ry = pnext()
                        phi = float(pathdata.pop(0))
                        large_arc = int(pathdata.pop(0))
                        sweep = int(pathdata.pop(0))
                        x, y = pnext()
                        x,y = self.rel_to_abs(x,y)
                        self.arc_to(rx, ry, phi, large_arc, sweep, x, y)
                        if opcode_follows():
                            break
                elif opcode in 'zZ':
                    self.close_path()
                elif opcode == 'L':
                    self.line_to(*pnext())
                elif opcode == 'l':
                    x, y = pnext()
                    self.line_to(self.x + x, self.y + y)
                elif opcode == 'H':
                    x = float(pathdata.pop(0))
                    self.line_to(x, self.y)
                elif opcode == 'h':
                    x = float(pathdata.pop(0))
                    self.line_to(self.x + x, self.y)
                elif opcode == 'V':
                    y = float(pathdata.pop(0))
                    self.line_to(self.x, y)
                elif opcode == 'v':
                    y = float(pathdata.pop(0))
                    self.line_to(self.x, self.y + y)
                else:
                    self.warn("Unrecognised opcode: " + opcode)
            #print ' *** before end_path ***'
            self.end_path()
        elif e.tag.endswith('rect'):
            x = float(e.get('x'))
            y = float(e.get('y'))
            h = float(e.get('height'))
            w = float(e.get('width'))
            self.new_path()
            self.set_position(x, y)
            self.line_to(x+w,y)
            self.line_to(x+w,y+h)
            self.line_to(x,y+h)
            self.line_to(x,y)
            self.end_path()
        elif e.tag.endswith('polyline') or e.tag.endswith('polygon'):
            pathdata = e.get('points')
            pathdata = re.findall("(-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", pathdata)
            def pnext():
                return (float(pathdata.pop(0)), float(pathdata.pop(0)))
            self.new_path()
            while pathdata:
                self.line_to(*pnext())
            if e.tag.endswith('polygon'):
                self.close_path()
            self.end_path()
        elif e.tag.endswith('line'):
            x1 = float(e.get('x1'))
            y1 = float(e.get('y1'))
            x2 = float(e.get('x2'))
            y2 = float(e.get('y2'))
            self.new_path()
            self.set_position(x1, y1)
            self.line_to(x2, y2)
            self.end_path()
        elif e.tag.endswith('circle'):
            cx = float(e.get('cx'))
            cy = float(e.get('cy'))
            r = float(e.get('r'))
            self.new_path()
            for i in xrange(self.circle_points):
                theta = 2 * i * math.pi / self.circle_points
                self.line_to(cx + r * math.cos(theta), cy + r * math.sin(theta))
            self.close_path()
            self.end_path()
        elif e.tag.endswith('ellipse'):
            cx = float(e.get('cx'))
            cy = float(e.get('cy'))
            rx = float(e.get('rx'))
            ry = float(e.get('ry'))
            self.new_path()
            for i in xrange(self.circle_points):
                theta = 2 * i * math.pi / self.circle_points
                self.line_to(cx + rx * math.cos(theta), cy + ry * math.sin(theta))
            self.close_path()
            self.end_path()
        elif e.tag.endswith('linearGradient'):
            self.gradients[e.get('id')] = LinearGradient(e, self)
        elif e.tag.endswith('radialGradient'):
            self.gradients[e.get('id')] = RadialGradient(e, self)
        for c in e.getchildren():
            try:
                self.parse_element(c)
            except Exception, ex:
                print 'Exception while parsing element', c
                raise
        self.transform = oldtransform
        self.opacity = oldopacity                        

    def parse_float(self, txt):
        if len(txt)>2:
            if not txt[-1].isdigit() and not txt[-2].isdigit():
                # probably units like px,cm,mm,... see unit tab in inkscape
                return float(txt[:-2])
        return float(txt)

    def render_slowly(self):
        self.n_tris = 0
        self.n_lines = 0
        for path, stroke, tris, fill, transform in self.paths:
            if tris:
                self.n_tris += len(tris)/3
                if isinstance(fill, str):
                    g = self.gradients[fill]
                    fills = [g.interp(x) for x in tris]
                else:
                    fills = [fill for x in tris]
                #pyglet.graphics.draw(len(tris), GL_TRIANGLES, 
                #                     ('v3f', sum((x + [0] for x in tris), [])), 
                #                     ('c3B', sum(fills, [])))
                glBegin(GL_TRIANGLES)
                for vtx, clr in zip(tris, fills):
                    vtx = transform(vtx)
                    glColor4ub(*clr)
                    glVertex3f(vtx[0], vtx[1], 0)
                glEnd()
            if path:
                for loop in path:
                    self.n_lines += len(loop) - 1
                    loop_plus = []
                    for i in xrange(len(loop) - 1):
                        loop_plus += [loop[i], loop[i+1]]
                    if isinstance(stroke, str):
                        g = self.gradients[stroke]
                        strokes = [g.interp(x) for x in loop_plus]
                    else:
                        strokes = [stroke for x in loop_plus]
                    #pyglet.graphics.draw(len(loop_plus), GL_LINES, 
                    #                     ('v3f', sum((x + [0] for x in loop_plus), [])), 
                    #                     ('c3B', sum((stroke for x in loop_plus), [])))
                    glBegin(GL_LINES)
                    for vtx, clr in zip(loop_plus, strokes):
                        vtx = transform(vtx)
                        glColor4ub(*clr)
                        glVertex3f(vtx[0], vtx[1], 0)
                    glEnd()                     

    def calc_bounds(self):
        vertexes = []
        for path, stroke, tris, fill, transform in self.paths:
            if tris:
                more = [ transform(vtx) for vtx in tris ]
                vertexes.extend(more)
            if path:
                for loop in path:
                    more = [ transform(vtx) for vtx in loop ]
                    vertexes.extend(more)
        v = [ x for x,y in vertexes]
        self.min_x = min(v)
        self.max_x = max(v)
        v = [ y for x,y in vertexes]
        self.min_y = min(v)
        self.max_y = max(v)
        #used underscore to not collide with old code
        self._width = self.max_x-self.min_x
        self._height = self.max_y-self.min_y

    def new_path(self):
        self.x = 0
        self.y = 0
        self.close_index = 0
        self.path = []
        self.loop = [] 
    def close_path(self):
        self.loop.append(self.loop[0][:])
        self.path.append(self.loop)
        self.loop = []
    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.loop.append([x,y])

    def set_relative_position(self,dx,dy):
        self.set_position(self.x+dx, self.y+dy)

    def rel_to_abs(self,dx,dy):
        return (self.x+dx, self.y+dy)

    def arc_to(self, rx, ry, phi, large_arc, sweep, x, y):
        #print 'arc_to params:',rx, ry, phi, large_arc, sweep, x, y
        # This function is made out of magical fairy dust
        # http://www.w3.org/TR/2003/REC-SVG11-20030114/implnote.html#ArcImplementationNotes
        x1 = self.x
        y1 = self.y
        x2 = x
        y2 = y
        cp = math.cos(phi)
        sp = math.sin(phi)
        dx = .5 * (x1 - x2)
        dy = .5 * (y1 - y2)
        x_ = cp * dx + sp * dy
        y_ = -sp * dx + cp * dy
        r2 = (((rx * ry)**2 - (rx * y_)**2 - (ry * x_)**2)/
	      ((rx * y_)**2 + (ry * x_)**2))
        if r2 < 0: r2 = 0.0
        r = math.sqrt(r2)
        if large_arc == sweep:
            r = -r
        cx_ = r * rx * y_ / ry
        cy_ = -r * ry * x_ / rx
        cx = cp * cx_ - sp * cy_ + .5 * (x1 + x2)
        cy = sp * cx_ + cp * cy_ + .5 * (y1 + y2)

        def angle(u, v):
            tmp = (u[0]*v[0] + u[1]*v[1]) / math.sqrt((u[0]**2 + u[1]**2) * (v[0]**2 + v[1]**2))
            if tmp>1.0:
                tmp = 1.0
            elif tmp<-1.0:
                tmp = -1.0
            a = math.acos(tmp)
            sgn = 1 if u[0]*v[1] > u[1]*v[0] else -1
            return sgn * a
        
        psi = angle((1,0), ((x_ - cx_)/rx, (y_ - cy_)/ry))
        delta = angle(((x_ - cx_)/rx, (y_ - cy_)/ry), 
                      ((-x_ - cx_)/rx, (-y_ - cy_)/ry))
        if sweep and delta < 0: delta += math.pi * 2
        if not sweep and delta > 0: delta -= math.pi * 2
        n_points = max(int(abs(self.circle_points * delta / (2 * math.pi))), 1)
        
        for i in xrange(n_points + 1):
            theta = psi + i * delta / n_points
            ct = math.cos(theta)
            st = math.sin(theta)
            self.line_to(cp * rx * ct - sp * ry * st + cx,
                         sp * rx * ct + cp * ry * st + cy)

    def curve_to(self, x1, y1, x2, y2, x, y):
        if not self.bezier_coefficients:
            for i in xrange(self.bezier_points+1):
                t = float(i)/self.bezier_points
                t0 = (1 - t) ** 3
                t1 = 3 * t * (1 - t) ** 2
                t2 = 3 * t ** 2 * (1 - t)
                t3 = t ** 3
                self.bezier_coefficients.append([t0, t1, t2, t3])
        self.last_cx = x2
        self.last_cy = y2
        for i, t in enumerate(self.bezier_coefficients):
            px = t[0] * self.x + t[1] * x1 + t[2] * x2 + t[3] * x
            py = t[0] * self.y + t[1] * y1 + t[2] * y2 + t[3] * y
            self.loop.append([px, py])

        self.x, self.y = px, py

    def line_to(self, x, y):
        self.set_position(x, y)

    def end_path(self):
        self.path.append(self.loop)
        if self.path:
            path = []
            for orig_loop in self.path:
                if not orig_loop: continue
                loop = [orig_loop[0]]
                for pt in orig_loop:
                    if (pt[0] - loop[-1][0])**2 + (pt[1] - loop[-1][1])**2 > TOLERANCE:
                        loop.append(pt)
                path.append(loop)
            self.paths.append((path if self.stroke else None, self.stroke,
                               self.triangulate(path) if self.fill else None, self.fill,
                               self.transform))
        self.path = []

    def triangulate(self, looplist):
        tlist = []
        self.curr_shape = []
        spareverts = []

        @set_tess_callback(GLU_TESS_VERTEX)
        def vertexCallback(vertex):
            vertex = cast(vertex, POINTER(GLdouble))
            self.curr_shape.append(list(vertex[0:2]))

        @set_tess_callback(GLU_TESS_BEGIN)
        def beginCallback(which):
            self.tess_style = which

        @set_tess_callback(GLU_TESS_END)
        def endCallback():
            if self.tess_style == GL_TRIANGLE_FAN:
                c = self.curr_shape.pop(0)
                p1 = self.curr_shape.pop(0)
                while self.curr_shape:
                    p2 = self.curr_shape.pop(0)
                    tlist.extend([c, p1, p2])
                    p1 = p2
            elif self.tess_style == GL_TRIANGLE_STRIP:
                p1 = self.curr_shape.pop(0)
                p2 = self.curr_shape.pop(0)
                while self.curr_shape:
                    p3 = self.curr_shape.pop(0)
                    tlist.extend([p1, p2, p3])
                    p1 = p2
                    p2 = p3
            elif self.tess_style == GL_TRIANGLES:
                tlist.extend(self.curr_shape)
            else:
                self.warn("Unrecognised tesselation style: %d" % (self.tess_style,))
            self.tess_style = None
            self.curr_shape = []

        @set_tess_callback(GLU_TESS_ERROR)
        def errorCallback(code):
            ptr = gluErrorString(code)
            err = ''
            idx = 0
            while ptr[idx]: 
                err += chr(ptr[idx])
                idx += 1
            self.warn("GLU Tesselation Error: " + err)

        @set_tess_callback(GLU_TESS_COMBINE)
        def combineCallback(coords, vertex_data, weights, dataOut):
            x, y, z = coords[0:3]
            data = (GLdouble * 3)(x, y, z)
            dataOut[0] = cast(pointer(data), POINTER(GLvoid))
            spareverts.append(data)
        
        data_lists = []
        for vlist in looplist:
            d_list = []
            for x, y in vlist:
                v_data = (GLdouble * 3)(x, y, 0)
                d_list.append(v_data)
            data_lists.append(d_list)
        gluTessBeginPolygon(tess, None)
        for d_list in data_lists:    
            gluTessBeginContour(tess)
            for v_data in d_list:
                gluTessVertex(tess, v_data, v_data)
            gluTessEndContour(tess)
        gluTessEndPolygon(tess)
        return tlist       

    def warn(self, message):
        print "Warning: SVG Parser (%s) - %s" % (self.filename, message)
