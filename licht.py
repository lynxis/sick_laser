#!/usr/bin/env python3

import requests
import logging
import threading
import time

LOG_FILENAME = "/tmp/light.log"

LOG = logging.getLogger('dmx')

NETLOCK = threading.RLock()
BANDWIDTH = 0

SCHRANKE_LOCK = threading.RLock()
SCHRANKE = False

def setup_logging():
    logging.getLogger('dmx').setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes=100000, backupCount=1)
    line = "%(asctime)s %(name)-20s %(levelname)-8s %(message)s"
    handler.setFormatter(logging.Formatter(line))
    logging.getLogger('dmx').addHandler(handler)

class DmxNode(object):
    def __init__(self, offset, width):
        # channeloffset, channelsize
        self._channelwidth = width
        self._channeloffset = offset
        # dict[channel] = value
        self._values = {}

        for i in range(width):
            self._values[width] = 0

    @property
    def channel(self):
        return [self._channeloffset, self._channelwidth]

    @property
    def values(self):
        return self._values

class Dmx5Light(DmxNode):
    def __init__(self, offset):
        super().__init__(offset, 5)

    def set_color(self, red, green, blue):
        addr = self._channeloffset

        self._values[addr] = red
        self._values[addr+1] = green
        self._values[addr+2] = blue


class DMX(threading.Thread):
    def __init__(self):
        self.dmx = bytearray(255)
        self._licht_dmx = []
        self._licht_schranken = {}
        self._licht_network = []

        self._timer_schranke = 0

        self._network_animation = None
        self._network_oldbandwidth = 0
        self._network_animation_time = 50
        self._network_timer = 0

        super().__init__()

    def lichtschranke(self):
        pass

    def network(self):
        pass

    def _send_dmx(self):
        for licht in self._licht_dmx:
            for addr, value in licht.values:
                self.dmx[addr] = value

    def _tick_network(self):
        # basic color
        colors = [255, 0, 0]

        if self._network_animation == None:
            bandwidth = 0
            with NETLOCK:
                bandwidth = BANDWIDTH

            if bandwidth == 0:
                self._network_animation = "BLACKOUT"

            if bandwidth > self._network_oldbandwidth:
                self._network_animation = "UP"
            else:
                self._network_animation = "DOWN"

        step = self._network_animation_time / self._network_timer
        if self._network_animation == "UP":
            colors = [color * step for color in colors]
        elif self._network_animation == "DOWN":
            colors = [color * step for color in colors]

        if bandwidth == 0:
            # animation up
            pass

        else:
            # animation down
            pass

        factor = bandwidth * 1000
        # rgb
        colors = [factor * val for val in colors]

        [light.set_color(*colors) for light in self._licht_network]

    def _tick_schranke(self):
        with SCHRANKE_LOCK:
            schranke = SCHRANKE

        if schranke:
            self._timer_schranke = 0

        if self._timer_schranke == 0:
            pass

        elif self._timer_schranke == 25:
            pass

    def run(self):
        while True:
            self._tick_network()
            self._tick_schranke()
            self._send_dmx()
            time.sleep(0.1)

# TODO: thread get_network
# TODO: lichtschranke ...

class Networking(threading.Thread):
    def get_network(self):
        try:
            get = requests.get("http://c3netmon.congress.ccc.de/current.json", timeout=1)
            getjs = get.json()
            if getjs.has_key('bw'):
                return getjs['bw']
        except Exception as exep:
            LOG.error("get_network failed: " + str(exep))
        return None

    def run(self):
        while True:
            bandwidth = self.get_network()
            with NETLOCK:
                BANDWIDTH = bandwidth

            time.sleep(60)

if __name__ == "__main__":
    setup_logging()
    dmx = DMX()
