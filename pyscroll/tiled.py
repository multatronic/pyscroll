import pytmx

__all__ = ['TiledMapData']


class TiledMapData(object):
    """ Class that works with pytmx instances for getting scrolling map data
    """
    def __init__(self, data):
        self.data = data

    @property
    def orientation(self):
        return self.data.orientation

    @property
    def tile_width(self):
        return self.data.tilewidth

    @property
    def tile_height(self):
        return self.data.tileheight

    @property
    def width(self):
        return self.data.width

    @property
    def height(self):
        return self.data.height

    @property
    def visible_layers(self):
        return (int(i) for i in self.data.visible_layers)

    @property
    def visible_tile_layers(self):
        return (int(i) for i in self.data.visible_tile_layers)

    @property
    def visible_object_layers(self):
        return (layer for layer in self.data.visible_layers
                if isinstance(layer, pytmx.TiledObjectGroup))

    def get_tile_image(self, position):
        """ Return a surface for this position.
        """
        x, y, l = position
        return self.data.get_tile_image(x, y, l)

    def get_tile_image_by_gid(self, gid):
        """ Return surface for a gid
        """
        return self.data.get_tile_image_by_gid(gid)
