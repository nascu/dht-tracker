#!/usr/bin/env python
#coding:utf-8
"""
对http://www.bittorrent.org/beps/bep_0005.html中Routing Table的实现
优化了以桶为更新单位的方法，改为以节点为单位。
增加了权重和失误次数--每成功链接一次权重增加一失误次数重置为零，
每失误一次权重减少一失误次数增加一，下次更新时间以失误次数计算(timeout*(2**_missnum_missnum))
这样当有新的节点可以插入时，可以根据节点的权重去更换节点。
"""
from bisect import bisect_left
from time import time
from ..common import (
    unpack_nodes,
    pack_node,
    ascii2l16,
    nid
)
from ..config import (
    RETURN_NODE_MAX_LENGTH,
    NODE_UPDATE_TIME,
    KBUCKET_MAX_LENGTH,
    NODE_DEFAULT_WEIGHT,
    NID_LENGTH,
    TABLE_RANGE
)


class KNode(object):
    """KNode节点属性
    包含nid，ip，port的基本属性。
    优化了以桶为更新单位的方法，改为以节点为单位。
    增加了权重和失误次数--每成功链接一次权重增加一失误次数重置为零，
    每失误一次权重减少一失误次数增加一，下次更新时间以失误次数计算(timeout*(2**_missnum_missnum))
    这样当有新的节点可以插入时，可以根据节点的权重去更换节点。
    Attributes:
        nid: 节点的唯一nid标识
        weight: 节点的权重值
        ip: 节点的ipv4地址
        port: 节点的对等端口
        _timeout: 默认的单次检测节点响应的时间间隔
        addr: 节点的地址元组
        _ptime: 节点进入路由表的时间
        _utime: 节点下次检测的时间
        need_check: 判断节点是否需要检测
    """

    def __init__(self, nid, ip, port, weight, timeout):
        """初始化节点的基本信息
        Args:
            nid: 节点的唯一nid标识
            ip: 节点的ipv4地址
            port: 节点的端口
            weight: 节点的权重
            timeout: 节点单次的默认检测时间
        """
        self._weight = weight
        self._missnum = 0
        self._nid = nid
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self._utime = time() + self._timeout
        self._ptime = time()

    @property
    def weight(self):
        """节点的权重
        Returns:
            节点的权重
        """
        return self._weight

    @property
    def status(self):
        """节点的状态
        Return:
            weight: 节点的权重
            utime: 节点下次的检测时间
            missnum: 节点失误次数
            ptime: 节点第一次加入路由表的时间
            body: 节点的主要信息(nid,addr0
        """
        res = {
            "weight":self._weight,
            "utime":self._utime,
            "missnum":self._missnum,
            "ptime":self._ptime,
            "body":(self.nid,self.addr)
        }
        return res

    @property
    def body(self):
        """节点被使用，返回节点的主要信息(nid,addr)
        Returns:
            nid: 节点的唯一nid标识
            addr: 节点的网络地址
        """
        self._use()
        return self.nid,self.addr

    def update(self):
        """节点对我们的请求作出响应后更新节点，
        将节点的失误次数重置为零，节点的权重增加二(在使用时权重已经减一，实际上对权重加一)，
        更新节点的下次检测时间，当前时间加延时，time() + self._timeout*(2**self._missnum)
        其中self._missnum为零
        """
        self._missnum = 0
        self._weight += 2
        self._utime = time() + self._timeout

    def _use(self):
        """节点被使用
        重置下次检测的时间，
        节点权重减一(在节点正常响应后，权重加二，实际上是一次正常响应，权重会加一)
        节点失误次数加一(在节点正常响应后，节点的失误次数重置为零，如果没有正常响应失误次数将累加)
        """
        self._utime = time() + self._timeout*(2**self._missnum)
        self._missnum += 1
        self._weight -= 1

    @property
    def ip(self):
        """节点的ipv4地址
        Returns:
            节点的ipv4地址
        """
        return self._ip

    @property
    def port(self):
        """节点的端口
        Returns:
            节点的端口
        """
        return self._port

    @property
    def nid(self):
        """节点的唯一标识符
        Returns:
            节点的唯一标识符
        """
        return self._nid

    @property
    def addr(self):
        """节点的网络地址
        Returns:
            以元组的形式返回节点的网络地址(ip,port)
        """
        return (self._ip,self._port)

    @property
    def utime(self):
        """节点下次检测的时间
        Returns:
            节点下次检测时间
        """
        return self._utime

    @property
    def need_check(self):
        """节点是否需要更新
        Returns:
            True: 节点需要更新
            False: 节点不需要更新
        """
        return time() > self._utime

    def __str__(self):
        """将节点转换成26位的字符串，以便后面使用"""
        return pack_node(self._nid,self._ip,self._port)



class KBucket(object):
    """KBucket桶，
    采用列表的方式实现:
    [KNode,KNode,KNode...]
    用来存放le <= 与nid的距离 < gt 的KNode节点，
    最大存放数量为k个。
    Notes:
        优化了官方的功能，官方以KBucket桶为更新单位，这里实现了以KNode节点为更新单位，
        详细情况请查看KNode的介绍。
    Attributes:
        le: gt: KBucket桶的范围，里面的节点 le <= KNode的nid与自己的距离 < gt
        k: KBucket桶存放节点的最大数量
        weight: 节点的默认权重
        timeout: 节点默认超时时间
        lenght: KBucket桶内节点的数量
        ranges: KBucket桶的范围
        nodes: KBucket桶里面的节点
        items: KBucket桶里面节点的(nid,ip,port)信息
        nid_list: KBucket桶内所有节点的nid
        need_check: KBucket桶内需要更新的检测的节点
    """

    def __init__(self,le,gt,k,weight,timeout):
        """初始化一个KBucket桶，设定桶的范围、桶内节点的数量、
        节点的默认权重和节点默认的超时时间
        Args:
            le: gt: KBucket桶的范围，里面的节点 le <= KNode的nid与自己的距离 < gt
            k: KBucket桶存放节点的最大数量
            weight: 节点的默认权重
            timeout: 节点默认超时时间
        """
        self._le = le
        self._gt = gt
        self._k = k
        self._weight = weight
        self._timeout = timeout
        self._nodes = [] 

    @property
    def status(self):
        """桶的状态
        Returns:
            length: KBucket桶内节点的数量
            range: KBucket桶的范围
            canSplit: KBucket桶是否还可分隔(可分隔是指gt/le>2)
            items: KBucket桶里面节点的(nid,ip,port)信息
            detail: 每个KNode节点的详细信息
        """
        res = {
            "length":len(self._nodes),
            "range":self.ranges,
            "canSplit":self.canSplit(),
            "items":self.items,
            "detail":[]
        }
        for node in self._nodes:
            res["detail"].append(node.status)
        return res

    def isEmpty(self):
        """判断KBucket桶是否为空
        Returns:
            True: KBucket桶为空
            False: KBucket桶不为空
        """
        return len(self._nodes) == 0

    @property
    def length(self):
        """KBucket桶内节点的数量
        Returns:
            type() is int
        """
        return len(self._nodes)

    @property
    def ranges(self):
        """KBucket桶的范围
        Returns:
            (le,gt): KBucket桶的范围，里面的节点 le <= KNode的nid与自己的距离 < gt
        """
        return self._le,self._gt

    @property
    def nodes(self):
        """KBucket桶内所有的KNode节点
        Returns:
            [KNode,KNode,...]
        """
        return self._nodes

    @property
    def items(self):
        """KBucket桶里面节点的(nid,ip,port)信息
        Returns:
            [(nid,ip,port),(nid,ip,port),...]
        """
        return [(node.nid,node.ip,node.port) for node in self._nodes]

    def isFull(self):
        """KBucket桶是否已经满
        Returns:
            True: 桶已经满了
            False: 桶没有满
        """
        return len(self._nodes) == self._k

    def canSplit(self):
        """判断KBucket桶是否还可分隔(可分隔是指gt/le>2)
        Returns:
            True: 可分隔
            False: 不可分隔
        """
        return self._gt/self._le !=2

    @property
    def nid_list(self):
        """KBucket桶内所有节点的nid
        Returns:
            [nid，nid,..]
        """
        return [node.nid for node in self._nodes]

    def index(self,nid):#待优化空间复杂度
        """获取某个nid在KBucket桶内的索引值
        Args:
            nid: 响应请求的节点的20位唯一标识
        Returns:
            num: 某个nid在KBucket桶内的索引值
            None: 该nid不在KBucket桶内
        """

        if nid in self.nid_list:
            return self.nid_list.index(nid)      

    @property
    def need_check(self):
        """KBucket桶内需要更新的检测的节点，方便对节点的操作
        Returns:
            [node,node,...]
        """
        return [node for node in self._nodes if node.need_check]

    def update(self,nid):
        """根据响应请求的节点的id对该KNode节点进行更新操作
        Args:
            nid: 响应请求的节点的20位唯一标识
        """
        for node in self._nodes:
            if node.nid == nid:
                node.update()
                return

    def replace(self,newnode):
        """替换节点
        如果桶内有节点失误的次数过多，则该节点的权重将会低于一个新节点的初始权重，
        用新的节点去代替旧的节点
        Args:
            newnode: KNode节点或者节点(nid,ip,port)信息
        """
        if not isinstance(newnode,KNode):
            newnode = KNode(newnode[0],newnode[1],newnode[2],self._weight,self._timeout)
        for node in self._nodes:
            if node.weight < newnode.weight:
                node = newnode
                return

    def push(self,newnode):
        """向桶内添加一个新的节点
        Args:
            newnode: KNode节点或者节点(nid,ip,port)信息
        """
        newnode = KNode(newnode[0],newnode[1],newnode[2],self._weight,self._timeout)
        self._append(newnode)        

    def _append(self,node):
        """向桶内添加一个新的节点
        Args:
            node: KNode节点
        """
        self._nodes.append(node)

    def __contains__(self,nid):
        """判断某个nid是否在KBucket桶内
        Args:
            nid: 响应请求的节点的20位唯一标识
        Returns:
            True: 该nid在KBucket桶内
            False: 该nid不在KBucket桶内
        """
        for node in self._nodes:
            if node.nid == nid:
                return True
        return False

    def __len__(self):
        """KBucket桶内节点的数量，方便通过len(KBucket)方法使用
        Returns:
            type() is int
        """
        return len(self._nodes)

    def __lt__(self,dist):
        """小于比较符，
        主要用在bisect_left中，bisect_left将在路由表中返回一个桶位置的索引，
        该索引将在[...,False,False,False,True,True,True...]最后一个False的索引位置
        Args:
            dist: type()->int 该nid与自身nid异或后的距离
        Returns:
            True: 大于桶的最大边界
            False: 小于等于桶的最大边界
        """
        return self._gt < dist

    def __getitem__(self,nid):
        """方便使用KBucket[nid]的方法获取该nid的KNode节点
        如果KBucket桶内没有响应的KNode节点将返回None
        Args:
            nid: 响应请求的节点的20位唯一标识
        Returns:
            node: 该nid匹配到的KNode节点
            None: 没有匹配到响应的KNode节点
        """
        for node in self._nodes:
            if node.nid == nid:
                return node
        return None

    def __iter__(self):
        """将KBucket变成可迭代的生成器，方便路由表取出数据"""
        for node in self._nodes:
            yield node



class KTable(object):
    """路由表
    采用列表的方式实现：
    [KBucket[KNode,KNode,KNode...],
    KBucket[KNode,KNode,KNode...],
    KBucket[KNode,KNode,KNode...],
    ...]
    用来存放范围在2**0到2**160之间的KBucket，所以最多有160个KBucket，
    最开始只有一个最大范围的KBucket，随着节点的增加，当KBucket中的节点数量达到了16，
    如果桶可以分隔，则将桶拆分成两个。
    notes:
        对官方进行了一些修改，在插入节点的过程中，如果路由表已经有了该节点，则更新该节点
        权重(详情参照KNode介绍)，在桶不可以分隔的情况下，官方使用丢弃的处理方式，我们采用
        替换路由表的权重低，失误次数高的节点
    Attributes:
        _k: 每个KBucket最大数量
        _timeout: 默认初始节点的更新间隔时间
        _weight: 默认初始节点的权重
        _nid_l16: nid的16进制整数
        push: 添加一个节点
        find_node2chrlist: 最近的node列表
        find_node2chrall: 最近的node字符串
        need_check: 需要更新的节点
    """
    _k = KBUCKET_MAX_LENGTH
    _timeout = NODE_UPDATE_TIME
    _weight = NODE_DEFAULT_WEIGHT
    _nid = nid
    _nid_l16 = ascii2l16(nid)    
    
    def __init__(self):
        """初始化路由表，
        初始路由表中只包含一个最大范围的KBucket桶
        """
        self._buckets = [KBucket(TABLE_RANGE[0],TABLE_RANGE[1],self._k,self._weight,self._timeout)]
    
    @property
    def buckets(self):
        """路由表中所有的KBucket桶
        Returns:
            [KBucket,KBucket,KBucket,...]
        """
        return self._buckets
    
    @property
    def status(self):
        """路由表的状态
        Returns:
            length: 路由表中KBucket桶的数量
            nodes_num: 路由表中KNode节点的数量
            bucket_max_length： KBucket桶中节点的最大数量
            detail: 每个KBucket桶的详细信息
        """
        res = {
            "length":len(self._buckets),
            "nodes_num":len(self),
            "bucket_max_length":self._k,
            "detail":[]
        }      
        for bucket in self._buckets:
            res["detail"].append(bucket.status)
        return res
    
    @property
    def nodes(self):
        """路由表中所有的KNode节点
        Returns:
            [KNode,KNode,KNode,...]
        """
        nodes = []
        for bucket in self._buckets:
            nodes += bucket.nodes
        return nodes
    
    @property
    def length(self):
        """路由表中KBucket桶的数量"""
        return len(self._buckets)
    
    def push(self,node):
        """向路由表中添加一个node节点，
        如果这个node的唯一标识nid不合法将触发断言异常，
        如果这个node的唯一标识nid是自己，则跳过(不存储自身节点)
        Args:
            node: 元组的形式，由唯一标识nid和ipv4地址组成(nid,ip,port)
        Raises:
            AssertionError: "nid的长度必须为%d"%NID_LENGTH
        """
        assert len(node[0]) == NID_LENGTH, "nid的长度必须为%d"%NID_LENGTH
        if node[0] == self._nid:return
        self._node2bucket(node)
    
    def _index(self,nid):
        """通过nid与自己的nid的距离，
        确定该nid位于路由表中KBucket桶的索引
        Returns:
            index: KBucket桶的索引值
        """
        dist = self._cmp(nid)
        return bisect_left(self._buckets, dist) 
    
    def _node2bucket(self,node): #待优化桶分隔后节点权重等问题
        """将node插入到路由表中
        根据node节点的唯一标识nid确定，该节点在路由表中的KBucket桶的索引->index，
        获取应该放置该节点的KBucket桶->bucket,
        通过该桶尝试获取该节->knode
        if 该节点已经存在，则更新该节点，
        elif KBucket桶没有满，则在该桶中插入该节点，
        elif KBucket桶可以继续分隔，则将该KBucket桶拆成两个，将该节点与原节点合并后重新分配，
        else 用该节点去替换桶中权重过低，失误次数过多的不活跃节点
        Args:
            node: 元组的形式，由唯一标识nid和ipv4地址组成(nid,addr = (ip,port))
        """
        nid = node[0]
        index = self._index(nid)
        bucket = self._buckets[index]
        knode = bucket[nid]
        if knode is not None:
            knode.update()
        elif not bucket.isFull():
            bucket.push(node)
        elif bucket.canSplit():
            nodelist = bucket.items+[node]
            lt,ge = bucket.ranges
            point = ge/2
            self._buckets[index] = KBucket(point,ge,self._k,self._weight,self._timeout)
            self._buckets.insert(index,KBucket(lt,point,self._k,self._weight,self._timeout))
            for node in nodelist:
                self._node2bucket(node)
        else:
            bucket.replace(node)
    
    def _cmp(self,nid):
        """比较nid与自身nid的距离
        Args:
            nid: node节点的唯一标识
        Returns:
            dist: type()->int nid与自身nid的距离
        """
        nid_l16 = ascii2l16(nid)       
        return nid_l16^self._nid_l16

    def find_node2chrlist(self,target):
        """查找与target最近的节点信息，以node的形式返回
        Args:
            target: 需要查找的node.nid或者peer.info_hash
        Returns:
            [(nid,addr(ip,port)),(nid,addr(ip,port)),...]
        """
        return [(node.nid,node.addr) for node in self._find_node(target)]
    
    def find_node2chrall(self,target):
        """查找与target最近的节点信息，以字符串的形式返回
        Args:
            target: 需要查找的node.nid或者peer.info_hash
        Returns:
            str(KNode)+str(KNode)+str(KNode)+...
        """
        return "".join([str(node) for node in self._find_node(target)])
    
    def _find_node(self,target):
        """查找与target最近的节点，
        如果从最近的桶不满默认数量个则向后推，直到推到最后
        Args:
            target: 需要查找的node.nid或者peer.info_hash
        Returns:
            [KNode,KNode,KNode,...]
        """
        assert len(target) == NID_LENGTH,"target 必须是%s位字符串"%NID_LENGTH
        index = self._index(target)
        nodes = []
        while len(nodes) < RETURN_NODE_MAX_LENGTH and index<len(self._buckets):
            for node in self._buckets[index].nodes:
                nodes.append(node)
            index += 1
        return nodes
    
    def need_check(self):
        """每个桶中取出一个需要检测的节点
        Returns:
            [KNode,KNode,KNode,...]
        """
        nodes = []
        for bucket in self._buckets:
            nodes += bucket.need_check
        return nodes    
    
    def __len__(self):
        """路由表中所有KNode节点的数量"""
        return reduce(lambda x,y:y+x,[len(bucket) for bucket in self._buckets])
    
    def __getitem__(self,nid):
        """通过节点的唯一标识nid获取KNode节点
        Args:
            nid: 节点的唯一标识
        Returns:
            KNode
        """
        index = self._index(nid)
        bucket = self._buckets[index]
        node = bucket[nid]
        return node
    
    def __contains__(self,nid):
        """通过节点的唯一标识nid判断节点是否在路由表中
        Args:
            nid: 节点的唯一标识
        Returns:
            True: 节点在路由表中
            False 节点不在路由表中
        """
        index = self._index(nid)
        bucket = self._buckets[index]
        node = bucket[nid]
        if node:
            return True
        else:
            return False
    
    def __iter__(self):
        """"""
        for bucket in self._buckets:
            yield bucket