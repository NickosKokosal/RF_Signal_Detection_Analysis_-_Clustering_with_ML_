# RF Signals Detection, Analysis & Clustering with ML to a Specific Air Object  
# Machine-Learning-based ADS-B Signal Analysis


This project performs RF signal detection and classification from aircraft ADS-B transmissions  
using a Software Defined Radio (RTL-SDR) and the "dump1090" decoder.

The device which been used is the "RTL2832U TV Tuner for Laptop / 
PC with DVB-T Terrestrial Receiver and USB-A connection".
| Chip                                        | Role                                                 |
| ------------------------------------------- | ---------------------------------------------------- |
| RTL2832U                                    | digital interface (USB => PC) & baseband processor    | 
| Tuner chip (usually R820T / R820T2)         | adjusts the reception frequency (24 MHz – 1766 MHz)  |

The R820T2 is acting like the RF tuner:
selects the frequency (e.g. 1090 MHz for ADS-B), demodulates => and sends the I/Q samples to the RTL2832U.
The conversion that I did in practice. 
I didn't change the hardware —
I unlock its capabilities through driver software that makes it work like an SDR.

For the Windows system:
1) Install Zadig
2) Replace the “Bulk-In Interface (Interface 0)” driver with the WinUSB driver
With this way the operating system sees the tuner as an "RTL-SDR dongle" instead of a "TV tuner"!

For the macOS / Linux:
1) Install the rtl-sdr package
2) The librtlsdr driver is talking directly to the chip (bypassing the DVB-T firmware)
3) The dump1090 program is using this I/Q data to decode ADS-B packets

How it became an "RF receiver"?

With this process, the tuner no longer searches for TV channels and in parallel 
is open to any RF frequency within its spectrum (e.g. 24 MHz – 1766 MHz).
After this dump1090 takes the raw RF samples Decodes the Mode-S / ADS-B packets (1090 MHz)
and sends the decoded data (ICAO, altitude, lat/lon, speed, etc.) to port 30003 => where your Python logger is connected.

What does it mean in practice?
A 25€ TV tuner becomes an SDR receiver for RF signals (24 MHz – 1.7 GHz) which is Able to detect:
1) aircraft (ADS-B at 1090 MHz) 
2) AIS from ships (162 MHz)
3) FM radio (88–108 MHz)
4) NOAA weather satellites (~137 MHz)
5) GPS L1 (1.575 GHz)
even RF noise/interference with FFT/Waterfall
While the receiver can tune to 1.575 GHz, GPS signals are extremely weak (below the noise floor). 
To "locate" or decode GPS, a simple TV tuner antenna is not enough. 
You usually need an Active Patch Antenna (with an LNA amplifier) to see the signal.


USAGE from terminal:
1) Start dump1090 server
dump1090 interactive net
2) Run the logger
python adsb_logger_enhanced.py
3) Analyze saved data
python adsb_analyzer_ML.py

## Compliance & Safety — Passive Reception Only

**Attestation:** This project performs *passive RF reception* only. I do **not** transmit or broadcast any RF signals as part of this work.

### What we do
- Use an inexpensive consumer RTL-SDR USB tuner (RTL2832U + R820T/R820T2) configured as an SDR **receiver**.
- Decode *ADS-B* (1090 MHz) packets using `dump1090` and process them offline or stream decoded messages over a local TCP socket for analysis.
- All software and scripts in this repository perform **decoding** and **analysis** only — there is **no transmission** code.

### Hardware / Driver notes
- Device used: RTL2832U tuner (DVB-T USB dongle). No hardware modifications were made.
- On **Windows** the device driver was replaced using *Zadig* with **WinUSB** so the dongle acts as an RTL-SDR receiver only.
- On **macOS/Linux** the `rtl-sdr` library (librtlsdr) is used to access I/Q samples; this library supports reception only for this device.
- We do **not** install or use transmit-capable drivers/software (e.g., no HackRF tools, no bladeRF host programs, no `soapy` transmit modules).

### Legal & safety reminder
- Regulations differ by country. This repository documents passive reception only. If you intend to *transmit*, check and obtain the required licenses/permits from your national communications regulator before doing so.
- For questions on local law, contact your national authority (e.g., FCC in the USA, Ofcom in the UK, EETT/RAE in Greece).
