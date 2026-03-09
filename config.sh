
#!/usr/bin/env bash

MEASUREMENT=$(jack_lsp | awk '/measure/ {print $1}')
REFERENCE=$(jack_lsp | awk '/reference/ {print $1}')
GENERATOR=$(jack_lsp | awk '/OpenSoundMeter:out/ {print $1}')
REFL=$(jack_lsp | awk '/capture_AUX2$/')
REFR=$(jack_lsp | awk '/capture_AUX3$/')
INL=$(jack_lsp | awk '/capture_AUX0$/')
INR=$(jack_lsp | awk '/capture_AUX1$/')
HEADL=$(jack_lsp | awk '/playback_AUX2$/')
HEADR=$(jack_lsp | awk '/playback_AUX3$/')
OUTL=$(jack_lsp | awk '/playback_AUX0$/')
OUTR=$(jack_lsp | awk '/playback_AUX1$/')
USEXLRREFERENCE="0" #cli parameter
