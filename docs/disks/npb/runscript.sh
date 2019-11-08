#!/bin/sh

m5 readfile > script.sh
if [ -s script.sh ]; then
    # if the file is not empty, execute it
    chmod +x script.sh
    ./script.sh
    m5 exit
fi
# otherwise, drop to the terminal
