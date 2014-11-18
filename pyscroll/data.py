__all__ = ['AbstractMapData']


class AbstractMapData(object):
    """Abstract class for use as data for Pyscroll scrolling maps
    """

    @property
    def orientation(self):
        raise NotImplementedError

    @property
    def tile_width(self):
        raise NotImplementedError

    @property
    def tile_height(self):
        raise NotImplementedError

    @property
    def width(self):
        raise NotImplementedError

    @property
    def height(self):
        raise NotImplementedError

    @property
    def visible_layers(self):
        raise NotImplementedError

    @property
    def visible_tile_layers(self):
        raise NotImplementedError

    @property
    def visible_object_layers(self):
        raise NotImplementedError

    def get_tile_image(self, position):
        raise NotImplementedError

    def get_tile_image_by_id(self, id):
        raise NotImplementedError
