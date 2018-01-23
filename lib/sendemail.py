#!/usr/bin/python

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders

class Email :
    def __init__(self, From, To, SMTP_IP):
      self._from = From
      self._to   = To
      self._smtp = SMTP_IP
      self._path=  None 
      self._subject = ''
    def subject(self, subject):
      self._subject = subject
    
    def setpath(self, path):
      self._path = path
      
    def send_email(self,attach_list,html=None):
        if self._path is None:
           return " Please set the path to email object"
     
        msg = MIMEMultipart('alternative')
        msg['Subject'] = self._subject
        msg['From'] = self._from
        msg['To'] = self._to

        if html:
           body = MIMEText(html, 'html')
           msg.attach(body)
        
        for _file in attach_list:
             fp= open(self._path+'/'+_file, 'rb')
             a=fp.read().rstrip()
             attachment = MIMEText(a)
             fp.close()
             attachment.add_header('Content-Disposition', 'attachment', filename=_file) 
             msg.attach(attachment)
         
        
         
        s = smtplib.SMTP(self._smtp)
        s.sendmail(self._from, self._to, msg.as_string())
        
        s.quit()
        print " Email has been successfully delivered"