import pygame

__all__ = ['ScrollGroup']


class ScrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites on a scrolling map
    """

    def __init__(self, *args, **kwargs):
        """ map_layer keyword argument is not optional
        """
        self._size = None
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        try:
            self.map_layer = kwargs.get('map_layer')
        except KeyError:
            print('map layer must be specified')
            raise KeyError

    def update(self, *args, **kwargs):
        """ Update the group

        Any positional or keyword arguments will be passed to the sprites
        """
        pygame.sprite.LayeredUpdates.update(self, *args, **kwargs)

    def center(self, point):
        """ Center the group/map on a pixel

        The basemap and all sprites will be realigned correctly.
        Centering the map will not change the rect of the sprites, just their
        position on the screen.

        :param point: where the map should be centered
        :type point: (x, y)
        :return: None
        """
        self.map_layer.center(point)

    def draw(self, surface):
        """ Draw all sprites and map onto the surface

        :param surface: Where the map should be drawn to
        :type surface: pygame.surface.Surface
        :return: list of screen areas needing updates (dirty rect)
        """
        # in order to get the offsets, we need to set the renderer size first
        rect = surface.get_rect()
        if not self._size == rect.size:
            self._size = rect.size
            self.map_layer.size = rect.size

        new_surfaces = list()
        xx, yy = self.map_layer.sprite_offset
        spritedict = self.spritedict
        get_layer = self.get_layer_of_sprite
        new_surfaces_append = new_surfaces.append
        for spr in self.sprites():
            new_rect = spr.rect.move(xx, yy)
            new_surfaces_append((spr.image, new_rect, get_layer(spr)))
            spritedict[spr] = new_rect
        dirty = self.map_layer.draw(surface, surface.get_rect(), new_surfaces)
        return dirty