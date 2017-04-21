import struct
import socket
import sys
from xml.dom import minidom
import threading
import time
import Queue

lengthDict = {"u32" : 4, "u16" : 2, "u8" : 1}
TypeDict = {"u32" : "I", "u16" : "H", "u8" : "B"}
    
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
        except:
            print "socket connect failed"
            self.rxSem.release()
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
                self.rxSem.release()
    
    
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

class xmlParser(object):
    def __init__(self, file):
        self.file = file

    def getAttrValue(self, node, attrname):
         return node.getAttribute(attrname) if node else ''

    def getNodeValue(self, node, index = 0):
        return node.childNodes[index].nodeValue if node else ''

    def getXmlNode(self, node, name):
        return node.getElementsByTagName(name) if node else []
    
    def parse(self):
        doc = minidom.parse(self.file)
        root = doc.documentElement

        #get scenatio
        infoNodes = self.getXmlNode(root, "INFO")
        self.name = self.getNodeValue(self.getXmlNode(infoNodes[0], "NAME")[0])
        self.brief = self.getNodeValue(self.getXmlNode(infoNodes[0], "BRIEF")[0])
        
        #get testcases
        testcasesNodes = self.getXmlNode(root, "TESTCASES")
        caseNodes = self.getXmlNode(testcasesNodes[0], "CASE")
        
        self.testcases = []
        for case in caseNodes:
            #{"casename":caseName, "subsystemname":subsystemName, "testcasename":testcaseName, "param":[{"name":paramName, "value":(valueType, value)},]}
            #casename
            caseElement = {}
            caseName = self.getNodeValue(self.getXmlNode(self.getXmlNode(case, "TESTMAN")[0], "CASENAME")[0])
            #message
            #subsystemname
            subsystemName = self.getNodeValue(self.getXmlNode(self.getXmlNode(self.getXmlNode(case, "MESSAGE")[0], "TBTSHEADER")[0], "SUBSYSTEMNAME")[0])
            #testcasename
            testcaseName = self.getNodeValue(self.getXmlNode(self.getXmlNode(self.getXmlNode(case, "MESSAGE")[0], "TBTSHEADER")[0], "TESTCASENAME")[0])
            
            caseElement["casename"], caseElement["subsystemname"], caseElement["testcaseName"] = (str(caseName), str(subsystemName), str(testcaseName))
            param = []
            #param
            paramNodes = self.getXmlNode(self.getXmlNode(case, "MESSAGE")[0], "PARAM")
            length = 0
            for paramNode in paramNodes:
                paramName = str(self.getAttrValue(paramNode, "name"))
                valueType = str(self.getAttrValue(paramNode, "valueType"))
                value = int(self.getNodeValue(paramNode))
                
                paramElement = {"name": paramName, "value":(valueType, value)}
                
                param.append(paramElement)
                length += lengthDict[valueType]
            
            caseElement["length"] = length
            caseElement["param"] = param
            self.testcases.append(caseElement)
        return self.testcases
    
class tbts(syscom):
    def __init__(self, subsystemName, testcaseName, length, params):
        self.subsystemName = subsystemName
        self.testcaseName = testcaseName
        self.length = length
        self.params = params
    
    #params = [(type, value), (type, value), ]
    def tbtsReqStruct(self):
        #struct TbtsStartTestReq
        #{
        ##if !defined(AASYSCOM_IN_USE)
        #    SMessageHeader  msgHeader;                                /**< Message header (message id = TBTS_START_TEST_REQ_MSG) */
        ##endif
        #    char            subsystemName[MAX_SUBSYSTEM_NAME_LENGTH]; /**< Name of the subsystem where test should be */
        #    char            testCaseName[MAX_TESTCASE_NAME_LENGTH];   /**< Name of test to be performed */
        #    u32             parametersSize;                           /**< Input parameters size for the test */
        #    u8              parameters[1];                            /**< Input parameters pointer */
        #};
        print "-------------------------------start test sct-------------------------------" 
        print "subsystem:", self.subsystemName, "testcase:", self.testcaseName, "length:", self.length, "params:", self.params
        payload = struct.pack("<48s48sI", self.subsystemName, self.testcaseName, self.length)
        for param in self.params:
            payload += struct.pack("<"+TypeDict[param[0]], param[1])
        return payload
    
    def tbtsRespStruct(self, payload):
        #struct TbtsStartTestResp           
        #{
        ##if !defined(AASYSCOM_IN_USE)
        #    SMessageHeader          msgHeader;                                /**< Message header (message_id = TBTS_START_TEST_RESP_MSG) */
        ##endif
        #    char                    subsystemName[MAX_SUBSYSTEM_NAME_LENGTH]; /**< Subsystem name */
        #    char                    testCaseName[MAX_TESTCASE_NAME_LENGTH];   /**< Test case name */
        #    ETbtsTestStart          status;                                   /**< Test start success status */  
        #    u32                     runningId;                                /**< Test unique id running in target */  
        #};
        return struct.unpack("<48s48sII", payload)
    
    def tbtsResultStruct(self, payload):
        #struct TbtsTestResultInd           
        #{
        ##if !defined(AASYSCOM_IN_USE)
        #    SMessageHeader  msgHeader;  /**< Message header (message id = TBTS_TEST_RESULT_IND_MSG) */
        ##endif
        #    u32             runningId;  /**< Test unique id running in target */
        #    u32             status;     /**< Success information of test */
        #    u32             dataSize;   /**< Test extra result data in bytes */
        #    u32             data[1];    /**< Test extra result data */
        #};
        #typedef struct TbtsTestResultInd TbtsTestResultInd;
        return struct.unpack("<III", payload[0:12])
    
    def tbtsMsgCheck(self, msg):
        msgId = self.getMsgId(msg)
        if msgId == 0xFF01:
            payload = self.getMsgPayload(msg)
            resp = self.tbtsRespStruct(payload)
            if resp[2] == 0:
                print "status = ETbtsTestStart_Ok"
                return True
            elif resp[2] == 1:
                print "status = ETbtsTestStart_NotRegistered"
            elif resp[2] == 2:
                print "status = ETbtsTestStart_ValidateFailed"
            elif resp[2] == 3:
                print "status = ETbtsTestStart_AllreadyRunning"
            else:
                print "status =", resp[2]
            return False
        elif msgId == 0xFF07:
            payload = self.getMsgPayload(msg)
            result = self.tbtsResultStruct(payload)
            if result[1] != 0:
                print "test finished succesfully"
                return False
            else:
                print "test failed"
                return False
        else:
            print "receive unknown message:", msgId
            return False
            
def sct_runner_help():
    print "***********************************************"
    print "*     python sct_runner.py xml_file id_addr     *"
    print "***********************************************"
    return
            
if __name__ == "__main__":
    #parse XML
    if 3 != len(sys.argv):
        sct_runner_help()
    else:
        xmlFile = xmlParser(sys.argv[1])
        testcases = xmlFile.parse()
        print "#############################################All TestCase In the XML file#############################################"
        for case in testcases:
            print case
        print "######################################################################################################################"
        
        syscomObj = syscom(sys.argv[2], 15003)
        syscomObj.registLink()
        
        for testcase in testcases:
            params = []
            for param in testcase["param"]:
                params.append(param["value"])
            tbtsObj = tbts(testcase["subsystemname"], testcase["testcaseName"], testcase["length"], params)
            tbtsPayload = tbtsObj.tbtsReqStruct()           
            syscomObj.createMsg(0xFF00, 0x0F0104b8, 48+48+4+testcase["length"], tbtsPayload)
            syscomObj.sendMsg()
            RecvedMsg = syscomObj.recvMsg()
            status = tbtsObj.tbtsMsgCheck(RecvedMsg)
            if status:
                RecvedMsg = syscomObj.recvMsg()
                tbtsObj.tbtsMsgCheck(RecvedMsg)

        print "sct_runner end"
        syscomObj.createMsg(0, 0x120d1111, 0, "exit")
        syscomObj.sendMsg()
        syscomObj.deregistLink()
        syscomObj.tcpThread.join()
        syscomObj.tcpRecvThread.join()

    




