#!/usr/bin/env python
#coding:utf-8


import gevent
from random import choice
from struct import unpack
from struct import error as structerror
from gevent import sleep
from . import KRPC,KTable
from ..common import tidlink,taskline
from ..common import nid,unpack_nodes
from ..common import netcount,count
from ..config import BOOTSTRAP_NODES    

########################################################################
class BaseDHT(KRPC):
    """"""
    #----------------------------------------------------------------------
    def __init__(self,port):
        """Constructor"""
        KRPC.__init__(self,port,self.default)
        self.nid = nid
        self.table = KTable()
        self.tidlink = tidlink
        self.tiditer = iter(tidlink)
        self.tid = self.tiditer.next()
        self.taskline = taskline 
        self._set_handle() 
        self._r_handle = {
            "ping":self.r_ping,
            "find_node":self.r_find_node,
            "get_peers":self.r_get_peers,
            "announce_peer":self.r_announce_peer
        }
        self._task_map = {
            "ping":self.ping,
            "find_node":self.find_node,
            "get_peers":self.get_peers,
            "announce_peer":self.announce_peer
        }
        self._q_handle = {
            "ping": self._on_ping,
            "find_node":self._on_find_node,
            "get_peers":self._on_get_peers,
            "announce_peer":self._on_announce_peer
        }
        self.taskline.push("find_node",self.nid)
        self.taskline.push("ping","ping")
         
    #----------------------------------------------------------------------
    def _set_handle(self):
        """"""
        self.add_handle('r', self._r)
        self.add_handle('q', self._q)
        self.add_handle('e', self._e)    
        
    #----------------------------------------------------------------------
    def _add_tid_to_send(self,msg,id,nid,addr):
        """"""
        msg["t"] = self.tid[0]
        self.tid = self.tiditer.send((msg["q"],id,nid,addr))  #将信息添加到挑战者-响应 链表
        self.send_msg(msg, addr)
    #----------------------------------------------------------------------
    def _q(self,msg,addr):
        """"""
        if not (msg.has_key("a") and msg.has_key("q") and 
                isinstance(msg["a"],dict) and 
                isinstance(msg["q"],str)):return
        func = self._q_handle.get(msg["q"])
        if not func:
            self.default(msg, addr)
        else:
            func(msg,addr)
    #----------------------------------------------------------------------
    def _on_ping(self,msg,addr):
        """"""
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.nid,
            }
        }
        self.send_msg(msg, addr)
    #----------------------------------------------------------------------
    def _on_find_node(self,msg,addr):
        """"""
        target = msg["a"].get("target")
        if target:
            nodes = self.table.find_node2chrall(target)
        else:
            nodes = ""
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.nid,
                "nodes":nodes
            }
        }
        self.send_msg(msg, addr)

    #----------------------------------------------------------------------
    def _on_get_peers(self,msg,addr):
        """"""
        if msg["a"].has_key("info_hash"):
            self.on_get_peers_info(msg["a"], addr)
            target = msg["a"]["info_hash"]
            nodes = self.table.find_node2chrall(target)
        else:
            nodes = ""
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.nid,
                "nodes":nodes,
                "token":"aoeusnth"
            }
        }
        self.send_msg(msg, addr)
    #----------------------------------------------------------------------
    def _on_announce_peer(self,msg,addr):
        """"""
        if msg["a"].has_key("info_hash"):
            self.on_announce_peer_info(msg["a"], addr)        
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.nid,
            }
        }
        self.send_msg(msg, addr)    
    #----------------------------------------------------------------------
    def _r(self,msg,addr):
        """"""
        if not (isinstance(msg["r"],dict) and msg["r"].has_key("id")):return
        index = 0
        try:
            index = unpack("!H",msg["t"])[0]
        except structerror:
            return
        try:
            info = self.tidlink[index]
        except IndexError:
            return
        if not info :return
        if msg["r"]["id"]==info[2] and addr==info[3]:self.table.push((msg["r"]["id"],addr[0],addr[1]))
        func = self._r_handle.get(info[0])
        if not func:return
        task = self.taskline[info[0]][info[1]]
        if not task:return
        func(task,msg,addr)
    #----------------------------------------------------------------------
    def _task_start(self):
        """"""
        num = 0
        while 1:
            for tubename,func in self._task_map.iteritems():
                for task in self.taskline[tubename].tubes:
                        func(task)
                        sleep(0.0001)
                sleep(0.0001)
                        
    #----------------------------------------------------------------------
    def start_dht(self):
        """"""
        gevent.spawn(self.auto_check_table)
        gevent.spawn(self._task_start)
        self.serve_forever()
        

    #----------------------------------------------------------------------
    def auto_check_table(self):
        """"""
        while 1:
            task = self.taskline("ping").get("ping")
            if not task:break
            need_check_nodes = self.table.need_check()
            for node in need_check_nodes:
                nid,addr = node.body
                task.put("ping",(nid, addr))
            sleep(60)
        
    #----------------------------------------------------------------------
    def _e(self,msg,addr):
        """"""
        pass    
    @count(netcount,"recv","default")
    def default(self,msg,addr):
        """"""
        msg = {
            "t":msg["t"],
            "y":"e",
            "e":self.erro_msg[202]
        }
        self.send_msg(msg, addr)    
    
    def erro(self):
        """"""
        pass
    #----------------------------------------------------------------------
    def _ping(self,ping,nid,addr):
        """"""
        msg = {
            "y":"q",
            "q":"ping",
            "a":{
                "id":self.nid
            }
        }
        self._add_tid_to_send(msg, ping, nid, addr)
    #----------------------------------------------------------------------
    def ping(self,task):
        """"""
        if not task.started:return
        if task.length:
            taskitem = task.get()
            self._ping(task.id, *taskitem)        
    #----------------------------------------------------------------------
    def find_node(self,task):
        """"""
        print len(self.table)
        if task.id == self.nid and len(self.table) > (16**2)*4:
            task.stop()        
        if not task.started:return
        if task.length:
            taskitem = task.get()
            self._find_node(task.id, *taskitem)
        else:
            self.boot_task(task) 
    #----------------------------------------------------------------------
    def _find_node(self,target,nid,addr):
        """"""
        msg = {
            "y":"q",
            "q":"find_node",
            "a":{
                "id":self.nid,
                "target":target
            }
        }
        self._add_tid_to_send(msg, target, nid, addr)        
    #----------------------------------------------------------------------
    def get_peers(self,task):
        """"""
        if not task.started:return
        if task.length:
            taskitem = task.get()
            self._get_peers(task.id, *taskitem)
        else:
            self.boot_task(task) 
    def boot_task(self,task):
        if len(self.table) < 200:
            items = [(None,choice(BOOTSTRAP_NODES))]
        else:
            items = self.table.find_node2chrlist(task.id)
        for item in items:
            task.put(item)
    
    #----------------------------------------------------------------------
    def _get_peers(self,info_hash,nid,addr):
        """"""   
        msg = {
            "y":"q",
            "q":"get_peers",
            "a":{
                "id":self.nid,
                "info_hash":info_hash
            }
        }
        self._add_tid_to_send(msg, info_hash, nid, addr)
    #----------------------------------------------------------------------
    def announce_peer(self,target,addr):
        """"""
        pass
    #----------------------------------------------------------------------
    def r_ping(self,task,msg,addr):
        """"""
        pass
    #----------------------------------------------------------------------
    def r_find_node(self,task,msg,addr):
        """"""
        if not task.started:return
        if not msg["r"].has_key("nodes"):return
        nodelist = unpack_nodes(msg["r"]["nodes"])
        for node in nodelist:
            if node[0] == task.id and node[0] != self.nid:
                self.on_find_node_node(task, node)
            task.put(node)
        
    def r_get_peers(self,task,msg,addr):
        """"""
        if not task.started:return
        if msg["r"].has_key("nodes"):
            nodelist = unpack_nodes(msg["r"]["nodes"])
            for node in nodelist:
                task.put(node)
        if msg["r"].has_key("values") and msg["r"]["values"]:
            self.on_get_peers_values(task,msg["r"]["values"])
    #----------------------------------------------------------------------
    def r_announce_peer(self,task,msg,addr):
        """"""
        pass    
    #----------------------------------------------------------------------
    def on_get_peers_values(self,task,values):
        """"""
        print values
    #----------------------------------------------------------------------
    def on_find_node_node(self,task,node):
        """"""
        pass
    #----------------------------------------------------------------------
    def on_get_peers_info(self,info,addr):
        """"""
        print info,addr
    #----------------------------------------------------------------------
    def on_announce_peer_info(self,info,addr):
        """"""
        print info,addr
        
########################################################################
class DHTSpider(BaseDHT):
    """"""
    
    #----------------------------------------------------------------------
    def find_node(self, task):
        """"""
        if task.length:
            taskitem = task.get()
            self._find_node(task.id, *taskitem)
        else:
            self.boot_task(task)
    #----------------------------------------------------------------------
    def r_find_node(self,task,msg,addr):
        """"""
        if not msg["r"].has_key("nodes"):return
        nodelist = unpack_nodes(msg["r"]["nodes"])
        for node in nodelist:
            if node[0] == task.id and node[0] != self.nid:
                self.on_find_node_node(task, node)
            task.put(node) 
    def _find_node(self,target,nid,addr):
        """"""
        snid = (nid[:10], self.nid[10:]) if nid else self.nid
        msg = {
            "y":"q",
            "q":"find_node",
            "a":{
                "id":snid,
                "target":target
            }
        }
        self._add_tid_to_send(msg, target, nid, addr)     
