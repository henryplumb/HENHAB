#!/bin/bash
 
while [ 1 ]; do
{
raspistill -o /images/`date +"%Y%m%d%H%M"`.jpg
sleep 30
}
 
done