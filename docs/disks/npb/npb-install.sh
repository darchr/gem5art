# install build-essential (gcc and g++ included) and gfortran

#Compile NPB

echo "12345" | sudo apt-get install build-essential gfortran

cd /home/gem5/NPB3.3-OMP/

mkdir bin

make suite HOOKS=1
