import struct
import socket
import sys
from xml.dom import minidom
import threading
import time
import Queue


typedict = {"u16" : 1, "u32":2, "strings":3, "any" : 4}

class syscom(object):
    def __init__(self, ipaddr, port):
        self.ipaddr = ipaddr
        self.port = port
        self.txQueue = Queue.Queue()
        self.rxQueue = Queue.Queue()
        self.txSem = threading.Semaphore(0)
        self.rxSem = threading.Semaphore(0)
        self.tcpSem = threading.Semaphore(0)
        self.tcpStop = False
        self.tcpStopTime = 0
        
    def tcpLoop(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.s.bind(("0.0.0.0", 8888))
        self.s.settimeout(5)
        try:
            self.s.connect((self.ipaddr, self.port))
            #buff = self.s.recv(1024)
        except Exception, e:
            print "socket connect failed"
            print e
            self.tcpStop = True
            self.tcpSem.release()
            return  
        self.tcpSem.release()
        #print buff
        #print "tcp client start"
        while True:
            self.txSem.acquire()
            if self.txQueue.empty():
                time.sleep(1)
            else:
                msg = self.txQueue.get()
                if "exit" == self.getMsgPayload(msg):
                    print "tcp send exit"
                    self.tcpStop = True
                    break
                self.s.send(msg)
        self.s.close()
    
    def tcpRecvLoop(self):
        #wait send thread ok
        #print "wait send thread ok"
        self.tcpSem.acquire()
        #print "start tcp recv loop"
        while True:
            if self.tcpStop:
                print "tcp recv exit"
                break
            buff = ""
            try:
                buff += self.s.recv(1024)
                self.tcpStopTime = 0
            except:
                self.tcpStopTime += 5
                if self.tcpStopTime > 600:
                    print "more then 10min didn't receive message"
                    self.tcpStop = True
                    break;
            if self.tcpStopTime == 0:
                self.rxQueue.put(buff)
    
    def createMsgHeader(self, msgId, target, size):
        #typedef struct SInternalMsgHeader
        #{
        #    u16              reserved;
        #    TAaSysComMsgId   msgId;
        #    TAaSysComSicad   target;
        #    TAaSysComSicad   sender;
        #    TAaSysComMsgSize msgSize;
        #    u16              flags;
        #} SInternalMsgHeader;
        header = struct.pack("!HHIIHH", 0, msgId, target, 0, 16+size, 4)
        return header
    
    def getMsgPayload(self, msg):
        return msg[16::] 
    
    def getMsgId(self, msg):
        if len(msg) < 16:
            print "receive wrong message"
            return ""
        header = msg[0:16]
        headrTuple = struct.unpack("!HHIIHH", header)
        print headrTuple
        return headrTuple[1]
    
    def createMsg(self, msgId, target, size, payload):
        #header
        header = self.createMsgHeader(msgId, target, size)
        #payload
        self.msg = header + payload
        #print self.msg
        return
        
    def sendMsg(self):
        self.txQueue.put(self.msg)
        self.txSem.release()
        
    def recvMsg(self):
        self.rxSem.acquire()
        if not self.rxQueue.empty():
            buff = self.rxQueue.get()
            return buff
        return ""
            
    def registLink(self):
        self.tcpThread = threading.Thread(target=self.tcpLoop, name="tcpTread")
        self.tcpRecvThread = threading.Thread(target=self.tcpRecvLoop, name="tcpRecvThread")
        self.tcpThread.start()
        self.tcpRecvThread.start()
        
    def deregistLink(self):
        self.s.close()
        
class tag(syscom):
    def __init__(self, ip, name, value, type="u32", length=4):
        syscom.__init__(self, ip, 15003)
        self.name = name
        self.value = value
        self.length = length
        self.type = typedict[type]
    
    def tagPublicNotifStruct(self):
        #/** @brief Config tag public set notification. */
        #typedef struct SAaConfigTagPublicSetNotifMsg
        #{
        #  char           name[AACONFIG_TAG_MAX_NAME_LENGTH];                /**< name of config tag */
        #  u32            vlen;                                              /**< length of value */
        #  EAttributeType type;                                              /**< type of config tag */
        #  u8             value[1];                                          /**< value of config tag */
        #} SAaConfigTagPublicSetNotifMsg;
        int
        
        print "name:", self.name, "value:", self.value, "length:", self.length, "type:", self.type
        payload = struct.pack("<80sII", self.name, self.length, self.type)
        if self.type == 1:
            payload += struct.pack("<H", int(self.value))
        elif self.type == 2:
            payload += struct.pack("<I", int(self.value))
        elif self.type == 3:
            payload += struct.pack("<"+ str(self.length) +"s", self.value)
        elif self.type == 4:
            pass
        else:
            print "wrong type"
        return payload

def help():
    print "**************************************************************************************"
    print "*     python tag_change_online.py ip_addr tagName tagValue [tagType] [tagLength]     *"
    print "*     tagType -- default(u32)       tagLength -- default(4)                          *"
    print "**************************************************************************************"
    return
        
if __name__ == "__main__":
    if len(sys.argv) < 4:
        help()
    else:
        if len(sys.argv) == 4:
            obj = tag(sys.argv[1], sys.argv[2], sys.argv[3])
            length = 80+4+4+4
        elif len(sys.argv) == 5:
            obj = tag(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
            length = 80+4+4+4
        elif len(sys.argv) == 6:
            obj = tag(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
            length = 80+4+4+int(sys.argv[5])
        else:
            help()
        
        obj.registLink()
        payload = obj.tagPublicNotifStruct()
        obj.createMsg(0x08E6, 0x0F01062B, length, payload)
        obj.sendMsg()
        
        time.sleep(3)
        #exit
        obj.createMsg(0, 0x120d1111, 0, "exit")
        obj.sendMsg()
        obj.tcpThread.join()
        obj.tcpRecvThread.join()
        
        
        
        
        