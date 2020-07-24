#!/usr/bin/env python
#coding:utf-8
"""
任务管道
实现对单个任务的控制,方便根据运行时间、执行次数对任务的管控
"""
from __future__ import absolute_import
from time import time
from ..config import TASK_MAX_LENGTH

class Task(object):
    """任务单元
    任务的暂停与启动
    管道内放置需要执行的任务集合
    对任务的开始时间以及任务的执行时间进行记录
    Notes:
        对于任务的控制，可以通过时间，也可以通过已经执行的任务数量，通过将remove设为真，则
        在下次遍历时，将该任务删除
    Attributes:
        id: 任务的标识符
        maxlength: 任务管道内集合的最大长度，超过将会被丢弃
        removed: 任务移除标识(0-不移除，1任务需要移除)
        length: 管道内需要执行任务的数量
        num: 已经执行的任务数量
        started: 任务的状态(是否被启动)
        rtime: 任务本次执行时间
        ptime: 任务放置的初始时间
        put: 向任务管道内添加一个任务(去重，超过最大长度将会被丢弃)
        get: 从任务管道获取一个待执行的任务
        remove: 将任务设置为需要移除状态
        start: 将任务的状态设置为开始
        stop: 将任务的状态设置为暂停
        clear: 清空任务的管道
    """
    _maxlength = TASK_MAX_LENGTH
    
    def __init__(self,id):
        """任务单元初始化
        _ptime: 任务初始时间
        _queue: 一个空的任务管道
        _removed: 任务移除标识(0-不移除，1任务需要移除)
        start: 默认将任务状态设置为开始
        Args:
            id: 任务的唯一标识
        """
        self._id = id
        self._ptime = time()
        self._queue = set()
        self._removed = 0
        self._num = 0
        self.start()
    
    @property
    def num(self):
        """"""
        return self._num
        
    @property
    def removed(self):
        """任务移除标识(0-不移除，1任务需要移除)"""
        return self._removed 
        
    def remove(self):
        """将任务设置为需要移除状态"""
        self.stop()
        self._removed = 1
        
    @property
    def maxlength(self):
        """任务管道内集合的最大长度，超过将会被丢弃"""
        return self._maxlength
    
    @property
    def length(self):
        """管道内需要执行任务的数量"""
        return len(self._queue)
    @property
    def items(self):
        """任务管道内待执行任务的集合
        Returns:
            set([...])
        """
        return self._queue
    
    def clear(self):
        """清空任务管道"""
        return self._queue.clear()
    
    @property
    def id(self):
        """任务的标识符"""
        return self._id
    
    @property
    def started(self):
        """任务的状态(是否被启动)
        Returns:
            True: 任务状态为开始
            False: 任务状态为暂停
        """
        return self._started
    
    @property
    def rtime(self):
        """本次任务的执行时间"""
        return time() - self._stime
    
    @property
    def ptime(self):
        """任务放置的初始时间"""
        return self._ptime
    
    @property
    def status(self):
        """任务的状态
        Returns:
            id: 任务的唯一标识
            started: 任务的状态(是否被启动)
            ptime: 任务放置的初始时间
            rtime: 本次任务的执行时间
            num: 已经执行的任务数量
            length: 管道内需要执行任务的数量
            maxlength: 任务管道内集合的最大长度，超过将会被丢弃
            items: 任务管道内待执行任务的集合
        """
        res = {
            "id":self.id,
            "started":self.started,
            "ptime":self.ptime,
            "rtime":self.rtime,
            "num":self.num,
            "length":self.length,
            "maxlength":self.maxlength,
            "items":list(self.items)
        }
        return res
        
    def put(self,item):
        """向任务管道内添加一个任务
        使用set的hash进行去重操作，如果管道内集合数量超过最大数量则丢弃
        """
        if self.length < self._maxlength:
            self._queue.add(item)
    
    def get(self):
        """从任务管道获取一个待执行的任务"""
        try:
            item = self._queue.pop()
            self._num += 1
        except KeyError:
            item = None
        return item
    
    def start(self):
        """将任务的状态设置为开始
        设置新的开始时间
        """
        self._stime = time()
        self._started = 1
    
    def stop(self):
        """将任务的状态设置为暂停"""
        self._started = 0
        
    def __len__(self):
        """"""
        return self.length
        
        

class Tubes(object):
    """任务管道，使用列表的方式实现
    以任务的唯一标识id为识别方式，提供添加，删除，获取等操作
    Attributes:
        push: 向任务管道内添加一个任务,如果管道内已经有了该任务，则不添加
        remove: 从管道内移除一个任务
        get: 通过任务唯一标识id获取任务
        start: 通过任务唯一标识id启动任务
        stop: 通过任务唯一标识id暂停任务
    """
    
    def __init__(self):
        """初始化一个空的任务管道"""
        self._tubes = list()
    
    @property
    def length(self):
        """"""
        return len(self._tubes)
    
    @property
    def tubes(self):
        """任务管道内所有的任务"""
        return self._tubes
    
    def push(self,id):
        """向任务管道内添加一个任务,
        如果管道内已经有了该任务，则不添加
        Args:
            id: 任务唯一标识
        Returns:
            True: 任务添加成功
            False: 管道内已经有该任务
        """
        task = self._position(id)
        if task:
            return False
        else:
            self._tubes.append(Task(id))
            return True
    
    def remove(self,id):
        """从管道内移除一个任务
        Args:
            id: 任务唯一标识
        Returns:
            True: 任务设置为待移除
            None: 管道没有该任务
        """
        task = self._position(id)
        if task:
            task.remove()
            return True
    
    def get(self,id):
        """通过任务唯一标识id获取任务
        Args:
            id: 任务唯一标识
        Returns:
            task: 任务单元
            None: 管道内没有该id的任务
        """
        return self._position(id)
    
    def _position(self,id):
        """通过任务唯一标识id获取任务
         Args:
            id: 任务唯一标识
        Returns:
            task: 任务单元
            None: 管道内没有该id的任务
        """
        for task in self._tubes:
            if task.id == id:
                return task
    
    def start(self,id):
        """通过任务唯一标识id启动任务
         Args:
            id: 任务唯一标识
        Returns:
            True: 任务启动成功
            None: 管道内没有该id的任务
        """
        task = self._position(id)
        if task:
            task.start()
            return True
    
    @property
    def status(self):
        """"""
        res = {
            "length":self.length,
        }
        res["detail"] = [task.status for task in self.tubes]
        return res
    
    def stop(self,id):
        """通过任务唯一标识id暂停任务
         Args:
            id: 任务唯一标识
        Returns:
            True: 任务暂停成功
            None: 管道内没有该id的任务
        """
        task = self._position(id)
        if task:
            task.stop()
            return True 
    
    def resize(self):
        """重新调整，将需要移除的任务移除"""
        for task in self._tubes:
            if task.removed:
                self._tubes.remove(task)
                self.resize()
        
    def __getitem__(self,id):
        """方便通过[id]的方式获取任务
        Args:
            id: 任务唯一标识
        Returns:
            task: 任务单元
            None: 管道内没有该id的任务
        """
        return self.get(id)

        

class TaskLine(object):
    """任务队列，使用字典的方式实现
    以key-value的方式可以添加多个不同类型的任务管道
    对目前没有的key可以通过使用自动添加
    Attributes:
        tubes: 所有的任务类型
        addtube: 添加一个类型的任务管道(key-value)
        push: 向一个任务管道中添加任务
        get: 从一个任务管道中获取一个任务
    """
    def __init__(self):
        """初始化一个字典用来存放任务管道"""
        self.mqueue = dict()
    
    @property
    def length(self):
        """"""
        return len(self.mqueue)
    
    @property
    def tubes(self):
        """所有的任务类型"""
        return self.mqueue.keys()
    
    def addtube(self,key):
        """添加一个类型的任务管道(key-value)
        如果已经存在该类型的管道则跳过
        """
        if not self.mqueue.has_key(key):
            self.mqueue[key] = Tubes()
    
    def push(self,key,id):
        """向一个任务管道中添加任务
        Args:
            key: 任务类型
            id: 任务唯一标识id
        Returns:
            True: 任务添加成功
            False: 管道内已经有该任务
        """
        self.addtube(key)
        return self.mqueue[key].push(id)
    
    def stop(self,key,id):
        """停止管道内的一个任务
        Args:
            key: 任务类型
            id: 任务唯一标识id
        Returns:
            True: 任务暂停成功
            None: key管道内没有该id的任务
        """
        self.addtube(key)
        return self.mqueue[key].stop(id)
    
    def start(self,key,id):
        """启动管道内的一个任务
        Args:
            key: 任务类型
            id: 任务唯一标识id
        Returns:
            True: 任务启动成功
            None: key管道内没有该id的任务
        """
        self.addtube(key)
        return self.mqueue[key].start(id)
    
    def remove(self,key,id):
        """从管道内移除一个任务
        Args:
            key: 任务类型
            id: 任务唯一标识id
        Returns:
            True: 任务设置为待移除
            None: key管道内没有该id的任务
        """
        self.addtube(key)
        return self.mqueue[key].remove(id)        
    
    @property
    def status(self):
        """"""
        res = {
            "length":self.length,
        }
        res["detail"] = [(key,tubes.status) for key,tubes in self.mqueue.items()]
        return res
        
    def get(self,key):
        """获取一个管道
        Args:
            key: 任务类型
        Returns:
            Tubes: 任务管道
        """
        self.addtube(key)
        return self.mqueue[key]
    
    def __getitem__(self,key):
        """可通过[key],获取一个管道
        Args:
            key: 任务类型
        Returns:
            Tubes: 任务管道
        """
        return self.get(key)

    def __call__(self,key):
        """可通过call方法，获取一个管道
        Args:
            key: 任务类型
        Returns:
            Tubes: 任务管道
        """
        return self.get(key)