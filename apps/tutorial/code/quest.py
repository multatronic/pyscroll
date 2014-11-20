""" Quest - An epic journey.

Simple game that demonstrates PyTMX and pyscroll.

requires pygame and pytmx.

https://github.com/bitcraft/pytmx
"""

import os.path
import pygame
from pyscroll import OrthogonalRenderer, ScrollGroup
from pyscroll.tiled import TiledMapData
from pytmx.util_pygame import load_pygame
from pygame.locals import *


# define configuration variables here
RESOURCES_DIR = 'data'
HERO_MOVE_SPEED = 200  # pixels per second
MAP_FILENAME = 'grasslands.tmx'

# global used for 2x scaling.  see the game loop run code for info
temp_surface = None


# simple wrapper to keep the screen resizeable
def init_screen(width, height):
    global temp_surface
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    temp_surface = pygame.Surface((width / 2, height / 2)).convert()
    return screen


# make loading stuff a little easier by doing path transformations
def get_map(filename):
    return os.path.join(RESOURCES_DIR, filename)

def load_image(filename):
    return pygame.image.load(os.path.join(RESOURCES_DIR, filename))


class Hero(pygame.sprite.Sprite):
    """ Our Beloved Hero

    The Hero has two collision rects:
       one for the whole sprite: "rect"
       and another to check collisions with walls: "feet"

    The position list is used because pygame rects are inaccurate for
    positioning sprites; because the values they get are 'rounded down' to
    integers, the sprite would move faster moving left or up.  The values in
    position are floats.  The old_position attribute is used to move the sprite
    back in case there is a collision.

    Feet is 1/2 as wide as the normal rect, and 8 pixels tall.  This size size
    allows the top of the sprite to overlap walls.

    The game hero has a somewhat complicated way to move, compared to the way
    most pygame tutorials tell you.  It is actually more close to modern games
    with physics engines, so don't feel scared now~

    The benefits are that you can be assured that the movement will be the same
    on fast or slow computers, even with a low framerate and it prevents
    ingeter truncation from giving you odd speed.  Integer truncation happens
    with pygame rects.

    Essentially:
       - each game loop input check
       1) determine if the arrow keys are pressed
       2) instead of moving the rect or position directly, set the velocity

       - each game loop update, check the hero's velocity
       3) multiply the velocity by the amount of time that has passed
       4) set the position of the hero to the value found in #1
       5) rejoice in smooth framerate independent movement
    """

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image('hero.png').convert_alpha()
        self.velocity = [0, 0]
        self._position = [0, 0]
        self._old_position = self.position
        self.rect = self.image.get_rect()
        self.feet = pygame.Rect(0, 0, self.rect.width * .5, 8)

    @property
    def position(self):
        return list(self._position)

    @position.setter
    def position(self, value):
        self._position = list(value)

    def update(self, dt):
        """
        1) Save the current position to _old_position
        2) Multiply the current
        """
        self._old_position = self._position[:]
        self._position[0] += self.velocity[0] * dt
        self._position[1] += self.velocity[1] * dt
        self.rect.topleft = [round(i, 0) for i in self._position]
        self.feet.midbottom = self.rect.midbottom

    def move_back(self, dt):
        """ If called after an update, the sprite can move back
        """
        self._position = self._old_position
        self.rect.topleft = self._position
        self.feet.midbottom = self.rect.midbottom


class QuestGame(object):
    """ This class is a basic game.

    This class will load data, create a pyscroll group, a hero object.  It also
    reads input and moves the Hero around the map. Finally, it uses a pyscroll
    group to render the map and Hero.
    """
    filename = get_map(MAP_FILENAME)

    def __init__(self):

        # true while running
        self.running = False

        """
        pyscroll requires a data source so it can get information about how to
        place the tiles.  To do so, it requires a source that has certain
        methods (see the AbstractMapData class...duck typing FTW!).  Here I will
        be using the TiledMapData class, which is able to use maps loaded from
        pytmx.

        pytmx.util_pygame.load_pygame() will load a map and all the images for
        the tiles.  If you make your own data class, you will need to make sure
        that you have all the surfaces loaded.
        """
        tmx_data = load_pygame(self.filename)
        map_data = TiledMapData(tmx_data)
        self.map_layer = OrthogonalRenderer(map_data)

        """
        A game isn't fun if you can't run your head into walls!  Or something.
        Here I am going to build a simple collision system from data in the TMX
        map.  It is simply getting all the objects in the map and using their
        size and position to make a list of pygame Rects.  Later, that list of
        rects will be used to check for collisions.  I will store the rects in
        QuestGame.walls.
        """
        self.walls = list()
        for object in tmx_data.objects:
            self.walls.append(pygame.Rect(
                object.x, object.y,
                object.width, object.height))

        """
        pyscroll supports layered rendering.

        The tutorial map has 3 layers and they are zero-indexed:
           0) solid ground tiles
           1) partial tiles and walls
           2) stuff that is really tall

        We want the sprites to cover the ground and walls (layers #0 and #1),
        but also be covered by the top layer of the map (#2).  Since we want the
        sprites to be on top of layer 0 and 1, we set the default layer for
        sprites as 2.  Layers that are the same number or higher than a sprite
        will cover it.
        """
        self.group = ScrollGroup(map_layer=self.map_layer, default_layer=2)

        """
        Now we make our Hero, which is our slightly better than pygame Sprite,
        but it is still a subclass of pygame.sprite.Sprite, so it can be added
        to groups, drawn by groups, etc
        """
        self.hero = Hero()
        self.group.add(self.hero)

        """
        pyscroll maps by default set the camera center to the center of the map,
        so we are taking advantage of that by getting the center of the map from
        the camera and setting the Hero's position there.
        """
        self.hero.position = self.map_layer.map_rect.center

    def draw(self, surface):
        """ draw the game to the screen (actually, a buffer because we have a
        pixelated look)
        """

        """
        pyscroll doesn't follow sprites, so you need to set the center each time
        the map is drawn.  Luckily it isn't difficult to do, just supply (x, y).
        Here were get the center of the hero rect and draw like a normal group.
        """
        self.group.center(self.hero.rect.center)
        self.group.draw(surface)

    def handle_input(self):
        """ Handle pygame input events
        """
        event = pygame.event.poll()
        while event:
            if event.type == QUIT:
                self.running = False
                break

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                    break

            elif event.type == VIDEORESIZE:
                """
                This bit of sorcery allows the game window to be resized. yay!~~
                """
                init_screen(event.w, event.h)
                self.map_layer.size = (event.w / 2, event.h / 2)

            event = pygame.event.poll()

        # using get_pressed is slightly less accurate than testing for events
        # but is much easier to use.
        pressed = pygame.key.get_pressed()
        if pressed[K_UP]:
            self.hero.velocity[1] = -HERO_MOVE_SPEED
        elif pressed[K_DOWN]:
            self.hero.velocity[1] = HERO_MOVE_SPEED
        else:
            self.hero.velocity[1] = 0

        if pressed[K_LEFT]:
            self.hero.velocity[0] = -HERO_MOVE_SPEED
        elif pressed[K_RIGHT]:
            self.hero.velocity[0] = HERO_MOVE_SPEED
        else:
            self.hero.velocity[0] = 0

    def update(self, dt):
        """ Tasks that occur over time should be handled here
        """
        self.group.update(dt)

        # check if the sprite's feet are colliding with wall
        # sprite must have a rect called feet, and move_back method,
        # otherwise this will fail
        for sprite in self.group.sprites():
            if sprite.feet.collidelist(self.walls) > -1:
                sprite.move_back(dt)

    def run(self):
        """ Run the game loop
        """
        fps = 60
        clock = pygame.time.Clock()
        scale = pygame.transform.scale
        self.running = True

        try:
            while self.running:
                dt = clock.tick(fps) / 1000.
                self.handle_input()
                self.update(dt)

                """
                To get the cool pixelated look, I do a couple steps:
                   1) use a temporary surface that is 1/2 the screen size
                   2) draw everything to the temp surface
                   3) scale the temp surface to the display surface
                """
                self.draw(temp_surface)
                scale(temp_surface, screen.get_size(), screen)
                pygame.display.flip()

        except KeyboardInterrupt:
            self.running = False


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    screen = init_screen(800, 600)
    pygame.display.set_caption('Quest - An epic journey.')

    try:
        game = QuestGame()
        game.run()
    except:
        pygame.quit()
        raise
