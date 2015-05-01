# sick_laser
Connects a sick 3000 laser with DMX Lights on an embedded Linux (OpenWrt).

* `sick_laser.py`: sick laser 3000 class
* `laser.py`: implement filters on input data
* `dmx.py`: talk to DMX bus via USB serial

# runnable applicantions
* `licht.py` Projecting network usage on DMX Lights.
* `foo.py` Controls brightness of DMX Lights depending on the distance read by the Laser.
