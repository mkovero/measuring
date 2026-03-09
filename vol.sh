#!/bin/bash -x
        amixer -c 1 set 'Main-Out AN1',0 $@ 
        amixer -c 1 set 'Main-Out AN2',0 $@
        amixer -c 1 set 'Main-Out PH3',0 $@
        amixer -c 1 set 'Main-Out PH4',0 $@
