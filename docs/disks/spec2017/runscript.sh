#!/bin/sh

cd /home/gem5/spec2017
source shrc
m5 readfile > workloads
echo "Done reading workloads"
if [ -s workloads ]; then
    # if the file is not empty, run spec with the parameters
    echo "Workload detected"
    echo "Reset stats"
    m5 exit

    # run the commands
    read -r workload size m5filespath < workloads
    runcpu --size $size --iterations 1 --config myconfig.x86.cfg --noreportable --nobuild $workload
    m5 exit
    
    # copy the SPEC result files to host
    for filepath in /home/gem5/spec2017/result/*; do
        filename=$(basename $filepath)
        m5 writefile $filepath $m5filespath/$filename
    done
    m5 exit
else
    echo "Couldn't find any workload"
    m5 exit
    m5 exit
    m5 exit
fi
# otherwise, drop to the terminal
