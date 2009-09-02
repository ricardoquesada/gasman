# Copyright (c)Claudio Canepa 2009
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Claudio Canepa nor the names of its
#     contributors may be used to endorse or promote products
#     derived from this software without specific prior written
#     permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------
"""svg support for the cocos library

example typical use:
import cocos
import squirtle_cocos_adaptor as sqa

scene = cocos.Scene.scene()
cache_group = sqa.SVG_CacheNode()
scene.add(cache_droup)
ball = sqa.SVGnode("ball",position=123,123)
cache_group.add(ball)
flower1 = sqa.SVGnode('flower.png',position=(200,0),anchor_hint='S')
cache_group.add(flower1)
flower2 = sqa.SVGnode('flower.png',position=(300,0),anchor_hint='S')
cache_group.add(flower2)
...

remarks about the example:
A SVG_Cache_Node is needed even if only one SVGnode wiil be in use.
The anchor_hint defaults to 'CC' --> center
To values for anchor_hint come from a rosewind analogy, with the aditional
value 'CC' meaning center.
The instances flower1, flower2 share the same vertex list.

cocos_adaptor entities:

class SVG_CacheNode:
    a cocosnode subclass that acts as a container for SVGnodes
    Responsabilities:
        display list provider: childs get the display list that represent
        the svg file through this node.
        
        vertex lists caching: childs that use the same svg with the same
        conversion parameters will share the vertext list ( and the file
        will be parsed and converted only once)

        Set and unset a fine open gl state to draw the SVG nodes.

    Aditional notes:
    You can have more than one SVG_CacheCode, but caching would not apply
    across diferent cache nodes.
    Childs must be SVGnodes.

class SVGnode:
    A cocosnode subclass to display a svg file

    Responsabilities:
        handle the anchor_hint
        draw the object
        offer aditional info:
            members min_x, max_x, min_y, max_y describes the bounding box for
            the vertexes in the display list

            members fwidth, fheight gives the width and size for that bounding box.

    Aditional notes:
    Any SVGnode instance must have an SVG_CacheNode ancestor. In practice,
    you probably will create one SVG_CacheNode instance, then add to him a bunch
    of SVGnode instances, and maybe add some more SVGnodes as childs of the lasts.
    If you want to add non SVG class instances as SVGnode childs, you must
    handle set/unset the proper gl state. 

    The __init__ anchor_hint parameter dont translate to standart cocosnode
    anchors members until the SVGnode on_enter gets called.
    In particular, the anchor values are meaningless all along the __init__method.

    The aditional info ( size, bounding box ) is not available until the
    SVGnode on_enter is called. 

    Note that the bounding box and size related members are untransformed values,
    ie dont reflect any rotation or scale.

    The anchor_hint parameter values follow the rosewind analogy, with the
    aditional value 'CC' meaning center. Examples: 'SW' refers to the bounding
    box lower left corner, 'N' (or 'CN' or 'NC') refers to the bb top segment
    center.

function f_rosewind_offset :
    this is a helper used internally to build the anchors from the anchor hint
    and the bounding box.
    It can be handy if you roll your own custom adaptor.

this is a preliminar design; after collecting some use cases things may change.
feel free to mail coments (with concrete use cases samples) to ccanepacc@gmail.com
mention svg or squirtle in the subject, please
or, if fits the cocos-discuss list, mail there.

"""
import os

from pyglet.gl import *
import cocos
import squirtle_core


class SVG_CacheNode(cocos.cocosnode.CocosNode):
    def __init__(self):
        super(SVG_CacheNode,self).__init__()
        self.db = {} # <descriptor> : id_list

    def on_enter(self):#debug
        super(SVG_CacheNode,self).on_enter()
            
    def on_exit(self):
        super(SVG_CacheNode,self).on_exit()
        for e in self.db:
            id_list ,width, height, min_x, max_x, min_y, max_y = self.db[e]
            glDeleteLists( id_list, 1)
        self.db = {}

    def visit(self):
        squirtle_core.begin_svg()
        super(SVG_CacheNode,self).visit()
        squirtle_core.end_svg()

    def add(self, child, z=0, name=None ):
        assert( isinstance(child, SVGnode))
        super(SVG_CacheNode,self).add( child, z=z, name=name) 
    
    #def remove():
    #better caching would need usage cnt to free unused display lists
    #for modest childs quantity sufices with free in on_exit 

    def pre_render(self, descriptor):
        if descriptor not in self.db:
            filename , bezier_divs, circle_divs = descriptor
            id_list ,width, height, min_x, max_x, min_y, max_y = (
                squirtle_core.SVG_pre_render(filename, bezier_divs, circle_divs).get_result())
            self.db[descriptor] = (id_list, width, height, min_x, max_x, min_y, max_y)
        return self.db[descriptor]    

# helper to build common offsets
def f_rosewind_offset(min_x, max_x, min_y, max_y, selector=None):
    """
    Given a bounding box in the form min_x, max_x, min_y, max_y,
    and a two char char string cc where c can be any in 'N','E','S','W','C'
    (NESW hint the cardinal points, C hints center)
    returns an offset ox,oy so that adding the offset to the object position
    then the designated point will overlap position.

    Example (pseudocode):
       ox, oy = f_rosewind(obj.min_x, obj.max_x, obj.min_y, obj.max_y,'NE')
       obj.position += ox,oy
       --> at obj.position will sits the upper right corner of the bounding box
    (feel free to mail me a better description)
    
    Note that your coord system must be that left = W points to negative x,
    top or N points to positive y
       
    Also, 'Cx' , 'xC' performs same as 'x' ( x in NSWEC )

    None and '' (empty string) are aceptable selectors, will act as 'CC' (center)

    Remark: you *add* the offset 
    """
    if selector is None or len(selector)==0:
        selector = 'CC'
    elif len(selector)==1:
        selector += 'C'
    elif len(selector)>2:
        raise KeyError
    c1,c2 = selector
    if c1=='C':
        tmp = c2
        c2 = c1
        c1 = tmp        
    if c1 in 'EW':
        tmp = c2
        c2 = c1
        c1 = tmp
#    print 'canonical anchor:%s%s'%(c1,c2)
    if c1 == 'N':
        oy = max_y
    elif c1 == 'C':
        oy = (min_y+max_y)/2.0
    elif c1 == 'S':
        oy = min_y
    else:
        raise KeyError
    if c2 == 'E':
        ox = max_x
    elif c2 == 'C':
        ox = (min_x+max_x)/2.0
    elif c2 == 'W':
        ox = min_x
    else:
        raise KeyError
    return -ox, -oy


class SVGnode( cocos.cocosnode.CocosNode ):
    is_event_handler = True
    # params adapted from sprite params
    def __init__(self, filename,
                 bezier_divs=squirtle_core.BEZIER_POINTS, circle_divs=squirtle_core.CIRCLE_POINTS,
                 position=(0,0), rotation=0, scale=1.0, anchor_hint = None ):
        self.filename = os.path.abspath(filename)
        self.bezier_divs = bezier_divs
        self.circle_divs = circle_divs
        self._anchor_hint = anchor_hint #unused after 1st on_enter 
        self._anchor_from_hint = True
        
        #To be filled in the first on_enter  
        self.fwidth = None # width as calc from the vertexes (unscaled)
        self.fheight = None # height as calc from the vertexes (unscaled)
        self.min_x = None # vertexes bounding box
        self.max_x = None
        self.min_y = None
        self.man_y = None
        self.display_list = None
        
        super(SVGnode,self).__init__()
        
        #: position of the obj in (x,y) coordinates
        self.position = position

        #: rotation degrees of the obj. Default: 0 degrees
        self.rotation = rotation

        #: scale of the obj where 1.0 the default value
        self.scale = scale
        
    def on_enter(self):
        cache_group = self.get_ancestor(SVG_CacheNode)
        descriptor = self.filename, self.bezier_divs, self.circle_divs
        display_list, width, height, min_x, max_x, min_y, max_y = (
            cache_group.pre_render(descriptor))
        self.display_list = display_list
        self.fwidth = max_x-min_x
        self.fheight = max_y-min_y
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.man_y = max_y
        if self._anchor_from_hint:
            self._anchor_from_hint = False
            self.anchor = f_rosewind_offset(min_x, max_x, min_y, max_y,
                                             selector=self._anchor_hint)
        super(SVGnode,self).on_enter()

    def draw(self):
        glPushMatrix() # preserve
        self.transform() #prepare
        # ... draw ..
        glCallList(self.display_list)
        glPopMatrix() # restore

