#coding:utf-8
from __future__  import division
#不可修改的设置
NODE_LENGTH                   = 26             #node长度
NID_LENGTH                    = 20             #nid长度
ADDR_LENGTH                   = 4              #ip地址长度
TABLE_RANGE                   = (2**0,2**160)  #路由表的范围

#可以修改的设置
#挑战者-响应链表设置
TID_MAX_LENGTH                = 256**2          #链表的最大长度
#任务设置
TASK_MAX_LENGTH               = 1024            #任务队列的最大长度
#路由表设置
NODE_UPDATE_TIME              = 900             #对节点单次的检测时间
NODE_DEFAULT_WEIGHT           = 5               #节点的默认权重
KBUCKET_MAX_LENGTH            = 16              #K桶存放节点的最大数量
RETURN_NODE_MAX_LENGTH        = 16              #返回节点的最大数量
#路由表检测间隔时间，在NODE_UPDATE_TIME时间内对所有的K桶内节点都可检测一遍
NODE_CHECK_INTERVAL_TIME      = NODE_UPDATE_TIME/KBUCKET_MAX_LENGTH
#DHT设置
BOOTSTRAP_NODES               = (          
    ("router.utorrent.com",6881),
    ("grenade.genua.fr",6880),
    ("dht.transmissionbt.com",6881),
    ("router.bittorrent.com", 6881),
)                                               #启动节点
DHTPORT                       = 6881            #默认DHT网络端口
PER_SECOND_MAX_TIME           = 1024            #DTH每秒发送的最大次数
#停止主动向节点请求自己的路由表长度
MIN_STOP_TABLE_LENGTH         = KBUCKET_MAX_LENGTH**2*2
#停止对任务使用启动节点去请求的路由表长度
MIN_STOP_BOOT_LENGTH          = KBUCKET_MAX_LENGTH**2
#单个任务的最多请求次数
MAX_TASK_NUM                  = TASK_MAX_LENGTH*PER_SECOND_MAX_TIME
MAX_RUN_TIME                  = 600             #单个任务的最大运行时间
#共享内存设置
SYNC_INTERVAL_TIME            = 3               #共享内存映射间隔时间
CONTROL_INTERVAL_TIME         = 1               #任务控制间隔时间

#reset api 设置
WEBPORT                       = 8888           #默认reset api 端口
