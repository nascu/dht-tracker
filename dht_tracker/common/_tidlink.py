#!/usr/bin/env python
#coding:utf-8
"""
挑战者-响应 请求映射链表
使链表可以通过iter()方法获取一个无限循环的迭代器(链表的最大长度为)
方便对链表的信息的添加,缩短时间
"""
from itertools import cycle
from struct import unpack,pack
from . import Node,Linklist
from ..config import TID_MAX_LENGTH

class TidLink(Linklist):
    """
    """
    _max_length = TID_MAX_LENGTH
    tid_iter = cycle(xrange(0,TID_MAX_LENGTH))

    @property
    def max_length(self):
        """"""
        return self._max_length
        
    def __iter__(self):
        """使链表可以通过iter()方法获取一个无限循环的迭代器(链表的最大长度为)，
        并可以通过send()方法修改节点信息
        初始链表为空链表，通过无限循环的迭代器cycle可以无限的循环链表，链表的节点位置即为tid的整数形式
        当链表为空，在头部添加一个节点，通过send方法为链表添加干节点的内容，
        链表没有下一个节点并且不是cycle的最大长度，为该链表添加下一个节点
        Yields:(tid,node)
            tid: 该位置(正整数索引) 的网络大端字节
            node: 该位置(正整数索引)的节点
        """
        if self._head is None:
            self._head = Node(None)
            self._length += 1        
        while 1:
            tid_num = self.tid_iter.next()
            if tid_num == 0:node = self._head           
            data = yield (pack("!H",tid_num),node)
            if node._next is None and self.length < self._max_length:
                node._next = Node(None)
                self._length += 1
            if data:node.data = data
            node = node._next        