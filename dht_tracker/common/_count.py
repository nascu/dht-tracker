#!/usr/bin/env python
#coding:utf-8

"""
进行数据统计
用树结构实现对数据的统计，父节点可通过递归获取所有子节点的所有数据统计之和
count生成器，通过传入的参数进行惰性计算，缩短运行时的数据结构
reserve_time 对时间进行结构化
"""
from functools import wraps
from time import time,localtime,strftime
class CountTree(object):
    """"""
    def __init__(self):
        """Constructor"""
        self._child = dict()
        self._count = 0
    @property
    def count(self):
        if self._child:
            return reduce(lambda x,y:x+y, [i.count for i in self._child.itervalues()])
        else:
            return self._count
    @count.setter
    def count(self,num):
        """"""
        self._count = num
    @property
    def status(self):
        """"""
        res = {
            "count":self.count,
        }
        res["detail"] = [(name,child.status) for name,child in self._child.iteritems()]
        return res
   
    def get(self,key):
        if key not in self._child:
            self._child[key] = CountTree()
        return self._child[key]        
    #----------------------------------------------------------------------
    def __getitem__(self,key):
        """"""
        return self.get(key)
    def __call__(self,key):
        """"""
        return self.get(key)
    #----------------------------------------------------------------------
    def __contains__(self,key):
        """"""
        return key in self._child
        


def count(cls,*args):
    """"""
    assert isinstance(cls,CountTree)
    for arg in args:
        cls = cls[arg]    
    def inner(func):
        @wraps(func)
        def wrapper(*args,**kwargs):
            incls = cls
            for key in reserve_time():
                incls = incls[key]
            incls.count+=1
            return func(*args,**kwargs)
        return wrapper
    return inner

#----------------------------------------------------------------------
def reserve_time():
    """"""
    return strftime("%Y %m %d %H %M",localtime(time())).split(" ")