# VULNLAB — Deliberately Vulnerable Web Application

A self-hosted, intentionally insecure web app for hands-on security training,
modeled after TryHackMe / HackTheBox style labs.

> ⚠️ **WARNING — READ THIS FIRST**
> This application is **intentionally vulnerable**. It exists to be broken.
> Run it **only** on an isolated local machine, a VM, or a private lab network.
> **NEVER** expose it to the public internet or any network you don't own.
> The authors accept no liability for misuse.

---

## 1. What's inside

| # | Vulnerability | Endpoint | Impact |
|---|---------------|----------|--------|
| 1 | SQL Injection (auth bypass) | `/login` | Log in as `admin` without a password |
| 2 | OS Command Injection | `/tools/ping` | Remote Code Execution (RCE) |
| 3 | Reverse shell / interactive RCE | `/tools/ping` | Full shell on the host |
| 4 | Verbose SQL error leakage | `/login` | Info disclosure |
| 5 | Hardcoded Flask secret key | app.py | Session forgery |

The end goal (the "flag") is the admin panel at `/admin`, and the root loot
file at `/root/root.txt`.

---

## 2. Requirements

- Python 3.8+
- Flask  (`pip install -r requirements.txt`)
- `netcat` (`nc`) on your attacking machine for the reverse shell

## 3. Run it

```bash
cd vuln-lab
pip install -r requirements.txt
python3 init_db.py      # creates + seeds vulnlab.db
python3 app.py          # starts the server on 0.0.0.0:8000
```

Or simply:

```bash
./run.sh
```

Then open: **http://127.0.0.1:8000**

To reach it from another machine (e.g. your Kali VM), browse to
`http://<server-ip>:8000` — the app binds on all interfaces.

---

## 4. Suggested lab topology (realistic setup)

```
 +---------------------+          +----------------------------+
 |  Attacker (Kali)    |  HTTP    |  Target (this app)         |
 |  nc -lvnp 4444      | -------> |  http://TARGET_IP:8000     |
 |  LHOST=KALI_IP      | <------- |  command injection -> RCE  |
 +---------------------+  reverse |
                        shell     |
```

1. Run VULNLAB on the "target" host.
2. From Kali, browse to the target, do the SQLi bypass, then the command injection.
3. Start `nc -lvnp 4444` on Kali and fire the reverse-shell payload.

---

## 5. File layout

```
vuln-lab/
├── app.py                 # the vulnerable Flask application
├── init_db.py             # database initializer / seeder
├── requirements.txt
├── run.sh                 # convenience launcher
├── templates/             # HTML (Jinja2)
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── ping.html
│   ├── admin.html
│   └── denied.html
├── static/
│   └── style.css
├── exploits/
│   ├── listener.sh        # start an nc listener
│   ├── reverse_shell.sh   # generate a payload for your IP/port
│   └── payloads.txt       # cheat-sheet of all payloads
├── README.md              # this file
└── WALKTHROUGH.md         # step-by-step solution (SPOILERS)
```

---

## 6. Reset the lab

Delete the database and restart to reset all state:

```bash
rm -f vulnlab.db && python3 init_db.py
```

---

## 7. Legal / ethics

This is for **education and authorised testing only**. Only attack systems you
own or have explicit written permission to test. Unauthorised access to computer
systems is illegal in virtually every jurisdiction.
