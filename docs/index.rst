.. pyscroll documentation master file, created by
   sphinx-quickstart on Mon May 19 21:53:31 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyscroll's Documentation!
====================================

pyscroll is a  simple, fast module for adding scrolling maps to your new or
existing pygame application.  pyscroll doesn't require any external map format
so you can use your existing map data, or take advantage of the built-in support
for pytmx to load maps created in the Tiled Map Editor.

Basically, pyscroll can create a pygame surface that represents your game map.
The OrthographicalRenderer class accepts map data and can draw directly to the
pygame display, or to another surface.

To handle scrolling, you can use the center or scroll methods to move the map.
If you are using pygame Sprites (are are using them, aren't you?), you can also
use the ScrollGroup, which supports layered sprites and maps plus scrolling.


New Game Tutorial
=================

Open quest.py in the apps/tutorial folder for a gentle introduction to pyscroll
and the PyscrollGroup for PyGame.  There are plenty of comments to get you
started.  You should have a basic understanding of python and pygame before you
get started with the tutorial.

The Quest Demo shows how you can use a pyscroll group for drawing, how to load
maps with pytmx, and how pyscroll can quickly render layers.


Example Use with pytmx
======================

pyscroll and pytmx can load your maps from Tiled and use pygame sprites.

.. code-block:: python

    # Load TMX data
    tmx_data = pytmx.load_pygame("desert.tmx")

    # Make data source for the map
    map_data = pyscroll.TiledMapData(tmx_data)

    # Make the scrolling layer
    screen_size = (400, 400)
    map_layer = pyscroll.BufferedRenderer(map_data, screen_size)

    # make the PyGame SpriteGroup with a scrolling map
    group = pyscroll.PyscrollGroup(map_layer=map_layer)

    # Add sprites to the group
    group.add(srite)

    # Center the layer and sprites on a sprite
    group.center(sprite.rect.center)

    # Draw the layer
    group.draw(screen)


Adapting Existing Games / Map Data
==================================

pyscroll can be used with existing map data, but you will have to create a
class to interact with pyscroll or adapt your data handler to have these
functions and attributes:


.. code-block:: python

    class MyData:

        @property
        def tile_width(self):
            """ Return width of a tile in pixels
            """

        @property
        def tile_height(self):
            """ Return height of a tile in pixels
            """

        @property
        def width(self):
            """ Return the width of the map in tiles
            """

        @property
        def height(self):
            """ Return the height of the map in tiles
            """

        @property
        def visible_tile_layers(self):
            """ Return list of visible layer index numbers
            If using a single layer map, just return [0]

            :return: list of visible layers
            :rtype: sequence
            """

        def get_tile_image(self, position):
            """ Return the tile image for some position on the map

            :param position: position of tile in the map
            :type position: (x, y, layer)
            :return: tile image
            :rtype: pygame.surface.Surface
            """

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

