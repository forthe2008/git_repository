import sys
import commands
import os
import urllib2
import urllib
import cookielib
from ftplib import FTP
from optparse import OptionParser
import time
import getpass

username = ""
password = ""

class crawler(object):
    def __init__(self, baseline):
        self.baseline = baseline
        cj =  cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
        
    def post(self, url, header, data):
        try:
            req = urllib2.Request(url, data, header)
            reqs = urllib2.urlopen(req) 
        except:
            print "ERROR, maybe wrong password or connection error"
            return None
        return reqs.read()
    
    def get(self, url):
        try:
            req = urllib2.Request(url)
            reqs = urllib2.urlopen(req) 
        except:
            print "ERROR, maybe wrong password or connection error"
            return None
        return reqs.read()
    
    def structHeader(self):
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6,et;q=0.4,zh-TW;q=0.2"
            }
        return header

    def structData(self, username, password, target):
        data = urllib.urlencode({
            "SMENC": "ISO-8859-1", 
            "SMLOCALE": "US-EN", 
            "USER": username, 
            "PASSWORD": password, 
            "target": target, 
            "smauthreason": 0, 
            "postpreservationdata": ""
            })
        return data       
        
class wft(crawler):
    def __init__(self, baseline):
        crawler.__init__(self,baseline)
        self.baseline = baseline
        self.loginAddr = " https://wam.inside.nsn.com/siteminderagent/forms/login.fcc "
        self.DNHAddr = "https://wft.inside.nsn.com/builds/" + self.baseline + "/partial.js?partial=baselines"
        self.PSAddr = "https://wft.inside.nsn.com/builds/" + self.baseline + "/partial.js?partial=baselines"
        self.releaseAddr = "https://wft.inside.nsn.com/builds/" + self.baseline + "/partial.js?partial=release"
        self.PSRel = ""
     
    def getPsRel(self, username, password):
        header = self.structHeader()
        post_data = self.structData(username, password, self.DNHAddr)
        resp = self.post(self.loginAddr, header, post_data)
        if None == resp:
            return
        PSTemRel = "FBLRC_PS_REL"
        if self.baseline[0:6] == "DNH0.0":
            PSTemRel = "MBLRC_PS_REL"
        beginIndex = resp.find(PSTemRel)
        endIndex = resp.find(PSTemRel, beginIndex+1)
        endIndex -= 3
        self.PSAddr = "https://wft.inside.nsn.com/builds/" + resp[beginIndex:endIndex] + "/partial.js?partial=baselines"
        self.PSRel = resp[beginIndex:endIndex]
    
    def getUpAddr(self):
        if self.baseline[0:3] == "DNH":
            self.getPsRel(username, password)
        else:
            self.PSRel = self.baseline
        header = self.structHeader()
        post_data = self.structData(username, password, self.PSAddr)
        resp = self.post(self.loginAddr, header, post_data)
        if None == resp:
            print "test 3 none"
            return
        beginIndex = resp.find("/isource/svnroot", resp.find("PS_DSPHWAPI_SW"))
        endIndex = resp.find("\\n", beginIndex)
        return " https://beisop60.china.nsn-net.net" + resp[beginIndex:endIndex] + " "
        
    def getEclAddr(self):
        header = self.structHeader()
        post_data = self.structData(username, password, self.releaseAddr)
        resp = self.post(self.loginAddr, header, post_data)
        print self.releaseAddr
        if None == resp:
            print "test None"
            return
        beginIndex = resp.rfind("/ALL/secure_download/load_attachment", 0, resp.find("ECL.txt"))
        endIndex = resp.find("\\", beginIndex)
        return "https://wft.inside.nsn.com" + resp[beginIndex:endIndex]

    def getEclContent(self):
        eclAddr = self.getEclAddr()
        print "eclAddr", eclAddr
        header = self.structHeader()
        post_data = self.structData(username, password, eclAddr)
        resp = self.post(self.loginAddr, header, post_data)
        if None == resp:
            print "Test 2 None"   
            return
        resp = self.get(eclAddr)
        beginIndex = resp.find("ECL_UPHWAPI")
        beginIndex += 12
        endIndex = resp.find("\n", beginIndex)
        return  " https://beisop60.china.nsn-net.net" + resp[beginIndex:endIndex] + " "
        
    def zipKnife(self, workspace):
        if not os.path.exists(workspace):
            print "workspace didn't exists"
            return
        if os.path.exists(workspace+"/Platforms"):
            os.system("rm -rf " + workspace+ "Platforms")
        if self.PSRel == "":
            if self.baseline[0:3] == "DNH":
                self.getPsRel(username, password)
            else:
                self.PSRel = self.baseline
        os.system("mkdir -p " + workspace + "Platforms/PS_REL/" + self.PSRel + "/C_Platform/CCS_RT/")
        if not os.path.exists(workspace + "C_Platform/CCS_RT/Tar"):
            print "didn't have tar file"
            return
        os.system("cp -rf " + workspace + "C_Platform/CCS_RT/Tar " + workspace + "Platforms/PS_REL/" + self.PSRel + "/C_Platform/CCS_RT/")
        os.system( "cd " + workspace + " && " + "zip -r " + "knife.zip " + " Platforms ")
        
class svn(wft):
    #1.svn co
    #2.ECL
    def __init__(self, baseline):
        wft.__init__(self, baseline)
        self.baseline = baseline
        self.workspace = "./knife_"+baseline + "/"
        self.ECL = self.workspace + "ECL.py"
    
    def parseBaseline(self):
        if self.baseline == "trunk":
            self.svnAddr = "https://beisop60.china.nsn-net.net/isource/svnroot/BTS_SC_DSPHWAPI/MAINBRANCH_LRC/trunk/ "
        elif self.baseline[0:3] == "DNH":
            self.svnAddr = self.getUpAddr()
        elif self.baseline[0:12] == "FBLRC_PS_REL":
            self.svnAddr = self.getUpAddr()
        else:
            print "Wrong baseline"
            
    def checkout(self):
        if os.path.exists(self.workspace):
            yes = raw_input("Do you want to remove origin workspace[Y/N]:")
            if yes == "Y" or yes == "y":
                os.system("rm -rf "+ self.workspace)
            else:
                return
        os.system("svn co " + self.svnAddr + self.workspace)

    def updateECL(self):
        if os.path.exists(self.workspace+ "ECL"):
            print "Updating ECL"
            os.system("cd " + self.workspace + " && " + "python ECL.py")
        else:
            print "Downloading ECL"
            os.system("cd " + self.workspace + " && " + "svn switch " + self.getEclContent())
            os.system("cd " + self.workspace + " && " + "python ECL.py")

    def uploadToWft(self):
        #zip knife
        self.zipKnife(self.workspace)
        #ftp
        ftp = FTP()
        ftp.connect("beeefsn01.china.nsn-net.net", '21')
        ftp.login(username, password)
        print ftp.getwelcome()
        try:
            ftp.cwd(self.workspace)
            ftp.delete("knife.zip")
        except:
            ftp.mkd(self.workspace[0:-1])
            ftp.cwd(self.workspace)      
        f = open(self.workspace + "knife.zip", "rb")
        ftp.storbinary("STOR %s" % os.path.basename("knife.zip"), f)
        ftp.quit() 
        f.close()
        
    def makeKnife(self):
        url = "https://wft.inside.nsn.com/ALL/knife_requests"
        header = self.structHeader()
        post_data = self.structData(username, password, url)
        resp = self.post(self.loginAddr, header, post_data)
        if None == resp:
            return
        data = urllib.urlencode({
            "knife_request[request_type]": "baseline",
            "knife_request[baseline]": self.baseline,
            "knife_request[module]": "hdbde",
            "use_knife_package" : 1,
            "knife_request[knife_dir]": "\\\\beeefsn01.china.nsn-net.net\\DCM_project\\xiangfei\\" + "knife_" + self.baseline,
            "knife_request[force_knife_dir]": 1,
            "knife_request[version_number]": 99,
            "knife_request[dcm_knife]": 0,
            "knife_request[impact_wcdma]": 0,
            "knife_request[server]": "http://beling18.china.nsn-net.net:8080",
            "knife_request[edit_config]": 0,
            "knife_request[flags][]": "bts",
            "knife_request[no_reference]": 1,
            "knife_request[purpose]":"debug",
            "knife_request[result_receiver]" : "xiang.1.fei@nokia.com"
            })

        data += '&' + urllib.urlencode({
             "knife_request[flags][]": "map"
            })
        

        if '0.0' in self.baseline and len(self.baseline) == 25:
            data += '&' + urllib.urlencode({
              "knife_request[knife_type]": "trunk",
              "knife_request[rebuild_sc][]":"PS_REL"
            })
        else:
            print "check if in here?"
            data += '&' + urllib.urlencode({
              "knife_request[knife_type]": "fb",
              "knife_request[rebuild_sc][]":"PS_REL"
            })
        ##real post action
        resp = self.post(url, header, data)
        
        
class knife(svn):
    def __init__(self, baseline):
        svn.__init__(self, baseline)
            
    def make(self):
        self.uploadToWft()
        self.makeKnife()

    def build(self):
        os.system("cd " + self.workspace + " && " + "make DSP_RT_TAR -j64")
    
    
# 1.knife.py trunk opt
# 2.knife.py DHN3.0... opt
# 3.knife.py FBLRC_PS_REL... opt
# opt:(0--checkout, 1--make rt, 2-- make all, 3--build knife)
def main(baseline, checkout, build, isKnife, all):
    global username
    global password
    username = raw_input("Enter your name:")
    password = getpass.getpass("Enter your password:")
    Obj = knife(baseline)
    if all: 
        Obj.parseBaseline()
        Obj.checkout()
        Obj.updateECL()
        Obj.build()
        if baseline[0:3] == "DNH":
            Obj.make()
    else:
        if checkout:
            Obj.parseBaseline()
            Obj.checkout()
            Obj.updateECL()
        if build:
            Obj.build()
        if isKnife:
            if baseline[0:3] != "DNH":
                return
            Obj.make()
    return
    
def optionParse():
    parser = OptionParser()
    parser.add_option("-v", "--version", dest="version", help="baseline version,default is trunk", default="trunk")
    parser.add_option("-c", "--checkout", action="store_true", dest="checkout", help="only checkout code", default=False)
    parser.add_option("-b", "--build", action="store_true", dest="build", help="only build code", default=False)
    parser.add_option("-k", "--knife", action="store_true", dest="knife", help="only upload knife", default=False)
    parser.add_option("-a", "--all", action="store_true", dest="all", help="checkout code, build and make knife", default=False)
    return parser
    
if __name__ == "__main__":
    parser = optionParse()
    (options, args) = parser.parse_args()
    if options.checkout == False and options.build == False and options.knife == False and options.all == False:
        parser.print_help()  
    else:
        main(options.version, options.checkout, options.build, options.knife, options.all)
        
