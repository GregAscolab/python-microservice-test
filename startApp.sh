#!/bin/bash

python_env_home=/data/ascolab/run_env_python
script_home="$python_env_home/app"
script_name="$script_home/main.py"
script_args=""
pid_file="$script_home/main.pid"

init() {
    echo "Start app..."
    # echo "Start CAN1 at 500kB"
    Start_CAN 1
    ip link set canfd1 type can bitrate 500000 restart-ms 100
    ip link set canfd1 up

    echo "Activate Python venv"
    source $python_env_home/bin/activate
    cd $script_home
}

deinit() {
    echo "Stop app..."
    # echo "Stop CAN1"
    # ip link set canfd1 down
}


# returns a boolean and optionally the pid
running() {
    local status=false
    if [[ -f $pid_file ]]; then
        # check to see it corresponds to the running script
        local pid=$(< "$pid_file")
        local cmdline=/proc/$pid/cmdline
        # you may need to adjust the regexp in the grep command
        if [[ -f $cmdline ]] && grep -q "$script_name" $cmdline; then
            status="true $pid"
        fi
    fi
    echo $status
}

start() {
    echo "starting $script_name"
    init
    if [[ -z "$1" ]]; then
        python $script_name $script_args > /dev/null 2>&1 &
    elif [[ "$1" = "test" ]]; then
        echo "Running test mode..."
        python $script_name $script_args
    else
        echo "Logging output to $1"
        nohup python $script_name $script_args > $1 &
    fi
    echo $! > "$pid_file"
}

stop() {
    # `kill -0 pid` returns successfully if the pid is running, but does not
    # actually kill it.
    echo "Stopping..."
    kill -0 $1 && kill -SIGINT $1
    rm "$pid_file"
    sleep 5
    echo "Deinit..."
    deinit
    echo "Stopped"
}

read running pid < <(running)

case $1 in
    start)
        if $running; then
            echo "$script_name is already running with PID $pid"
        else
            start
        fi
        ;;
    stop)
        if $running; then
            stop $pid
        else
            echo "$script_name is not running"
        fi
        ;;
    restart)
        stop $pid
        start
        ;;
    status)
        if $running; then
            echo "$script_name is running with PID $pid"
        else
            echo "$script_name is not running"
        fi
        ;;
    bench)
        if $running; then
            echo "$script_name is already running with PID $pid"
        else
            echo "Start benchmark application"
            start "bench.log"
            echo "App will be terminated in $2 s"
            sleep $2
            read running pid < <(running)
            stop $pid
        fi
        ;;
    test)
        if $running; then
            echo "$script_name is already running with PID $pid"
        else
            echo "Start application in test mode"
            start "test"
        fi
        ;;
    *)  echo "usage: $0 <start|stop|restart|status|test|bench (sec)>"
        exit
        ;;
esac
