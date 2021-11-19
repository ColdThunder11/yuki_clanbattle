import ws_protocol_pb2
import websocket
import time
import re
import os
import _thread as thread


def on_message(ws, message):
    #print(ws)
    print(message)

def on_error(ws, error):
    #print(ws)
    print(error)
    print("Websocket got a error")


def on_close(ws):
    print("Websocket connection closed")

def on_open(ws):
    print("Websocket crearte sucess")
    def run(*args):
        header = b'\xf7\x01'
        ws.send('\xf7\x01')

        time.sleep(1)
        traffic = Network()
        time.sleep(10)
    thread.start_new_thread(run, ())


while True:
    try:
        print("Connecting to clan battle server")
        ws = websocket.WebSocketApp("wss://127.0.0.1:28385/api/clanbattle/websocket/ws",
                                    on_open = on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.run_forever()
        time.sleep(3)
    except Exception as e:
        time.sleep(3)
        print("Caught Exception:", e)