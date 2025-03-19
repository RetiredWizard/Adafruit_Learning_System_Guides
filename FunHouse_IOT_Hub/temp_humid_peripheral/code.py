# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Setting Adafruit IO feeds from a MagTag with a sensor connected over STEMMA QT
Uses:
    * https://www.adafruit.com/product/4819
    OR
        * https://www.adafruit.com/product/4800
        * https://www.adafruit.com/product/4236
        * https://www.adafruit.com/product/4631
    AND
    * https://www.adafruit.com/product/4885 (although any sensor should work with a few changes)
    * https://www.adafruit.com/product/4399
"""

from os import getenv
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

from adafruit_magtag.magtag import MagTag
import busio
import board
import adafruit_sht4x

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

if None in [ssid, password, aio_username, aio_key]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME' and 'ADAFRUIT_AIO_KEY' at a minimum."
    )

### WiFi ###

magtag = MagTag()

connected = False
try:
    print(f"Connecting to {ssid}")
    wifi.radio.connect(ssid, password)
    print(f"Connected to {ssid}!")

    # Create a socket pool
    pool = socketpool.SocketPool(wifi.radio)

    # Initialize a new MQTT Client object
    mqtt_client = MQTT.MQTT(
        broker="io.adafruit.com",
        username=aio_username,
        password=aio_key,
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
    )

    # Initialize an Adafruit IO MQTT Client
    io = IO_MQTT(mqtt_client)

    # Connect to Adafruit IO
    print("Connecting to Adafruit IO...")
    io.connect()

    connected = True
except ConnectionError:
    pass

i2c = busio.I2C(board.SCL, board.SDA)
sht = adafruit_sht4x.SHT4x(i2c)
print("Found SHT4x with serial number", hex(sht.serial_number))

sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
# Can also set the mode to enable heater
# sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
print("Current mode is: ", adafruit_sht4x.Mode.string[sht.mode])

magtag.add_text(
    text_position=(50, 128 / 4,), text_scale=2,
)

magtag.add_text(
    text_position=(50, (2 * 128) / 4,), text_scale=2,
)

magtag.add_text(
    text_position=(50, (3 * 128) / 4,), text_scale=2,
)

temperature, relative_humidity = sht.measurements
magtag.set_text("Temperature: %0.1f C" % temperature, 0, False)
magtag.set_text("Humidity: %0.1f %%" % relative_humidity, 1, False)
T = temperature * 1.8 + 32
humidity = relative_humidity
HI = (
    -42.379
    + 2.04901523 * T
    + 10.14333127 * humidity
    - 0.22475541 * T * humidity
    - 0.00683783 * T * T
    - 0.05481717 * humidity ** 2
    + 0.00122874 * T * T * humidity
    + 0.00085282 * T * humidity ** 2
    - 0.00000199 * T * T * humidity ** 2
)
magtag.set_text("Feels like: %0.1f F" % HI, 2)
if connected:
    io.publish("temperature", temperature)
    io.publish("humidity", relative_humidity)
    io.publish("heatindex", HI)
magtag.exit_and_deep_sleep(600)
