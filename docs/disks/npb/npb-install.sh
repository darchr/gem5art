# install build-essential (gcc and g++ included) and gfortran

#Compile NPB

echo "12345" | sudo apt-get install build-essential gfortran

cp /home/gem5/NPB3.3-OMP/config/suite.def_C /home/gem5/NPB3.3-OMP/config/suite.def

cd /home/gem5/NPB3.3-OMP/
make suite
