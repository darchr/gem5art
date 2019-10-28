#!/bin/bash
echo 'Post Installation Started'

mv /home/gem5/serial-getty@.service /lib/systemd/system/

mv /home/gem5/m5 /sbin
ln -s /sbin/m5 /sbin/gem5

mv /home/gem5/exit.sh /root/

# Add exit script to bashrc
echo "/root/exit.sh" >> /root/.bashrc

echo 'Post Installation Done'
