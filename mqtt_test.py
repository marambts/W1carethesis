#This code serves to send data via MQTT to the CARE server.
#This code sends LAeq readings in dBA, Heartbeat readings in BPM and MFCC values.
#Written in MicroPython, IDE is ThonnyIDE

#credentials stored on config.py

import time
import json
from micropython import datetime
import ubinascii
import machine
import network
from umqtt.simple import MQTTClient
import ussl
from config import BROKER_URL, USER, PASSWORD

    
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

            client.connect()
            print("Successfully connected to MQTT")
            
        except OSError as e:
            print(e)
            print("Connect unsuccessful. Rebooting.")
            time.sleep(10)
            machine.reset()
            
        self.topic = "jsontest/ECE199_TRAFFIC_MONITORING"
        
    
    def make_message_staticlaeq(self,node_ID, laeq):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] = datetime.now().isoformat()
        out_msg['INMP441_LAeq'] = int(staticLaeq)
        
        return json.dumps(out_msg)
        time.sleep(3)
         
    def make_message_wearablelaeq(self,node_ID, laeq):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] = datetime.now().isoformat()
        out_msg['INMP441_LAeq'] = int(wearableLAeq)
        
        return json.dumps(out_msg)

    def make_message_heartbeat(self,node_ID, heartbeat):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] = datetime.now().isoformat()
        out_msg['MAXX30102_BPM'] = int(heartbeat)
        
        return json.dumps(out_msg)
    
    def make_message_mfcc(self,node_ID, mfcc):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] = datetime.now().isoformat()
        out_msg['MFCC'] = MFCC
        
        return json.dumps(out_msg)

    def publish(self,msg):
        self.client.publish(self.topic,msg,False,1)
        

    
if __name__ == "__main__":
    # import certs
    with open('hivemq-com-chain.der') as f:
        cacert_data = f.read()
    
    client = MQTT_client()
    
    staticlaeq = client.make_message_staticlaeq('Static LAeq',) #confirm arguments used
    wearablelaeq = client.make_message_wearablelaeq('Wearable LAeq',) #confirm arguments used
    heartbeat = client.make_message_heartbeat('Heartbeat Reading',) #confirm arguments used
    mfcc = client.make_message_mfcc('MFCC',) #confirm arguments used

    client.publish(staticlaeq)
    client.publish(wearablelaeq)
    client.publish(heartbeat)
    client.publish(mfcc) 

    print("Finished sending all data.")


    client.disconnect()