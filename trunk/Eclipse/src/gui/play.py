'''
Created on 4 janv. 2012

@author: jglouis
'''
from cocos.scene import Scene
from cocos.layer.base_layers import Layer
from cocos.text import Label
from cocos.director import director
from cocos.scenes.transitions import FadeUpTransition, FadeDownTransition
from cocos.layer.util_layers import ColorLayer
from cocos.draw import Line
import math
from cocos.layer.scrolling import ScrollableLayer, ScrollingManager
import pyglet
from cocos.sprite import Sprite
from hexmanager import HexManager
from cocos.actions.base_actions import IntervalAction
import random
from engine.zone import Sector, ResourceSlot
from engine.component import InfluenceDisc, Ship, Interceptor, Cruiser
from pyglet.window.mouse import LEFT, RIGHT
from pyglet.event import EVENT_HANDLED
from cocos.rect import Rect

pyglet.resource.path.append('./image')
pyglet.resource.path.append('../image')
pyglet.resource.path.append('./font')
pyglet.resource.path.append('../font')
pyglet.resource.path.append('./gui')
pyglet.resource.reindex()
try:
    pyglet.font.add_directory('font')
except:
    pyglet.font.add_directory('../font')
    
def color_convert(text):
    if text == 'blank':
        return (255,255,255)
    if text == 'red':
        return (255,0,0)
    if text == 'green':
        return (0,255,0)
    if text == 'blue':
        return (0,0,255)
    if text == 'yellow':
        return (255,255,0)
    if text == 'black':
        return (50,50,50)
    if text == 'grey':
        return (150,150,150)


class SelectableSprite(Sprite):
    def __init__(self, obj, *args, **kwargs):
        super(SelectableSprite, self).__init__(*args, **kwargs)
        self.obj = obj
        
class BoardLayer(ScrollableLayer):
    is_event_handler = True
    def __init__(self, scroller, info_layer, game):
        self.px_width = 6000
        self.px_height = 6000
        super(BoardLayer, self).__init__()
        self.add(Label('BoardLayer'))
        #self.add(Sprite(pyglet.resource.image('mkw.jpg'), scale = 3, position = (self.px_width / 2, self.px_height / 2)), -1)
        #self.add(Sprite(pyglet.resource.animation('planet.gif'), scale = 0.5, position = (self.px_width / 2, self.px_height / 2)))
        self.hex_width = 200
        self.hex_manager = HexManager(self.hex_width, (self.px_width / 2, self.px_height / 2))
        self.scroller = scroller
        self.scroller.set_focus(self.px_width / 2, self.px_height / 2)
        self.info_layer = info_layer
        self.game = game
        self.hex_color_sprites = {}

        if self.game:
            for coord, sector in self.game.board.get_content().iteritems():
                self.display_sector(coord)
    
    def set_hex_color(self, coord, color):
        color = color_convert(color)
        if coord in self.hex_color_sprites:
            self.hex_color_sprites[coord].color = color
        else:
            u, v = coord
            rect_position = self.hex_manager.get_rect_coord_from_hex_coord(u, v)
            hexa = Sprite('infhexa.png', 
                scale = 0.85,
                position = rect_position,
                color = color)
            self.add(hexa)
            self.hex_color_sprites[coord] = hexa
        
    def display_sector(self, coord):
        u, v = coord
        sector = self.game.board.get_content()[coord]
        rect_position = self.hex_manager.get_rect_coord_from_hex_coord(u, v)
        #hex_color
        try:
            color = sector.get_content(InfluenceDisc)[0].color
        except:
            color = 'grey'
        self.set_hex_color(coord, color)
        
        #ships
        for ship in sector.get_content(Ship):
            if isinstance(ship, Interceptor):
                ship_picture = 'interceptor.png'
            elif isinstance(ship, Cruiser):
                ship_picture = 'cruiser.png'
            ship_coord = self.hex_manager.get_fleet_coord(u, v)
            ship_sprite = SelectableSprite(ship,
                                           ship_picture,
                                           scale = 0.2,
                                           position = ship_coord,
                                           color = color_convert(ship.color)
                                           )
            self.add(ship_sprite, z = 2)
        #planets
        ordered_slots = [slot for slot in sector.get_content(ResourceSlot)]
        ordered_slots.sort(key=lambda x: x.resource_type)
        type_of_planets = set([slot.resource_type for slot in ordered_slots])
        for rt,scoord in zip(type_of_planets, self.hex_manager.get_planets_coord(u, v)):
            color = {None       :(255,255,255),
                     'money'    :(212,100,4),
                     'material' :(136,72,41),
                     'science'  :(230,146,161)
                     }[rt]
            planet_sprite = Sprite('planet.png',
                                   position = scoord,
                                   scale = 0.05,
                                   color = color
                                   )
            self.add(planet_sprite, z = 1)
        #vp
        vp = sector.victory_points
        vp_picture = {1 :'reputation1.png',
                      2 :'reputation2.png',
                      3 :'reputation3.png',
                      4 :'reputation4.png'}[vp]
        vp_sprite = Sprite(vp_picture,
                           position = rect_position,
                           scale = 0.2)
        self.add(vp_sprite, z = 1)

    def on_mouse_press (self, x, y, button, modifiers):        
        x, y = self.scroller.pixel_from_screen(x,y)
        hex_u, hex_v = self.hex_manager.get_hex_from_rect_coord(x, y)
        coord = (hex_u, hex_v)
        
        for child in self.get_children():            
            if isinstance(child, SelectableSprite):
                if child.get_AABB().contains(x, y):
                    print child.obj
                
        if self.game:          
            
            
            sector = self.game.board.get_content(coord, Sector)
            
            #explore the sector if right click and sector empty
            #influence the sector if right click and not empty
            if button == RIGHT:   
                if sector is None:    
                    sector_tile = self.game.draw_hex(coord)
                    if sector_tile is not None:
                        self.game.place_hex(sector_tile, coord)
                        self.info_layer.set_info('New Sector discovered: ' + sector_tile.name)
                        self.display_sector(coord)
                    else:
                        self.info_layer.set_info('No New Sector to explore -Aborting')
                elif len(sector.get_content(InfluenceDisc)) == 0:
                                             
                    self.game.move(zone_from = self.game.current_player.personal_board.influence_track, zone_to = sector)
                    self.set_hex_color(coord, self.game.current_player.color)
                    self.info_layer.set_info('Influence on sector '+ sector.name)
                else:
                    self.info_layer.set_info('Action not recognized') 
            
            elif sector is not None:
                self.info_layer.set_info(str(sector))
            else:
                self.info_layer.set_info('Unknown Sector')
        
        self.game.end_turn()             
        
    def on_mouse_motion(self, x, y, dx, dy):    
        x, y = self.scroller.pixel_from_screen(x,y)
        hex_u, hex_v = self.hex_manager.get_hex_from_rect_coord(x, y)
        hex_x, hex_y = self.hex_manager.get_rect_coord_from_hex_coord(hex_u, hex_v)
        for child in self.get_children():
            if isinstance(child, Line):
                child.kill()
        self.add_hex((hex_x, hex_y), self.hex_width / 2)
        #self.add(Line((500,500),(600,500), (255,255,255,255), 3))
        
        
    def add_hex(self, centre, r):        
        hex_coord = []
        hex_centre = centre
        hex_r = r
        hex_coord.append((hex_centre[0],                hex_centre[1] + 2 * hex_r / math.sqrt(3)))
        hex_coord.append((hex_centre[0] + hex_r,        hex_centre[1] + hex_r / math.sqrt(3)))
        hex_coord.append((hex_centre[0] + hex_r,        hex_centre[1] - hex_r / math.sqrt(3)))
        hex_coord.append((hex_centre[0],                hex_centre[1] - 2 * hex_r / math.sqrt(3)))
        hex_coord.append((hex_centre[0] - hex_r,        hex_centre[1] - hex_r / math.sqrt(3)))
        hex_coord.append((hex_centre[0] - hex_r,        hex_centre[1] + hex_r / math.sqrt(3)))       
        w = 3        
        line1 = Line(hex_coord[0], hex_coord[1],(255,255,255,255) , w)
        line2 = Line(hex_coord[1], hex_coord[2],(255,255,255,255) , w)
        line3 = Line(hex_coord[2], hex_coord[3],(255,255,255,255) , w)
        line4 = Line(hex_coord[3], hex_coord[4],(255,255,255,255) , w)
        line5 = Line(hex_coord[4], hex_coord[5],(255,255,255,255) , w)
        line6 = Line(hex_coord[5], hex_coord[0],(255,255,255,255) , w)
        self.add(line1, 2)
        self.add(line2, 2)
        self.add(line3, 2)
        self.add(line4, 2)
        self.add(line5, 2)
        self.add(line6, 2)   
        
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.scroller.scale += scroll_y * 0.1
        self.scroller.scale = min(max(self.scroller.scale, 0.2), 2)
                
    def on_key_press(self, key, modifiers):
        pass
        
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers ):
        fx, fy = self.scroller.fx, self.scroller.fy
        xdx, ydy = self.scroller.pixel_from_screen(x + dx, y + dy)
        x, y = self.scroller.pixel_from_screen(x, y)        
        dx = xdx - x
        dy = ydy - y
        x_focus = fx - dx
        y_focus = fy - dy
        self.scroller.set_focus(x_focus, y_focus)
        
    def on_enter(self):
        super(BoardLayer, self).on_enter()
        self.scroller = self.get_ancestor(ScrollingManager)
        
class PlayerBoardLayer(Layer):
    is_event_handler = True
    def __init__(self, player):
        super(PlayerBoardLayer, self).__init__()
        self.add(Label('PlayerBoardLayer'))
        width,height = director.get_window_size()
        position = (width/2, height/2)
        picture_name = 'player_board_' +\
                        player.color +\
                        ('_terran' if 'terran' in player.faction.name else '_alien') +\
                        '.jpg'
        player_board_sprite = Sprite(picture_name,
                                     scale = 0.45,
                                     position = position                              
                                     )
        self.add(player_board_sprite)
        #defining the rectangular zone
        self.rect_player_board = player_board_sprite.get_AABB()
        width, heigth = self.rect_player_board.size
        x, y = self.rect_player_board.bottomleft
        self.rect_influence = Rect(x + width * 0.107, 
                                   y + height * 0.075, 
                                   width * 0.72, 
                                   heigth * 0.07)
        self.draw_rect(self.rect_influence)
        
    def draw_rect(self, rect):   
        for line in ((rect.topleft,     rect.topright), 
                     (rect.topright,    rect.bottomright),
                     (rect.bottomright, rect.bottomleft),
                     (rect.bottomleft,  rect.topleft)):
            self.add(Line(line[0], line[1], (255,255,255,255)), 2)
            
    def on_mouse_press (self, x, y, button, modifiers):
        x, y = director.get_virtual_coordinates(x, y)
        print self.rect_player_board.contains(x,y)
        
class ReasearchTrackLayer(Layer):
    def __init__(self):
        super(ReasearchTrackLayer, self).__init__()
        
class ControlLayer(Layer):
    is_event_handler = True    
    def __init__(self,game):
        super(ControlLayer, self).__init__()
        self.game = game
        
    def on_key_press(self, key, modifiers):
        if key == 112:
            index = self.game.players.index(self.game.current_player) + 1 
            director.replace(FadeDownTransition(self.control_list[index], duration = 0.2))
        elif key == 98:
            director.replace(FadeUpTransition(self.control_list[0], duration = 0.2))
        elif 65462 >= key >= 65457:
            director.replace(FadeDownTransition(self.control_list[key-65456], duration = 0.2))
            
class InfoLayer(Layer):
    def __init__(self):
        super(InfoLayer, self).__init__()
        self.base_color = (0, 205, 0, 200)
        self.info = Label('', 
                          (0, director.get_window_size()[1] - 50),
                          font_name = 'Estrogen',
                          font_size = 15,
                          color = self.base_color,
                          width = 1000,
                          multiline = True)
        self.add(self.info)
        
        self.schedule_interval(self.update_time, .1)

    def update_time(self, dt):
        new_color = [0, random.randint(230,255), 0, 255]       
        self.info.element.color = new_color
        
    def set_info(self, text):
        self.info.do(InfoAction(text, '_', 0.4))
        
class ActionLayer(Layer):
    is_event_handler = True
    def __init__(self, game):
        super(ActionLayer, self).__init__()
        self.game = game
        self.action_board_sprite = Sprite('action_board_terran.png', scale = 0.3)
        #self.action_board_sprite.transform_anchor = (1,100000)
        self.add(self.action_board_sprite)
        self.action_board_sprite.position = self.action_board_sprite.get_AABB().topleft
        self.action_board_sprite.x += director.get_window_size()[0]
        self.action_list = ('Explore',
                            'Influence',
                            'Research',
                            'Upgrade',
                            'Build',
                            'Move'
                            )
        self.action_position = [0.2, 1.12, 2.05, 3, 3.95, 4.9]
        self.selection_sprite = Sprite('action_selection_halo.png', scale = 0.3, position = self.action_board_sprite.position)
        
    def on_mouse_press(self, x, y, button, modifiers): 
        rect = self.action_board_sprite.get_AABB()        
        x, y = director.get_virtual_coordinates(x, y)
        if rect.contains(x, y):
            dx = (rect.right - rect.left) / 6.0
            for n in range(6):
                if rect.left + dx * n < x < rect.left + dx * (n + 1):
                    self.parent.info_layer.set_info('Select Action: ' + self.action_list[n])
                    self.add(self.selection_sprite)
                    self.selection_sprite.x = rect.left + (self.action_position[n] + 0.5) * dx 
                    self.selection_sprite.color = color_convert(self.game.current_player.color)
                    return EVENT_HANDLED
                   
class BoardScene(Scene):
    def __init__(self, control_layer, game):
        super(BoardScene, self).__init__()
        self.add(ColorLayer(0,0,0,255), 0)
        scroller = ScrollingManager()        
        self.info_layer = InfoLayer()
        action_layer = ActionLayer(game)
        scroller.add(BoardLayer(scroller, self.info_layer, game))
        self.add(scroller)
        self.add(control_layer, 2)
        self.add(self.info_layer, 3)
        self.add(action_layer, 4)
        
class PlayerBoardScene(Scene):
    def __init__(self, control_layer, player):
        super(PlayerBoardScene, self).__init__()
        self.add(ColorLayer(200,200,200,255), 0)
        self.add(PlayerBoardLayer(player), 1)
        self.add(control_layer, 2)
        
class MainScreen(object):
    def __init__(self, game):  
        director.init(fullscreen = False, resizable = True, do_not_scale = False, width = 1200, height = 800)
        self.control_layer = ControlLayer(game)
        board_scene = BoardScene(self.control_layer, game)
        player_board_scenes = []
        for player in game.players:
            player_board_scenes.append(PlayerBoardScene(self.control_layer, player))
        self.control_layer.control_list = [board_scene] + player_board_scenes
        director.run(board_scene)
        
class InfoAction(IntervalAction):
    """Action that can be applied to any Label to make a dynamic text display
    """
    def init(self, word, post_text, duration ):
        self.duration = duration    #: Duration in seconds
        self.word = word
        self.word_size = len(word)
        self.post_text = post_text
        
    def start(self):
        self.current_text = ''    
        
    def update(self, t):
        current_text_size = int(t * self.word_size)
        self.current_text = self.word[0:current_text_size]
        self.current_text += self.post_text
        self.target.element.text = self.current_text
        
    def __reversed__(self):
        pass
        
if __name__ == "__main__":
    MainScreen(None)