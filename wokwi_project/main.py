"""
MicroPython IoT Weather Station Example for Wokwi.com

To view the data:

1. Go to http://www.hivemq.com/demos/websocket-client/
2. Click "Connect"
3. Under Subscriptions, click "Add New Topic Subscription"
4. In the Topic field, type "wokwi-weather" then click "Subscribe"

Now click on the DHT22 sensor in the simulation,
change the temperature/humidity, and you should see
the message appear on the MQTT Broker, in the "Messages" pane.

Copyright (C) 2022, Uri Shaked

https://wokwi.com/arduino/projects/322577683855704658
"""

import network
import time
from machine import Pin, PWM, I2C
import dht
import ujson
from umqtt.simple import MQTTClient
from ssd1306 import SSD1306_I2C
import urequests
import os
import ubinascii
import gc
import random


# Parts for the ESP32

sensor = dht.DHT22(Pin(15))
ledr = Pin(23, Pin.OUT)
buzzer = PWM(Pin(27))
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = SSD1306_I2C(128, 64, i2c, addr=0x3c)
oled_2 = SSD1306_I2C(128, 64, i2c, addr=0x3d)
buzzer.freq(1000)  # 1kHz tone
buzzer.duty(0)     # Turn off buzzer

# Configuration variables

delay = 10
api_key = "e2029e14dfbb872bf7a67b3b8b03a3c5"

# Construction Site configuration variables (get values from Database)

lat = 0.0
lon = 0.0
max_delta_weather_temp = 0.0
max_delta_weather_humi = 0
max_delta_weather_wind = 0.0
max_print_temp = 0
max_print_humi = 0
min_print_temp = 0
min_print_humi = 0
code = 0
site_status = 0 

# Enable Wifi  

print("Connecting to WiFi", end="")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '')
while not sta_if.isconnected():
  print(".", end="")
  time.sleep(0.1)
print(" Connected!")




# Weather condition variables at job start 

weather_temp_0 = "N/A"
weather_humi_0 = "N/A"
weather_wind_0 = "N/A"
url = "https://api.openweathermap.org/data/2.5/weather?lat="+str(lat)+"&lon="+str(lon)+"&appid="+api_key+"&units=metric"



def generate_led_buzz_alert():
    ledr.on()
    buzzer.duty(512)
    time.sleep(0.1)
    buzzer.duty(0)
    ledr.off()

def get_cons_site_vals_from_db(url):
    resp = urequests.get(url)
    dict = resp.json()
    if 'items' in dict:
        if len(dict['items']) == 0:
            return False
        else:
            result = dict['items'][0]
            return {    'lat' : result['latitude'],
                        'lon' : result['longitude'],
                        'max_delta_weather_temp' : result['max_delta_weather_temp'],
                        'max_delta_weather_humi' : result['max_delta_weather_humi'],
                        'max_delta_weather_wind' : result['max_delta_weather_wind'],
                        'max_print_temp' : result['max_print_temp'],
                        'max_print_humi' : result['max_print_humi'],
                        'min_print_temp' : result['min_print_temp'],
                        'min_print_humi' : result['min_print_humi'],
                        'code' : result['code'],
                        'site_status' : result['status'],
                        'descrption' : result['descrption']
                    }
    else:
        return False

def generate_unique_id():
    """
    Generates a 25-character unique ID using os.urandom and ubinascii.hexlify.

    Returns:
        str: A 25-character hexadecimal string representing a unique ID.
    """
    # Generate 13 random bytes (13 * 2 = 26 hex characters)
    random_bytes = os.urandom(13)
    # Convert bytes to a hexadecimal string
    hex_string = ubinascii.hexlify(random_bytes).decode('utf-8')
    # Return the first 25 characters
    return hex_string[:25]

def get_random_color_name():
    """
    Returns a random common color name.
    """
    color_names = [
        "red", "blue", "green", "yellow", "orange", "purple",
        "pink", "brown", "black", "white", "gray", "cyan",
        "magenta", "lime", "teal", "indigo", "violet", "gold",
        "silver", "maroon", "olive", "navy", "aqua"
    ]
    return random.choice(color_names)        

# Loop variables

i = 0  # 'i' increases each time data is retrieved from DB and weather API
j = 0  # 'j' resets to 0 when 'delay' value is reached

printing_session_id = ""

while True:
    
    sensor.measure()
    print_temp = sensor.temperature()
    print_humi = sensor.humidity()
    message = ujson.dumps({
        "temp": print_temp,
        "humidity": print_humi,
    })

    oled.fill(0)

    if j == 0 or j == delay:

        if site_status == 0:
            con_site_url = "https://apex.oracle.com/pls/apex/a00439670/consite/cons"
        else:
            con_site_url = "https://apex.oracle.com/pls/apex/a00439670/consite/conscod?scode=" + str(code) 

        cons_site_vals = get_cons_site_vals_from_db(con_site_url)

        if cons_site_vals == False:
            # print("Waiting for site with status = 0")
            oled_2.fill(0)
            oled_2.text("Waiting for site", 0, 0)
            oled_2.text("with status 0", 0, 15)
            oled_2.show()
            oled.text("Waiting for site", 0, 0)
            oled.text("with status 0", 0, 15)
            oled.show()
            time.sleep(3)
            continue

        #if cons_site_vals != False:

        else:

            lat = cons_site_vals['lat']
            lon = cons_site_vals['lon']
            max_delta_weather_temp = cons_site_vals['max_delta_weather_temp']
            max_delta_weather_humi = cons_site_vals['max_delta_weather_humi']
            max_delta_weather_wind = cons_site_vals['max_delta_weather_wind']
            max_print_temp = cons_site_vals['max_print_temp']
            max_print_humi = cons_site_vals['max_print_humi']
            min_print_temp = cons_site_vals['min_print_temp']
            min_print_humi = cons_site_vals['min_print_humi']
            code = cons_site_vals['code']
            site_status = cons_site_vals['site_status']
            descrption = cons_site_vals['descrption']

            if printing_session_id == "" and site_status == 0:
                
                #Create printing session id and insert it into DB
                printing_session_id = generate_unique_id()
                site_session_id = generate_unique_id()
                ses_color = get_random_color_name()
                ins_ses_url = "https://apex.oracle.com/pls/apex/a00439670/consite/insses?sscode="+site_session_id+"&scode="+str(code)+"&sses="+printing_session_id+"&color="+ses_color
                resp = urequests.get(ins_ses_url)
                gc.collect()


            if site_status == 0:
                url_upd_stat = "https://apex.oracle.com/pls/apex/a00439670/sitestat/upd?sstat=1&scode="+str(code)
                resp = urequests.get(url_upd_stat)
                gc.collect()
                site_status = 1

            elif site_status > 1:
                oled_2.fill(0)
                oled_2.text("Pause print job!", 0, 0)
                oled_2.show()
                oled.text("Pause print job!", 0, 0)
                oled.show()
                continue
                


        weather_alert = 0
        temp_weather_alert_txt = ""
        humi_weather_alert_txt = ""
        wind_weather_alert_txt = ""
        weather_txt = "-Stable weather-"

        oled_2.fill(0)

        
        url = "https://api.openweathermap.org/data/2.5/weather?lat="+str(lat)+"&lon="+str(lon)+"&appid="+api_key+"&units=metric"

        resp = urequests.get(url)
        weather_dict = resp.json()
        gc.collect()
        weather_temp = "N/A"
        weather_humi = "N/A"
        weather_wind = "N/A"

        # print(weather_dict)
        # print("")

        i = i + 1;

        # print("Waiting for weather response")

        if 'temp' in weather_dict['main']:
            weather_temp = str(weather_dict['main']['temp'])
            if weather_temp_0 == "N/A":
                weather_temp_0 = weather_temp

        if 'humidity' in weather_dict['main']:
            weather_humi = str(weather_dict['main']['humidity'])
            if weather_humi_0 == "N/A":
                weather_humi_0 = weather_humi

        if 'speed' in weather_dict['wind']:
            weather_wind = str(weather_dict['wind']['speed'])
            if weather_wind_0 == "N/A":
                weather_wind_0 = weather_wind

        delta_weather_temp = abs(float(weather_temp) - float(weather_temp_0))
        delta_weather_humi = abs(float(weather_humi) - float(weather_humi_0))
        delta_weather_wind = abs(float(weather_wind) - float(weather_wind_0))

        if delta_weather_temp >= max_delta_weather_temp:
            weather_alert = weather_alert + 1
            temp_weather_alert_txt = "-T"

        if delta_weather_humi >= max_delta_weather_humi:
            weather_alert = weather_alert + 1
            humi_weather_alert_txt = "-H"

        if delta_weather_wind >= max_delta_weather_wind:
            weather_alert = weather_alert + 1
            wind_weather_alert_txt = "-W"

        if weather_alert > 0:
            weather_txt = temp_weather_alert_txt + " " + humi_weather_alert_txt + " " + wind_weather_alert_txt + " changed!"

        j = 0

        oled_2.text("   Start  Curr", 0, 0)
        oled_2.text("i:  1      " + str(i), 0, 11)
        oled_2.text("T: " + weather_temp_0 + "  " + weather_temp, 0, 22)
        oled_2.text("H: " + weather_humi_0 + " %   " + weather_humi + " %", 0, 33)
        oled_2.text("W: " + weather_wind_0 + "   " + weather_wind, 0, 44)
        oled_2.text(weather_txt, 0, 55)
        oled_2.show()

        # INSERT SENSOR VALUES IN DB
        
        sensvalid = generate_unique_id()

        url_ins_sen = "https://apex.oracle.com/pls/apex/a00439670/consite/inslec?sensvalid="+sensvalid+"&max_print_temp="+str(max_print_temp)+"&min_print_temp="+str(min_print_temp)+"&max_print_humi="+str(max_print_humi)+"&min_print_humi="+str(min_print_humi)+"&max_delta_weather_temp="+str(max_delta_weather_temp)+"&max_delta_weather_humi="+str(max_delta_weather_humi)+"&max_delta_weather_wind="+str(max_delta_weather_wind)+"&print_temp="+str(print_temp)+"&print_humi="+str(print_humi)+"&weather_temp="+str(weather_temp)+"&weather_humi="+str(weather_humi)+"&weather_wind="+str(weather_wind)+"&sessionid="+printing_session_id+"&sitecode="+str(code)
        #print(url_ins_sen)
        resp = urequests.get(url_ins_sen)
        gc.collect()

    printer_txt = "Ok! within ranges"

    if weather_alert > 0:
        generate_led_buzz_alert()

    elif print_temp >= max_print_temp:
        generate_led_buzz_alert()
        printer_txt = "Temp. above max"

    elif print_temp <= min_print_temp:
        generate_led_buzz_alert()
        printer_txt = "Temp. below min"

    elif print_humi >= max_print_humi:
        generate_led_buzz_alert()
        printer_txt = "Humid. above max"

    elif print_humi <= min_print_humi:
        generate_led_buzz_alert()
        printer_txt = "Humid. below min"

    else:
        time.sleep(0.1)
    oled.text("Site: " + descrption, 0, 0)    
    oled.text("Concrete Mix", 0, 9)
    oled.text("   Min  Max", 0, 20)
    oled.text("T: " + str(min_print_temp) + "   " + str(max_print_temp), 0, 31)
    oled.text("H: " + str(min_print_humi) + "%  " + str(max_print_humi) + "%", 0, 42)
    oled.text(printer_txt, 0, 55)
    oled.show()

    j = j + 1;

    gc.collect()
