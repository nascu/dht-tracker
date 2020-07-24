#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
from multiprocessing import Process
from dht_tracker.web import web_start
from dht_tracker.dht import BaseDHT,KRPC,KTable,NormalDHT,DHTSpider
from dht_tracker.common import netcount,sync
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s][%(filename)s][%(funcName)s]LINE %(lineno)-4d : %(levelname)-8s %(message)s'
                    ) 
dhtser = NormalDHT()

#----------------------------------------------------------------------
def collect_on_get_peers(info,addr):
    """重写收集到的get_peers信息的处理
    这里仅打印，以示例
    """
    print "get_peers",(info,addr)
#----------------------------------------------------------------------
def collect_on_announce_peer(info,addr):
    """重写收集到的announce_peer信息的处理
    这里仅打印，以示例
    """
    print "announce_peer",(info,addr)
#----------------------------------------------------------------------
def recv_find_node_node(task,node):
    """重写对find_node任务返回的node信息的处理
    这里仅打印，以示例
    """
    print "find_node_node",task.id,node
#----------------------------------------------------------------------
def recv_get_peers_values(task,values):
    """重写对get_peers任务返回的values信息的处理
    这里仅打印，以示例
    """
    print "get_peers_values",task.id,values
    
dhtser.on_get_peers_info = collect_on_get_peers
dhtser.on_announce_peer_info = collect_on_announce_peer
dhtser.on_find_node_node = recv_find_node_node
dhtser.on_get_peers_values = recv_get_peers_values

dhtser.taskline.push("get_peers",'\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z')
dhtser.start_dht()
#try:
    #p = Process(target=dhtser.start_dht, args=())
    #q = Process(target=web_start, args=())
    #p.start()
    #q.start()
    #p.join()
    #q.join()
#except Exception, e:
    #logging.warning(e)

