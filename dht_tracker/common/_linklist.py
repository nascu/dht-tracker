#!/usr/bin/env python
#coding:utf-8
"""链表"""


class Node(object):
    """链表的Node节点
    Attributes:
        data: 当前节点的数据
        _next: 下一个节点的指针
    """
    
    def __init__(self,data,pnext=None):
        """初始化一个节点"""
        self.data = data
        self._next = pnext
    
    def __str__(self):
        """将该节点的数据转为字符串格式"""
        return str(self.data)
        
    

class Linklist(object):
    """链表
    Attributes:
        _head: 整条链表的信息
        _length,length: 链表的长度
        isEmpty: 判断链表是否为空
    """

    def __init__(self):
        """初始化链表，长度为零，整条链表的信息为None"""
        self._head = None
        self._length = 0
    
    @property
    def length(self):
        """链表的长度
        Returns:
            返回链表的长度(int)
        """
        return self._length
    
    @property
    def isEmpty(self):
        """判断链表是否为空
        Returns:
            True: 链表为空链表
            False: 链表为非空链表
        """
        return self._length == 0
    
    def append(self,item):
        """在链表尾部添加上一个节点
        Args:
            item: 可以是节点Node，或者节点Node的信息
        Returns:
            返回链表的长度(int)
        """
        if isinstance(item,Node):
            item = item
        else:
            item = Node(item)
        if not self._head:
            self._head = item
        else:
            node = self._head
            while node._next:
                node = node._next
            node._next = item
        self._length += 1
        return self._length
    
    def _checkindex(self,index):
        """检验输入的索引值的合法性是否在链表索引范围内
        Args:
            index: type->int 链表的索引值
        Raises:
            IndexError: 索引值不合法或者超出链表索引范围
        """
        if not (index >= 0 and index <= self.length):
            raise IndexError("Linklist index out of range")   
    
    def _splitbyindex(self,index):
        """在链表该索引前一个节点和该索引的节点
        Args: 
            index: type->int 链表的索引值
        Returns:
            prev: 链表该索引前的节点
            node: 链表该索引的节点
        """
        self._checkindex(index)
        node = self._head
        prev = None
        i = 0
        while node and i < index:
            prev = node
            node = node._next
            i += 1
        return prev,node
    
    def _checkitem(self,item):
        """判断item是否为Node类型，不是将返回Node类型的节点
        Args:
            item: 节点信息或者Node节点
        Returns:
            Node节点
        """
        if isinstance(item,Node):
            item = item
        else:
            item = Node(item)
        return item
    
    def _position(self,index):
        """根据链表索引返回该索引的Node节点
        Args:
            index: 链表索引值
        Returns:
            该索引值下的Node节点
        """
        node = self._head
        i = 0
        while node and i < index:
            node = node._next
            i += 1
        return node
    
    def insert(self,item,index):
        """向链表索引处插入节点
        Args: 
            item: 节点信息或者Node节点
            index: 链表的索引值
        Raises:
            IndexError: 索引值不合法或者超出链表索引范围
        """
        item = self._checkitem(item)
        prev,node = self._splitbyindex(index)
        item._next = node
        if prev:
            prev._next = item
        else:
            self._head = item
        self._length += 1

    def delete(self,index):
        """删除链表索引处的节点
        Args:
            index: 链表的索引值
        Raises:
            IndexError: 索引值不合法或者超出链表索引范围
            IndexError: 空链表没有节点可以删除
        """
        if self.isEmpty:
            raise IndexError("delete from empty Linklist")
        prev,node = self._splitbyindex(index)        
        if prev:
            prev._next = node._next
        else:
            self._head = node._next
        self._length -= 1
    
    def update(self,data,index):
        """更新链表索引下的节点信息
        Args:
            data: 更新的节点信息
            index: 链表的索引值
        Raises:
            IndexError: 索引值不合法或者超出链表索引范围
            IndexError: 空链表没有节点可以删除
        """
        if self.isEmpty:
            raise IndexError("update from empty Linklist")
        self._checkindex(index)
        node = self._position(index)
        node.data = data
    
    def index(self,data):
        """获取某个信息或者节点在链表的第一个索引值
        Args:
            data: Node节点或者信息
        Returns:
            i: 该信息或者给节点的信息在链表的第一个索引值
            None: 在该链表中没有匹配到响应的信息
        """
        if isinstance(data,Node):
            data = data.data
        i = 0
        node = self._head
        while node:
            if node.data == data:
                return i
            i += 1
            node = node._next     
    
    def items(self):
        """返回该链表下所有节点的信息
        Returns:
            该链表下所有节点的信息
        """
        res = []
        node = self._head
        while node:
            res.append(node.data)
            node = node._next
        return res
   
    def getitem(self,index):
        """通过索引值获取节点信息
        Args:
            index: 链表的索引值
        Returns:
            链表索引值下节点的信息
        Raises:
            IndexError: 索引值不合法或者超出链表索引范围
        """
        self._checkindex(index)
        node = self._position(index)
        return node.data
    
    def __getitem__(self,index):
        """使链表可以通过[index]的方式获取节点信息，方法同self.getitem"""
        return self.getitem(index)
   
    def __len__(self):
        """使链表可以通过len()方法获取链表的长度
        Returns:
            链表的长度
        """
        return self._length
   
    def __iter__(self):
        """使链表可以通过iter()方法获取一个无限循环的迭代器，
        并可以通过send()方法修改节点信息
        """
        node = self._head
        while 1:
            if not node:
                node = self._head
            data = yield node
            if data:
                node.data = data
            node = node._next