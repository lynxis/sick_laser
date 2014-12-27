#!/usr/bin/env python3

import time

import sick_laser
import dmx
from struct import unpack


FACTOR = 0.5
RESPONSE = 0.1

LASERDEV = '/dev/ttyUSB2'
DMXDEV = '/dev/ttyUSB1'


if __name__ == '__main__':
    dmx = dmx.DMX(DMXDEV)

    laser = sick_laser.Laser(device=LASERDEV)
    laser.connect()
    dmxvals = [0]*70
    lastvalues = None
#    last = time.time()
    print('initialization finished')

    clipbyte = lambda x: int(max(0, min(x, 255)))

    while True:
        try:
            cont = laser.read_cont()
            if cont:
                print('received values')
                values = [unpack('<H', cont.messdata[i*2:i*2+2])[0] & 0x1fff for i in
                        range(int(len(cont.messdata)/2))]
                assert len(values) == 381
                if lastvalues is None:
                    lastvalues = values
                    continue

                deltavalues, lastvalues = [ abs(l-c) for l,c in zip(lastvalues, values)], values
                dmxvals = [clipbyte(d*FACTOR + sum(deltavalues[15+i*5:15+(i+1)*5])*0.2*RESPONSE) for i,d in enumerate(dmxvals) ]
                print([sum(deltavalues[15+i*5:15+(i+1)*5])*0.2*RESPONSE for i,d in enumerate(dmxvals) ])
                assert len(dmxvals) == 70

                dmx.send_frame(dmxvals+[0]*(512-len(dmxvals)))
                print('sent frame')
                print(dmxvals)
            else:
                print('did not receive values')
            
#            # sleep to achieve roughly 1/INTERVAL fps
#            new = time.time()
#            delta = (new-last)
#            if delta < INTERVAL:
#                time.sleep(INTERVAL-delta)
#            last = new
        except RuntimeError as e:
            print('error:', e)

