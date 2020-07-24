#!/usr/bin/env python
#coding:utf-8
"""
对http://www.bittorrent.org/beps/bep_0005.html中KRPC Protocol的实现，
实现对发送信息的编码以及对接收信息的解码
对接收信息基本格式的检验，并对格式不正确的自动进行error回复
"""
import logging
from gevent.server import DatagramServer
from ..common import Dict,bdumps,bloads,netcount,count

class KRPC(DatagramServer):
    """KRPC的实现
    对发送、接收信息的Bencode解码与转码
    对接收信息基本格式的校验
    对格式不正确的信息进行自动error回复
    Attributes:
        error_msg: 官方定义的错误信息集合
        _auto_handle: 对于响应的处理映射关系表
        _default_handle: 对于找不到响应处理方式的默认处理方式
        handle_func: 已经设置的处理方式的键值
        add_handle: 添加处理方式
        handle: 对于udp收到的所有信息的处理
        send_msg: 对需要发送的信息进行编码，并通过udp发送到相应的网络地址
    """
    error_msg = {
        201:[201,'Generic Error'],
        202:[202,'Server Error'],
        203:[203,'Protocol Error, such as a malformed packet, invalid arguments, or bad token'],
        204:[204,'Method Unknown']
    }    

    def __init__(self,port,default):
        """添加默认的处理方式，对udp服务进行初始设置，初始一个空的响应的处理映射关系表
        Args:
            port: udp服务的端口号
            default: 对于找不到响应处理方式的默认处理方式
        """
        self._default_handle = default
        self._set_server(port)
        self._auto_handle = Dict()
    
    @property
    def handle_func(self):
        """已经设置的处理方式的键值"""
        return self._auto_handle.keys()

    def add_handle(self,key,func):
        """添加处理方式
        Args:
            key: 响应的键值
            func: 对于响应的处理方式
        """
        self._auto_handle[key] = func
    
    def _set_server(self,port):
        """对udp服务进行初始设置
        Args:
            port: udp服务的端口号
        """
        self.port,self.bind = int(port),":{}".format(port)        
        DatagramServer.__init__(self,self.bind) 
    
    def handle(self,msg,addr):
        """对于udp收到的所有信息的处理
        对收到的信息进行bencode解码，如果不符合krpc规则则进行响应的error处理
        通过响应处理映射进行相应的处理
        Args:
            msg: 接收到的信息
            addr: 接收的网络地址
        """
        msg = bloads(msg)
        if not (isinstance(msg,dict) and msg.has_key("t")):
            self._error_handle(203, addr)
        elif not (msg.has_key("y") and msg.has_key(msg["y"])):
            self._error_handle(204, addr,msg["t"])
        else:
            self._auto_handle(msg["y"].lower(),self._default_handle)(msg,addr)
    
    @count(netcount,"recv","error")
    def _error_handle(self,code,addr,t = "er"):
        """对接收错误的信息进行相应的error处理"""
        msg = {
            "y":"e",
            "t":t,
            "e":self.error_msg[code]
               }
        self.send_msg(msg,addr)
        logging.debug("错误的信息:来自%s，错误编码%d"%(str(addr),code))
        
    def send_msg(self,msg,addr):
        """对需要发送的信息进行编码，并通过udp发送到相应的网络地址
        Args:
            msg: 需要发送的信息(type->dict)
            addr: 需要发送到的网络地址
        """
       
        try:
            if not (isinstance(msg,dict) and msg.has_key("t")):
                raise TypeError,"发送的信息必须是dict格式"
            if not msg.has_key("t"):
                raise KeyError,"发送的信息必须包含key:t"
            try:
                self.sendto(bdumps(msg),addr)
            except:
                logging.error("网络不可用，或者地址不可用%s"%str(addr))
        except:
            logging.warn("发送的信息格式不正确:发送的格式 -> %s,发送的内容 -> %s"%(type(msg),str(msg)))
        

