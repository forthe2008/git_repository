
import struct
import socket
import sys
from xml.parsers.expat import ParserCreate



class sct(object):
    
    def __init__(self, ip_addr, xml_file):
        self.ip_addr = ip_addr
        self.xml_file = xml_file
        return

    def Run(self):
        #parse xml
        self.parseXml()
        #tcp connect and send
        pass

    def parseXml(self):
        
        pass

    def tcpConnect(self):
        pass

    def structData(self):
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






