import paramiko
import os
import sys
import time
from optparse import OptionParser

class scp(object):
    def __init__(self, ip, username, passwd):
        self.ip = ip
        self.username = username
        self.passwd = passwd

    def scpPut(self, localFile, remoteFile):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.ip, 22, self.username, self.passwd)
        sftp = paramiko.SFTPClient.from_transport(self.ssh.get_transport())
        sftp = self.ssh.open_sftp()
        sftp.put(localFile, remoteFile)
    
    def scpGet(self, localFile, remoteFile):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.ip, 22, self.username, self.passwd)
        sftp = paramiko.SFTPClient.from_transport(self.ssh.get_transport())
        sftp = self.ssh.open_sftp()
        sftp.get(remoteFile, localFile)
        
class journal(scp):
    def __init__(self):
        scp.__init__(self, "10.69.120.33", "root", "rootadmin")
        
    def parse(self, file):
        self.scpPut(file, "usr/xiangfei/jou_parse/" + file)
        stdin, stdout, stderr = self.ssh.exec_command("cd usr/xiangfei/jou_parse/ && journalctl --file "+ file +" > ./journal.log")
        localFile = "journal_"+ str(int(time.time())) +".log"
        self.scpGet(localFile, "usr/xiangfei/jou_parse/" + "journal.log")
        print "generate journal file:", localFile

def optionParse():
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="file", help="input a file name")
    parser.add_option("-j", "--journalctl", action="store_true", dest="journalctl", default=False, help="parse systemd journal file")
    return parser
        
if __name__ == "__main__":
    parser = optionParse()
    (options, args) = parser.parse_args()
    if options.journalctl == True:
        obj = journal()
        if options.file != None:
            obj.parse(options.file)
        else:
            parser.print_help() 
    else:
        parser.print_help() 

   
