# T4 — Demo reliability: technical readiness (Tung's slice)

**Task:** T4 (Sprint 10, Category A — fixed date 23 Sep)
**Owners:** Tung (this doc), Andre, Tai
**Checked by:** Taylor
**Handoff to:** Andre, Tai — you drive the live demo and own the fallback
recording; this is what I can verify remotely so you don't have to.

**Definition of Done** (from the sprint plan)
> One complete three-plus-three-plus-two run-through has been performed
> live, end to end, and the fallback recording exists and plays.

I can't verify the physical/recording half of this from here — that's
listed at the bottom as what I need from you, not something I've done.

---

## 1. What I've actually done (my slice)

Extended the existing readiness script (`scripts/check_demo_ready.py`,
originally Sprint 6 T29) rather than writing a new one — it already checked
that every container is up and warm; the sprint plan additionally wants
proof that *the specific question we ask live* returns a real, grounded
answer, not the fallback. Added that check.

```powershell
python scripts/check_demo_ready.py
```

Run this and paste the output back to me — I'll read it and tell you
whether anything needs fixing before rehearsal, rather than you having to
interpret a stack trace mid-demo-prep.

```
Paedia demo readiness check
======
[PASS] postgres (container)         state=running health=healthy
[PASS] chromadb (container)         state=running health=n/a
[PASS] chromadb (heartbeat)         heartbeat ok
[PASS] ollama (container)           state=running health=n/a
[PASS] ollama (models)              models available: gemma4:12b
[PASS] api (container)              state=running health=healthy
[WARN] api (/api/health)            warm-up status=degraded: pull_failed: ReadTimeout: HTTPConnectionPool(host='ollama', port=11434): Read timed out. (read timeout=600)
[PASS] streamlit (container)        state=running health=healthy
[PASS] streamlit (/_stcore/health)  http 200 ok
[FAIL] demo question ('What is retrieval-augmented generation?'...) demo question returned the FALLBACK answer, not a grounded one — this is exactly the failure mode task 4 exists to catch. answer[:150]='Based on general knowledge — not verified against course materials.\n\n[LLM Error: 500 Server Error: Internal Server Error for url: http://ollama:11434/'
======
FAIL - see the [FAIL] lines above. Check `docker compose logs <service>`.
```

The FAIL here is a confirmed hardware ceiling on my dev machine (8GB RAM,
no dedicated VRAM), not a code defect — see "Known issue #3" below for the
full diagnosis, including the `docker compose logs ollama` evidence. The
`api (/api/health)` WARN above is also stale — it's the cached failure from
issue #1, from before the manual `/api/warmup` retrigger.

**What a clean run looks like** (all nine lines `PASS`, last line is the
demo-question check):
```
[PASS] postgres (container)         state=running health=healthy
[PASS] chromadb (container)         state=running health=n/a
[PASS] chromadb (heartbeat)         heartbeat ok
[PASS] ollama (container)           state=running health=n/a
[PASS] ollama (models)              models available: gemma4:12b
[PASS] api (container)              state=running health=healthy
[PASS] api (/api/health)            model=gemma4:12b warmup_ms=<n>
[PASS] streamlit (container)        state=running health=healthy
[PASS] streamlit (/_stcore/health)  http 200 ok
[PASS] demo question ('What is retrieval-augmented gener...')  grounded answer, N source(s): ...
READY - all services healthy and the demo question is grounded. Open http://localhost:8501 to demo.
```

### Known first-run issue: Ollama model pull times out

**Seen on:** first `docker compose up -d --build` against a brand-new
`ollama_data` volume (confirmed during T4 verification, 24 Sep 2026).

```
[WARN] ollama (models)              no models pulled yet — first warm-up may still be pulling
[WARN] api (/api/health)            warm-up status=degraded: pull_failed: ReadTimeout: HTTPConnectionPool(host='ollama', port=11434): Read timed out. (read timeout=600)
[FAIL] demo question (...)          demo question returned the FALLBACK answer... [LLM Error: 404 Client Error: Not Found for url: http://ollama:11434/api/generate
```

**Cause:** `gemma4:12b` is large enough that our own warm-up code
(`src/api/warmup.py`, `pull_timeout=600`) can time out pulling it over HTTP
before the download finishes, leaving no model installed — hence the `404`
on generate and the fallback answer. This is a first-run/cold-volume issue,
not a code regression, and not specific to any one machine's network.

**Fix — pull it once, directly, with no short timeout:**
```powershell
docker compose exec ollama ollama pull gemma4:12b
python scripts/check_demo_ready.py
```
Once pulled, the model persists in the `ollama_data` named volume, so this
is a one-time cost per host/volume — it will not need re-pulling on every
`docker compose up`, only after `docker compose down -v` wipes the volume.

**Relevant for demo day:** if the GPU host's Ollama volume is ever reset
(fresh host, `-v` down, disk wiped), do this pull step **well before** the
1:30pm slot — don't let the first pull happen live or during the 3:30pm
rehearsal.

### Known issue #2: warm-up doesn't auto-retry after a failed pull, and the first real load is slow

**Seen on:** immediately after fixing issue #1 above, same session.

```
[PASS] ollama (models)              models available: gemma4:12b
[WARN] api (/api/health)            warm-up status=degraded: pull_failed: ReadTimeout... (read timeout=600)
[FAIL] demo question (...)          POST /api/query failed (status=0, 'timed out')
```

**Cause:** the API container runs warm-up once, at its own startup. If that
attempt failed (issue #1), the failure is cached in `warmup_status` and
nothing retries it automatically — the model can be sitting there correctly
pulled and the API still won't know. Separately, whichever request first
asks the model to actually generate text is paying the cost of loading a
12B model into memory for the first time, which can run well past a normal
request timeout.

**Fix — trigger warm-up again by hand, with a timeout long enough for a
cold load:**
```powershell
$login = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" -Method Post -ContentType "application/json" -Body '{"email":"lecturer@uow.edu.au","password":"lecturer123"}'
$token = $login.access_token
Invoke-RestMethod -Uri "http://localhost:5000/api/warmup" -Method Post -Headers @{Authorization = "Bearer $token"} -TimeoutSec 600
python scripts/check_demo_ready.py
```

**Relevant for demo day, more so than issue #1:** `OLLAMA_KEEP_ALIVE`
defaults to 30 minutes — if the model sits idle longer than that (e.g. a
long gap between the 3:30pm rehearsal and the 1:30pm slot on a different
day, or a host reboot), the *next* question pays this same cold-load delay
again. Whoever is driving the stack on the day should hit `/api/warmup` (or
just ask any question once through the UI) a few minutes before the session
starts — not rely on it already being warm from a rehearsal hours earlier.

### Known issue #3 — confirmed hardware ceiling on my dev laptop, not a bug

**Seen on:** my own machine (i5-1135G7, 8GB RAM, integrated graphics — no
dedicated VRAM), immediately after fixing issue #2.

```
error : generate_failed: HTTPError: 500 Server Error: Internal Server Error
        for url: http://ollama:11434/api/generate
```

**Confirmed cause** (via `docker compose logs ollama --tail 50`):
```
load_tensors:          CPU model buffer size =  2808.41 MiB
load_tensors:   CPU_REPACK model buffer size =  5003.44 MiB
...
msg="Load failed" ... error="llama-server process has terminated: signal: killed"
[GIN] ... 500 | 1m27s | POST "/api/generate"
```
`model params = 11.91 B` had already allocated ~7.8GB of CPU buffers when
the Linux OOM killer terminated the `llama-server` process outright
(`signal: killed`) — this is Docker/the OS reclaiming memory by force, not
an application error. This is a hardware limit of an 8GB-RAM laptop with no
dedicated VRAM: Docker Desktop, Windows itself, Postgres, and ChromaDB were
all competing for the same 8GB before Ollama even started loading. **Not a
defect in this sprint's code or in the pull/warmup fixes above** — the
sprint plan itself specifies the real system runs on a GPU host, and this
laptop was never a substitute for that.

**What this means:** I cannot get a full end-to-end `PASS` on the demo
question from my own machine. **The last-mile "does the live demo question
return a grounded answer" check needs to run on the GPU host itself** (or
any machine with enough RAM/VRAM to load a 12B model), not on my hardware.

**What I've still verified, and what remains open:**

| Layer | Verified on my machine? |
|---|---|
| Containers start, stay healthy, network correctly | Yes — postgres, chromadb, api, streamlit all clean |
| Model pull, once given a long enough timeout | Yes |
| Auth, course scoping, retrieval plumbing up to the point of calling Ollama | Yes (the request reaches `/api/generate` correctly — it's Ollama's own load that fails) |
| Actual grounded answer + sources on the real production model | **Not verified locally — needs the GPU host** |

**Action for whoever has GPU-host access (Andre/Tai, or Taylor):** run
`python scripts/check_demo_ready.py` directly on/against the GPU host and
paste the output back. That's the one piece of Task 4 my hardware cannot
close out.

If the **last line only** fails, it doesn't mean the stack is broken — it
means the specific question isn't well answered by the current corpus. Try
alternatives before assuming something regressed:

```powershell
$env:PAEDIA_DEMO_QUESTION = "Explain the chunking strategy used in this course"
python scripts/check_demo_ready.py
```

---

## 2. Choosing the actual demo question — this needs your input, not mine

The script defaults to *"What is retrieval-augmented generation?"* because
it's what the test corpus was built around, but I haven't seen the run-of-
show (Task 1, Taylor) or whatever question you two rehearsed with when you
recorded the fallback video. Whatever question ends up in the run-of-show:

1. Set `$env:PAEDIA_DEMO_QUESTION` to the real one and re-run the script
   above — confirm it still says `PASS` with real sources, not the fallback.
2. Tell me the question you land on and I'll fold it into the script's
   default so this stays useful for future runs instead of drifting out of
   sync with the actual demo.

One caveat from the known limitations list, worth keeping in mind when
picking: **questions phrased around course structure** ("what did week 5
cover") **retrieve poorly** — pick something about a concept or topic, not a
week number.

---

## 3. What only you two can verify — I've listed it, I haven't done it

| Check | Why it's yours, not mine | Done? |
|---|---|---|
| Laptop actually used on the day is the one tested | Different machine = different Docker Desktop resource limits, different network | <fill in> |
| Network at the venue (or Tailscale route to the GPU host, if not running locally on the day) | Can't test the venue's wifi from here | <fill in> |
| Display resolution / projector scaling | Physical, not something a script sees | <fill in> |
| Editor font size for the code segment (Task 3) readable from the back of the room | Physical | <fill in> |
| Fallback recording exists, plays, and shows the *current* UI (not an outdated build) | I don't have the recording file | <fill in> |
| Fallback recording is introduced as a recording if used, per the plan | Presentation choice, not infra | n/a — just a reminder for the day |

If you've already recorded the fallback video: can you tell me which build/
commit it was recorded against? If it predates the Task 8 sample-document
fix or the T9 course-selection merge, the recording will show stale UI next
to a live demo that looks different — worth a quick re-record once those
land on `develop`, not necessarily urgent right now.

---

## 4. Morning-of checklist (for whoever's running the stack on the day)

```powershell
docker compose up -d
Start-Sleep -Seconds 30
python scripts/check_demo_ready.py
```

Run this **before** the session, not during it, per the plan's own
"confirm services are up and warm before the session rather than during it."
If anything shows `WARN`, wait ~15s and re-run — that's usually Ollama still
loading the model into VRAM. If anything shows `FAIL`, `docker compose logs
<service>` for that one and ping me/Taylor before assuming it needs a full
rebuild.

---

## 5. Result

**My part (script + verification on my own dev machine):** PARTIAL —
container health, networking, model pull, and the query-to-Ollama code path
all verified clean on 8GB-RAM consumer hardware. The final step (a real
grounded answer from `gemma4:12b`) could not be verified on this machine —
likely an out-of-memory limit on a 12B model, not a code defect (see Known
issue #3 above). **This needs to be re-run on the GPU host** before it can
be marked fully done.

**Andre/Tai's part (Section 3):** not yet reported back to me.

**Outstanding before this can be checked off:** someone with GPU-host
access runs `python scripts/check_demo_ready.py` there and confirms a clean
`PASS` including the demo-question line.

**Handoff:** once Section 3's table is filled in and Section 1 shows a
clean run against the real run-of-show question, this is ready for Taylor
to check off.
