# install build-essential (gcc and g++ included) and gfortran
echo "12345" | sudo DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential gfortran

# mount the SPEC2017 ISO file and install SPEC to the disk image
mkdir /home/gem5/mnt
mount -o loop -t iso9660 /home/gem5/cpu2017-1.1.0.iso /home/gem5/mnt
mkdir /home/gem5/spec2017
echo "y" | /home/gem5/mnt/install.sh -d /home/gem5/spec2017 -u linux-x86_64
cd /home/gem5/spec2017
. /home/gem5/mnt/shrc
umount /home/gem5/mnt
rm -f /home/gem5/cpu2017-1.1.0.iso

# use the example config as the template 
cp /home/gem5/spec2017/config/Example-gcc-linux-x86.cfg /home/gem5/spec2017/config/myconfig.x86.cfg

# Use sed command to replace the default gcc_dir
sed -i "s/\/opt\/rh\/devtoolset-7\/root\/usr/\/usr/g" /home/gem5/spec2017/config/myconfig.x86.cfg

# Use sed command to remove the march=native flag when compiling
sed -i "s/-march=native//g" /home/gem5/spec2017/config/myconfig.x86.cfg

# build all SPEC workloads
runcpu --config=myconfig.x86.cfg --action=build all
