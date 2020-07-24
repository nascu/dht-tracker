# dht-tracker:基于gevent和tornado的DHT网络

dht-tracker是一个基于gevent和tornado的DHT网络，
该网络完整实现了[`BEP5`](http://www.bittorrent.org/beps/bep_0005.html)
并对
原协议中的部分进行了优化。例如：为路由表中的节点添加权重，使用链表完成挑战响应者模式。
并通过tornado框架搭建的reset api 可以对dht中的任务进行查看及控制，另外做了流量信息统计树可以对实时流量进行数据分析。

### 依赖包

-   gevent

-   tornado

-   bencode

-   logging

### 安装

推荐使用virtualenv进行安装。

从GitHub clone 代码:

```bash
git clone https://github.com/nascu/dht-tracker
```

然后进入文件夹进行安装:

```bash
cd dht-tracker
python setup.py install
```

### 用法示例

```python
#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging
from multiprocessing import Process
from dht_tracker.web import web_start
from dht_tracker.dht import BaseDHT,KRPC,KTable,NormalDHT,DHTSpider
from dht_tracker.common import netcount,sync
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s][%(filename)s][%(funcName)s]LINE %(lineno)-4d : %(levelname)-8s %(message)s'
                    )
dhtser = NormalDHT()

def collect_on_get_peers(info,addr):
    """重写收集到的get_peers信息的处理
    这里仅打印，以示例
    """
    print "get_peers",(info,addr)

def collect_on_announce_peer(info,addr):
    """重写收集到的announce_peer信息的处理
    这里仅打印，以示例
    """
    print "announce_peer",(info,addr)

def recv_find_node_node(task,node):
    """重写对find_node任务返回的node信息的处理
    这里仅打印，以示例
    """
    print "find_node_node",task.id,node

def recv_get_peers_values(task,values):
    """重写对get_peers任务返回的values信息的处理
    这里仅打印，以示例
    """
    print "get_peers_values",task.id,values

dhtser.on_get_peers_info = collect_on_get_peers
dhtser.on_announce_peer_info = collect_on_announce_peer
dhtser.on_find_node_node = recv_find_node_node
dhtser.on_get_peers_values = recv_get_peers_values
#添加一个任务
dhtser.taskline.push("get_peers",'\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z')
try:
    p = Process(target=dhtser.start_dht, args=())
    q = Process(target=web_start, args=())
    p.start()
    q.start()
    p.join()
    q.join()
except Exception, e:
    logging.warning(e)
```

### 通过web查看统计信息

通过get方式获取统计信息
以层级递进的方式获取下级统计信息

```shell
curl http://localhost:8888/count              #查看所有统计信息
curl http://localhost:8888/count/recv         #查看收到的统计信息
curl http://localhost:8888/count/cllect       #查看收集到的统计信息
...
curl http://localhost:8888/count/cllect/announce_peer #查看收集到的announce_peer统计信息
```
经测试在阿里云服务器（国内）2M带宽、双核8G的虚拟机上运行，平均每秒获取10个announce_peer信息（NormalDHT模式）

采用DHTSpider(DHT爬虫模式)会占用较多的网络带宽，在外网访问web控制端时会产生很大的延时，所以推荐在DHTSpider(DHT爬虫模式)下使用内网过渡进行web控制端的链接。

如有建议请指出微信号&QQ号：1107775282
