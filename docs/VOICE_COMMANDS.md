# NIGHTWATCH Voice Commands Reference

This document provides a comprehensive reference for voice commands supported by the NIGHTWATCH telescope control system. Commands are processed using natural language understanding, so exact phrasing is flexible.

## Quick Reference

| Category | Example Command |
|----------|-----------------|
| **Mount** | "Go to Mars" / "Park the telescope" |
| **Catalog** | "What is M31?" / "Find galaxies in Orion" |
| **Ephemeris** | "Where is Jupiter?" / "Is it dark?" |
| **Weather** | "What's the weather?" / "Is it safe?" |
| **Meteor** | "Watch for meteors tonight" / "Meteor status" |
| **Guiding** | "Start guiding" / "What's the guiding RMS?" |
| **Camera** | "Start capture on Jupiter" / "Set gain to 280" |
| **Focus** | "Auto focus" / "Move focus in 50 steps" |
| **Enclosure** | "Open the roof" / "Close the roof" |
| **Power** | "Battery status" / "Emergency shutdown" |
| **Encoder** | "What's the encoder position?" / "Check pointing error" |
| **PEC** | "Start PEC playback" / "Record PEC" |
| **INDI** | "List INDI devices" / "Set INDI filter to Ha" |
| **Alpaca** | "Discover Alpaca devices" / "Alpaca focuser status" |

---

## Mount Control Commands

### Slewing to Objects

| Voice Command | Action |
|--------------|--------|
| "Go to [object]" | Slew to named object |
| "Point at [object]" | Slew to named object |
| "Slew to [object]" | Slew to named object |
| "Show me [object]" | Slew to named object |

**Supported object types:**
- Planet names: *Mars, Jupiter, Saturn, Venus, Mercury, Uranus, Neptune*
- Messier objects: *M31, M42, M13, M57*
- NGC/IC objects: *NGC 7000, IC 1396*
- Named objects: *Orion Nebula, Ring Nebula, Andromeda Galaxy*
- Star names: *Vega, Polaris, Betelgeuse, Sirius*

**Examples:**
- "Go to Mars"
- "Point the telescope at M31"
- "Show me the Ring Nebula"
- "Slew to NGC 7000"

### Coordinate Slewing

| Voice Command | Action |
|--------------|--------|
| "Go to RA [hh:mm:ss] Dec [dd:mm:ss]" | Slew to coordinates |
| "Slew to coordinates [ra] [dec]" | Slew to coordinates |

### Tracking Control

| Voice Command | Action |
|--------------|--------|
| "Start tracking" | Enable sidereal tracking |
| "Stop tracking" | Disable tracking |
| "Track this object" | Start tracking at current position |

### Emergency Commands

| Voice Command | Action |
|--------------|--------|
| "Stop" | Emergency stop all motion |
| "Abort" | Emergency stop all motion |
| "Cancel" | Stop current slew |
| "Wait" | Pause current operation |

**Note:** Emergency commands are processed immediately with highest priority.

### Park/Unpark

| Voice Command | Action |
|--------------|--------|
| "Park the telescope" | Slew to park position |
| "Park" | Slew to park position |
| "Unpark" | Resume from parked state |
| "Unpark the telescope" | Resume from parked state |

### Sync Position

| Voice Command | Action |
|--------------|--------|
| "Sync to [object]" | Sync mount position to centered object |
| "Sync on [object]" | Sync mount position to centered object |

---

## Object Lookup Commands

### Information Queries

| Voice Command | Action |
|--------------|--------|
| "What is [object]?" | Get object information |
| "Tell me about [object]" | Get object description |
| "What am I looking at?" | Identify current target |
| "What's at this position?" | Identify objects at current pointing |

### Object Search

| Voice Command | Action |
|--------------|--------|
| "Find [type] in [constellation]" | Search for objects |
| "What galaxies are visible?" | List visible objects by type |
| "Show me nebulae brighter than magnitude 8" | Filtered search |

**Object types:** galaxy, nebula, cluster, star, planet

---

## Ephemeris Commands

### Planet Positions

| Voice Command | Action |
|--------------|--------|
| "Where is [planet]?" | Get planet position |
| "What planets are visible?" | List visible planets |
| "Show visible planets" | List planets above horizon |

### Moon Information

| Voice Command | Action |
|--------------|--------|
| "Where is the Moon?" | Get moon position |
| "What's the moon phase?" | Get current phase |
| "Moon info" | Get position and phase |

### Sky Conditions

| Voice Command | Action |
|--------------|--------|
| "Is it dark?" | Check if astronomical night |
| "Is it night?" | Check twilight status |
| "When does it get dark?" | Get astronomical twilight time |
| "What's up tonight?" | Get observing recommendations |

---

## Weather & Safety Commands

### Weather Status

| Voice Command | Action |
|--------------|--------|
| "What's the weather?" | Get current conditions |
| "How windy is it?" | Get wind speed |
| "What's the humidity?" | Get humidity reading |
| "What's the temperature?" | Get temperature |
| "Cloud status" | Get cloud sensor reading |

### Safety Checks

| Voice Command | Action |
|--------------|--------|
| "Is it safe to observe?" | Check all safety conditions |
| "Is it safe?" | Quick safety check |
| "Safety status" | Detailed safety report |
| "Check conditions" | Weather and safety overview |
| "Sensor health" | Check all sensor status |

---

## Meteor Tracking Commands

NIGHTWATCH includes meteor and fireball monitoring capabilities with NASA CNEOS and American Meteor Society data integration.

### Watch Commands

| Voice Command | Action |
|--------------|--------|
| "Watch for meteors tonight" | Create watch window for tonight |
| "Watch for the Perseids" | Create watch window for specific shower |
| "Watch the sky from Nevada" | Create watch window with location |
| "Keep an eye on the sky" | Casual meteor watch |

**Natural language examples:**
- "Quadrantids peak January 3-4, Nevada should be clear"
- "Watch for the Perseids next week from Astoria"
- "Alert me if anything bright shows up tonight"

### Status Commands

| Voice Command | Action |
|--------------|--------|
| "Meteor status" | Get watch windows and recent detections |
| "What's the meteor status?" | Summary of tracking activity |
| "Check for fireballs" | Manual check of fireball databases |
| "Active watch windows" | List current watch windows |

### Shower Information

| Voice Command | Action |
|--------------|--------|
| "What meteor showers are coming?" | Upcoming showers list |
| "Tell me about the Perseids" | Specific shower info |
| "When is the next meteor shower?" | Next major shower |

**Major showers tracked:** Quadrantids, Lyrids, Eta Aquariids, Perseids, Orionids, Leonids, Geminids, Ursids

---

## Autoguiding Commands (PHD2 Integration)

### Guiding Control

| Voice Command | Action |
|--------------|--------|
| "Start guiding" | Begin autoguiding |
| "Stop guiding" | Stop autoguiding |
| "Pause guiding" | Temporarily pause corrections |

### Guiding Status

| Voice Command | Action |
|--------------|--------|
| "Guiding status" | Get RMS, SNR, star info |
| "How's the guiding?" | Get guiding quality summary |
| "What's the RMS?" | Get tracking error |

### Dithering

| Voice Command | Action |
|--------------|--------|
| "Dither" | Default 5-pixel dither |
| "Dither [N] pixels" | Custom dither amount |

---

## Camera Commands

### Capture Control

| Voice Command | Action |
|--------------|--------|
| "Start capture on [target]" | Begin video capture |
| "Start recording [target]" | Begin video capture |
| "Capture [target] for [N] seconds" | Timed capture |
| "Stop capture" | End current capture |

**Recommended targets:** Mars, Jupiter, Saturn, Moon

### Camera Settings

| Voice Command | Action |
|--------------|--------|
| "Set gain to [value]" | Adjust camera gain (0-500) |
| "Set exposure to [N] milliseconds" | Set exposure time |
| "Camera status" | Get current settings |

**Recommended settings (from Damian Peach):**
- Mars: gain 280, exposure 8ms
- Jupiter: gain 250, exposure 12ms
- Saturn: gain 300, exposure 15ms

---

## Focus Commands

### Auto Focus

| Voice Command | Action |
|--------------|--------|
| "Auto focus" | Run automatic focus routine |
| "Focus" | Run auto focus |
| "Focus the telescope" | Run auto focus |

### Manual Focus

| Voice Command | Action |
|--------------|--------|
| "Move focus in [N] steps" | Move focuser inward |
| "Move focus out [N] steps" | Move focuser outward |
| "Focus position" | Get current position |
| "Focus status" | Get position and temperature |

### Temperature Compensation

| Voice Command | Action |
|--------------|--------|
| "Enable temperature compensation" | Auto-adjust for temp changes |
| "Disable temperature compensation" | Manual focus only |

---

## Enclosure Commands (Roll-off Roof)

### Roof Control

| Voice Command | Action |
|--------------|--------|
| "Open the roof" | Open roll-off roof |
| "Close the roof" | Close roll-off roof |
| "Stop the roof" | Emergency stop roof motion |

### Roof Status

| Voice Command | Action |
|--------------|--------|
| "Roof status" | Get position and safety state |
| "Is the roof open?" | Check roof position |
| "Can I open the roof?" | Check if conditions allow |

**Safety notes:**
- Telescope must be parked before roof can open
- Roof auto-closes on rain detection (hardware interlock)
- 30-minute rain holdoff before reopening

---

## Power Management Commands

### UPS Status

| Voice Command | Action |
|--------------|--------|
| "Battery status" | Get UPS battery level |
| "Power status" | Get full power report |
| "How much battery?" | Get remaining runtime |

### Power Events

| Voice Command | Action |
|--------------|--------|
| "Any power events?" | Get recent outages |
| "Power history" | Get power event log |

### Emergency

| Voice Command | Action |
|--------------|--------|
| "Emergency shutdown" | Safe shutdown sequence |

**Automatic power responses:**
- 50% battery: Auto-park telescope
- 20% battery: Emergency roof close and shutdown

---

## Encoder Feedback Commands (Phase 5.1)

### Position Queries

| Voice Command | Action |
|--------------|--------|
| "Encoder position" | Get high-resolution encoder reading |
| "What's the encoder reading?" | Get axis positions |

### Pointing Correction

| Voice Command | Action |
|--------------|--------|
| "Pointing error" | Compare encoder vs mount position |
| "Check pointing correction" | Get position error in arcseconds |

---

## Periodic Error Correction (PEC) Commands

### PEC Status

| Voice Command | Action |
|--------------|--------|
| "PEC status" | Check recording/playback state |
| "Is PEC active?" | Check if playing corrections |

### PEC Control

| Voice Command | Action |
|--------------|--------|
| "Start PEC" | Begin playback of trained data |
| "Stop PEC" | Stop playback |
| "Record PEC" | Start recording (requires guiding) |

### Driver Diagnostics

| Voice Command | Action |
|--------------|--------|
| "Driver status" | TMC5160 health check |
| "Check RA driver" | Axis 1 diagnostics |
| "Check Dec driver" | Axis 2 diagnostics |

---

## Alert Management Commands

### Alert Queries

| Voice Command | Action |
|--------------|--------|
| "Any alerts?" | Get unacknowledged alerts |
| "Show alerts" | Get all recent alerts |
| "Alert status" | Summary of alert state |

### Alert Actions

| Voice Command | Action |
|--------------|--------|
| "Acknowledge alert" | Clear current alert |
| "Dismiss alert" | Clear current alert |

---

## Session & Voice Style Commands

### Voice Style

| Voice Command | Action |
|--------------|--------|
| "Set voice to normal" | Standard responses |
| "Set voice to alert" | Faster, urgent delivery |
| "Set voice to calm" | Slower, relaxed delivery |
| "Set voice to technical" | Detailed diagnostic output |

**Recommended styles:**
- Visual observing: "calm" mode
- Imaging sessions: "alert" mode
- Troubleshooting: "technical" mode

### Session Log

| Voice Command | Action |
|--------------|--------|
| "What have I observed?" | Get session history |
| "Observation log" | Get detailed log |
| "What did I look at last?" | Get recent observations |

---

## INDI Device Control Commands (Phase 5.1)

INDI provides Linux-native device control for cameras, filter wheels, focusers, and other astronomy equipment connected via INDI server (port 7624).

### Device Discovery

| Voice Command | Action |
|--------------|--------|
| "List INDI devices" | Show all connected INDI devices |
| "What INDI devices are connected?" | Show device list |

### Filter Wheel (INDI)

| Voice Command | Action |
|--------------|--------|
| "INDI filter position" | Get current filter |
| "Set INDI filter to [name/position]" | Change filter |
| "Change INDI filter to Ha" | Set to hydrogen-alpha filter |
| "INDI filter to position 3" | Set by position number (1-7) |

**Filter names:** L, R, G, B, Ha, OIII, SII

### Focuser (INDI)

| Voice Command | Action |
|--------------|--------|
| "INDI focuser status" | Get position, temp, movement state |
| "Move INDI focuser to [position]" | Absolute move |
| "Move INDI focuser in [N] steps" | Relative move inward |
| "Move INDI focuser out [N] steps" | Relative move outward |

---

## Alpaca Device Control Commands (Phase 5.1)

ASCOM Alpaca provides network-based device control via REST API (port 11111), enabling cross-platform control of Windows ASCOM devices from Linux.

### Device Discovery

| Voice Command | Action |
|--------------|--------|
| "Discover Alpaca devices" | UDP broadcast discovery |
| "Find Alpaca devices" | Search local network |
| "What Alpaca devices are available?" | List discovered devices |

### Filter Wheel (Alpaca)

| Voice Command | Action |
|--------------|--------|
| "Alpaca filter position" | Get current filter |
| "Set Alpaca filter to [name/position]" | Change filter |
| "Alpaca filter to OIII" | Set to OIII filter |
| "Alpaca filter position 2" | Set by position (0-6) |

**Note:** Alpaca filter positions are 0-indexed (0=first filter), while INDI uses 1-indexed (1=first filter).

### Focuser (Alpaca)

| Voice Command | Action |
|--------------|--------|
| "Alpaca focuser status" | Get position, temp, temp compensation |
| "Move Alpaca focuser to [position]" | Absolute move |
| "Alpaca focuser in [N] steps" | Relative move inward |
| "Alpaca focuser out [N] steps" | Relative move outward |

---

## Command Confirmation

For critical operations with low voice recognition confidence, NIGHTWATCH will ask for confirmation:

**System:** "Please confirm: Park telescope. Say 'confirm' or 'cancel'."

**Responses:**
- "Confirm" - Proceed with action
- "Yes" - Proceed with action
- "Cancel" - Abort action
- "No" - Abort action

---

## Tips for Best Recognition

1. **Speak clearly** - Pause briefly before commands
2. **Use natural phrasing** - The system understands variations
3. **Wait for acknowledgment** - Listen for "Acknowledged" or "Slewing to..."
4. **Use object names** - "M31" and "Andromeda Galaxy" both work
5. **Emergency commands** - "Stop" works instantly from any state

## Version History

- **v3.3** - Added INDI and Alpaca cross-platform device control commands
- **v3.1** - Added encoder, PEC, and voice style commands
- **v3.0** - Added enclosure, power, focus, and astrometry commands
- **v2.0** - Added guiding and camera commands
- **v1.0** - Initial mount, catalog, ephemeris, and weather commands
