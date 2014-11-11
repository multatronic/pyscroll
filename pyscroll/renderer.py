import math
import threading
from functools import partial
from itertools import islice, product, chain

import pygame
import pygame.gfxdraw
from pygame.compat import xrange_

from . import quadtree


__all__ = ['OrthogonalRenderer']


class AbstractRenderer(object):
    """ Renderer that can be updated incrementally

    Base class to render a map onto a buffer that is suitable for blitting onto
    the screen as one surface, rather than a collection of tiles.

    The buffered renderer must be used with a data class to get tile and shape
    information.  See the data class api in pyscroll.data, or use the built in
    pytmx support.  Data for the render must follow the specified format.
    """

    def __init__(self, data, size, colorkey=None, padding=4,
                 clamp_camera=False):

        # default public values
        self.padding = padding
        self.clamp_camera = clamp_camera
        self.flush_on_draw = True
        self.update_rate = 100
        self.map_rect = None
        self.default_shape_texture_gid = 1
        self.default_shape_color = (0, 255, 0)
        self.default_image = None

        # internal names
        self._lock = threading.Lock()
        self._idle = False
        self._blank = False
        self._view = None
        self._half_width = None
        self._half_height = None
        self._offset_x = None
        self._offset_y = None
        self._previous_x = None
        self._previous_y = None
        self._buffer = None
        self._colorkey = None
        self._size = None
        self._data = None
        self._layer_quadtree = None

        # set the instance up
        self._colorkey = colorkey
        self.data = data
        self.size = size
        self.queue = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.generate_default_image()

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        """ Set the size of the map in pixels and init the buffer
        """
        data = self.data
        tw = data.tilewidth
        th = data.tileheight

        # this is the pixel size of the entire map
        self.map_rect = pygame.Rect(0, 0, data.width * tw, data.height * th)

        buffer_width = size[0] + tw * self.padding
        buffer_height = size[1] + th * self.padding
        self._buffer = pygame.Surface((buffer_width, buffer_height))
        self._view = pygame.Rect(0, 0, math.ceil(buffer_width / tw),
                                 math.ceil(buffer_height / th))

        self._half_width = size[0] / 2
        self._half_height = size[1] / 2

        # quadtree is used to correctly draw tiles that cover 'sprites'
        mk_rect = lambda x, y: pygame.Rect((x * tw, y * th), (tw, th))

        rects = [mk_rect(x, y)
                 for x, y in product(xrange_(self._view.width),
                                     xrange_(self._view.height))]

        # TODO: figure out what depth -actually- does (benchmark it?)
        self._layer_quadtree = quadtree.FastQuadTree(rects, 2)

        if self._colorkey is not None:
            self.colorkey = self._colorkey

        self._size = size
        self._idle = False
        self._blank = True
        self._offset_x = 0
        self._offset_y = 0
        self._previous_x = 0
        self._previous_y = 0

    @property
    def colorkey(self):
        return self._colorkey

    @colorkey.setter
    def colorkey(self, value):
        self._colorkey = pygame.Color(value)
        self._buffer.set_colorkey(self._colorkey)
        self._buffer.fill(self._colorkey)

    def generate_default_image(self):
        raise NotImplementedError

    def scroll(self, vector):
        """ scroll the background in pixels
        """
        raise NotImplementedError

    def center(self, point):
        """ center the map on a pixel
        """
        raise NotImplementedError

    def blit_tiles(self, iterator):
        raise NotImplementedError

    def get_filled_queue(self):
        """ get iterator of all tiles in the current view
        """
        raise NotImplementedError

    def get_edge_tiles(self, offset):
        """ Get the tile coordinates that need to be redrawn
        """
        raise NotImplementedError

    def do_overdraw(self, surface, offset, surfaces):
        """ redraw tiles that were covered by sprites
        """
        return list()

    def get_tile_image(self, position):
        try:
            return self.data.get_tile_image(position)
        except ValueError:
            return self.default_image

    def draw(self, surface, area=None, surfaces=None):
        """ Draw the map onto a surface

        pass a rect that defines the draw area for:
            dirty screen update support
            drawing to an area smaller that the whole window/screen

        surfaces may optionally be passed that will be blitted onto the surface.
        this must be a list of tuples containing a layer number, image, and
        rect in screen coordinates.  surfaces will be drawn in order passed,
        and will be correctly drawn with tiles from a higher layer overlapping
        the surface.
        """
        if self._blank:
            self._blank = False
            self.redraw()

        elif self.flush_on_draw:
            self.flush()

        original_clip = None
        if area is not None:
            original_clip = surface.get_clip()
            surface.set_clip(area)

        # draw the entire map to the surface,
        # taking in account the scrolling offset
        ox, oy = self._offset_x - area.left, self._offset_y - area.top

        if self._idle:
            # this gigantic blit could be changed to dirty rect someday
            surface.blit(self._buffer, (-ox, -oy))
            dirty = self.do_overdraw(surface, (ox, oy), surfaces)
        else:
            surface.blit(self._buffer, (-ox, -oy))
            self.do_overdraw(surface, (ox, oy), surfaces)
            dirty = [area]

        if original_clip is not None:
            surface.set_clip(original_clip)

        return dirty

    def redraw(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        self.queue = self.get_filled_queue()
        self.flush()

    def update_queue(self, iterator):
        """ Add some tiles to the queue
        """
        if self.queue is None:
            self.queue = iterator
        else:
            self.queue = chain(self.queue, iterator)

    def update(self, dt=None):
        """ Draw tiles in the background

        the drawing operations and management of the buffer is handled here.
        if you are updating more than drawing, then updating here will draw
        off screen tiles.  this will limit expensive tile blits during screen
        draws.  if your draw and update happens every game loop, then you will
        not benefit from updates, but it won't hurt either.
        """
        if self.queue is not None:
            self.blit_tiles(islice(self.queue, self.update_rate))

    def flush(self):
        """ Blit the tiles and block until the tile queue is empty
        """
        if self.queue is not None:
            self.blit_tiles(self.queue)


class OrthogonalRenderer(AbstractRenderer):
    """ Scrolling map renderer for orthographical maps.
    """
    @property
    def sprite_offset(self):
        return (-self._previous_x + self._half_width,
                -self._previous_y + self._half_height)

    def get_filled_queue(self):
        return product(xrange_(self._view.left, self._view.right),
                       xrange_(self._view.top, self._view.bottom),
                       self.data.visible_tile_layers)

    def get_edge_tiles(self, offset):
        """ Get the tile coordinates that need to be redrawn
        """
        x, y = map(int, offset)
        layers = list(self.data.visible_tile_layers)
        view = self._view
        queue = None

        # NOTE: i'm not sure why the the -1 in right and bottom are required
        # for python 3.  it may have some performance implications, but
        # i'll benchmark it later.

        # right
        if x > 0:
            queue = product(xrange_(view.right - x - 1, view.right),
                            xrange_(view.top, view.bottom), layers)

        # left
        elif x < 0:
            queue = product(xrange_(view.left, view.left - x),
                            xrange_(view.top, view.bottom), layers)

        # bottom
        if y > 0:
            p = product(xrange_(view.left, view.right),
                        xrange_(view.bottom, view.bottom - y - 1, -1), layers)
            queue = p if queue is None else chain(p, queue)

        # top
        elif y < 0:
            p = product(xrange_(view.left, view.right),
                        xrange_(view.top, view.top - y), layers)
            queue = p if queue is None else chain(p, queue)

        return queue

    def generate_default_image(self):
        self.default_image = pygame.Surface((self.data.tilewidth,
                                             self.data.tileheight))
        self.default_image.fill((0, 0, 0))

    def do_overdraw(self, surface, offset, surfaces):
        def above(x, y):
            return x > y

        surface_blit = surface.blit
        ox, oy = offset
        left, top = self._view.topleft
        hit = self._layer_quadtree.hit
        get_tile = self.get_tile_image
        tile_layers = tuple(self.data.visible_tile_layers)

        dirty = [(surface_blit(i[0], i[1]), i[2]) for i in surfaces]
        for dirty_rect, layer in dirty:
            for r in hit(dirty_rect.move(ox, oy)):
                x, y, tw, th = r
                for l in [i for i in tile_layers if above(i, layer)]:
                    tile = get_tile((int(x / tw + left),
                                     int(y / th + top), int(l)))
                    if tile:
                        surface_blit(tile, (x - ox, y - oy))

        return dirty

    def center(self, coords):
        """ center the map on a pixel
        """
        x, y = [round(i, 0) for i in coords]
        hpad = int(self.padding / 2)
        tw = self.data.tilewidth
        th = self.data.tileheight

        if self.clamp_camera:
            if x < self._half_width:
                x = self._half_width
            elif x + self._half_width > self.map_rect.width:
                x = self.map_rect.width - self._half_width
            if y < self._half_height:
                y = self._half_height
            elif y + self._half_height > self.map_rect.height:
                y = self.map_rect.height - self._half_height

        if self._previous_x == x and self._previous_y == y:
            self._idle = True
            return

        self._idle = False

        # calc the new position in tiles and offset
        left, self._offset_x = divmod(x - self._half_width, tw)
        top, self._offset_y = divmod(y - self._half_height, th)

        # determine if tiles should be redrawn
        dx = int(left - hpad - self._view.left)
        dy = int(top - hpad - self._view.top)

        # adjust the offsets of the buffer
        self._offset_x += hpad * tw
        self._offset_y += hpad * th

        # adjust the view if the buffer is scrolled too far
        if (abs(dx) >= 1) or (abs(dy) >= 1):
            self.flush()
            self._view = self._view.move((dx, dy))

            # scroll the image (much faster than redrawing the tiles!)
            self._buffer.scroll(-dx * tw, -dy * th)
            self.update_queue(self.get_edge_tiles((dx, dy)))

        self._previous_x, self._previous_y = x, y

    def scroll(self, vector):
        """ scroll the background in pixels
        """
        self.center((vector[0] + self._previous_x, vector[1] + self._previous_y))

    def blit_tiles(self, iterator):
        """ Bilts (x, y, layer) tuples to buffer from iterator
        """
        tw = self.data.tilewidth
        th = self.data.tileheight
        blit = self._buffer.blit
        ltw = self._view.left * tw
        tth = self._view.top * th
        get_tile = self.get_tile_image
        colorkey = self.colorkey

        if colorkey:
            fill = partial(self._buffer.fill, colorkey)
            old_tiles = set()
            for x, y, l in iterator:
                tile = get_tile((x, y, l))
                if tile:
                    if l == 0:
                        fill((x * tw - ltw, y * th - tth, tw, th))
                    old_tiles.add((x, y))
                    blit(tile, (x * tw - ltw, y * th - tth))
                else:
                    if l > 0:
                        if (x, y) not in old_tiles:
                            fill((x * tw - ltw, y * th - tth, tw, th))
        else:
            for x, y, l in iterator:
                tile = get_tile((x, y, l))
                if tile:
                    blit(tile, (x * tw - ltw, y * th - tth))

        self.queue = None
