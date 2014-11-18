import pygame

__all__ = ['ScrollGroup']


class ScrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites on a scrolling map
    """

    def __init__(self, *args, **kwargs):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        try:
            self.map_layer = kwargs.get('map_layer')
        except KeyError:
            print('map layer must be specified')
            raise KeyError

    def update(self, dt):
        pygame.sprite.LayeredUpdates.update(self, dt)
        self.map_layer.update(dt)

    def center(self, value):
        """ Center the group/map on a pixel

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.
        """
        self.map_layer.center(value)

    def draw(self, surface):
        """ Draw all sprites and map onto the surface

        Group.draw(surface): return None
        Draws all of the member sprites onto the given surface.
        """
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
