#!/usr/bin/env python
#coding:utf-8
"""
对http://www.bittorrent.org/beps/bep_0005.html中DHT Queries的实现
使用链表优化了挑战-响应模式,使每一次的请求都对应唯一一个tid,可以对每一个收到的信息进行真实性检测
使用任务队列对任务的调控、以及流量的控制
通过Pipe实现web对任务的控制
NormalDHT -> 正常模式
DHTSpider -> 爬虫模式
"""

import gevent
import logging
from random import choice
from struct import unpack
from struct import error as structerror
from gevent import sleep
from . import KRPC
from . import table
from ..common import tidlink,taskline,sync,control_out
from ..common import nid,unpack_nodes
from ..common import netcount,count
from ..config import (
    BOOTSTRAP_NODES,
    DHTPORT,
    NODE_CHECK_INTERVAL_TIME,
    SYNC_INTERVAL_TIME,
    CONTROL_INTERVAL_TIME,
    PER_SECOND_MAX_TIME,
    MIN_STOP_TABLE_LENGTH,
    MIN_STOP_BOOT_LENGTH,
    MAX_RUN_TIME,
    MAX_TASK_NUM
)


class BaseDHT(KRPC):
    """基础DHT网络
    提供对网络的启动，路由表的更新检测，挑战-响应模式的支持
    Attributes:
        default: 对于找不到响应处理方式的默认处理方式(KRPC中)
        nid: DHT网络中自己的唯一标识
        table: 路由表
        tidlink: 挑战者-响应链表
        tiditer: 挑战者-响应链表的生成器，用于循环更改发送的请求的tid与内容
        taskline: 任务管道，用来存放各种需要请求的任务
        _r_handle: 对收到的回复进行处理的关系映射
        _q_handle: 对收到的请求进行处理的关系映射
        _task_map: 对需要发送请求的任务类型处理的关系映射
        start_dht: 启动DHT网络
        auto_check_table: 更新路由表，对长时间没有互动的接近进行ping检测
    """
    
    def __init__(self,port):
        """初始基本信息
        nid: DHT网络中自己的唯一标识
        table: 路由表
        tidlink: 挑战者-响应链表
        tiditer: 挑战者-响应链表的生成器，用于循环更改发送的请求的tid与内容
        tid: 挑战者-响应链表的生成器初始化
        taskline: 任务管道，用来存放各种需要请求的任务
        _r_handle: 对收到的回复进行处理的关系映射
        _q_handle: 对收到的请求进行处理的关系映射
        _task_map: 对需要发送请求的任务类型处理的关系映射
        Args:
            port: 需要监听的网络端口

        """
        KRPC.__init__(self,port,self.default)
        self.nid = nid
        self.table = table
        self.tidlink = tidlink
        self.tiditer = iter(tidlink)
        self.tid = self.tiditer.next()
        self.taskline = taskline
        self._r_handle = {}
        self._q_handle = {}
        self._task_map = {}         
        self._init()
    
    def _init(self):
        """添加默认任务
        find_node: 寻找自己的节点，让更多的节点认识自己
        ping: 对路由表更新的默认任务
        """
        self.taskline.push("find_node",self.nid)
        self.taskline.push("ping","ping") 

    def getnid(self,nid = None):
        """预留接口，用于在别的模式使用，可改写为欺骗节点信息"""
        return self.nid
        
    @count(netcount,"recv","default")
    def default(self,msg,addr):
        """对于找不到响应处理方式的默认处理方式"""
        logging.debug("未定义的信息方式:信息方式y -> %s,没有被定义相应的处理方式"%msg["y"])
        msg = {
            "t":msg["t"],
            "y":"e",
            "e":self.error_msg[202]
        }
        self.send_msg(msg, addr) 
        
    def _add_tid_to_send(self,msg,id,nid,addr):
        """向挑战-响应者链表中获取tid并将需要发送的任务信息添加到链表中，
        再将网络请求发送
        Args:
            msg: 需要发送的信息
            id: 任务的id
            nid: 请求节点的nid唯一标识
            addr: 请求节点的网络地址
        """
        msg["t"] = self.tid[0]
        self.tid = self.tiditer.send((msg["q"],id,nid,addr))  #将信息添加到挑战者-响应 链表
        self.send_msg(msg, addr)    

    def _task_start(self):
        """对任务的处理
        获取任务映射关系的键值和操作
        从管道中取出任务，让程序去执行任务，在子类中设置各种处理的操作
        Notes:
            目前管道没有加锁操作，使用try防止对管道进行添加、删除操作后，
            遍历管道报错
        """
        sleep_time = float(1)/PER_SECOND_MAX_TIME
        while 1:
            sleep(sleep_time)
            try:
                for tubename,func in self._task_map.iteritems():
                    self.taskline[tubename].resize()
                    for task in self.taskline[tubename].tubes:
                            func(task)
            except:
                pass
            
    def show(self):
        """将统计信息、任务队列映射到共享内存"""
        while 1:
            sleep(SYNC_INTERVAL_TIME)
            try:
                sync["netcount"] = netcount
                sync["taskline"] = taskline
                logging.info("update [netcount] [taskline] ok")
            except:
                logging.warn("error in update [netcount] [taskline]")

    def start_dht(self):
        """启动DHT网络"""
        gevent.joinall(
            [
                gevent.spawn(self.auto_check_table),
                gevent.spawn(self._task_start),
                gevent.spawn(self.show),
                gevent.spawn(self.auto_check_task),
                gevent.spawn(self.serve_forever)
             ]
        )

    
    def auto_check_table(self):
        """每隔NODE_CHECK_INTERVAL_TIME秒对路由表进行检查，将需要检测的节点放入到任务管道中"""
        while 1:
            sleep(NODE_CHECK_INTERVAL_TIME) 
            task = self.taskline("ping").get("ping")
            if task is None:raise SystemError,"没有添加默认ping任务"
            need_check_nodes = self.table.need_check()
            for node in need_check_nodes:
                nid,addr = node.body
                task.put(("ping",(nid, addr)))
    
    def auto_check_task(self):
        """"""
        while 1:
            sleep(CONTROL_INTERVAL_TIME)
            if control_out.closed:
                logging.warn("任务控制输出端被关闭")
                break
            if not control_out.poll():continue
            control = control_out.recv()
            if (control[1][0] == "find_node" and control[1][1] == self.nid) or (control[1][0] == "ping" and control[1][1] == "ping"):
                logging.debug("原始任务不可设置,管道 -> %s,任务 -> %s,设置 -> %s,禁止(原始任务不可更改)")
                continue
            res = getattr(self.taskline, control[0])(*control[1])
            if res:
                logging.info("任务设置成功,管道 -> %s,任务 -> %s,设置 -> %s，成功True")
            elif res is None:
                logging.error("任务设置失败,管道 -> %s,任务 -> %s,设置 -> %s，失败Flase(任务不存在)")
            else:
                logging.debug("任务已经存在,管道 -> %s,任务 -> %s,设置 -> %s，失败Flase(任务已经存在)")

                




class S_Handle(BaseDHT):
    """发送信息的处理方式"""

    
    def __init__(self,port):
        """添加任务类型处理的关系映射"""
        super(S_Handle,self).__init__(port)
        self._task_map["ping"] = self.ping
        self._task_map["find_node"] = self.find_node
        self._task_map["get_peers"] = self.get_peers
        self._task_map["announce_peer"] = self.announce_peer
        
    @count(netcount,"send","ping")
    def _ping(self,ping,nid,addr):
        """进行ping操作的信息模版
        Args:
            ping: 填充位置，填写"ping"
            nid: 需要请求的节点nid唯一标识
            addr: 需要请求的节点网络地址
        """
        msg = {
            "y":"q",
            "q":"ping",
            "a":{
                "id":self.getnid(nid)
            }
        }
        self._add_tid_to_send(msg, ping, nid, addr)
        
    @count(netcount,"send","find_node")
    def _find_node(self,target,nid,addr):
        """进行find_node操作的信息模版
        Args:
            target: 需要寻找的节点的标识
            nid: 需要请求的节点nid唯一标识
            addr: 需要请求的节点网络地址
        """
        msg = {
            "y":"q",
            "q":"find_node",
            "a":{
                "id":self.getnid(nid),
                "target":target
            }
        }
        self._add_tid_to_send(msg, target, nid, addr) 
        
    @count(netcount,"send","get_peers")
    def _get_peers(self,info_hash,nid,addr):
        """进行get_peers操作的信息模版
        Args:
            info_hash: 需要寻找的种子的标识
            nid: 需要请求的节点nid唯一标识
            addr: 需要请求的节点网络地址
        """   
        msg = {
            "y":"q",
            "q":"get_peers",
            "a":{
                "id":self.getnid(nid),
                "info_hash":info_hash
            }
        }
        self._add_tid_to_send(msg, info_hash, nid, addr)  
    
    @count(netcount,"send","announce_peer")
    def _announce_peer(self,info_hash,nid,addr):
        """本网络只收集和请求信息，不将收集到的种子信息通知周围节点，
        因此不提供announce_peer操作，这里仅仅占位，保证代码的结构
        """
        pass
    
    def control_find_node(self,task):
        """对find_node任务的默认控制
        根据任务的运行时间和任务执行次数对任务进行控制
        """
        if task.id == self.nid:
            if len(self.table) > MIN_STOP_TABLE_LENGTH:
                task.stop()
            return
        if task.rtime > MAX_RUN_TIME or task.num > MAX_TASK_NUM:
            task.stop()
    
    def control_get_peers(self,task):
        """对find_node任务的默认控制
        根据任务的运行时间和任务执行次数对任务进行控制
        """
        if task.rtime > MAX_RUN_TIME or task.num > MAX_TASK_NUM:
            task.stop()
            
    def ping(self,task):
        """ping一个任务
        从任务队列中取出一个需要执行的任务，进行ping操作
        Args:
            task: 需要操作的任务管道
        """
        if not task.started:return
        taskitem = task.get()
        if taskitem:
            self._ping(task.id, *taskitem)        
    
    def find_node(self,task):
        """find_node一个任务
        从任务队列中取出一个需要执行的任务
        如果任务队列中有任务，则进行find_node操作
        如果没有任务，则进行任务初始化
        Args:
            task: 需要操作的任务管道
        """
        self.control_find_node(task)      
        if not task.started:return
        taskitem = task.get()
        if taskitem:
            self._find_node(task.id, *taskitem)
        else:
            self.boot_task(task) 
    
    def get_peers(self,task):
        """get_peers一个任务
        从任务队列中取出一个需要执行的任务
        如果任务队列中有任务，则进行get_peers操作
        如果没有任务，则进行任务初始化
        Args:
            task: 需要操作的任务管道
        """
        self.control_get_peers(task)
        if not task.started:return
        taskitem = task.get()
        if taskitem:
            self._get_peers(task.id, *taskitem)
        else:
            self.boot_task(task) 

    def boot_task(self,task):
        """任务初始化
        路由表不完善，则从启动节点获取一个进行启动(将需要进行的信息放入任务管道)
        如果路由表完善则从路由表中取出离任务id与或最近的节点进行启动(将需要进行的信息放入任务管道)
        Args:
            task: 需要操作的任务管道
        """
        if len(self.table) < MIN_STOP_BOOT_LENGTH:
            items = [(None,choice(BOOTSTRAP_NODES))]
        else:
            items = self.table.find_node2chrlist(task.id)
        for item in items:
            task.put(item)

    def announce_peer(self,task):
        """本网络只收集和请求信息，不将收集到的种子信息通知周围节点，
        因此不提供announce_peer操作，这里仅仅占位，保证代码的结构
        """
        pass    
    


class R_Handle(BaseDHT):
    """对收到的回复进行处理的方式"""

    
    def __init__(self,port):
        """添加响应的映射关系(KRPC中)，初始收到回复的关系映射表"""
        super(R_Handle,self).__init__(port)
        self.add_handle('r', self._r)
        self._r_handle["ping"] = self.r_ping
        self._r_handle["find_node"] = self.r_find_node
        self._r_handle["get_peers"] = self.r_get_peers
        self._r_handle["announce_peer"] = self.r_announce_peer
    
    def _check_r_msg_uptable(self,msg,addr):
        """对收到的回复处理
        对收到信息进行格式合法性检查，过滤掉不合法的信息
        对收到的tid转换为整数型获取其在挑战响应链表的索引位
        从挑战响应链表中取出当时发送的信息
        如果信息能对上，说明节点是正常节点
        返回挑战响应链表中取出当时发送的信息
        Args:
            msg: 收到的进行bencode解码后的信息
            addr: 收到的节点网络地址
        Returns:
            info: 挑战响应链表中取出当时发送的信息
            None: 收到错误的回复信息
        """
        if not (isinstance(msg["r"],dict) and msg["r"].has_key("id")):
            logging.debug("收到错误的回复信息:来自%s,信息格式 -> %s,节点nid -> %s"%(str(addr),type(msg),msg["r"].get("id")))
            return
        try:
            index = unpack("!H",msg["t"])[0]
        except structerror:
            logging.debug("收到错误的回复信息:来自%s,信息响应t -> %s"%(str(addr),msg["t"]))
            return
        try:
            info = self.tidlink[index]
            if (msg["r"]["id"]==info[2] and addr==info[3]) or info[2] is None:return info
            logging.debug("收到虚假的回复信息:来自%s,信息响应t -> %s,不存在于挑战响应链表"%(str(addr),msg["t"]))
        except IndexError:
            logging.debug("收到虚假的回复信息:来自%s,信息响应t -> %s,不存在于挑战响应链表,索引超过链表长度"%(str(addr),msg["t"]))
            return
        
    def _r(self,msg,addr):
        """对收到的回复处理
        对收到信息进行格式合法性检查，过滤掉不合法的信息
        对收到的tid转换为整数型获取其在挑战响应链表的索引位
        从挑战响应链表中取出当时发送的信息
        如果信息能对上，说明节点是正常节点，对路由表进行更新，如果节点不正常进行错误处理
        根据请求时使用的请求方式，通过收到回复的关系映射表找到响应的处理方式func
        根据请求时使用的请求方式和任务id，找到对应的任务task
        func(task,msg,addr) 
        Args:
            msg: 收到的进行bencode解码后的信息
            addr: 收到的节点网络地址
        """
        info = self._check_r_msg_uptable(msg, addr)
        if not info:
            self.r_error(msg, addr)
            return
        if info[2] is not None :self.table.push((msg["r"]["id"],addr[0],addr[1]))
        func = self._r_handle.get(info[0])
        if not func:
            logging.error("未定义处理方式:func -> %s 未在_r_handle 中定义相应的处理方式"%info[0])
            return
        task = self.taskline[info[0]][info[1]]
        if task is None:
            logging.info("任务已被移除:任务管道tubes -> %s,任务的id -> %s"%(info[0],info[1]))
            return
        func(task,msg,addr)     
        
    @count(netcount,"recv","r","ping")
    def r_ping(self,task,msg,addr):
        """对ping响应，只需将其更新路由表就行，因此不需要操作，这里仅仅占位，
        保持代码的结构
        """
        pass
    
    @count(netcount,"recv","r","find_node")
    def r_find_node(self,task,msg,addr):
        """对find_node请求后收到的回复进行处理，
        如果任务没有开始，则返回，
        如果收到的回复信息没有nodes则返回
        将nodes解析为节点信息，将其放入任务队列中
        on_find_node_node为扩展接口，可以对收到的正确node进行处理
        Args:
            task: 当时执行的任务
            msg: 收到的回复信息
            addr: 节点的网络地址
        """
        if not task.started:return
        if not msg["r"].has_key("nodes"):return
        nodelist = unpack_nodes(msg["r"]["nodes"])
        for node in nodelist:
            if node[0] == task.id and node[0] != self.nid:
                self.on_find_node_node(task, node)
            task.put(node)
            
    @count(netcount,"recv","r","get_peers")
    def r_get_peers(self,task,msg,addr):
        """对get_peers请求后收到的回复进行处理，
        如果任务没有开始，则返回，
        如果收到的回复信息有nodes则将nodes解析为节点信息，将其放入任务队列中
        如果有values信息，则调用on_get_peers_values
        on_get_peers_values为扩展接口，可以对收到的正确values进行处理
        Args:
            task: 当时执行的任务
            msg: 收到的回复信息
            addr: 节点的网络地址
        """
        if not task.started:return
        if msg["r"].has_key("nodes"):
            nodelist = unpack_nodes(msg["r"]["nodes"])
            for node in nodelist:
                task.put(node)
        if msg["r"].has_key("values") and msg["r"]["values"]:
            self.on_get_peers_values(task,msg["r"]["values"])
            
    @count(netcount,"recv","r","announce_peer")
    def r_announce_peer(self,task,msg,addr):
        """未发送nnounce_peer信息，因此不会收到正确的nnounce_peer回复，
        此处仅仅占位，保持代码结构
        """
        pass   
    
    @count(netcount,"recv","r","error")
    def r_error(self,msg,addr):
        """"""
        pass
        
    def on_get_peers_values(self,task,values):
        """对回复中包含请求的种子信息的扩展接口，在使用是自己添加"""
        pass
    
    def on_find_node_node(self,task,node):
        """对回复中包含任务节点的信息，扩展接口，在使用是自己添加"""
        pass    

        
    

class Q_Handle(BaseDHT):
    """对收到的请求信息的处理方式"""
    
    def __init__(self,port):
        """添加响应请求的映射关系(KRPC中)，初始收到请求的关系映射表"""
        super(Q_Handle,self).__init__(port)
        self.add_handle('q', self._q)
        self._q_handle["ping"] = self.on_ping
        self._q_handle["find_node"] = self.on_find_node
        self._q_handle["get_peers"] = self.on_get_peers
        self._q_handle["announce_peer"] = self.on_announce_peer
        
    def _q(self,msg,addr):
        """对收到的请求处理，
        首先检查收到的请求结构是否合法，不合法则返回
        通过收到请求的关系映射表获取处理方式
        func(msg,addr) 
        """
        if not (msg.has_key("a") and msg.has_key("q") and 
                isinstance(msg["a"],dict) and isinstance(msg["q"],str)
                and msg["a"].has_key("id")):
            logging.debug("收到错误的请求信息:来自%s,请求方式q -> %s,请求信息类型 -> %s"%(str(addr),msg.get("q"),type(msg.get("a"))))
            self.q_error(msg, addr)
            return
        func = self._q_handle.get(msg["q"])
        if not func:
            logging.debug("未定义的信息方式:信息方式q -> %s,没有被定义相应的处理方式"%msg["q"])
            return
        func(msg,addr) 
    
    @count(netcount,"recv","q","error")
    def q_error(self,msg,addr):
        """"""
        pass
        
    @count(netcount,"recv","q","ping")
    def on_ping(self,msg,addr):
        """对ping请求进行回复，正常响应
        """
        msg = {
                "t":msg["t"],
                "y":"r",
                "r":{
                    "id":self.getnid(msg["a"]["id"]),
                }
            }
        self.send_msg(msg, addr)
    
    @count(netcount,"recv","q","find_node")
    def on_find_node(self,msg,addr):
        """对find_node请求进行回复，去路由表获取距离最近的节点"""
        if not msg["a"].has_key("target"):return
        target = msg["a"]["target"]
        nodes = self.table.find_node2chrall(target)
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.getnid(msg["a"]["id"]),
                "nodes":nodes
            }
        }
        self.send_msg(msg, addr)
        
    @count(netcount,"recv","q","get_peers")
    def on_get_peers(self,msg,addr):
        """对get_peers请求进行回复，去路由表获取距离最近的节点"""
        if not msg["a"].has_key("info_hash"):return
        self._on_get_peers_info(msg["a"], addr)
        target = msg["a"]["info_hash"]
        nodes = self.table.find_node2chrall(target)
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.getnid(msg["a"]["id"]),
                "nodes":nodes,
                "token":"aoeusnth"
            }
        }
        self.send_msg(msg, addr)
    
    @count(netcount,"recv","q","announce_peer")
    def on_announce_peer(self,msg,addr):
        """对announce_peer请求进行回复，正常响应"""
        if not msg["a"].has_key("info_hash"):return
        self._on_announce_peer_info(msg["a"], addr)        
        msg = {
            "t":msg["t"],
            "y":"r",
            "r":{
                "id":self.nid,
            }
        }
        self.send_msg(msg, addr)    
    
    @count(netcount,"collect","get_peers")
    def _on_get_peers_info(self,info,addr):
        """扩展接口，收到的get_peers的主要信息"""
        self.on_get_peers_info(info, addr) 
    
    @count(netcount,"collect","announce_peer")
    def _on_announce_peer_info(self,info,addr):
        """扩展接口，收到的gannounce_peer的主要信息"""
        self.on_announce_peer_info(info, addr) 
        
    def on_announce_peer_info(self,info,addr):
        """扩展接口，收到的gannounce_peer的主要信息"""
        print info,addr    
        
    def on_get_peers_info(self,info,addr):
        """扩展接口，收到的get_peers的主要信息"""
        print info,addr    


class E_Handle(BaseDHT):
    """收到的错误信息的处理方式"""

    def __init__(self, port):
        """添加响应请求的映射关系(KRPC中)"""
        super(E_Handle,self).__init__(port)
        self.add_handle('e', self._e)
    
    @count(netcount,"recv","e")
    def _e(self,msg,addr):
        """对错误信息不处理"""
        pass


        
class NormalDHT(S_Handle,R_Handle,Q_Handle,E_Handle):
    """通过多继承的方式，将处理方式合并，获取一个正常的DHT"""

    
    def __init__(self,*args):
        """Constructor"""
        if args:
            super(NormalDHT,self).__init__(*args)
        else:
            super(NormalDHT,self).__init__(DHTPORT)

########################################################################
class DHTSpider(NormalDHT):
    """"""
    #----------------------------------------------------------------------
    def getnid(self,nid = None):
        """"""
        return nid[:10]+self.nid[10:] if nid else self.nid
    def find_node(self,task):
        """find_node一个任务
        从任务队列中取出一个需要执行的任务
        如果任务队列中有任务，则进行find_node操作
        如果没有任务，则进行任务初始化
        Args:
            task: 需要操作的任务管道
        """
        if task.id == self.nid and len(self.table) > MIN_STOP_TABLE_LENGTH:
            pass       
        if not task.started:return
        taskitem = task.get()
        if taskitem:
            self._find_node(task.id, *taskitem)
        else:
            self.boot_task(task) 
        
        
    
    
