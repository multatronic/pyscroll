__author__ = 'Leif'

from unittest import TestCase
import pygame
import pyscroll


def get_test_data():
    return


class AbstractRendererTests(TestCase):
    def SetUp(self):
        data = get_test_data()
        self.r = pyscroll.AbstractRenderer(data)

    def test_set_data(self):
        data = get_test_data()
        self.assertEqual(data, self.r.data)
