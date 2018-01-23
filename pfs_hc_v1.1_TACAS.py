#!/usr/bin/python


### version 1.1 :-
### Updating manaual input for TACAS 11/07/2017
### Removing port scan for faster execution


import getopt
import platform
import shutil
import os.path
import os
import subprocess
import errno
import inspect
import threading
import re
import time
import signal
from datetime import datetime
from datetime import timedelta
import collections
import sys
import csv
from time import ctime






timeout  = 60
Login    ='root'

TACAS          = True
FOLDER         = '/root/PFS3903_HC' ### Set the path to script's folder
Last_Scanpath  = FOLDER+'/Results'
Results_path   = FOLDER+'/Results'
Last_Scan_time = ''

#sys.path.append(FOLDER)
sys.path.append(FOLDER+'/lib')



try:
    import pexpect
except ImportError:
    msg = "Failed to import pexpect file, file missing?"
    print msg
    sys.exit(1)
try:
    import sendemail

except ImportError:
    print " Failed to import sendemail"
    sys.exit(1)

if os.path.isfile(Last_Scanpath+'/Last_Scan_time'):
   f=open(Last_Scanpath+'/Last_Scan_time','rb')
   Last_Scan_time=f.read()
   f.close()
  
if not os.path.exists(Last_Scanpath):
    os.makedirs(Last_Scanpath)

if not os.path.exists(Results_path):
    os.makedirs(Results_path)

class Server:
   # _p            = None
    _Ip           = None
    _Username     = None
    _Password     = None
    _Timeout      = 60
    _TimeInterval = None
   # _Status       = None

    _Report       = None
    _Port         = 53058
    _Alias        = None

    _Switches     = None
    
    def __init__(self,ip,username,password,timeout,timeinterval,alias=None):
        self._p        = None
        self._Ip       = ip 
        self._Username = username 
        self._Password = password
        self._Alias    = alias
        self._TimeInterval = timeinterval
        self._Status   = None
        self._Name     = None
        self._StdbyIP    = None
        self._Switches = []
        self._sw       = None

        self._sys_alarm = None ## sho sys ala curr
        self._prt_alarm = None ## sho por ala curr
        self._switchesdata = None
        self._curr_sys_alarms=[]
        self._curr_port_alarms=[]
        self._StdbyName = None  

        self._hc        = None 
        self._rootusage = None
        self._optusage  = None        
        self._Stdbyhc   = None
        self._Stdbyrootusage = None
        self._Stdbyoptusage  = None
        


    def AddSwitch(self,name,status=None):
        self._Switches.append(Switch(name,status))
        ### show switches
    def Add_hc(self,omrep_output):
        ### omreport chassis output
        self._hc.append(omrep_output)

    def AddSwitches_data(self, data):
        self._switchesdata = data

    def Clear(self):
        self._Switches = []
class Switch:
    _Name   = None
    _Status = None
    _Blades = None

    def __init__(self,name,status=None):
        self._Name = name 
        self._Status = status
        self._Blades = []
 ### show switch "Tulsa PFS-02"
        self._IP     = None
        self._cnt    = None
        self._model  = None
        self._status = None
        self._psu1   = None
        self._psu2   = None
        self._fan    = None
        self._pwrbudget = None
  #### diagstat cha "cnt"      
        self._brdstat = None
        #self._brdstatchng= []
        self._ports  = {}
        self._portschng ={}
    
    def AddBlade(self,name,version=None,status=None):
        self._Blades.append(Blade(name,version,status))
        
####ports status for switch        
    def Addports_status(self, lines):
      try:  
        f=re.findall('.*Connected|.*Not Connected',lines)
        for i in f:
          
          i=i.replace('Not ','Not-')
          i=i.split()
          self._ports[i[0]]=i[1]
        print self._ports  
      except:
         print "could not add ports"
        
    def GetBlades():
        pass
        
class Blade:
    _Name    = None 
    _Version = None
    _Status  = None

    def __init__(self,name,slot=None,brdstat=None,status=None,version=None):
  
        self._Name    = name
        self._Version = version
  ### diag bla 1.01
        self.brdstat  =brdstat
        self._Status  = status
        self._slot    = slot
        self._temp    = ''
        self._connfilter = ''
    def UpdateStatus(self,status):
        self._Status = status

    def GetBladeStatus():
        pass




def spawn(server):
    print "Attempting to connect to ", server._Ip
    try:
        COMMAND_PROMPT = "=> "
        p = pexpect.spawn('telnet %s %s' %(server._Ip,server._Port))
        i = p.expect([pexpect.TIMEOUT, pexpect.EOF, COMMAND_PROMPT], timeout=server._Timeout)
        if i == 0:
            server._Status = "Timed out trying to reach server"
            print "  Timed out trying to reach server"
            return False
        if i == 1:
            server._Status = "Unable to reach server"
            print "  Unable to reach server"
            return False
        
        output = p.before
        lines  = output.splitlines()
        #for line in lines:
        #    print line
        server._p = p
        return True
    except:
        print "ERROR: Not able to Connect to", server._Ip


def logon(server):
    print "Attempting to Logging on to ", server._Ip
    try:
        p = server._p
        p.sendline('logon %s %s \r'%(server._Username,server._Password))
        i = p.expect(["Access denied", pexpect.TIMEOUT, pexpect.EOF, server._Username + " is now logged on.", 'ACCEPT'], timeout=server._Timeout)
        if i == 0:
            print "    Invalid credentials"
            server._Status =  "Invalid credentials"
            return False
        if i == 1:
            print "    Timed out"
            server._Status = "No response"
            return False
        if i == 2:
            print "    Connection unexpectingly closed"
            server._Status = "Connection unexpectingly closed"
            return False
        if i == 4:
            print "    Sending accept to license"
            p.sendline('A\r')
        if i == 3: 

            print "Successfully Logged on to ", server._Ip
        
        output = p.before
        lines  = output.splitlines()

        server._p = p
        return True
    except:
        print "ERROR: Not able to log on to server ", server._Ip
        
def exit_server(server):
    try:
        p = server._p
        p.sendline('exit\r')
        i = p.expect([pexpect.TIMEOUT, pexpect.EOF], timeout = timeout)
        if i == 0:
            print "Failed to exit ", server._Ip
            return
        server._p = None

        print "Ended connection to", server._Ip
    except:
        print "ERROR: Did not finish exiting ", server._Ip

def logoff(server):
    try:
        COMMAND_PROMPT = "=> "
        p = server._p
        p.sendline('exit\r')
        i = p.expect([pexpect.TIMEOUT, pexpect.EOF, COMMAND_PROMPT], timeout = timeout)
        if i == 0:
            print "Failed to log out of ", server._Ip
            return
        server._p = p
        print "Logged Out of ", server._Ip
    except:
        print "ERROR: Did not finish logging off ", server._Ip
        

        
      
def Scan1(server):

  try:
        utcTime = datetime.utcnow()
        print "Starting Scan For Server: " , server._Ip,"AT TIME:", utcTime.strftime("%Y-%m-%d %H:%M:%S")
        #server._Switches = []
        p = server._p
    
        # Add Switches to system
        #print ("  Retrieving switches")
        COMMAND_PROMPT = "=> "
        p.sendline('\r')
        p.expect(COMMAND_PROMPT)
        p.sendline('show switches \r')
        i = p.expect(["ERROR:", pexpect.TIMEOUT, pexpect.EOF, "-----------", COMMAND_PROMPT], timeout=60)
        if i == 0:
            server._Status = "Switch returned an error:" + p.after
            print "Switch returned an error:" + p.after
        elif i == 1:
            server._Status = "Failed to get switches: Timeout"
            print "Failed to get switches: Timeout"
        elif i == 2:
            server._Status = "Lost connection to the server"
            print "    Lost connection to the server"

    
        p.expect(COMMAND_PROMPT)
        ### Add switches to server
        switches = p.before.splitlines()
        print switches
        
        for i in switches[2:-1]:
         
          server.AddSwitch(i)
        for switch in server._Switches:
            GetSwitch_Status(p,switch)
            
        ## SW version
        
        #p.expect(COMMAND_PROMPT)
        p.sendline('show stat \r')
        p.expect(COMMAND_PROMPT)
        sho_stat=p.before
        server._sw=re.findall('Version (.*)',sho_stat)[0].rstrip()
        
        ### sys alarm
        #p.expect(COMMAND_PROMPT)
        p.sendline('sho sys ala curr \r')
        p.expect(COMMAND_PROMPT)
        server._sys_alarm=p.before.splitlines()[1:]
        print server._sys_alarm
        
        ### port alarm
        #p.expect(COMMAND_PROMPT)
        p.sendline('sho port ala curr \r')
        p.expect(COMMAND_PROMPT)
        server._prt_alarm=p.before.splitlines()[1:]
        print server._prt_alarm
        

        
  except:
       print "Cannot Scan server"+server._Ip
       raise 
       #sys.exit(1)
       #return True
  try:
        #### Standby server
      
        p.sendline('show servers \r')
        p.expect(COMMAND_PROMPT)
        server._StdbyIP=re.findall('Standby Server:\s*(.*\d)',p.before)[0].rstrip()



  except:
        
        print " Could not get standby information of "+server._StdbyIP
        

  return True         
       
def GetSwitch_Status(_p,switch):
  try:
        p=_p
        COMMAND_PROMPT = "=> "
        p.sendline('\r')
        p.expect(COMMAND_PROMPT) 
        print switch._Name        
        p.sendline('show switch "%s" \r'%switch._Name)
        i = p.expect(["ERROR:", pexpect.TIMEOUT,pexpect.EOF, COMMAND_PROMPT], timeout=60)
        if i == 0:
            switch._Status = "Switch returned an error:" + p.after
            print "Switch returned an error:" + p.after
        elif i == 1:
            switch._Status = "Failed to get switches: Timeout"
            print "Failed to get switches: Timeout"
        elif i == 2:
            switch._Status = "Lost connection to the server"
            print "    Lost connection to the server"       
        #print i
        #p.expect(COMMAND_PROMPT)
        elif i==3:
          data=p.before
        print data
        ## Switch IP
        try:
           switch._IP = re.findall('Ipv4: (..*\..*\..*[0-9]),',data)[0].rstrip()
            ## Switch status 
           switch._status =  re.findall('Switch Model.*Status: (\w?\w?\w?.\w*)',data)[0].rstrip() 
              ## Switch model
           switch._model  =  re.findall('Switch Model.* :  (.*), Ipv4',data)[0].rstrip() 
        except:
           print "Error in accessing data"

        if switch._status == 'Active':
            try:
              ## Switch controller Number
              switch._cnt    =  re.findall('Results.*FAN.*controller (.*) :',data)[0].rstrip()
             

             
             
             
              ## PSU1
              switch._psu1   =  re.findall('PSU 1.*status (.*)',data)[0].rstrip()
             
              ## PSU2
              switch._psu2   = re.findall('PSU 2.*status (.*)',data)[0].rstrip()
             
              ## FAN
              switch._fan    = re.findall('FAN.*status is (.*)',data)[0].rstrip()
             
              ## Power Budget
              switch._pwrbudget =  re.findall('Max. draw: (.*W)',data)[0].rstrip()
              
              #### blades Status
              blades = re.findall(' ([0-9]*\.[0-9]*).*Blade',data)
            except:
              print "Error in accessing data"

            p.sendline('sel switch "%s" \r'%switch._Name)
            i = p.expect([pexpect.TIMEOUT, pexpect.EOF, COMMAND_PROMPT], timeout=timeout)
            if i == 0:
               print "Switch: " + switch._Name + " cannot select switch"
            
            elif i==2:
               p.sendline('diagstat cha %s \r'%switch._cnt)
               i_ = p.expect([pexpect.TIMEOUT, pexpect.EOF, COMMAND_PROMPT], timeout=timeout)
               
               if i_ == 0:
                  print "Controller: " + switch._cnt + " cannot run diagstat"
               else: 
                  print "diagstat i is %s"%i
                  data1=p.before
                  print " data for cha-->"+data1
                  switch._brdstat = re.findall('Slot.*board(.?(?:NOT)? PRESENT)',data1)
                  print switch._brdstat
            
            
            
            for i in blades:
                slotnum = int(re.findall('1.0(.)',i)[0])
                brdstat  = switch._brdstat[slotnum-1]
                switch.AddBlade(i,slotnum,brdstat)
            
            #else:
            for blade in switch._Blades:
                    #if brdstat =='PRESENT'
                         Getbladestatus(p,blade)
            
                  
         #   p.sendline('\r')
         #   p.expect(COMMAND_PROMPT)
         #   
         #   p.sendline('show port info * SWI "%s" \r'%switch._Name)
         #   i = p.expect([pexpect.TIMEOUT, pexpect.EOF, COMMAND_PROMPT], timeout=timeout)
         #   print i
         #   
         #   if i == 0:
         #      print "Controller: " + switch._cnt + " cannot run port info"
         #   else: 
         #      lines=p.before
         #      print lines
         #      switch.Addports_status(lines)
              #print switch.Addports_status  

        #else: 
        #    switch._cnt,switch._model,
  except:
        print "Cannot get Switch"+ switch._Name +"status"  
        raise
def Getbladestatus(p,blade):
  try :
       
        COMMAND_PROMPT = "=> "
        p.sendline('\r')
        p.expect(COMMAND_PROMPT)       
        p.sendline('diagstat bla "%s" \r'%blade._Name)
        i = p.expect(["ERROR:", pexpect.TIMEOUT,pexpect.EOF, COMMAND_PROMPT], timeout=60)
        if i == 0:
            blade._Status = "Blade returned an error:" + p.after
            print "Blade returned an error:" + p.after
        elif i == 1:
            blade._Status = "Failed to get blade : Timeout"
            #blade._temp = 'NA'
            #blade._connfilter = 'NA'
            print "Failed to get blade: Timeout "+blade._Name

        #,"Timeout waiting for response from slot %s\r\n\r\n"%blade._slot, "Board number %s not present\r\n\r\n"%blade._slot
        #elif i == 2:
        #    blade._Status = "Failed to get blade : Timeout"
        #    blade._temp = 'NA'
        #    blade._connfilter = 'NA'
        #elif i == 3:
        #    blade._Status = "Not Present"
        #    blade._temp = 'NA'
        #    blade._connfilter = 'NA'
        #    print "Failed to get blade: Not present "+blade._Name
        elif i == 2:
            blade._Status = "Lost connection to the server"
            print "    Lost connection to the server"              
        
        #p.expect(COMMAND_PROMPT)
        elif i == 3:
           data=p.before
           print data
           good=re.findall('GOOD',data)
           
           if len(good) == 14:
              blade._Status = 'GOOD'
           else:
              blade._Status = 'ERROR PRESENT'
             
           blade._temp=re.findall('Temperature of Blade: (.*)',data)[0].rstrip()
           blade._connfilter= re.findall('Connection Filter Resources Available: at least(.*)',data)[0].rstrip()
           blade._Version = re.findall ('SW Version:\s?(.*)',data)[0].rstrip()
           
        #p.sendline('\r')
  except: 
        print "Cannot get Blade"+blade._Name+"status" 
        blade._Status= "Failed to get blade %s"%blade._Name   

def makeSurePathExists(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except:
        print "Failed to create directory:", path
        
def Log_Results(server):
    try:
       if server._Status==None:
          pass
       switches_data=[]
       data=[]
       for switch in server._Switches:
            
            data.append(switch._Name)
            data.append(switch._IP)
            data.append(server._Ip)
            data.append(server._sw)
            data.append(switch._model)
            data.append(switch._status)
            if switch._status=='Active': 
              data.append(switch._psu1)          
              data.append(switch._psu2) 
              data.append(switch._fan)          
              data.append(switch._pwrbudget)
              data=data+switch._brdstat 
              data.append(switch._cnt)
              
              for blade in switch._Blades:
                 data.append(blade._Status)
                 data.append(blade._Version)
                 data.append(blade._temp)
                 data.append(blade._connfilter)
          
            
            else:
                 data=data+['NA' for i in range(8)]
            data = ['None' if v is None else v for v in data]
            switches_data.append(data)
            data=[]

       server._switchesdata = switches_data 
       print "Logging results"
       print server._switchesdata
    except:
       print "Cannot log data for switch"+switch._Name
 

def PortScan(server,path):

    try:
        for switch in server._Switches:
            if os.path.isfile(path+'/'+switch._Name+'_port_scan'):
                port_oldstatus={}
                f = open(path+'/'+switch._Name+'_port_scan', 'rb')
                for line in f:
                    line=line.split()
                    port_oldstatus[line[0]]=line[1]
                for i in switch._ports:
                    if i in port_oldstatus and port_oldstatus[i]!=switch._ports[i]:
                         switch._portschng[i]=[port_oldstatus[i],switch._ports[i]]
                f.close()
            
            f=open(path+'/'+switch._Name+'_port_scan', 'wb')
            for port in switch._ports:
              f.write(port+' '+switch._ports[port]+'\n')
            f.close() 
            print "Ports scan file for %s has been created"%switch._Name
        
    except:
        print " Cannot scan ports for server "+server._Name    

def CurrAlarmScan(server):
    try:
     if Last_Scan_time:
        time_now=datetime.now()
        time_lastscan=datetime.strptime(Last_Scan_time,"%a %b %d %H:%M:%S %Y")
     ##### portsalarm
        for i in server._prt_alarm:
              alarmtime=re.findall('.*/../[0-9]{2}',i)
              
              if alarmtime:
                _alarmtime=datetime.strptime(alarmtime[0],"%I:%M:%S%p %m/%d/%y")
                if _alarmtime > time_lastscan:
                   server._curr_port_alarms.append(i)
      #### sysalarm
        for i in server._sys_alarm:
              alarmtime=re.findall('.*/../[0-9]{2}',i)
              if alarmtime:
                _alarmtime=datetime.strptime(alarmtime[0],"%I:%M:%S%p %m/%d/%y")
                if _alarmtime > time_lastscan:
                   server._curr_sys_alarms.append(i)

    except:
       print " Cannot scan currnet alarm scan for server "+server._Name


class ScanThread(threading.Thread):

    def __init__(self, server):
        threading.Thread.__init__(self)
        self.__server = server
        self._stop = threading.Event()
        self._interval = server._TimeInterval
        self._scanstats = False
    def run(self):
        spawned_successfully = spawn(self.__server)
        logged_on_successfully = logon(self.__server)
        #while not self.__stopevent.isSet():
        if spawned_successfully and logged_on_successfully:
            self._scanstats=self.scan()
        else:
            print "Failed to run Scan"
            self.stop()
            self._scanstats= True


    def logoff(self):
        logoff(self.__server)

    def stop(self):
        self._stop.set()
        self._is_running = False
        exit_server(self.__server)

    def stopped(self):
        return self._stop.isSet()

    #def join(self,timeout = None):
    #    #self.__stopevent.set()
    #    threading.Thread.join(self,timeout)
    #    print "stopped"
    #    return

    def scan(self):
        Scan1(self.__server)
        GetServerHealth (self.__server)

        #DISPLAY RESULTS
        #Display_Results(self.__server)
        Log_Results(self.__server)
        #PortScan(self.__server,Last_Scanpath)
        CurrAlarmScan(self.__server)
        return True
    def auto_scan(self):
        #TODO REMOVE
        #print 'current count: ',count
        #print 'current time:  ',datetime.utcnow()

        #TODO
        #MAKE REPEAT EVERY INTERVAL EXACTLY
        #######
        interval_time = timedelta(hours = self._interval)
        restart_time = datetime.utcnow() 

        while(self.isAlive()):
            #if count == self._interval:
            if datetime.utcnow() > restart_time:

                restart_time += interval_time

                self.scan()
                #count = 0
            else:
                still_logged_in = show_stat(self.__server)
                if still_logged_in == False:
                    print "-----Connection Lost Server: ", self.__server._Ip, "at time: ", datetime.utcnow()
                    self.stop()
                    break
                #print "standby... time: " ,datetime.utcnow()

            #count += 1

            time.sleep(10)  
def usage():
    print "   "
    print "   This Utility checks the status of PFS systems periodically based on a defined interval"
    print "   "
    print "   Runs on any linux system. Requires Python 2.7."
    print "   "
    print "   Please Provide a File with list of servers, a username, a password, and a time interval"
    print "   "
    print "   Note: The File with the list of server ip addresses should be entered in rows following"
    print "   "
    print "         the first line with 'SERVERS LIST:' "
    print "   "
    print "   Command Line Parameters:"
    print "   "
    print "       -f , file="
    print "       -e , email ="

    print "   "
    print "   Note: Accepts time interval in hours. Supports partial hours: for 30 min enter '0.5'"
    print "   "
    print "   Examples: "
    print "   "
    print "       $ ./pfs_hc.py -f ips.txt -e email_info"
    print "   "
 
    sys.exit(1)


def LoadDb( myFile, IpDb ):
    try:
        f = open(myFile)
        reader = csv.reader(f)
        for row in reader:
            print row
            IpDb.append(row)    

        f.close()
    except:
        print "could not open file"
        e = sys.exc_info()[1]
        sys.exit(0)

def GetServerHealth (server):
   ####### For Server HC data#########################
    timeout=30
    try:  
        print """ Initiating Server Health check """
        
        omreport_command= """ omreport chassis """
        output, err = ssh_command(server._Ip, omreport_command,timeout)
        if output:
           server._hc=re.findall('(.*)\s{1,7}:.*',output)[1:]
        
        hostname_command= """hostname"""
        output, err = ssh_command(server._Ip, hostname_command,timeout)
        if output:
           server._Name=re.findall('.*',output)[0].rstrip()

        root_usage="""df -h | grep "/$"|awk '{print $5}'"""
        output, err = ssh_command(server._Ip, root_usage,timeout)
        if output:
           server._rootusage=re.findall('.*',output)[0].rstrip()
        
        opt_usage="""df -h | grep "/opt"|awk '{print $5}'"""
        output, err = ssh_command(server._Ip, opt_usage,timeout)
        if output:
           server._optusage=re.findall('.*',output)[0].rstrip()
           
        
    except:
        print " Cannot get HC data of %s"%server._Ip 
        
   ##### For Standby Server HC data #######################################
    try:  
        print """ Initiating Standby Server Health check """
        print server._StdbyIP
        omreport_command= """ omreport chassis """
        output, err = ssh_command(server._StdbyIP, omreport_command,timeout)
        if output:
           server._Stdbyhc=re.findall('(.*)\s{1,7}:.*',output)[1:]
        
        hostname_command= """hostname"""
        output, err = ssh_command(server._StdbyIP, hostname_command,timeout)
        if output:
           server._StdbyName=re.findall('.*',output)[0].rstrip()

        root_usage="""df -h | grep "/$"|awk '{print $5}'"""
        output, err = ssh_command(server._StdbyIP, root_usage,timeout)
        if output:
           server._Stdbyrootusage=re.findall('.*',output)[0].rstrip()
        
        opt_usage="""df -h | grep "/opt"|awk '{print $5}'"""
        output, err = ssh_command(server._StdbyIP, opt_usage,timeout)
        if output:
           server._Stdbyoptusage=re.findall('.*',output)[0].rstrip()           
        
    except:
        print " Cannot get HC data of standby server %s"%server._StdbyIP 

    

#def ssh_command(IP, command):
#    if re.search('.*\..*\..*\..*',IP):
#       if int(os.popen('ping -c 2 %s|grep received | cut -d, -f2 |grep -o [0-9]'%IP).read().rstrip()) > 0:
#                 
#                 p= subprocess.Popen(["ssh",Login+'@'+IP,command], stdout=subprocess.PIPE)
#                 output,err= p.communicate()
#    elif re.search('.*:.*:.*:.*:.*:.*:.*:.*',IP):
#         if int(os.popen('ping6 -c 2 %s|grep received | cut -d, -f2 |grep -o [0-9]'%IP).read().rstrip()) > 0:
#                
#                 p= subprocess.Popen(["ssh","-6",Login+'@'+IP,command], stdout=subprocess.PIPE)
#                 output,err= p.communicate()
#    return output,err        

def ssh_command(IP,command,timeout):
    #"""call shell-command and either return its output or kill it
    #if it doesn't normally exit within timeout seconds and return None"""

    start = datetime.now()
    process = subprocess.Popen(["ssh",Login+'@'+IP,command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while process.poll() is None:
      time.sleep(0.1)
      now = datetime.now()
      if (now - start).seconds> timeout:
        os.kill(process.pid, signal.SIGKILL)
        os.waitpid(-1, os.WNOHANG)
        return None
    output,err =process.communicate()
    return output,err
def get_error_output(error_dic, data):
    errors_output={}
    html=''
    for error in error_dic:
        errors_output[error]=[]
    q=0
    for i in data:
      for j,k in error_dic.items():
        print j
        print k
        print i[k[1]]
        if (re.search(k[0],i[k[1]])):
          errors_output[j].append(q)
          
      q=q+1 
    #return errors_output 
    for error,index in errors_output.items():
        if index:
           html+=""" <h2>%s (%s)</h2> """%(error,len(index))
           html+=""" <table> """
           for num in index:
           
              html+= "<tr align=justify><td>%s</td><td>%s</td><td> %s  </td> </tr>"%(data[num][0],data[num][1],data[num][error_dic[error][1]])
           
           html+=""" </table>\n """
           html+="         "

    return html
   
def DataProcessing(servers):
    total_servers=len(servers)
    servers_responded=0
    total_switches=0
    total_blades=0
    total_ports=0
    total_connected_ports=0
    
    for server in servers:
        if server._Name:
           servers_responded+=1
        for switch in server._Switches:
            total_switches+=1
            for blade in switch._Blades:
              total_blades+=1
        
            total_ports+=len(switch._ports)
            total_connected_ports+=len([k for i,k in switch._ports.items() if k == 'Connected'])  

    return {
    'Total Servers':total_servers,
    'Total Servers Responded':servers_responded,
    'Total Switches':total_switches,
    'Total Blades':total_blades,
    'Total Ports':total_ports,
    'Total Connected ports':total_connected_ports,
      }      
def proto_main(argv):

    #INITIALIZE EVERYTHING
    Manifest           = None
    Ip_Address         = None
    Universal_Username = None
    Universal_Password = None
    TimeInterval       = None
    IpDb               = []
    ips                = []
    servers            = []
    ScanThreads        = []
    timeout            = 60

    #PARSE OPTIONS

    try:
        opts, args = getopt.getopt(argv, "h:f:e:", ["help","file=","email="])
    except:
        e = sys.exc_info()[1]
        usage()
    for opt, arg in opts:
        #print opt + "," + arg
        if opt in ("-h", "--help"):
            usage()
        elif opt in ( "-f", "file="):
            Manifest = arg
        elif opt in ("-e","email="):
            Emailfile = arg

    print Manifest
    if Manifest == None:
        usage()
    if Emailfile == None:
        usage()
    
    
    if Emailfile =='NA':
        print " Email option is not selected"
   
           
    #print "________________________________________________________________________________"
    #print ""
    #print "                        AUTOMATIC SERVER SCAN STARTING" 
    #print "________________________________________________________________________________"

    print "Automatic Server Scan Starting" 
    if TACAS:
        print " Type TACAS login Credentials"
        username = raw_input("Enter your username: ")
        password = raw_input (" Enter your password: ")

    if (Manifest!= None):
        LoadDb(Manifest, IpDb)
        isHeader = True
        for row in IpDb:
            print row
            if not isHeader:
                ip        = row[0].strip()
                ips.append(ip)
                if len(row) >= 1:
                    username1     = row[1].strip() 
                    password1     = row[2].strip()
                    timeout      = int(row[3].strip())
                    timeinterval = None
                    alias        = None
                #if len(row) == 6:
                #    alias = row[5].strip()

                #if alias == None:
                #    servers.append(Server(ip,Universal_Username,Universal_Password,timeout,timeinterval,alias))
                #else:
                if TACAS:
                   servers.append(Server(ip,username,password,timeout,TimeInterval))
                else : 
                   servers.append(Server(ip,username1,password1,timeout,TimeInterval))
            else:
                isHeader = False

    
   
    #CREATE SERVERS LIST
    #for ip in ips:
    #    server = Server(ip,Universal_Username,Universal_Password,timeout)
    #    servers.append(server)

    #START THREADS AND ADD THEM TO LIST
    for server in servers:
        scan_thread = ScanThread(server)
        scan_thread.daemon = True
        scan_thread.start()
        ScanThreads.append(scan_thread)

    #MAKE SURE ALL THREADS STARTED SUCCESSFULLY
    all_threads_started_successfully = True
    for scan_thread in ScanThreads:
        if not scan_thread.isAlive():
            all_threads_started_successfully = False
            print "Scan Failed to Initiate on Server: ",scan_thread.__server._Ip

    if all_threads_started_successfully == True:
        print "All Server Threads Successfully Initiated"

    for scan_thread in ScanThreads:
         scan_thread.join()
    
    def CleanUp(ScanThreads):
        try:
            all_threads_stopped_successfully = True
            
             #LOGOFF OF SERVERS AND STOP THREADS
            while(stop == False):
                scan_status=[]
                for scan_thread in ScanThreads:
                    if not scan_thread.stopped():
                       all_threads_stopped_successfully = False
                scan_status.append(scan_thread._scanstats)
                if all( i== True for i in scan_status) and all_threads_stopped_successfully:
                    stop = True
                    for scan_thread in ScanThreads:
                        scan_thread.logoff()
                        scan_thread.stop()
                time.sleep(2)
            
             #    scan_thread.join()
             #    if scan_thread.isAlive():
             #        print "not terminated"
            
             #CHECK IF ALL THREADS HAVE SUCCESSFULLY BEEN STOPPED
              #for scan_thread in ScanThreads:
              #    if not scan_thread.stopped():
              #        all_threads_stopped_successfully = False
            if all_threads_stopped_successfully:
                #print "________________________________________________________________________________"
                #print ""
                #print "                         All threads successfully stopped"
                #print "________________________________________________________________________________"
                #print ""
                print "All threads successfully stopped"
    
            #TODO ADD JOIN ALL HERE TOO
                    ###
                    #scan_thread.join()
    
                #    print scan_thread.__server._Ip, "not terminated"
            #CLEAR ALL SERVERS AND THREADS
            #servers = []
            #ScanThreads = []
        except:
            print "ERROR: Not able to properly clean up"
    
    def signal_handler(signal, frame):
    #def signal_handler(ScanThreads):
        print "\n"
        #print "________________________________________________________________________________"
        #print ""
        #print "                               SCAN END REQUESTED"
        #print "________________________________________________________________________________"
        #print ""
        #print "________________________________________________________________________________"
        #print ""
        #print "                                 FINISHING UP..."
        #print "________________________________________________________________________________"
    
        print "Scan Termination Requested"
        print "Finishing Up..."
    
        CleanUp(ScanThreads)
    
        print "Scan Terminated" 
        print "All Logs can be found in the Results Directory"
        print ""
    
        #print "________________________________________________________________________________"
        #print ""
        #print "                                   SCAN ENDED" 
        #print "________________________________________________________________________________"
        #print ""
        #print "                  Results can be found in the Results Directory"
        #print ""
    
        #sys.exit(0)
    
    #signal.signal(signal.SIGINT,signal_handler)
    
    
    #print "Scan Termination Requested"
    #print "Finishing Up..."
    #
    #CleanUp(ScanThreads)
    
    print "Scan Terminated" 
    #print "All Logs can be found in the Results Directory"
    print ""
    
    server_hdr=[
         'Server',
         'Server IP',
         'Standby IP',
         'Fans',
         'Intrusion',
         'Memory',
         'Power Supplies',
         'Power Management',
         'Processors',
         'Temperatures',
         'Voltages',
         'Hardware Log',
         'Batteries',
         '/ Usage',
         '/opt Usage']
  
  
  
    switch_hdr=[
    'Switch',
    'Switch IP',
    'Server',
    'Software Version',
    'Model',
    'Switch Status',
    'PSU1 Status',
    'PSU2 Status',
    'FAN Status',
    'Max Power Budget',
    'Slot 1 Status',
    'Slot 2 Status',
    'Slot 3 Status',
    'Active Controller',
    'Blade 1.01 Status',
    'Blade 1.01 Version',
    'Blade 1.01 Temp',
    'Blade 1.01 Conn Filter',
    'Blade 1.02 Status',
    'Blade 1.02 Version',
    'Blade 1.02 Temp',
    'Blade 1.02 Conn Filter',
    'Blade 1.03 Status',
    'Blade 1.03 Version',
    'Blade 1.03 Temp',
    'Blade 1.03 Conn Filter']
    
  
  
  
  

  
    file1=open(Results_path+"/Server_HW_Status.csv",'wb')
    file1.write(','.join(server_hdr))
    file1.write('\n')

    file2=open(Results_path+"/Switch_Status.csv",'wb')
    file2.write(','.join(switch_hdr))
    file2.write('\n')
   
    servers_data=[]
    switches_data=[]
    port_scan_html=''
    port_curr_alarm=''
    sys_curr_alarm=''
    for server in servers: 
        try:
        #print server._Name+','+server._Ip+','+server._StdbyIP+','+','.join(server._hc)+','+server._rootusage+','+server._optusage 
          data=server._Name+','+server._Ip+','+server._StdbyIP+','+','.join(server._hc)+','+server._rootusage+','+server._optusage
          file1.write(data)
          file1.write('\n')
          servers_data.append(data.split(','))
          
        except:
             print """data of server %s cannot be written"""%server._Ip
        try:
          stdby_data=server._StdbyName+','+server._StdbyIP+','+'NA'+','+','.join(server._Stdbyhc)+','+server._Stdbyrootusage+','+server._Stdbyoptusage
          file1.write(stdby_data)
          file1.write('\n')
          servers_data.append(stdby_data.split(','))
          
        except:
             print """data of standby server %s cannot be written"""%server._StdbyIP
        
        
        if server._switchesdata is not None:
          print server._switchesdata
          for data in server._switchesdata:
           file2.write(','.join(data))
           file2.write('\n')
           
           na_data=[]
           if len(data) < len(switch_hdr):
               na_data=['NA' for i in range(len(switch_hdr)-len(data))]  
               
           switches_data.append(data+na_data)   
        ###############Port scan data
        if Last_Scan_time:
             
            for switch in server._Switches:
                if switch._portschng:
                    scan_html=''
                    scan_html+=""" <h4> Switch : %s </h4>"""%switch._Name
                    scan_html+=""" <table>"""
                    #scan_html+=""" <tr>"""
                    
                    for port,status in switch._portschng.items():
                         scan_html+= """<tr align=justify><td> %s </td> <td>  %s (old) </td> <td> %s (new) </td></tr>""" %(port,status[0],status[1])
                    
                    #else:
                    #     scan_html+=""" <p> %s ports status are same as last scan <p> """%switch._Name
                    scan_html+=""" </table>"""
                    port_scan_html+=scan_html
        ########### ####################
        ##### Alarm Scan Data##################
        if server._curr_port_alarms:
            port_curr_alarm+= "<h4> Server : "+server._Name+"</h4>"
            port_curr_alarm+= "<p>"+'<br><br>\n'.join(server._curr_port_alarms)+"</p>"
            
        if server._curr_sys_alarms:
            sys_curr_alarm+= "<h4> Server : "+server._Name+"</h4>"
            sys_curr_alarm+= "<p>"+'<br><br>\n'.join(server._curr_sys_alarms)+"</p>"            
   
    print switches_data    
    file1.close() 
    file2.close()
    print "Output File has been create in %s"%os.getcwd()
    #keep main thread alive
    #while True:
        #TODO
        #for scan_thread in ScanThreads:
        #    if scan_thread.stopped():
        #        scan_thread.join()
                
        #time.sleep(1)
    ####################################################ERROR SUMMARY####################################################################################
  
    server_err_dic={}
    for item in server_hdr[3:13]:
       server_err_dic[item+' Failure']=['^(?!Ok)',server_hdr.index(item)]
    server_err_dic.update({
         '/ > 90%':['^9[1-9]|^100',server_hdr.index('/ Usage')],
         '/opt > 90%':['^9[1-9]|^100',server_hdr.index('/opt Usage')]
        })
 
    
    switch_err_dic={
      'Switch Status':['^(?!Active)',switch_hdr.index('Switch Status')],
      'PSU1 Error':['^(?!(?:GOOD|NA))',switch_hdr.index('PSU1 Status')],
      'PSU2 Error':['^(?!(?:GOOD|NA))',switch_hdr.index('PSU2 Status')],
      'FAN Error':['^(?!(?:GOOD|NA))',switch_hdr.index('FAN Status')],
      #'Max Power Budget',
      #'Slot 1 Status',
      #'Slot 2 Status',
      #'Slot 3 Status',
      #'Active Controller',
      'Blade 1.01 Error':['^(?!(?:GOOD|NA))',switch_hdr.index('Blade 1.01 Status')],
      'Blade 1.02 Error':['^(?!(?:GOOD|NA))',switch_hdr.index('Blade 1.02 Status')],
      'Blade 1.03 Error':['^(?!(?:GOOD|NA))',switch_hdr.index('Blade 1.03 Status')],
      'Blade 1.01 Temp':['^[5-9]* C',switch_hdr.index('Blade 1.01 Temp')],
      'Blade 1.02 Temp':['^[5-9]* C',switch_hdr.index('Blade 1.02 Temp')],
      'Blade 1.03 Temp':['^[5-9]* C',switch_hdr.index('Blade 1.03 Temp')],
      'Blade 1.01 Conn Filter > 90%':['^9[1-9]|^100',switch_hdr.index('Blade 1.01 Temp')],
      'Blade 1.02 Conn Filter > 90%':['^9[1-9]|^100',switch_hdr.index('Blade 1.02 Temp')],
      'Blade 1.03 Conn Filter > 90%':['^9[1-9]|^100',switch_hdr.index('Blade 1.03 Temp')]

      }
    
    ### Getting Sever Error data
    html=""" <h2 style="color:red;font-family:verdana;"> Server Errors </h2>""" 
    html+=get_error_output(server_err_dic, servers_data)
    html+=""" <br><br><hr>"""
    html+=""" <h2 style="color:red;font-family:verdana;"> Switch Errors </h2>""" 
    ### Getting Switch Error data
    html+=get_error_output(switch_err_dic, switches_data)
    
    file3=open(Results_path+"/PFS Error Summary.html",'wb')
    
    align='auto'
    width='35%'
    file3.write(""" <!DOCTYPE html>
         <html>
         <body>
         <h1 style="color:red;font-family:verdana;"><u> PFS Error Summary</u> </h1>
         <h3 style="font-family:verdana;"> Date: %s <h2>
                <style>
          table {
             border: 1px solid black;
             border-collapse: collapse;
             width: %s
             }
         td {
            border: 1px solid black;
            padding: 5px;
            text-align: %s;
            }
         tr {
           align:"center"
         }
         h2 {
            color :black
            
            }
         </style>
         """%(ctime(),width,align))
    file3.write(html)
    file3.write(" </body></html>  ")
    file3.close()
    #####################################################Port Scan Results#############################################################################
    if Last_Scan_time and port_scan_html:
        file4=open(Results_path+"/Port_Change_Status.html",'wb')
        
        file4.write(""" <!DOCTYPE html>
         <html>
         <body>
         <h3> Previous Scan : %s </h3>
         <h3> Current  Scan : %s </h3>
         
         <style>
          table {
             border: 1px solid black;
             border-collapse: collapse;
             width: %s
             }
         td {
            border: 1px solid black;
            padding: 5px;
            text-align: %s;
            }
         tr {
           align:"center"
         }
         h3 {
            color :brown
            
            }
         </style>"""%(Last_Scan_time,time.ctime(),width,align))
        file4.write(port_scan_html)
        
        file4.write(" </body></html>  ")
        file4.close()
    #####################################################################################################################################
   
    ############################################Alarm Scan Results###################################################################################
    if Last_Scan_time and (sys_curr_alarm or port_curr_alarm):
        file5=open(Results_path+"/Alarms_since_PreviouScan.html",'wb')
        
        file5.write(""" <!DOCTYPE html>
         <html>
         <body>
         <h3> Previous Scan : %s </h3>
         <h3> Current  Scan : %s </h3>
         <style>
          table {
             border: 1px solid black;
             border-collapse: collapse;
             width: %s
             }
         td {
            border: 1px solid black;
            padding: 5px;
            text-align: %s;
            }
         tr {
           align:"center"
         }
         h3 {
            color :brown
            
            }
         </style>"""%(Last_Scan_time,time.ctime(),width,align))
        file5.write("""<h4 style="color:red;font-family:verdana;"> Port Alarms since previous scan</h4>""")
        file5.write(port_curr_alarm)
        file5.write("<br><br><hr>")
        file5.write("""<h4 style="color:red;font-family:verdana;"> Sys Alarms since previous scan</h4>""")
        file5.write(sys_curr_alarm)      
        file5.write(" </body></html>  ")
        file5.close()

    ### Writing Healthcheck time to disk"######################################################################################
    file6=open(Last_Scanpath+'/Last_Scan_time','w+')
    file6.write(time.ctime())
    file6.close()  


    #### Email Data##################
    #'Total Servers':total_servers
    #'Total Servers Responded':servers_responded
    #'Total Switches':total_switches
    #'Total Blades':total_blades
    #'Total Ports':total_ports
    #'Total Connected ports':total_connected_ports
    email_data=DataProcessing(servers)
    email_html = """
       <html>
       <head></head>
       <style>
           h5 {
         color:lightgrey;
         font-size:75%%
        
         }
         h4 {
         font-family:"Bradley Hand ITC";
         color:red
         }
         h3{
         font-family:"Bradley Hand ITC";
         color:brown
         }
          div{
         font-family:sans-serif;
         font-size:85%%
         }
         </style>
          <body>
          <h5>PFS Health-Check Scan v1.1<br>%s<br></h5>""" %time.ctime()
    email_html+= "<p>"
    email_html+= '<div> Total Servers = %s </div>'%(email_data['Total Servers'])
    email_html+= '<div> Total Servers Responded = %s </div>'%(email_data['Total Servers Responded'])
    email_html+= '<div> Total Switches = %s </div>'%(email_data['Total Switches'])
    email_html+= '<div> Total Blades = %s </div>'%(email_data['Total Blades'])         
    #email_html+= '<div> Total Ports = %s </div>'%(email_data['Total Ports'])
    #email_html+= '<div> Total Connected Ports = %s </div>'%(email_data['Total Connected ports'])
    email_html+= " </p></body>"
     
    file7=open(Results_path+'/Summary.html','w+')
    file7.write(email_html)
    file7.close()  
    

    ######################################EMAIL#########################################################
    AttachmentList=['Server_HW_Status.csv', 'Switch_Status.csv', 'PFS Error Summary.html']
    if port_scan_html:
        AttachmentList.append('Port_Change_Status.html')
    if Last_Scan_time and (sys_curr_alarm or port_curr_alarm):
        AttachmentList.append('Alarms_since_PreviouScan.html')
    try:
        if Emailfile and   Emailfile !='NA':
            ef=open(Emailfile,'rb')
            for line in ef:
                if re.search( 'FROM.*:.*',line):
                    FROM=re.findall('\w*.?\w*@\w*.com',line)
                    FROM=','.join(FROM)
                    
                elif re.search( 'TO.*:.*',line):
                    TO=re.findall('\w*.?\w*@\w*.com',line)
                    TO=','.join(TO)
                elif re.search('SUBJECT.*:.*',line):
                    SUBJECT=re.findall('SUBJECT.*:(.*)',line)[0]
                elif re.search('SMTP.*:.*',line):
                    SMTP=re.findall('SMTP.*:\s*?(\d*\.\d*\.\d*\.\d*)',line)[0]
                else:
                    print " Email information is not correct in file %s"%Emailfile
                    sys.exit(1)
            print (FROM, TO, SMTP, SUBJECT)
             
            email_=sendemail.Email(FROM, TO, SMTP) 
            email_.subject(SUBJECT)
            email_.setpath(Results_path)
            email_.send_email(AttachmentList,email_html)
    except:
        raise
    #    print " Error occured, email cannot be sent"
    #        

if __name__ == '__main__':

    print "   ______    "
    print "    (___ \   NETSCOUT SYSTEMS"
    print "   ( (__) )  "
    print "    \____/   AUTOMATED 3903 PFS SERVER SCAN"
    print "             "
    #

    #ARGUMENTS
    argv = sys.argv[1:]
    #BEGIN MAIN
    proto_main(argv)
            
