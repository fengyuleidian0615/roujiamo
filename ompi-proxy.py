#!/usr/bin/env python

import re
import socket
import sys
import os
from subprocess import *

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print "usage: ompi-proxy.py <port>"
    sys.exit(1)
  
  port = int(sys.argv[1])
  host = ''
  
  print "Listening on %s:%d" % (host, port)
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind((host, port))
  s.listen(1)
  conn, addr = s.accept()
  print 'Connected by', addr
  data = conn.recv(1024)
  conn.close()
  print "cookie:%s" % data
  p = Popen(data, shell=True, stdout=PIPE)
  p.wait()
  #TODO: Add error handling here
  print p.stdout.read()
  print "orted exits"
  sys.exit(0)

