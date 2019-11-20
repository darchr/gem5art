cd /home/gem5/
echo "12345" | sudo apt update

# Allowing services to restart while updating some 
# libraries.
sudo apt install -y debconf-utils
sudo debconf-get-selections | grep restart-without-asking > libs.txt
sed -i 's/false/true/g' libs.txt
while read line; do echo $line | sudo debconf-set-selections; done < libs.txt
sudo rm libs.txt
##

# Installing packages needed to build PARSEC
sudo apt install -y build-essential 
sudo apt install -y m4 
sudo apt install -y git  
sudo apt install -y python
sudo apt install -y python-dev
sudo apt install -y gettext
sudo apt install -y libx11-dev 
sudo apt install -y libxext-dev 
sudo apt install -y xorg-dev 
sudo apt install -y unzip
sudo apt install -y texinfo
## 

# Building PARSEC
unzip parsec-benchmark.zip 
cd parsec-benchmark
source env.sh 
parsecmgmt -a build -p all
##