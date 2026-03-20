#!/usr/bin/env bash 
#set -x
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
source "$SCRIPT_DIR/functions.sh"

MEASUREMENT=$(jack_lsp | awk '/measure/ {print $1}')
REFERENCE=$(jack_lsp | awk '/reference/ {print $1}')
GENERATOR=$(jack_lsp | awk '/OpenSoundMeter-*.*:out/ { print $1 }')
REFL=$(jack_lsp | awk '/capture_AUX2$/')
REFR=$(jack_lsp | awk '/capture_AUX3$/')
INL=$(jack_lsp | awk '/capture_AUX0$/')
INR=$(jack_lsp | awk '/capture_AUX1$/')
HEADL=$(jack_lsp | awk '/playback_AUX2$/')
HEADR=$(jack_lsp | awk '/playback_AUX3$/')
OUTL=$(jack_lsp | awk '/playback_AUX0$/')
OUTR=$(jack_lsp | awk '/playback_AUX1$/')
USEXLRREFERENCE="1" #cli parameter



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
		export USEXLRREFERENCE="1"
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
