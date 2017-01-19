#!/usr/bin/env python

import sys
import os
from termcolor import colored, cprint
from fabric.api import *
from fabric.tasks import execute
import getpass
import jinja2

codepath = os.getcwd()
jinjadir = codepath+'/jinja2temps/'
outputdir = codepath+'/output/'

templateLoader = jinja2.FileSystemLoader( searchpath=jinjadir )
templateEnv = jinja2.Environment( loader=templateLoader )

TEMPVSFCONF = 'vsftpd.conf.j2'

tempvsf = templateEnv.get_template( TEMPVSFCONF )

ipaddress = colored('IP address', 'green', attrs=['bold', 'underline'])
username = colored('username', 'green', attrs=['bold', 'underline'])
password = colored('password', 'magenta', attrs=['bold', 'underline'])
successfully = colored('successfully', 'green', attrs=['bold', 'underline'])
centos  = colored('CentOS', 'yellow', attrs=['bold', 'underline'])
vsftpd = colored('Vsftpd', 'yellow', attrs=['bold', 'underline'])
enter = colored('Enter', 'cyan', attrs=['bold', 'underline'])

print('Script install and configure '+vsftpd+' with FTPS.')
print('It needs '+ipaddress+', '+username+' and '+password+' to start process.')
env.host_string = raw_input('Please enter '+ipaddress+' of '+vsftpd+': ')
env.user = raw_input('Please enter '+username+' for UNIX/Linux server: ')
env.password = getpass.getpass('Please enter '+password+' for '+vsftpd+': ')
ftpuser = raw_input('Please '+enter+' new username for FTP: ')

def tempconfiger(ipaddress):
    tempvsfVars = { "ipaddress" : ipaddress }

    outputvsfText = tempvsf.render( tempvsfVars )

    with open(outputdir+'vsftpd.conf', 'wb') as vfsout:
        vfsout.write(outputvsfText)

def ftpuser_creds():
    print('')
    print('Please remember entered FTP '+password+'. This '+password+' will be used to connect to the server with Filezilla client.')
    print('')
    global ftpuspass
    ftpuspass = getpass.getpass('  '+enter+' '+password+' for '+ftpuser+': ')
    global ftpuspass1
    ftpuspass1 = getpass.getpass('  Repeat '+password+' for '+ftpuser+': ')
    print('')

    while ftpuspass != ftpuspass1:
        print('')
        print(' Entered passwords must be the same. Please '+enter+' passwords again. ')
        ftpuspass = getpass.getpass('  '+enter+' '+password+' for '+ftpuser+': ')
        ftpuspass1 = getpass.getpass('  Repeat '+password+' for '+ftpuser+': ')

        if ftpuspass == ftpuspass1:
            print('')
            print(' The '+password+' set successfully!')
            break
        print(' Entered passwords must be the same. Please '+enter+' passwords again. ')


def variables():
    global osver
    osver = run('uname -s')
    global lintype
    lintype = run('cat /etc/centos-release | awk \'{ print $1 }\'')
    global getcosver
    getcosver = run('rpm -q --queryformat \'%{VERSION}\' centos-release')
    global netcards
    netcards = run('cat /proc/net/dev | egrep -v \'Inter|face|lo\' | cut -f1 -d\':\'')
    global extcard
    extcard = run('ip a | grep '+env.host_string+' | awk \'{ print $NF }\'')
    global ipaddress
    ipaddress = run('ifconfig '+extcard+' | grep \'inet \' | awk \'{ print $2 }\'')

servicelist = ['vsftpd', 'network']

def prints(extcard):
    print(' To open VSFTPD port with in firewalld you must '+enter+' network card name.')
    print('')
    print(' Script connected network card: '+extcard+'')
    print('')
    print(' Network card list: '+netcards+'')
    print('')
    global entcard
    entcard = raw_input(' Enter network card name to open port in firewall: ')


def exec_comms(ftpuser, ftpuspass):
    commands = ['yum update -y; yum -y install epel-release',
            'yum -y install net-tools bind-utils nload iftop wget git lftp htop tcpdump ntpdate vsftpd',
            'mkdir /etc/ssl/private',
            'ntpdate 0.asia.pool.ntp.org',
            'openssl req -x509 -nodes -days 365 -newkey rsa:1024 -keyout /etc/ssl/private/vsftpd.pem -out /etc/ssl/private/vsftpd.pem -subj "/C=AZ/ST=Baku/L=Khatai/O=OpSO/OU=IT Department/CN=vsftpd.lan"', 
            'adduser '+ftpuser+'',
            'echo "'+ftpuspass+'" | passwd --stdin '+ftpuser+'',]

    for comm in commands:
        run(comm)


def fire_exec_comms(entcard):
    firecommands = ['systemctl stop NetworkManager; systemctl disable NetworkManager',
            'setsebool -P allow_ftpd_full_access 1',
            'systemctl start firewalld ; systemctl enable firewalld',
            'echo NM_CONTROLLED=no >> /etc/sysconfig/network-scripts/ifcfg-'+entcard+'',
            'echo ZONE=external >> /etc/sysconfig/network-scripts/ifcfg-'+entcard+'',
            'firewall-cmd --set-default-zone=external',
            'firewall-cmd --permanent --zone=external --add-service={dns,ntp,ssh,ftp}',
            'firewall-cmd --permanent --add-port={21/tcp,40000-41000/tcp}',
            'firewall-cmd --permanent --zone=external --change-interface='+entcard+'',
            'firewall-cmd --complete-reload',]

    for firecom in firecommands:
        run(firecom)


def put_func():
    put(outputdir+'vsftpd.conf', '/etc/vsftpd/vsftpd.conf')

def check_service_vars():
    global vsftpdservice
    vsftpdservice = run('ps waux | grep vsftpd | grep -v grep | awk \'{ print $11 }\'')

with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
    variables()

    if osver == 'Linux' and lintype == 'CentOS':
        print('')
        print('OS type Linux '+centos+'.')

        if getcosver == '6':
            print('Version is "6"!')
        elif getcosver == '7':
            print('Version is "7"!')
            print('')

        print('')

        ftpuser_creds()

        print('  Be patient script will install and configure all needed packages!!!')
        exec_comms(ftpuser, ftpuspass)
        tempconfiger(ipaddress)
        put_func()
        prints(extcard)
        fire_exec_comms(entcard)

        for service in servicelist:
            run('systemctl restart '+service+'; systemctl enable '+service+'')

        check_service_vars()

        if vsftpdservice == '/usr/sbin/vsftpd':
            print('Vsftpd is '+successfully+' installed and configured!')
            sys.exit()
        else:
            print('There is some problem with installation. Vsftpd is not configured properly!!!')
            print('Please check SeLinux, firewalld!!!')
            sys.exit()
