
import struct
import socket
import sys
import xml.dom.minidom

length = {"u32" : 4, "u16" : 2, "u8" : 1}



class xmlHandler(xml.sax.ContentHandler):
    def start_element(name, attr):
        print "start: %s, attr :%s" % (name, attr)

    def end_element(name):
        print "end: %s" % name

    def data_element(data):
        print "data: %s" % data

class sct(object):
    
    def __init__(self, ip_addr, xml_file):
        self.ip_addr = ip_addr
        self.xml_file = xml_file
        self.sct_list = []
        return

    def Run(self):
        #parse xml
        self.parseXml()
        #tcp struct data
        self.structData()



        pass

    def parseXml(self):
        docTree = xml.dom.minidom.parse(self.xml_file)
        collection = docTree.documentElement
        
        #Get Testcase info
        infos = collection.getElementsByTagName("INFO")
        name = infos[0].getElementsByTagName("NAME")
        brief = infos[0].getElementsByTagName("BRIEF")
        print "Test Start:" + name[0].firstChild.data + "("+ brief[0].firstChild.data + ")"
        
        #Get Testcase
        cases = collection.getElementsByTagName("CASE")
        for case in cases:
            #Get info
            info = case.getElementsByTagName("INFO")[0]
            uiname = info.getElementsByTagName("UINAME")[0]
            brief = info.getElementsByTagName("BRIEF")[0]
            
            #Get testman
            testman = collection.getElementsByTagName("TESTMAN")[0]
            casename = testman.getElementsByTagName("CASENAME")[0]
            caseid = testman.getElementsByTagName("CASEID")[0]

            #Get message
            message = collection.getElementsByTagName("MESSAGE")[0]
            tbtsheader = message.getElementsByTagName("TBTSHEADER")[0]
            subsystemname = tbtsheader.getElementsByTagName("SUBSYSTEMNAME")[0]
            testcasename = tbtsheader.getElementsByTagName("TESTCASENAME")[0]    

            #for params
            params = message.getElementsByTagName("PARAM")
            paramLength = 0
            for param in params:
                name = param.getAttribute("name")
                valueType = param.getAttribute("valueType")
                data = param.firstChild.data
                
                print name, length[valueType], data
                paramLength += length[valueType]

                


            self.sct_list.append({"uiname":uiname.firstChild.data, 
                                  "brief" : brief.firstChild.data, 
                                  "casename" : casename.firstChild.data, 
                                  "caseid" : caseid.firstChild.data, 
                                  "subsystemname" : subsystemname.firstChild.data, 
                                  "testcasename" : testcasename.firstChild.data,
                                  "paramLength": paramLength})


        return

    def tcpConnect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.ip_addr, 0x315)
        s.send()
        s.close()
        return

    def structData(self, msg_size, subsystemName, testCaseName, parametersSize, parameters):
        buff = struct.pack(">HHIIHH48s48sI", 0, 0xFF00, 0x0F0104b8, 0,  msg_size, 0, subsystemName, testCaseName, parametersSize, ) 
        pass


def PrintHelp():
    print "***********************************************"
    print "*     python sct_run.py ip_addr xml_file      *"
    print "***********************************************"
    return

if __name__ == "__main__":
    if 3 != len(sys.argv):
        PrintHelp()
    else:
        testSct = sct(sys.argv[1], sys.argv[2])
        testSct.Run()






