#!/usr/bin/env python2

import logging
import logging.handlers
import threading
import time

class Filter(object):
    def input(self, distance, angle):
        pass

class FilterMaxValue(object):
    def __init__(self, threshold):
        self._threshold = threshold

    def filter(self, distance, angle):
        if angle not in self._threshold:
            return False

        return distance > self._threshold[angle]
