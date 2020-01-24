# -*- coding: utf-8 -*-
# Copyright (c) 2018 The Regents of the University of California
# All Rights Reserved.
#
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
# Authors: Jason Lowe-Power

from __future__ import print_function

import argparse
import m5
from m5.objects import TimingSimpleCPU, DerivO3CPU
from m5.objects import LTAGE, SimpleMemory
from m5.objects import Root
from m5.objects import *

from system import BaseTestSystem
from system import command_line_args
BranchPredictor = LTAGE

class IntALU(FUDesc):
    opList = [ OpDesc(opClass='IntAlu') ]
    count = 32

class IntMultDiv(FUDesc):
    opList = [ OpDesc(opClass='IntMult', opLat=1),
               OpDesc(opClass='IntDiv', opLat=20, pipelined=False) ]

    # DIV and IDIV instructions in x86 are implemented using a loop which
    # issues division microops.  The latency of these microops should really be
    # one (or a small number) cycle each since each of these computes one bit
    # of the quotient.
    if buildEnv['TARGET_ISA'] in ('x86'):
        opList[1].opLat=1

    count=32

class FP_ALU(FUDesc):
    opList = [ OpDesc(opClass='FloatAdd', opLat=1),
               OpDesc(opClass='FloatCmp', opLat=1),
               OpDesc(opClass='FloatCvt', opLat=1) ]
    count = 32

class FP_MultDiv(FUDesc):
    opList = [ OpDesc(opClass='FloatMult', opLat=1),
               OpDesc(opClass='FloatMultAcc', opLat=1),
               OpDesc(opClass='FloatMisc', opLat=1),
               OpDesc(opClass='FloatDiv', opLat=1, pipelined=False),
               OpDesc(opClass='FloatSqrt', opLat=1, pipelined=False) ]
    count = 32

class SIMD_Unit(FUDesc):
    opList = [ OpDesc(opClass='SimdAdd', opLat=1),
               OpDesc(opClass='SimdAddAcc', opLat=1),
               OpDesc(opClass='SimdAlu', opLat=1),
               OpDesc(opClass='SimdCmp', opLat=1),
               OpDesc(opClass='SimdCvt', opLat=1),
               OpDesc(opClass='SimdMisc', opLat=1),
               OpDesc(opClass='SimdMult', opLat=1),
               OpDesc(opClass='SimdMultAcc', opLat=1),
               OpDesc(opClass='SimdShift', opLat=1),
               OpDesc(opClass='SimdShiftAcc', opLat=1),
               OpDesc(opClass='SimdSqrt', opLat=1),
               OpDesc(opClass='SimdFloatAdd', opLat=1),
               OpDesc(opClass='SimdFloatAlu', opLat=1),
               OpDesc(opClass='SimdFloatCmp', opLat=1),
               OpDesc(opClass='SimdFloatCvt', opLat=1),
               OpDesc(opClass='SimdFloatDiv', opLat=1),
               OpDesc(opClass='SimdFloatMisc', opLat=1),
               OpDesc(opClass='SimdFloatMult', opLat=1),
               OpDesc(opClass='SimdFloatMultAcc', opLat=1),
               OpDesc(opClass='SimdFloatSqrt', opLat=1) ]
    count = 32

class ReadPort(FUDesc):
    opList = [ OpDesc(opClass='MemRead'),
               OpDesc(opClass='FloatMemRead') ]
    count = 32

class WritePort(FUDesc):
    opList = [ OpDesc(opClass='MemWrite'),
               OpDesc(opClass='FloatMemWrite') ]
    count = 32

class RdWrPort(FUDesc):
    opList = [ OpDesc(opClass='MemRead'), OpDesc(opClass='MemWrite'),
               OpDesc(opClass='FloatMemRead'), OpDesc(opClass='FloatMemWrite')]
    count = 32

class IprPort(FUDesc):
    opList = [ OpDesc(opClass='IprAccess', opLat = 1, pipelined = False) ]
    count = 32

class Ideal_FUPool(FUPool):
    FUList = [ IntALU(), IntMultDiv(), FP_ALU(), FP_MultDiv(), ReadPort(),
               SIMD_Unit(), WritePort(), RdWrPort(), IprPort() ]


class O3_W256CPU(DerivO3CPU):
    branchPred = BranchPredictor()
    fuPool = Ideal_FUPool()
    fetchWidth = 32
    decodeWidth = 32
    renameWidth = 32
    dispatchWidth = 32
    issueWidth = 32
    wbWidth = 32
    commitWidth = 32
    squashWidth = 32
    fetchQueueSize = 256
    LQEntries = 250
    SQEntries = 250
    numPhysIntRegs = 256
    numPhysFloatRegs = 256
    numIQEntries = 256
    numROBEntries = 256


class O3_W2KCPU(DerivO3CPU):
    branchPred = BranchPredictor()
    fuPool = Ideal_FUPool()
    fetchWidth = 32
    decodeWidth = 32
    renameWidth = 32
    dispatchWidth = 32
    issueWidth = 32
    wbWidth = 32
    commitWidth = 32
    squashWidth = 32
    fetchQueueSize = 256
    LQEntries = 250
    SQEntries = 250
    numPhysIntRegs = 1024
    numPhysFloatRegs = 1024
    numIQEntries = 2096
    numROBEntries = 2096

class SimpleCPU(TimingSimpleCPU):
    branchPred = BranchPredictor()

class DefaultO3CPU(DerivO3CPU):
    branchPred = BranchPredictor()




# Add more CPUs under test before this
valid_cpus = [SimpleCPU, DefaultO3CPU, O3_W256CPU, O3_W2KCPU]

valid_cpus = {cls.__name__[:-3]:cls for cls in valid_cpus}

class InfMemory(SimpleMemory):
    latency = '0ns'
    bandwidth = '0B/s'

class SingleCycleMemory(SimpleMemory):
    latency = '1ns'
    bandwidth = '0B/s'

class SlowMemory(SimpleMemory):
    latency = '100ns'
    bandwidth = '0B/s'

# Add more Memories under test before this
valid_memories = [InfMemory, SingleCycleMemory, SlowMemory]
valid_memories = {cls.__name__[:-6]:cls for cls in valid_memories}
parser = argparse.ArgumentParser()
parser.add_argument('cpu', choices = valid_cpus.keys())
parser.add_argument('memory_model', choices = valid_memories.keys())
parser.add_argument('binary', type = str, help = "Path to binary to run")
parser.add_argument('--l1i_size',type = str,  help = "CachesizeofL1i")
parser.add_argument('--l1d_size',type = str,  help = "CachesizeofL1d")
parser.add_argument('--l2_size', type = str,  help = "CachesizeofL2")

args  = parser.parse_args()

    #parser.add_argument('binary_input', type = str, help = "Inputs to the binary")

command_line_args(args.l1i_size,args.l1d_size,args.l2_size)

class MySystem(BaseTestSystem):
    _CPUModel = valid_cpus[args.cpu]
    _MemoryModel = None
system = MySystem()
system.setTestBinary(args.binary)
root = Root(full_system = False, system = system)
m5.instantiate()

exit_event = m5.simulate()

if exit_event.getCause() != 'exiting with last active thread context':
    print("Benchmark failed with bad exit cause.")
    print(exit_event.getCause())
    exit(1)
if exit_event.getCode() != 0:
    print("Benchmark failed with bad exit code.")
    print("Exit code {}".format(exit_event.getCode()))
    exit(1)

print("{} ms".format(m5.curTick()/1e9))
