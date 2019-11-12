# install build-essential (gcc and g++ included) and gfortran

#Compile NPB 
echo "12345" | sudo apt-get update install build-essential git m4 scons zlib1g zlib1g-dev libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev python-dev pythontexinfolibx11-devlibxext-devxorg-dev 

git clone git@github.com:darchr/parsec-benchmark

cd parsec-benchmark
./get-inputs
source env.sh 
parsecmgmt -a build -p all