echo "Start VCAN0 at 500kB"

ip link add dev vcan0 type vcan
#ip link set vcan1 type vcan bitrate 500000 restart-ms 100
ip link set vcan0 up
