# !/bin/sh
#
# Creates a directory for external libraries and installs dependencies as such:
#
# main
# |--lib
#     |--dependency_1
#     |--dependency_2
#     |--...

echo "Creating directory for external libraries..."
mkdir -v main/lib

mkdir -v tmp
cd tmp

echo "Installing dependencies..."
git clone https://github.com/d99kris/rapidcsv --branch v8.90
cp -v rapidcsv/src/rapidcsv.h ../main/lib/

git clone https://github.com/jarro2783/cxxopts --branch v3.3.1
cp -v cxxopts/include/cxxopts.hpp ../main/lib/

echo "Cleaning up..."
cd ..
rm -rf tmp

echo "Done."
