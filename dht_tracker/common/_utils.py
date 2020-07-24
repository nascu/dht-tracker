#!/usr/bin/env python
#coding:utf-8

from bencode import bdecode,bencode,BTL
from socket import inet_ntoa,inet_aton
from struct import pack,unpack
from uuid import uuid3,NAMESPACE_DNS
from hashlib import sha1
from ..config import (
    NODE_LENGTH,
    NID_LENGTH,
    ADDR_LENGTH,
)

nid = sha1(uuid3(NAMESPACE_DNS, "nascu").urn).digest()


class Dict(dict):
    """使用__setattr__,__getattr__,__delattr__,使之通过"."调用
    添加__call__使Dict("key")方法可以获取到Dict.get("key")相同的效果    
    """
    
    def __setattr__(self,key,value):
        """Dict.key = value"""
        self[key] = value
    
    def __getattr__(self,key):
        """Dict.key"""
        if self.has_key(key):
            return self[key]
        else:
            return None
    
    def __delattr__(self,key):
        """del Dict.key"""
        del self[key]
    
    def __call__(self,key,default = None):
        """Dict("key")"""
        return self.get(key,default)




def chr2ipv4(ip):
    """将4字节的ip字符串转为IPV4地址
    Args:
        ip: ASCII*ADDR_LENGTH
    Returns:
        ipv4: xx.xx.xx.xx
    """
    if len(ip) == ADDR_LENGTH:
        return inet_ntoa(ip)

def ipv42chr(ip):
    """将IPV4地址转为4字节的字符串
    Args:
        ipv4: xx.xx.xx.xx
    Returns:
        ip: ASCII*ADDR_LENGTH
    """
    try:
        return inet_aton(ip)
    except:
        pass

def ascii2l16(nid):
    """将16进制ASCII码转为10进制的长整数"""
    return long(nid.encode("hex"),16)    

def bloads(msg):
    """将信息用bencode解码
    Args:
        msg: 需要进行b解码的信息
    Returns:
        b解码后的信息
    """
    try:
        if msg:return bdecode(msg)
    except (BTL.BTFailure,KeyError):
        pass

def bdumps(msg):
    """将信息用bencode解码
    Args:
        msg: 需要进行b编码的信息
    Returns:
        b编码后的信息
    """
    try:
        if msg:return bencode(msg)
    except (BTL.BTFailure,KeyError):
        pass

def unpack_nodes(nodes):
    """将nodes转为nid,ip,port的列表
    Args:
        nodes: ASCII*NODE_LENGTH+ASCII*NODE_LENGTH+ASCII*NODE_LENGTH+...
    Returns:
        [(nid,(ip,port)),(nid,(ip,port)),(nid,(ip,port))...]
    """
    if len(nodes)%NODE_LENGTH:
        return []
    nrnodes = len(nodes) / NODE_LENGTH
    nodes = unpack("!" + "{}s{}sH" .format(NID_LENGTH,ADDR_LENGTH)*nrnodes, nodes)
    return [(nodes[i],(inet_ntoa(nodes[i+1]),nodes[i+2])) for i in xrange(0,len(nodes),3)]

def pack_node(nid,ip,port):
    """nid,ip,port的转为node
    Args:
        nid: 节点唯一标识
        ip: ipv4地址
        port: 端口号
    Returns:
        nid+ipv4地址的字符串格式+port的网络大端字节
    """
    try:
        return nid+inet_aton(ip)+pack("!H",port)
    except:
        return ''