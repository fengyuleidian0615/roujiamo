#!/usr/bin/env python
# This script enables user to run OpenMPI on Mesos.

import mesos
from mesos.interface import mesos_pb2
import mesos.native

import os
import errno
import logging
import re
import sys
import time
import math
import threading
import socket
import time
import tempfile

from optparse import OptionParser
from subprocess import *

# Hold the agents/ports to run ompi_proxy.py
# and the orted commands use the 'retry' to
# double check slow/deaf agents
class ProxyInfo():

  def __init__(self):
    self.hosts = ""
    self.ports = 0
    self.open_orte_arg = ""
    self.retry = False

def LaunchOpenRTE(callbacks, enable_retry):
 
  for proxy_info in callbacks:
    if (enable_retry == True and proxy_info.retry != True):
      continue

    chost = proxy_info.host
    cport = proxy_info.port
    open_orte_arg = proxy_info.open_orte_arg

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.info("Connect to host %s port %s" % (chost, cport))
        s.connect((chost, cport))
        s.send(open_orte_arg)
        s.close()
        logging.info("Sent the Open RTE cookies")
    except socket.error, (value,message):
        if s:
            # What's the likehood the proxy we sent out has not been started
            if value == errno.ECONNREFUSED:
              proxy_info.retry = True
            s.close()
        logging.error("Sending the cookie to proxy failed! error:%s %s" % (value, message))

def printMpiexecOutput(p):
  for line in p.stdout:
        print line,

def finalizeagents(callbacks):
  time.sleep(1)
  logging.info("Finalize agents")
  hosts = []

  for proxyinfo in callbacks:
    hosts.append(proxyinfo.host)

  agents = ",".join(hosts)
  cmd = ["mpiexec", "--allow-run-as-root", "-H", str(agents), "-n", str(total_procs)]
  cmd.extend(mpi_program)
  logging.info("Running mpiexec:\n%s" % cmd)
  p = Popen(cmd, stdout=PIPE)

  proxies_args = []
  index = 0
  while True:
    line = p.stdout.readline()
    pos = line.index("orted")
    cmd = line[pos:]
    logging.info("Open TRE cookies:\n%s" % cmd)
    callbacks[index].open_orte_arg = cmd
    index += 1
    if index == total_nodes:
      break

  LaunchOpenRTE(callbacks, False)
  LaunchOpenRTE(callbacks, True)

  logging.info("Done finalizing agents")

  #mpiexec has output once orted is running on slave nodes
  #spawn a thread to catch any outputs.
  t = threading.Thread(target=printMpiexecOutput, args=([p]))
  t.start()

class OmpiScheduler(mesos.interface.Scheduler):

  def __init__(self, options, implicitAcknowledgements):
    self.proxiesLaunched = 0
    self.proxiesRunning = 0
    self.proxiesFinished = 0
    self.options = options
    self.startedExec = False
    self.agents = set()
    self.callbacks = []
    self.finalizeTriggered = False
    self.implicitAcknowledgements = implicitAcknowledgements

  def registered(self, driver, fid, masterInfo):
    logging.info("Registered with framework ID %s" % fid.value)

  def resourceOffers(self, driver, offers):
    for offer in offers:
      if self.proxiesLaunched == total_nodes:
        driver.declineOffer(offer.id)
        continue

      cpus = 0
      mem = 0
      tasks = []

      #Why bother to do this?
      # mpiexec -H will specify list of hosts to invoke processes on.
      # And the hosts expects no duplicated ones.
      # From Mesos side, this scenario will be rare when cluster scales.
      if offer.hostname in self.agents:
        logging.info("Declining offer: offer from slave already scheduled")
        driver.declineOffer(offer.id)


      logging.info("receiving offering....")
      for resource in offer.resources:
        if resource.name == "cpus":
          cpus = resource.scalar.value
        elif resource.name == "mem":
          mem = resource.scalar.value
        elif resource.name == "ports":
          port = resource.ranges.range[0].begin

      if cpus < cores_per_node or mem < mem_per_node:
        logging.info("Declining offer due to too few resources")
        driver.declineOffer(offer.id)
      else:
        tid = self.proxiesLaunched
        self.proxiesLaunched += 1

        logging.info("Launching proxy on offer %s from %s" % (offer.id, offer.hostname))
        task = mesos_pb2.TaskInfo()
        task.task_id.value = str(tid)
        task.slave_id.value = offer.slave_id.value
        task.name = "task %d " % tid

        cpus = task.resources.add()
        cpus.name = "cpus"
        cpus.type = mesos_pb2.Value.SCALAR
        cpus.scalar.value = cores_per_node

        mem = task.resources.add()
        mem.name = "mem"
        mem.type = mesos_pb2.Value.SCALAR
        mem.scalar.value = mem_per_node

        ports = task.resources.add()
        ports.name = "ports"
        ports.type = mesos_pb2.Value.RANGES
        r = ports.ranges.range.add()
        r.begin = port
        r.end = port

        if options.docker_image != None:
          task.container.type = mesos_pb2.ContainerInfo.DOCKER
          task.container.docker.image = options.docker_image 
          #with open ("ompi-proxy.py", "r") as myfile:
          #    data=myfile.read()
          #TODO: why not pack ompi-proxy.py in command.value, since
          #      it's small enough and not depend on any external DFS.
          #      Make it self-contained.
          task.command.value = "python /ws/ompi-proxy.py %d" % port
    
        tasks.append(task)
        logging.info("Replying to offer: launching proxy %d on host %s" % (tid, offer.hostname))
        logging.info("Call-back at %s:%d" % (offer.hostname, port))

        proxy = ProxyInfo()
        proxy.host = offer.hostname
        proxy.port = port
        self.callbacks.append(proxy)
        self.agents.add(offer.hostname)

        driver.launchTasks(offer.id, tasks)

  def statusUpdate(self, driver, update):
    if (update.state == mesos_pb2.TASK_FAILED or
        update.state == mesos_pb2.TASK_KILLED or
        update.state == mesos_pb2.TASK_LOST):
      logging.error("A task finished unexpectedly: " + update.message)
      driver.stop()

    if (update.state == mesos_pb2.TASK_RUNNING):
      self.proxiesRunning += 1
      # Trigger real launch when threshold is met.
      if self.proxiesRunning >= total_nodes and not self.finalizeTriggered:
        self.finalizeTriggered = True
        threading.Thread(target = finalizeagents, args = ([self.callbacks])).start()

    if (update.state == mesos_pb2.TASK_FINISHED):
      self.proxiesFinished += 1
      if self.proxiesFinished == total_nodes:
        logging.info("All processes done, exiting")
        driver.stop()

    if not self.implicitAcknowledgements:
      driver.acknowledgeStatusUpdate(update)


  def offerRescinded(self, driver, offer_id):
    logging.info("Offer %s rescinded" % offer_id)


if __name__ == "__main__":
  parser = OptionParser(usage="Usage: %prog [options] mesos_master mpi_program")
  parser.disable_interspersed_args()
  parser.add_option("-N", "--nodes",
                    help="number of nodes to run processes (default 1)",
                    dest="nodes", type="int", default=1)
  parser.add_option("-n", "--num",
                    help="total number of MPI processes (default 1)",
                    dest="procs", type="int", default=1)
  parser.add_option("-c", "--cpus-per-task",
                    help="number of cores per MPI process (default 1)",
                    dest="cores", type="int", default=1)
  parser.add_option("-m","--mem",
                    help="number of MB of memory per MPI process (default 1GB)",
                    dest="mem", type="int", default=1024)
  parser.add_option("--name",
                    help="framework name", dest="name", type="string")
  parser.add_option("--docker_image",
                    help="Docker image", dest="docker_image", type="string")
  parser.add_option("--role",
                    help="framework role", dest="role", type="string")
  parser.add_option("-v", action="store_true", dest="verbose")

  # Add options to configure cpus and mem.
  (options,args) = parser.parse_args()
  if len(args) < 2:
    print >> sys.stderr, "At least two parameters required."
    print >> sys.stderr, "Use --help to show usage."
    exit(2)


  if options.verbose == True:
    logging.basicConfig(level=logging.INFO)

  total_procs = options.procs
  total_nodes = options.nodes
  cores = options.cores
  procs_per_node = math.ceil(total_procs / total_nodes)
  cores_per_node = procs_per_node * cores
  mem_per_node = options.mem
  mpi_program = args[1:]
  
  logging.info("Connecting to Mesos master %s" % args[0])
  logging.info("Total processes %d" % total_procs)
  logging.info("Total nodes %d" % total_nodes)
  logging.info("Procs per node %d" % procs_per_node)
  logging.info("Cores per node %d" % cores_per_node)

  implicitAcknowledgements = 1
  if os.getenv("MESOS_EXPLICIT_ACKNOWLEDGEMENTS"):
    print "Enabling explicit status update acknowledgements"
    implicitAcknowledgements = 0

  scheduler = OmpiScheduler(options, implicitAcknowledgements)

  framework = mesos_pb2.FrameworkInfo()
  #User name filled by Mesos as default
  framework.user = ""
  framework.checkpoint = True

  if options.role is not None:
    framework.role= options.role

  if options.name is not None:
    framework.name = options.name
  else:
    framework.name = "Open MPI: %s" % mpi_program[0]

  #TODO: Add credential support here
  driver = mesos.native.MesosSchedulerDriver(
    scheduler,
    framework,
    args[0],
    implicitAcknowledgements)

  status = 0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1

  # Ensure that the driver process terminates.
  driver.stop();

  sys.exit(status)
