#!/usr/bin/env python2

import requests
import logging
import logging.handlers
import threading
import time

LOG_FILENAME = "/tmp/light.log"

LOG = logging.getLogger('dmx')
LOG_SCHRANKE = logging.getLogger('schranke')
LOG_NETWORK = logging.getLogger('network')

NETLOCK = threading.RLock()
BANDWIDTH = 0

SCHRANKE_LOCK = threading.RLock()
SCHRANKE = False

def setup_logging():
    handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes=100000, backupCount=1)
    line = "%(asctime)s %(name)-20s %(levelname)-8s %(message)s"
    handler.setFormatter(logging.Formatter(line))
    for log in [LOG, LOG_SCHRANKE, LOG_NETWORK]:
        log.setLevel(logging.INFO)
        log.addHandler(handler)

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

class Animation(object):
    def tick(self):
        """ called by DMX main thread """
        pass

class Dmx5Light(DmxNode):
    def __init__(self, offset):
        super(Dmx5Light, self).__init__(offset, 5)

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
        self._network_bandwidth = 0

        super(DMX, self).__init__()

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
            self._network_bandwidth = 0
            with NETLOCK:
                self._network_bandwidth = BANDWIDTH

            if self._network_bandwidth == 0:
                self._network_animation = "BLACKOUT"
                LOG_NETWORK.info("New Animation BLACKOUT")

            if self._network_bandwidth > self._network_oldbandwidth:
                self._network_animation = "UP"
                LOG_NETWORK.info("New Animation UP")
            else:
                self._network_animation = "DOWN"
                LOG_NETWORK.info("New Animation DOWN")

        step = self._network_timer % self._network_animation_time
        if self._network_animation == "UP":
            colors = [color * step for color in colors]
        elif self._network_animation == "DOWN":
            colors = [color * step for color in colors]

        if self._network_bandwidth == 0:
            # animation up
            pass

        else:
            # animation down
            pass

        factor = self._network_bandwidth * 1000
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
        LOG.info("Starting DMX Thread")
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
        LOG.info("Starting Network Thread")
        while True:
            bandwidth = self.get_network()
            with NETLOCK:
                BANDWIDTH = bandwidth

            time.sleep(60)

class DummyNetwork(threading.Thread):
    def run(self):
        LOG.info("Starting Dummy Network Thread")
        while True:
            bandwidth = 100
            with NETLOCK:
                BANDWIDTH = bandwidth

            time.sleep(60)

if __name__ == "__main__":
    setup_logging()
    net = DummyNetwork()
    net.start()
    dmx = DMX()
    dmx.start()
    dmx.join()
