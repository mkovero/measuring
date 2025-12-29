#!/bin/bash

MEASUREMENT=$(jack_lsp |awk '/measure/ {print $1}')
REFERENCE=$(jack_lsp |awk '/reference/ {print $1}')
GENERATOR=$(jack_lsp |awk '/OpenSoundMeter:out/ {print $1}')
REFL=$(jack_lsp | awk '/capture_AUX2$/')
REFR=$(jack_lsp | awk '/capture_AUX3$/')
INL=$(jack_lsp | awk '/capture_AUX0$/')
INR=$(jack_lsp | awk '/capture_AUX1$/')
HEADL=$(jack_lsp | awk '/playback_AUX2$/')
HEADR=$(jack_lsp | awk '/playback_AUX3$/')
OUTL=$(jack_lsp | awk '/playback_AUX0$/')
OUTR=$(jack_lsp | awk '/playback_AUX1$/')
USEXLRREFERENCE="0" #cli parameter

function CheckOSM() {
if [ ! $(pidof OpenSoundMeter) ]; then
  echo "OSM not running, so we do not also."
  exit 1
fi
jack_lsp|grep -iq OpenSoundMeter
if [ ! $? -eq 0 ]; then
  echo "OSM is running but Jack is not initialized. Exiting.."
  exit 2
fi

if [ ! -z $MEASUREMENT ]; then 
  echo Found OSM measurement: $MEASUREMENT 
fi
if [ ! -z $REFERENCE ]; then 
  echo Found OSM reference: $REFERENCE
fi
if [ ! -z $GENERATOR ]; then
  echo Found OSM gen: $GENERATOR
fi
}

function DisablePhantom() {
if [ $1 -eq 1 ]; then 
  amixer  -c 1 set 'Mic-AN1 48V' off
  echo "AN1 phantom off"
fi
if [ $1 -eq 2 ]; then
  amixer -c 1 set 'Mic-AN2 48V' off
  echo "AN2 phantom off"
fi
}

function EnablePhantom() {
if [ $1 -eq 1 ]; then 
  amixer -c 1 set 'Mic-AN1 48V' on
  echo "AN1 phantom on"
fi
if [ $1 -eq 2 ]; then
  amixer -c 1 set 'Mic-AN2 48V' on
  echo "AN2 phantom on"
fi
}

function ResetPhantom() {
read -p "I'M GOING TO TURN PHANTOM POWER ON AT THE FIRST MIC INPUT (MEAS). THIS IS YOUR LAST CHANCE TO UNDERSTAND WHAT IS HAPPENING."
DisablePhantom 1
DisablePhantom 2
EnablePhantom 1
}

function GeneratorTo() {
  echo "Patching $GENERATOR -> $1"
  jack_connect "$GENERATOR" "$1" 
  if [ $? -gt 0 ]; then
    echo "Problem patching generator?"
  fi
}

function MeasureFrom() {
  echo "Patching $1 -> $MEASUREMENT"
  jack_connect "$1" "$MEASUREMENT"
  if [ $? -gt 0 ]; then
    echo "Problem patching measurement?"
  fi
}

function ReferenceFrom() {
  echo "Patching $1 -> $REFERENCE"
  jack_connect "$1" "$REFERENCE"
  if [ $? -gt 0 ]; then
    echo "Problem patching reference?"
  fi
}
function DisconnectFrom() {
  jack_disconnect "$1" "$2" 2>/dev/null
  if [ $? -eq 0 ]; then
    echo "Succesfully disconnected $1 from $2"
  fi
}

function ConnectGenerator() {
GeneratorTo "$HEADR"
GeneratorTo "$HEADL"
GeneratorTo "$OUTL"
GeneratorTo "$OUTR"
}
function DisconnectGenerator() {
DisconnectFrom "$GENERATOR" "$HEADR"
DisconnectFrom "$GENERATOR" "$HEADL"
DisconnectFrom "$GENERATOR" "$OUTL"
DisconnectFrom "$GENERATOR" "$OUTR"
}

function ConnectReference() {
if [ $USEXLRREFERENCE -gt 0 ]; then
ReferenceFrom "$INR"
else 
ReferenceFrom "$REFL"
fi
}
function DisconnectReference() {
if [ $USEXLRREFERENCE -gt 0 ]; then
DisconnectFrom "$REFERENCE" "$INR"
else
DisconnectFrom "$REFERENCE" "$REFL"
fi
}

function ConnectMeasurement() {
if [ $USEXLRREFERENCE -gt 0 ]; then
MeasureFrom "$INL"
else
MeasureFrom "$INL"
MeasureFrom "$INR"
fi
}

function DisconnectMeasurement() {
if [ $USEXLRREFERENCE -gt 0 ]; then
DisconnectFrom "$MEASUREMENT" "$INL"
else
DisconnectFrom "$MEASUREMENT" "$INL"
DisconnectFrom "$MEASUREMENT" "$INR"
fi
}

function ConnectDefault() {
 CheckOSM
 ConnectGenerator
 ConnectReference
 ConnectMeasurement
}

function DisconnectDefault() {
 DisconnectGenerator
 DisconnectReference
 DisconnectMeasurement
}

function DefaultInputGain() {
  amixer -c 1 set 'Mic-AN1 Gain' 1
  amixer -c 1 set 'Mic-AN2 Gain' 1
  amixer -c 1 set 'Mic-AN1 Gain' 0
  amixer -c 1 set 'Mic-AN2 Gain' 0
  amixer -c 1 set 'Line-IN3 Sens.' +4dBu
  amixer -c 1 set 'Line-IN4 Sens.' +4dBu
  amixer -c 1 set 'Line-IN3 Gain' 1
  amixer -c 1 set 'Line-IN4 Gain' 1
  amixer -c 1 set 'Line-IN3 Gain' 0
  amixer -c 1 set 'Line-IN4 Gain' 0
  amixer -c 1 set 'Mic-AN1 PAD' on
  amixer -c 1 set 'Mic-AN2 PAD' on
  amixer -c 1 set 'Mic-AN1 PAD' off
  amixer -c 1 set 'Mic-AN2 PAD' off

  for i in $(amixer -c1 |awk '/Main-Out / { print $5}'|awk -F\' '{print $1}'); do 
    amixer -c 1 set "Main-Out $i" 0
  done
  #amixer -c 1 set 'Main-Out AN1',0 32768 # probably not the best idea to max out output volume programmagically
  if [ $USEXLRREFERENCE -gt 0 ]; then 
    amixer -c 1 set 'Main-Out AN2',0 32768
  else
    amixer -c 1 set 'Main-Out PH3',0 16384
    amixer -c 1 set 'Main-Out PH4',0 16384
  fi
}

while getopts "hcdgrmGRMxPpi" opt; do
    case $opt in
	h)
	    echo "-c ConnectDefault"
	    echo "-d Disconnectdefault"
	    echo "-x use XLR IN (INR) as reference"
	    echo "-grm Connect either generator, reference or only measurement"
	    echo "-GRM Disconnect either.."
	    echo "-P enable phantom at startup"
	    echo "-p disable phantom"
	    echo "-i reset input gain"
	    ;;
        c)
	    ConnectDefault
            ;;
        d)
	    DisconnectDefault 
            ;;
	x) 
	    USEXLRREFERENCE="1"
	    ;;
	g)
	    ConnectGenerator
	    ;;
	r)
	    ConnectReference
	    ;;
	m)
	    ConnectMeasurement
	    ;;
        G)
            DisconnectGenerator
            ;;
        R)
            DisconnectReference
            ;;
        M)
            DisconnectMeasurement
            ;;
	P)
	    ResetPhantom
 	    ;;
	p)
	    DisablePhantom 1
	    DisablePhantom 2
	    ;; 
        i) 
	    DefaultInputGain
	    ;;
	*)
            echo "Invalid option"
            exit 1
            ;;
    esac
done
