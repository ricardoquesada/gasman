from cocos.actions import *
from cocos.layer import ColorLayer
from cocos.scene import Scene
from cocos.director import director

class Quit(InstantAction):
   def start(self):
       raise SystemExit

class TestLayer(ColorLayer):
   def on_enter(self):
       super(TestLayer, self).on_enter()
       action = FadeOut(1)
       self.do(action + Reverse(action) + Quit())

director.init()
director.run(Scene(TestLayer(255,0,0,100)))
