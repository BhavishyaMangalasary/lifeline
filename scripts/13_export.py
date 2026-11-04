import sys

sys.path.insert(0, "src")

from lifeline.geo.export import write_tile

for a in sys.argv[1:]:
    print(write_tile(int(a)))