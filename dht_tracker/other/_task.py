#!/usr/bin/env python
#coding:utf-8
"""
  Author:  NASCU --<>
  Purpose: 
  Created: 04/19/18
"""
from _utils import Dict
from time import time
from threading import Lock

########################################################################
class Task(object):
    """任务单元
    tid：任务id
    timeout：任务过期时间
    delay：任务延迟时间
    args，kwargs：任务执行的参数
    """

    #----------------------------------------------------------------------
    def __init__(self,tid,timeout,delay,*args,**kwargs):
        """Constructor"""
        self._ptime = time()
        self._num = 0
        self._data = Dict()
        self._tid = tid
        self.timeout = timeout
        self._kwargs = kwargs
        self._setkwargs(*args,**kwargs)
        self._int(delay)
    #----------------------------------------------------------------------
    def _int(self,delay):
        """"""
        self._state = 0
        self._stime = time() + delay
    #----------------------------------------------------------------------
    @property
    def status(self):
        """"""
        res =  {
            "tid":self.tid,
            "num":self._num,
            "state":self._state,
            "ptime":self._ptime,
            "stime":self._stime,
            "ustime":self.ustime,
            "timeout":self.timeout,
            "isready":self.isready
                }
        return res
        
    #----------------------------------------------------------------------
    def body(self):
        """"""
        
        return self._use()
    #----------------------------------------------------------------------
    def _use(self):
        """"""
        self._stime = time()
        self._num += 1
        return (self.tid,self._data.args,self._kwargs)
    #----------------------------------------------------------------------
    def get(self,key,default = None):
        """"""
        return self._data.get(key,default)
    #----------------------------------------------------------------------
    def kwargs(self):
        """"""
        return self._kwargs
    #----------------------------------------------------------------------
    @property
    def data(self):
        """"""
        return self._data
    #----------------------------------------------------------------------
    def _setkwargs(self,*args,**kwargs):
        """"""
        self._data["tid"] = self._tid
        self._data["args"] = args
        for key,value in kwargs.iteritems():
            self._data[key] = value
    #----------------------------------------------------------------------
    @property
    def tid(self):
        """"""
        return self._tid

    #----------------------------------------------------------------------
    @property
    def isready(self):
        """"""
        return self.ustime >=0 and not self._state
    #----------------------------------------------------------------------
    def ptime(self):
        """"""
        return self._ptime
    #----------------------------------------------------------------------
    @property
    def ustime(self):
        """"""
        return time() - self._stime
    #----------------------------------------------------------------------
    def touch(self,delay = 0):
        """"""
        self._int(delay)
    #----------------------------------------------------------------------
    def is_over_time(self):
        """"""
        return self.ustime >= self.timeout and self._state
    #----------------------------------------------------------------------
    def reput(self,timeout,delay = 0):
        """"""
        self.touch(delay)
        self.timeout = timeout

        
        
########################################################################
class Tubes(object):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self._tubes = []
    #----------------------------------------------------------------------
    def put(self,tid,timeout = 15,delay = 0,*args,**kwargs):
        """"""
        self._tubes.append(Task(tid,timeout,delay,*args,**kwargs))
    #----------------------------------------------------------------------
    def get(self,num = 1):
        """"""
        res = []
        for task in self._tubes:
            if task.isready:
                res.append(task)
            if len(res) == num:
                return res
        return res
        
    #----------------------------------------------------------------------
    def get_by(self,key,value):
        """"""
        res = []
        for task in self._tubes:
            if task.get(key) == value:
                res.append(task)
        return res
    #----------------------------------------------------------------------
    def remove(self,task):
        """"""
        if task in self._tubes:
            self._tubes.remove(task)
    #----------------------------------------------------------------------
    def remove_by(self,key,value):
        """"""
        res = False
        for task in self._tubes:
            if task.get(key) == value:
                self.remove(task)
                res = True
                break
        if res:self.remove_by(key, value)
    #----------------------------------------------------------------------
    def clear(self):
        """"""
        res = False
        for task in self._tubes:
            if task.is_over_time():
                self.remove(task)
                res = True
                break
        if res:self.clear()
    #----------------------------------------------------------------------
    @property
    def tid_list(self):
        """"""
        res = []
        for task in self._tubes:
            res.append(task.tid)
        return res
    #----------------------------------------------------------------------
    @property
    def status(self):
        """"""
        res = {
            "length":len(self._tubes),
            "tid_list":self.tid_list,
            "detailed":[task.status for task in self._tubes]
               }
        return res
            

########################################################################
class Mqueue(object):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.mqueue = Dict()
    #----------------------------------------------------------------------
    def addtube(self,key):
        """"""
        if not self.mqueue.has_key(key):
            self.mqueue[key] = Tubes()
    #----------------------------------------------------------------------
    def put(self,key,tid,timeout = 15,delay = 0,*args,**kwargs):
        """"""
        self.addtube(key)
        self.mqueue[key].put(tid,timeout = 15,delay = 0,*args,**kwargs)
    #----------------------------------------------------------------------
    def get(self,key,num = 1):
        """"""
        self.addtube(key)
        return self.mqueue[key].get(num)

    #----------------------------------------------------------------------
    def __call__(self,key):
        """"""
        self.addtube(key)
        return self.mqueue[key]

    
    
line = Mqueue()