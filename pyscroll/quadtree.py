"""
Two classes for quadtree collision detection.

A quadtree is used with pyscroll to detect overlapping tiles.
"""

from itertools import chain
from pygame import Rect

__all__ = ['FastQuadTree']


class FastQuadTree(object):
    """ An implementation of a quad-tree

    This faster version of the quadtree class is tuned for pygame's rect
    objects, or objects with a rect attribute.  The return value will always
    be a set of a tuples that represent the items passed.  In other words,
    you will not get back the objects that were passed, just a tuple that
    describes it.

    Items being stored in the tree must be a pygame.Rect or have have a
    .rect (pygame.Rect) attribute that is a pygame.Rect
    """
    __slots__ = ['_items', '_cx', '_cy', '_nw', '_sw', '_ne', '_se']

    def __init__(self, items, depth=4, boundary=None):
        """ Creates a quad-tree

        :param items: A sequence of items to store in the quad-tree
            Note: items must be a pygame.Rect or have a .rect attribute

        :param depth: The maximum recursion depth

        :param boundary:
            The bounding rectangle of all of the items in the quad-tree
        """
        self._nw = self._ne = self._se = self._sw = None

        # If we've reached maximum depth insert all items into this quadrant
        depth -= 1
        if depth == 0 or not items:
            self._items = items
            return

        # Find this quadrant's center
        if boundary:
            boundary = Rect(boundary)
        else:
            # If there isn't a bounding rect, then calculate it from the items
            boundary = Rect(items[0]).unionall(items[1:])

        cx = self._cx = boundary.centerx
        cy = self._cy = boundary.centery

        self._items = []
        nw_items = []
        ne_items = []
        se_items = []
        sw_items = []

        for item in items:
            # Which of the sub-quadrants does the item overlap?
            in_nw = item.left <= cx and item.top <= cy
            in_sw = item.left <= cx and item.bottom >= cy
            in_ne = item.right >= cx and item.top <= cy
            in_se = item.right >= cx and item.bottom >= cy

            # If it overlaps all 4 quadrants then insert it at the current
            # depth, otherwise append it to a list to be inserted under every
            # quadrant that it overlaps.
            if in_nw and in_ne and in_se and in_sw:
                self._items.append(item)
            else:
                if in_nw: nw_items.append(item)
                if in_ne: ne_items.append(item)
                if in_se: se_items.append(item)
                if in_sw: sw_items.append(item)

        # Create the sub-quadrants, recursively.
        if nw_items:
            self._nw = FastQuadTree(nw_items, depth,
                                   (boundary.left, boundary.top, cx, cy))

        if ne_items:
            self._ne = FastQuadTree(ne_items, depth,
                                   (cx, boundary.top, boundary.right, cy))

        if se_items:
            self._se = FastQuadTree(se_items, depth,
                                   (cx, cy, boundary.right, boundary.bottom))

        if sw_items:
            self._sw = FastQuadTree(sw_items, depth,
                                   (boundary.left, cy, cx, boundary.bottom))

    def __iter__(self):
        return chain(self._items, self._nw, self._ne, self._se, self._sw)

    def hit(self, rect):
        """ Returns the items that overlap a bounding rectangle.

        Returns the set of all items in the quad-tree that overlap with a
        bounding rectangle.

        :param rect: The bounding rect being tested against the quad-tree
            This must possess left, top, right and bottom attributes
        """

        # Find the hits at the current level
        hits = set(
            tuple(self._items[i]) for i in rect.collidelistall(self._items))

        # Recursively check the lower quadrants
        if self._nw and rect.left <= self._cx and rect.top <= self._cy:
            hits |= self._nw.hit(rect)
        if self._sw and rect.left <= self._cx and rect.bottom >= self._cy:
            hits |= self._sw.hit(rect)
        if self._ne and rect.right >= self._cx and rect.top <= self._cy:
            hits |= self._ne.hit(rect)
        if self._se and rect.right >= self._cx and rect.bottom >= self._cy:
            hits |= self._se.hit(rect)

        return hits
