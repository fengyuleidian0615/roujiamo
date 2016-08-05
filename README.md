
# Roujiamo
A framework to run ![OpenMPI](https://www.open-mpi.org/) on ![Mesos](http://mesos.apache.org/)

## How to deploy
### Deploy Mesos cluster

One Master with one slave is enough to run, follow the ![link](http://mesos.apache.org/documentation/latest/getting-started/
) for how to setup Mesos.

After the build/install, set MESOS_PROJECT enviroment.

 `export MESOS_PROJECT=/home/ws/mesos-dev`

###  Build Docker image for mpiexec
  Before the building, setup http proxy and DNS server correctly, refer Dockerfile.* for details.
  
  `docker build -f Dockerfile.mpiexec -t ubuntu:mpiexec  .`

###  Build Docker image for orted

   `docker build -f Dockerfile.orted -t ubuntu:orted  .`

   After the building, save and reload Docker image into Mesos
   slave node.

   On Mesos master:
   
   `docker save ubuntu:orted > ubuntu-orted.tar`

   On Mesos slave:
   
   `docker load < ubuntu-orted.tar`


## Run the demo

`docker run --net=host -v $MESOS_PROJECT:$MESOS_PROJECT  -ti ubuntu:mpiexec /ws/ompirun.sh $MESOS_PROJECT 192.168.1.110:5050`

    Find eggs in /home/ws/mesos-dev
    INFO:root:Connecting to Mesos master master@192.168.1.110:5050
    INFO:root:Total processes 4
    INFO:root:Total nodes 1
    INFO:root:Procs per node 4
    INFO:root:Cores per node 4
    I0806 18:54:50.582767    45 sched.cpp:226] Version: 1.1.0
    I0806 18:54:50.587851    48 sched.cpp:330] New master detected at master@192.168.1.110:5050
    I0806 18:54:50.588016    48 sched.cpp:341] No credentials provided. Attempting to register without authentication
    I0806 18:54:50.589655    48 sched.cpp:743] Framework registered with 1dd61f94-e33e-49cd-9163-e2df4aa1e74e-0002
    INFO:root:Registered with framework ID 1dd61f94-e33e-49cd-9163-e2df4aa1e74e-0002
    INFO:root:receiving offering....
    INFO:root:Launching proxy on offer value: "1dd61f94-e33e-49cd-9163-e2df4aa1e74e-O15"
     from mesos-ompi-slave.bj.intel.com
    INFO:root:Replying to offer: launching proxy 0 on host mesos-ompi-slave.bj.intel.com
    INFO:root:Call-back at mesos-ompi-slave.bj.intel.com:31000
    INFO:root:Finalize agents
    INFO:root:Running mpiexec:
    ['mpiexec', '--allow-run-as-root', '-H', 'mesos-ompi-slave.bj.intel.com', '-n', '4', '/ws/a.out']
    INFO:root:Open TRE cookies:
    orted --hnp-topo-sig 0N:1S:1L3:4L2:4L1:4C:8H:x86_64 -mca ess "env" -mca ess_base_jobid "1326972928" -mca ess_base_vpid 1 -mca ess_base_num_procs "2" -mca orte_hnp_uri "1326972928.0;usock;tcp://192.168.1.110:37793" -mca plm "rsh"

    INFO:root:Connect to host mesos-ompi-slave.bj.intel.com port 31000
    INFO:root:Sent the Open RTE cookies
    INFO:root:Done finalizing agents
    Hello world from processor mesos-ompi-slave, rank 0 out of 4 processors
    Hello world from processor mesos-ompi-slave, rank 1 out of 4 processors
    Hello world from processor mesos-ompi-slave, rank 2 out of 4 processors
    Hello world from processor mesos-ompi-slave, rank 3 out of 4 processors
    INFO:root:All processes done, exiting
    I0806 18:54:53.327512    53 sched.cpp:1987] Asked to stop the driver
    I0806 18:54:53.327672    53 sched.cpp:1187] Stopping framework 1dd61f94-e33e-49cd-9163-e2df4aa1e74e-0002
    I0806 18:54:53.328322    45 sched.cpp:1987] Asked to stop the driver

## Dependcies
* Need a small ![patch](https://github.com/fengyuleidian0615/ompi/commit/18607eb3b11a6c8b147f23ace6584741188d5d57) for ompi to retrieve orted args

## TODO
* Add more functionality
* Introduce `Mannual lancher` to OpenMPI

