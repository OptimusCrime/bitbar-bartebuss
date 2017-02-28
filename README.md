# BarteBuss BitBar

Simple BitBar plugin that uses the Bartebuss API to output the next few departures from a specified stop in Trondheim depending on what SSID you are currently connected to.

## Installation

Copy the script bartebuss.30s.py to your BitBar plugin directory. Make sure you make it executable. Follow instructions below to set up the script for your needs.

### Find stop id

Find your stop by browsing to [bartebuss.no](bartebuss.no/), find your bus stop and check what ID is written in the URL. For example [bartebuss.no/16011333](http://bartebuss.no/16011333).

### SSID

SSID is the name of the wireless network you are connected to. This needs to match the one in the script, otherwise this plugin will not fetch the correct departures for you. The idea is that you can switch which departures you want to list depending on where you are located.
