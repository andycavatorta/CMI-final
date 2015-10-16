#!/usr/bin/env python
# modified from http://elinux.org/RPi_Email_IP_On_Boot_Debian
# modified from Don Southard
import subprocess
import smtplib
import socket
import time
from email.mime.text import MIMEText
import datetime
import urllib2

def main(to_field, from_field, password_field, SMTP_field, SMTP_port):
	# Change to your own account information
	to = to_field
	gmail_user = from_field
	gmail_password = password_field
	smtpserver = smtplib.SMTP(SMTP_field, SMTP_port)
	smtpserver.ehlo()
	smtpserver.starttls()
	smtpserver.ehlo
	smtpserver.login(gmail_user, gmail_password)
	today = datetime.date.today()
	# Very Linux Specific
	arg='ip route list'
	p=subprocess.Popen(arg,shell=True,stdout=subprocess.PIPE)
	data = p.communicate()
	split_data = data[0].split()
	print "split_data",split_data
	ipaddr = split_data[split_data.index('src')+1]
	extipaddr = urllib2.urlopen("http://icanhazip.com").read()
	my_ip = 'Local address: %s\nExternal address: %s' %  (ipaddr, extipaddr)
	msg = MIMEText(my_ip)
	msg['Subject'] = 'ID=03 IP For RaspberryPi on %s' % today.strftime('%b %d %Y')
	msg['From'] = gmail_user
	msg['To'] = to
	time.sleep(5)
	smtpserver.sendmail(gmail_user, [to], msg.as_string())
	smtpserver.quit()


