#.......wifi initialization...............
import micropython
import network

#..........MQTT Initialization.............
import time
import json
#from micropython import datetime
import ubinascii
import machine
from umqtt.simple import MQTTClient
import ussl


#.........Send dB(A) reading via MQTT.............

def iso():
    # Convert seconds to a tuple representing local time
    local_time = time.localtime(time.time())

    # Format the local time in ISO 8601 format
    formatted_time = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        local_time[0],
        local_time[1],
        local_time[2],
        local_time[3],
        local_time[4],
        local_time[5]
    )
    return formatted_time
    
class MQTT_client:
    def __init__(self):
        try:
            print("Connecting to MQTT...")
            self.client = MQTTClient(client_id = ubinascii.hexlify(machine.unique_id()),
                server = BROKER_URL,
                user = USER,
                password = PASSWORD,
                ssl = True,
                keepalive = 60,
                ssl_params = {
                    'key' : None,
                    'cert' : cacert_data,
                    'server_side' : False,
                    'server_hostname' : BROKER_URL
                })

            self.client.connect()
            print("Successfully connected to MQTT")
            
        except OSError as e:
            print(e)
            print("Connect unsuccessful. Rebooting.")
            time.sleep(10)
            machine.reset()
        
            
        self.topic = b'jsontest/ECE199_NOISE_MONITORING'
    
    def make_message_mfcc(self,node_ID, ESP32_MFCC_1, ESP32_MFCC_2, ESP32_MFCC_3, ESP32_MFCC_4, ESP32_MFCC_5, ESP32_MFCC_6, ESP32_MFCC_7, ESP32_MFCC_8, ESP32_MFCC_9, ESP32_MFCC_10, ESP32_MFCC_11, ESP32_MFCC_12, ESP32_MFCC_13):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] =  iso() #datetime.datetime.now(timezone.utc).isoformat() #time.localtime()
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_1)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_2)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_3)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_4)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_5)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_6)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_7)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_8)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_9)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_10)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_11)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_12)
        out_msg['INMP441_MFCC'] = float(ESP32_MFCC_13)

        
        return json.dumps(out_msg)
    
    def publish(self,msg):
        self.client.publish(self.topic,msg,False,1)


#...............connect to wifi............
        
        
sta = network.WLAN(network.STA_IF)
sta.active(True)

ssid = 'momo' #change if using different wifi
pw = 'momo1515' #change if using different wifi

# connect to wifi
print("Connecting to ssid " + ssid)
sta.connect(ssid, pw)

while(not sta.isconnected()):
    pass

print("Connected successfully")


#.................main setup................


if __name__ == "__main__":
    
    BROKER_URL = b'ed7632329e6e4fbcbe77b1fa917585a1.s1.eu.hivemq.cloud'
    USER = b'mabutas.m'
    PASSWORD = b'noise196_EEECARE'
    
    # import certs
    with open('hivemq-com-chain.der') as f: #this might expire soon
        cacert_data = f.read()
    
    client = MQTT_client()
    time.sleep(3)
    
    while True:
        
        
        #run here main code for mfcc
        
        
        staticlaeq = client.make_message_staticlaeq('Static LAeq', ESP32_MFCC_1, ESP32_MFCC_2, ESP32_MFCC_3, ESP32_MFCC_4, ESP32_MFCC_5, ESP32_MFCC_6, ESP32_MFCC_7, ESP32_MFCC_8, ESP32_MFCC_9, ESP32_MFCC_10, ESP32_MFCC_11, ESP32_MFCC_12, ESP32_MFCC_13)
        client.publish(staticlaeq)
        time.sleep_ms(100)
    
    client.disconnect()

    print("Finished sending all data.")        
