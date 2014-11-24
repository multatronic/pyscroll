import threading
from math import ceil
from functools import partial
from itertools import product, chain

import pygame
from pygame.compat import xrange_

from . import quadtree


__all__ = ['AbstractRenderer', 'OrthogonalRenderer']


class AbstractRenderer(object):
    """ Renderer that can be updated incrementally

    Base class to render a map onto a surface that is suitable for blitting onto
    the screen at once, rather than a collection of tiles.
    """

    def __init__(self, data, colorkey=None, padding=4, clamp_camera=True):

        # default public values
        self.padding = padding
        self.clamp_camera = clamp_camera
        self.flush_on_draw = True
        self.update_rate = 10
        self.map_rect = None
        self.default_tile = None
        self.background_color = (0, 0, 0)

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
        self._size = None
        self._data = None
        self._layer_quadtree = None
        self._centered_point = None

        # set the instance up
        self._colorkey = colorkey
        self.data = data
        self.queue = None

    @property
    def data(self):
        """ Get or set data used to render the map.  The data must conform to
        the AbstractMapData class defined in pyscroll.data.
        """
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        self._generate_default_tile()

        # this is the pixel size of the entire map
        self.map_rect = pygame.Rect(0, 0,
                                    data.width * data.tile_width,
                                    data.height * data.tile_height)

    @property
    def size(self):
        """ Get or set the size of the rendered map view in pixels.
        """
        return self._size

    @size.setter
    def size(self, size):
        tw = self._data.tile_width
        th = self._data.tile_height

        buffer_width = size[0] + tw * self.padding
        buffer_height = size[1] + th * self.padding
        self._buffer = pygame.Surface((buffer_width, buffer_height))
        self._view = pygame.Rect(0, 0, ceil(buffer_width / tw),
                                 ceil(buffer_height / th))

        self._half_width, self._half_height = [i / 2 for i in size]

        rects = [pygame.Rect((x * tw, y * th), (tw, th))
                 for x, y in product(*map(xrange_, self._view.size))]

        self._layer_quadtree = quadtree.FastQuadTree(rects, 4)

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
        """ Get or set the colorkey of the map tiles.
        """
        return self._colorkey

    @colorkey.setter
    def colorkey(self, value):
        if value is None:
            self._colorkey = None
            self._buffer.set_colorkey(None)
        else:
            self._colorkey = pygame.Color(value)
            self._buffer.set_colorkey(self._colorkey)
            self._buffer.fill(self._colorkey)

    @property
    def sprite_offset(self):
        """ This value is used to determine the offset from a sprites 'world'
        position and their position on the screen.

        :return: offset of sprites
        :rtype: (x, y)
        """
        raise NotImplementedError

    def draw(self, surface, area=None, surfaces=None):
        """ Draw the map onto a surface.

        Surfaces may optionally be passed that will be coalesced during draw.
        These surfaces will be drawn correctly to show layer depth.  The
        sequence must be a list of tuples containing a layer number, image, and
        rect in screen coordinates.  Surfaces will be drawn in order passed and
        will be correctly drawn with tiles from a higher layer overlapping the
        surface.

        :param surface: Where map will be drawn to
        :type surface: pygame.surface.Surface
        :param area: (Optional) Define area to be drawn on the surface
        :type area: pygame.rect.Rect
        :param surfaces: (layer, surface, rect) list to be coalesced during draw
        :type surfaces: sequence
        """

        if self._blank:
            if self.size is None:
                if area is None:
                    self.size = surface.get_rect().size
                else:
                    self.size = pygame.Rect(area).size
            self.redraw()
            self._blank = False

        else:
            if self._centered_point is not None:
                self._center_map(self._centered_point)
                self._centered_point = None

        if self.queue and self.flush_on_draw:
            self._flush()

        original_clip = None
        if area is not None:
            original_clip = surface.get_clip()
            surface.set_clip(area)

        offset = -self._offset_x - area.left, -self._offset_y - area.top

        if self._idle:
            surface.blit(self._buffer, offset)
            if surfaces is not None:
                dirty = self._overdraw(surface, offset, surfaces)
            else:
                dirty = None
        else:
            surface.blit(self._buffer, offset)
            if surfaces is not None:
                self._overdraw(surface, offset, surfaces)
            dirty = [area]

        if original_clip is not None:
            surface.set_clip(original_clip)

        return dirty

    def redraw(self):
        """ Redraw the visible portion of the buffer.

        Beware, this is a slow operation and under normal circumstances should
        not need to be used.  If the map data has changed and specific tiles
        need to be redrawn, consider using update_queue and queue_tile.
        """
        self.queue = self._get_filled_queue()
        self._flush()

    def update_queue(self, iterator):
        """ Add some tiles to the draw queue.
        """
        if self.queue is None:
            self.queue = iterator
        else:
            self.queue = chain(self.queue, iterator)

    def queue_tile(self, position):
        """ Mark a tile position for update on the next draw.  Useful if you
        change the tile map data and need the tile to be updated on screen. For
        multiple updates, consider using update_queue().

        :param position: Position of tile that needs redraw
        :type position: (x, y, layer)
        """
        self.update_queue(iter(position,))

    def center(self, point):
        """ Center the map on a point.  If clamp_camera is enabled (it is by
        default) then the camera will not center exactly on the point it will
        cause the basemap to expose blank areas.

        :param point: Desired center position in pixels
        :type point: (x, y)
        """
        self._centered_point = point

    def scroll(self, vector):
        raise NotImplementedError

    def _flush(self):
        """ Draw all tiles in the queue.
        """
        if self.queue is not None:
            self._blit_tiles(self.queue)
            self.queue = None

    def _get_tile_image(self, position):
        try:
            return self.data.get_tile_image(position)
        except ValueError:
            return self.default_tile

    def _generate_default_tile(self):
        raise NotImplementedError

    def _overdraw(self, surface, offset, surfaces):
        raise NotImplementedError

    def _center_map(self, point):
        raise NotImplementedError

    def _blit_tiles(self, iterator):
        raise NotImplementedError

    def _get_filled_queue(self):
        raise NotImplementedError

    def _get_edge_tiles(self, offset):
        raise NotImplementedError


class OrthogonalRenderer(AbstractRenderer):
    """ Scrolling map renderer for orthographical maps.
    """
    @property
    def sprite_offset(self):
        try:
            return (-self._centered_point[0] + self._half_width,
                    -self._centered_point[1] + self._half_height)
        except TypeError:
            raise Exception, "sprite offset cannot be calculated until the renderer size is set or until after the first call to draw"

    def _get_filled_queue(self):
        return product(xrange_(self._view.left, self._view.right),
                       xrange_(self._view.top, self._view.bottom),
                       self.data.visible_tile_layers)

    def _get_edge_tiles(self, offset):
        """ Get the tile that need to be redrawn on edges
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

    def _generate_default_tile(self):
        self.default_tile = pygame.Surface((self.data.tile_width,
                                            self.data.tile_height))
        self.default_tile.fill(self.background_color)

    def _overdraw(self, surface, offset, surfaces):
        def above(x, y):
            return x > y

        ox, oy = offset
        surface_blit = surface.blit
        left, top = self._view.topleft
        hit = self._layer_quadtree.hit
        get_tile = self._get_tile_image
        tile_layers = tuple(self._data.visible_tile_layers)

        dirty = [(surface_blit(i[0], i[1]), i[2]) for i in surfaces]
        for dirty_rect, layer in dirty:
            for r in hit(dirty_rect.move(-ox, -oy)):
                x, y, tw, th = r
                for l in [i for i in tile_layers if above(i, layer)]:
                    tile = get_tile((int(x / tw + left),
                                     int(y / th + top), int(l)))
                    if tile:
                        surface_blit(tile, (x + ox, y + oy))

        return [i[0] for i in dirty]

    def _center_map(self, point):
        """ center the map on a pixel
        """
        x, y = [int(round(i, 0)) for i in point]
        hpad = int(self.padding / 2)
        tw = self.data.tile_width
        th = self.data.tile_height

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
            self._view = self._view.move((dx, dy))
            self._buffer.scroll(-dx * tw, -dy * th)
            self.update_queue(self._get_edge_tiles((dx, dy)))

        self._previous_x, self._previous_y = x, y

    def scroll(self, vector):
        """ Scroll the background in pixels.

        :param vector: Displacement of the camera in pixels
        :type vector: (x, y)
        """
        self.center((vector[0]+self._previous_x, vector[1]+self._previous_y))

    def _blit_tiles(self, iterator):
        """ Blits (x, y, layer) tuples to buffer from iterator
        """
        tw = self.data.tile_width
        th = self.data.tile_height
        blit = self._buffer.blit
        ltw = self._view.left * tw
        tth = self._view.top * th
        get_tile = self._get_tile_image
        colorkey = self._colorkey

        if colorkey:
            fill = partial(self._buffer.fill, colorkey)
            old_tiles = set()
            old_tiles_add = old_tiles.add
            for x, y, l in iterator:
                tile = get_tile((x, y, l))
                if tile:
                    old_tiles_add((x, y))
                    xx = x * tw - ltw
                    yy = y * th - tth
                    if l == 0:
                        fill((xx, yy, tw, th))
                    blit(tile, (xx, yy))
                elif l > 0 and (x, y) not in old_tiles:
                    fill((x * tw - ltw, y * th - tth, tw, th))
        else:
            for x, y, l in iterator:
                tile = get_tile((x, y, l))
                if tile:
                    blit(tile, (x * tw - ltw, y * th - tth))