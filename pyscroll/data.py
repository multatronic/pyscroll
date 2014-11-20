__all__ = ['AbstractMapData']


class AbstractMapData(object):
    """ Abstract class for use as data for Pyscroll scrolling maps

    Use this as a superclass or just make your own that follows this.
    """

    @property
    def tile_width(self):
        """ Return width of a tile in pixels
        """
        raise NotImplementedError

    @property
    def tile_height(self):
        """ Return height of a tile in pixels
        """
        raise NotImplementedError

    @property
    def width(self):
        """ Return the width of the map in tiles
        """
        raise NotImplementedError

    @property
    def height(self):
        """ Return the height of the map in tiles
        """
        raise NotImplementedError

    @property
    def visible_tile_layers(self):
        """ Return list of visible layer index numbers
        :return: list of visible layers
        :rtype: sequence
        """
        raise NotImplementedError

    def get_tile_image(self, position):
        """ Return the tile image for some position on the map

        :param position: position of tile in the map
        :type position: (x, y, layer)
        :return: tile image
        :rtype: pygame.surface.Surface
        """
        raise NotImplementedError