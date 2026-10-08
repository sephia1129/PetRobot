# Rex Control — Setup Guide

Control your Raspberry Pi–powered pet robot from your phone, from anywhere.

## How it fits together

```
[Your phone]  <--- Tailscale network --->  [Raspberry Pi]
   PWA UI                                    Flask server
(joystick + buttons)                    (GPIO motor control)
```

No port forwarding, no cloud relay, no public IP needed. Tailscale
puts your phone and your Pi on the same private network no matter
where either of them physically is.

## 1. Set up the Pi

Copy the `backend/` and `frontend/` folders onto the Pi (same parent
folder, side by side — the server serves the frontend itself).

```bash
cd pet-robot-app/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# On the Pi itself, also uncomment RPi.GPIO in requirements.txt and reinstall
python app.py
```

You should see it start on port 5000. Wire up your actual motors by
filling in the `TODO` sections in `app.py` — `drive()`, `stop()`, and
`do_action()`. Until then it runs in a safe mock mode that just
prints what it would do, so you can test the app end-to-end before
any hardware is wired.

**Run it on boot** (optional, recommended): create a systemd service
so the server starts automatically when the Pi powers on.

```ini
# /etc/systemd/system/rex-control.service
[Unit]
Description=Rex Control Server
After=network.target

[Service]
ExecStart=/home/pi/pet-robot-app/backend/venv/bin/python /home/pi/pet-robot-app/backend/app.py
WorkingDirectory=/home/pi/pet-robot-app/backend
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now rex-control
```

## 2. Install Tailscale

On the Pi:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow the printed link to log in (any Google/GitHub/Microsoft
account works, or make a free Tailscale account). Once connected,
find the Pi's Tailscale IP:

```bash
tailscale ip -4
```

It'll look like `100.x.y.z`. Write it down.

On your phone: install the **Tailscale app** (App Store / Play
Store), sign in with the *same account*. That's it — your phone can
now reach `100.x.y.z` as if it were on the Pi's own WiFi network,
wherever you are.

## 3. Open and install the control app

On your phone, open a browser and go to:

```
http://<pi-tailscale-ip>:5000
```

You should see the Rex Control screen with the joystick.

**Add it to your home screen** so it feels like a real app:
- **iPhone (Safari):** tap Share → *Add to Home Screen*
- **Android (Chrome):** tap the ⋮ menu → *Install app* / *Add to Home screen*

From then on it launches full-screen, no browser chrome, from an
icon on your home screen — even offline it'll open (it just won't
be able to reach the robot until Tailscale connects).

## 4. Using it

- **Joystick:** drag from the center of the ring. Up/down = forward/
  back, left/right = turn. Release to stop automatically.
- **Sit / Speak / Dance:** canned actions — wire these to servos,
  sounds, or LEDs in `do_action()` in `app.py`.
- **Stop:** always sends an immediate stop, independent of the
  joystick.
- The header shows live connection status and battery — wire
  `robot_state["battery_pct"]` up to a real reading (e.g. from a
  voltage divider on an ADC) whenever you're ready.

## Customizing

- **Rename the robot:** change `"name": "Rex"` in `app.py`'s
  `robot_state`, and in `frontend/manifest.json`.
- **Add a camera feed:** the Pi Camera module can stream MJPEG; add
  an `<img src="/api/camera">` tag to `index.html` and a matching
  streaming route in `app.py`.
- **Tune joystick sensitivity:** the `drive(x, y)` function in
  `app.py` receives raw -1..1 values — scale or curve them there if
  the robot feels too twitchy or sluggish.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| App shows "offline" | Tailscale not connected on phone or Pi — open the Tailscale app and check status |
| Can't reach the IP at all | Double-check `tailscale ip -4` on the Pi; make sure both devices are logged into the same Tailscale account |
| Joystick moves but robot doesn't | You're still in mock mode — fill in the GPIO `TODO`s in `app.py` |
| Page won't install to home screen | Must be loaded over `http://` on the local Tailscale IP or `https://` — some browsers require a secure-ish context |
