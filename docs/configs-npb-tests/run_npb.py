# -*- coding: utf-8 -*-
# Copyright (c) 2019 The Regents of the University of California.
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors: Jason Lowe-Power, Ayaz Akram

""" Script to run NAS parallel benchmarks with gem5.
    The script expects kernel, diskimage, benchmark to run
    and number of cpus as arguments.

    If your application has ROI annotations, this script will count the total
    number of instructions executed in the ROI. It also tracks how much
    wallclock and simulated time.
"""

import os
import sys
import time
import m5
import m5.ticks
from m5.objects import *

sys.path.append('gem5/configs/common/') # For the next line...
import SimpleOpts

from system import MySystem

def writeBenchScript(dir, bench):
    """
    This method creates a script in dir which will be eventually
    passed to the simulated system (to run a specific benchmark
    at bootup).
    """
    file_name = '{}/run_{}'.format(dir, bench)
    bench_file = open(file_name,"w+")
    bench_file.write('/home/gem5/NPB3.3-OMP/bin/{} \n'.format(bench))
    bench_file.write('m5 exit \n')
    bench_file.close()
    return file_name

if __name__ == "__m5_main__":
    (opts, args) = SimpleOpts.parse_args()
    kernel, disk, benchmark, num_cpus = args
    # create the system we are going to simulate
    system = MySystem(kernel, disk, int(num_cpus), opts, no_kvm=False)

    # For workitems to work correctly
    # This will cause the simulator to exit simulation when the first work
    # item is reached and when the first work item is finished.
    system.work_begin_exit_count = 1
    system.work_end_exit_count = 1

    # Create and pass a script to the simulated system to run the reuired
    # benchmark
    system.readfile = writeBenchScript(m5.options.outdir, benchmark)

    # set up the root SimObject and start the simulation
    root = Root(full_system = True, system = system)

    if system.getHostParallel():
        # Required for running kvm on multiple host cores.
        # Uses gem5's parallel event queue feature
        # Note: The simulator is quite picky about this number!
        root.sim_quantum = int(1e9) # 1 ms

    #needed for long running jobs
    m5.disableAllListeners()

    # instantiate all of the objects we've created above
    m5.instantiate()

    globalStart = time.time()


    print("Running the simulation")
    exit_event = m5.simulate()

    # While there is still something to do in the guest keep executing.
    # This is needed since we exit for the ROI begin/end
    foundROI = False
    while exit_event.getCause() != "m5_exit instruction encountered":
        # If the user pressed ctrl-c on the host, then we really should exit
        if exit_event.getCause() == "user interrupt received":
            print("User interrupt. Exiting")
            break

        print("Exited because", exit_event.getCause())

        if exit_event.getCause() == "a thread reached the max instruction count":
          break

        if exit_event.getCause() == "work started count reach":
            start_tick = m5.curTick()
            start_insts = system.totalInsts()
            foundROI = True
        elif exit_event.getCause() == "work items exit count reached":
            end_tick = m5.curTick()
            end_insts = system.totalInsts()

        print("Continuing")
        exit_event = m5.simulate()

    print()
    print("Performance statistics")

    print("Ran a total of", m5.curTick()/1e12, "simulated seconds")
    print("Total wallclock time: %.2fs, %.2f min" % \
                (time.time()-globalStart, (time.time()-globalStart)/60))

    if foundROI:
        print("Simulated time in ROI: %.2fs" % ((end_tick-start_tick)/1e12))
        print("Instructions executed in ROI: %d" % ((end_insts-start_insts)))
