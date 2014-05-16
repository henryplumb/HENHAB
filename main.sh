#!/bin/bash
 
while [ 1 ]; do
{
raspistill -o -n -q 100 /img/"%Y%m%d%H%M".jpg
sleep 15
}
 
done