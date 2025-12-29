#with 96k
#1024 = 10.7ms, 93.75hz
#512 = 5.33ms, 187.5hz
#256 = 2.67ms, 375hz
#with 48k
#1024 = Temporal resolution = 21.3 ms; FFT bin = ~46.9 Hz.
#512 = 10.7ms, 93.75hz
#256 = 5.33ms, 187.5hz

RATE="48000"
QUANTUM="1024"

pw-metadata -n settings 0 clock.force-quantum $QUANTUM 
pw-metadata -n settings 0 clock.rate $RATE 
PIPEWIRE_LATENCY="$RATE/$QUANTUM" $( hwloc-bind core:2-3 $(chrt -f 80 /home/mui/osm-latest/build/Qt_5_15_16_System-Rel/OpenSoundMeter) )
