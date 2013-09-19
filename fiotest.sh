#!/bin/bash

BASEDIR=/root/fiotest

function measure() {
  size=$1
  direction=$2
  depth=$3
  isdirect=$4
  filesize=$5

  testname="${size}_${direction}_${depth}"
  echo "${testname} start: `date`" > ${BASEDIR}/result/fio_${testname}.txt

  cmd="fio -name=${testname} -filename=${BASEDIR}/data/fiotest -rw=${random}${direction} -bs=${size} -iodepth=${depth} -direct=${isdirect} -runtime=180 -size=${filesize} >> ${BASEDIR}/result/fio_${testname}.txt"
  echo "${cmd}"
  fio -name=${testname} -filename=${BASEDIR}/data/fiotest -rw=${random}${direction} -bs=${size} -iodepth=${depth} -direct=${isdirect} -runtime=180 -size=${filesize} >> ${BASEDIR}/result/fio_${testname}.txt

  echo "${testname} finish: `date`" >> ${BASEDIR}/result/fio_${testname}.txt
}

function dotest() {
  size=$1
  random="rand"
  iodepth="1"
  isdirect="1"
  filesize=3g

  if [ "${size}" == "11" ]; then
    isdirect=0
    filesize=1g
  elif [ "${size}" == "512" ]; then
    filesize=1g
    iodepth="1 32"
  elif [ "${size}" == "4k" ]; then
    iodepth="1 32"
  elif [ "${size}" == "32k" ]; then
    :
  elif [ "${size}" == "512k" ]; then
    :
  elif [ "${size}" == "1m" ]; then
    random=""
  fi

  for direction in read write; do
    for depth in ${iodepth}; do
      measure ${size} ${direction} ${depth} ${isdirect} ${filesize}
    done
  done
}

iostat -mx 5 | awk '{print strftime("%H:%M:%S"),$0}' > ${BASEDIR}/result/iostat.txt &
top -bc -d5 | awk '{print strftime("%H:%M:%S"),$0}' > ${BASEDIR}/result/top.txt &
for size in 11 512 4k 32k 512k 1m; do
  dotest ${size}
done
ps ax | grep "top " | grep -v grep | awk '{print $1}' | xargs kill
ps ax | grep "iostat " | grep -v grep | awk '{print $1}' | xargs kill
