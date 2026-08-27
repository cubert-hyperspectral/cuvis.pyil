# Threading the cu3s read path: what the GIL release buys, and where the real ceilings are

Investigation, 2026-08-19 and 2026-08-20.
Target consumer: `C:\dev\cuvis_ai\cuvis-ai-dataloader`, whose `Cu3sCubeReader` is the heaviest cuvis user we ship against.

Starting question: the `poc/gil-release` branch releases the GIL around every wrapped cuvis call.
Does that translate into anything the dataloader can use, given that its async paths are irrelevant here?
The whole cu3s read path is synchronous: `SessionFile` -> `ProcessingContext.apply` -> `mesu.cube.array`.

Answers, in order of how much they matter.

1. The branch as first written was **unsafe**, and fixing that is the most important outcome here.
2. On GPU processing it is worth **up to 4.65x**, from 15.1 to 70.2 fps.
3. On CPU processing it is worth **almost nothing**, and the useful lever there is a settings value, not threads.
4. Both apparent concurrency ceilings turned out to be **configured caps**, not hardware or SDK limits. The genuine hardware ceiling is reached only after raising them.
5. Only the `SessionFile` needs multiplying. One `ProcessingContext` serves every thread, correctly and more cheaply.

Machine for every number below: 20 cores, RTX 4070 (8 GB), Windows 11, SDK 3.5.3.
Session `D:\Measurements\hbf\Auto_013+01.cu3s`, 940 frames, cube 1000x1080x61.

---

## 1. The blocker: releasing the GIL exposed a data race

`cuvis.swig/src/cuvis_il.i` returned C strings out of nine `%inline` helpers, each backed by a function-local `static std::string`:

```c
char const* cuvis_measurement_get_data_info_swig(...)
{
	//avoid dangling pointer (invalid pointer) when returnging c_str
	static std::string key;
	...
	return key.c_str();
}
```

The comment records the intent: `static` was reached for to stop the returned `c_str()` dangling.
It solves that and creates a process-wide shared buffer.

While the GIL was held for the duration of every call, exactly one thread could ever be inside these functions, so the race could not fire.
Releasing the GIL removed that accidental protection.
It reproduces at 2 threads and never on the stock binding:

```
File "cuvis/ProcessingContext.py", line 57, in apply
    mesu.refresh()
File "cuvis/Measurement.py", line 116, in refresh
    dformat=DataFormat[data.__getattribute__("format")],
KeyError: 0
```

The message hides the cause.
The helper hands back a key belonging to another thread's frame, `Measurement._refresh` passes that wrong key to `cuvis_measurement_get_data_image` **without checking the returned status**, `data` is left zero filled, `format` is `0`, and the enum lookup raises.

### What shipped

`cuvis.swig` commit `8997137` on `poc/gil-release`, three changes in one commit:

- **The nine helpers return `std::string` by value.** This removes the shared buffer rather than making it per-thread, so a helper added later cannot reintroduce the race by forgetting an annotation. `thread_local` was tried first and works, but it is a keyword someone can omit.
- **`cuvis_measurement_get_data_string_swig` is sized from `cuvis_measurement_get_data_string_length`.** The old fixed `CUVIS_MAXBUF*8` buffer silently truncated longer values and then read past its own end, because the SDK writes no terminator when the value fills the buffer exactly. A 3232 byte `settings_rec` came back as 2054 bytes ending in uninitialised stack, surfacing as lone surrogates. It now returns all 3231 characters as well-formed XML.
- **The GIL-releasing `%exception` is guarded with `#ifdef SWIGPYTHON`.** This file is shared with `cuvis.csharp`, whose submodule was still pinned before the GIL commit; unguarded, `PyEval_SaveThread` would have broken the C# build on its next bump.

No API change in either language: the helpers still yield `str` in Python and `string` in C#.
Verified: 134 tests pass, 311 GIL release sites unchanged, no static buffers left in the generated wrapper, 2/4/8 threads clean where 4 previously died, `swig -csharp` generates cleanly.

### Still open from this section

`Measurement._refresh` still ignores the status of `cuvis_measurement_get_data_image`, `_gps` and `_sensor_info`.
Checking it would have turned this into an `SDKException` naming the failing call instead of a `KeyError` three frames away.
That is a cuvis.python change, not a cuvis.swig one.

---

## 2. Method

One process, N threads, each owning its own `SessionFile`.
All threads cycle a ten frame window so the data stays in the page cache and the number measures compute rather than disk.
Two warmup frames per thread, then a barrier, then the clock.
Wall time runs from the last thread through the barrier to the first thread finished, so no thread's startup is counted.

`stock` is `cuvis_il` 3.5.3.2 from PyPI; `gil` is this branch.
Medians of 3 interleaved repeats where two bindings are compared.
Cube contents are hashed and compared against a single-threaded reference wherever a shared object could plausibly corrupt them; hashing a 63 MiB cube costs more than producing it, so verification runs are separate from throughput runs.

One early matrix was discarded: a background compile was running and the spread reached 2x.
Short runs also underestimate, because steady state is not reached; 12 iterations per thread gave 53.5 fps where 24 gave 70.1 for the same configuration.

---

## 3. What the GIL release is worth

GPU processing, Raw mode, per-thread `SessionFile` and `ProcessingContext`:

| threads | stock fps | scaling | gil fps | scaling |
| --- | --- | --- | --- | --- |
| 1 | 15.42 | 1.00x | 15.47 | 1.00x |
| 2 | 15.05 | 0.98x | 25.81 | 1.67x |
| 4 | 14.92 | 0.97x | 45.24 | **2.92x** |
| 8 | 14.40 | 0.93x | 58.67 | **3.79x** |

**Stock does not merely fail to scale, it slightly degrades**, 15.42 to 14.40 fps.
That is pure GIL contention: the extra threads add scheduling cost and contribute no work, because only one can be inside cuvis at a time.
Adding worker threads to the current binding is a small loss, not a neutral choice.

**Single thread performance is unchanged**, 15.42 against 15.47.
The two lock operations per wrapped call cost nothing at these rates, which is the obvious objection to the change and the answer to it.

---

## 4. Topology: only the SessionFile needs multiplying

Giving every thread its own `ProcessingContext` mirrors what a torch worker process owns, but it is not what the workload needs.
Only the disk read has to be parallel.
Re-measured with N `SessionFile` objects over the same file and a single shared `ProcessingContext`:

| threads | Raw fps | scaling | VRAM (MiB) | RSS (GB) | wrong cubes |
| --- | --- | --- | --- | --- | --- |
| 1 | 15.09 | 1.00x | 1951 | 2.66 | 0 |
| 2 | 26.32 | 1.74x | 2175 | 2.66 | - |
| 4 | 44.59 | 2.95x | 2591 | 2.66 | 0 |
| 6 | 55.07 | 3.65x | 2785 | 3.39 | - |
| 8 | 59.98 | 3.97x | 2945 | 4.24 | 0 |
| 12 | 67.18 | 4.45x | 3297 | 5.91 | - |
| 16 | 68.41 | 4.53x | 3653 | 7.52 | - |
| 20 | **70.17** | **4.65x** | 4005 | 9.18 | 0 |
| 24 | 70.12 | 4.65x | 4357 | 10.82 | - |

Sharing the context is safe and cheaper.
Zero wrong cubes at 4, 8 and 20 threads, so it is not mixing state between callers; this was worth checking rather than assuming, because a silently wrong cube would have looked like a win.
Setup falls from 8.7-10.5 s to 0.35-2.5 s, since the roughly 1.8 s context init is paid once instead of per thread.
That matters as much as throughput, because the dataloader's `persistent_workers` is `False`, so every epoch pays setup again.
VRAM grows far more slowly, and throughput is within noise of the per-context topology.

What still grows is RSS, roughly 0.35 GB per open `SessionFile`.
That is the unavoidable cost of parallel reads.

---

## 5. The ceilings are settings, and where the real one is

Two apparent hard limits both turned out to be configured caps.

**`cuda_host_memory_maximum_gb = 12.0`** capped GPU-mode concurrency.
Raising it to 40.0 on this 51 GB machine moved the first failure from 12 threads to 20.

**`processing_thread_count = 8`** caps CPU-mode throughput. See section 6.

With the caps raised, the hardware sets the limit and it is genuinely reached:

| mode | ceiling | at | limited by |
| --- | --- | --- | --- |
| Raw | **70.2 fps** (4.65x) | 20 threads | GPU saturated |
| SpectralRadiance | **29.5 fps** (3.43x) | 8 threads | 8 GB of VRAM |

Sampling `nvidia-smi` through a plateau run gives a median GPU utilisation of **99% while busy**, maximum 100%.
Past roughly 12 threads in Raw there is nothing left to win on this card: the bottleneck is no longer the GIL, the SDK, or the thread count.

SpectralRadiance stops much earlier because it holds far more VRAM per frame in flight, 5349 MiB at 8 threads against 2945 MiB for Raw.
At 12 threads it fails intermittently even with the caps raised, and at 16 it fails outright.
`cuda_device_memory_maximum_gb` cannot rescue that, because the card only has 8 GB.

SpectralRadiance is used here as the closest available stand-in for the dataloader's Reflectance default; this session carries Dark and SpRad references but no White, so Reflectance itself cannot run against it.

**The knee is much earlier than the ceiling, and that is what to build for.**
Six threads give 55.07 of 70.17 fps in Raw (78%) and 27.23 of 29.45 in SpectralRadiance (92%).
Going from 6 to 20 threads in Raw buys 27% more throughput for 2.7x the memory.

---

## 6. CPU processing: threads do nothing, the pool setting does

Same shared-context experiment with `force_gpu_mode = host`:

| threads | fps (pool=8, default) | cores busy | fps (pool=20) | cores busy |
| --- | --- | --- | --- | --- |
| 1 | 3.62 | 6.8 | 5.30 | 14.5 |
| 2 | 4.22 | 8.4 | **6.31** | 18.0 |
| 4 | 3.99 | 8.4 | 5.82 | 19.1 |
| 8 | 3.84 | 8.4 | 5.83 | 19.5 |
| 16 | 3.85 | 8.6 | 5.90 | 19.6 |

**Multiplying SessionFiles buys almost nothing on CPU.**
It peaks at two threads and then flattens or decays, in both topologies and at both pool sizes.
Sharing the context is still correct there (0 wrong cubes at 8 threads) and still cheaper to set up, it simply has no throughput to unlock.

The core counts explain it exactly.
With the default pool, one Python thread already occupies 6.8 cores and the process saturates at **8.4 cores no matter how many threads are added**.
Twelve of twenty cores sit idle and nothing at the Python level can reach them, because the work is inside the SDK's own pool.

That pool is configurable, in a block of `cuvis.settings` that is easy to miss:

```xml
<!-- processing: Pool for all tasks to do with measurement processing (the highest CPU load) -->
<property id="processing_thread_count" value="8" />
```

Raising it from 8 to 20 lifts single-threaded host throughput from 3.62 to 5.30 fps, a **1.46x gain with no Python threading at all**, and takes core usage from 6.8 to 14.5.
Setting it to 32 is no better than 20, as expected once it exceeds the physical core count.

Best CPU configuration measured: `processing_thread_count = 20` with **two** reader threads, 6.31 fps against a 3.62 fps stock baseline, **1.74x**.
Only 1.19x of that comes from threading; the rest is the setting.

The same setting does nothing for GPU processing (44.61 / 58.28 / 69.51 fps at 4 / 8 / 16 threads with the pool raised, within noise of the default), which is consistent with the GPU doing the work there.

**CPU remains an order of magnitude behind regardless**, 6.31 fps against 70.2 on the GPU.
The device question matters far more than the topology question.

---

## 7. Against the npz path, thread matched

The dataloader's alternative to live cu3s reading is pre-converted npz frames.
Same harness, mirroring `_MultiNpzDataset.__getitem__`: `np.load` then `asarray(float32)`.
The binding is irrelevant to this path because it never enters cuvis.

| threads | npz fps | scaling | RSS (GB) |
| --- | --- | --- | --- |
| 1 | 1.98 | 1.00x | 0.28 |
| 2 | 3.68 | 1.86x | 0.52 |
| 4 | 5.98 | 3.02x | 1.01 |
| 8 | 7.26 | 3.67x | 1.99 |

npz scales about as well as fixed cu3s does, because zlib releases the GIL during decompression, and it is far lighter on memory.
But at 4 threads, Raw:

| path | fps | RSS (GB) |
| --- | --- | --- |
| cu3s, GPU, gil | **44.59** | 2.66 |
| cu3s, GPU, stock | 14.92 | 2.66 |
| npz | 5.98 | 1.01 |
| cu3s, CPU, gil | 3.99 | 3.79 |

This inverts the conclusion of `benchmarks/cu3s_vs_npz` and `benchmarks/cu3s_workers_sdk353`, where npz matched or beat cu3s.
Those measured process workers through a torch DataLoader, where cu3s could not use more than one core no matter how many workers were spawned.

The npz side also carries an unforced cost: the cu3s Raw cube is `uint8` at 62.8 MiB, the npz cube is `float32` at 251 MiB compressed to 35 MiB on disk, because `npz_converter.py:203` upcasts before saving.
Every frame inflates 35 MiB to 251 MiB through zlib, four times the bytes the SDK path moves.
Storing the native dtype would move these numbers and was not tested here.

---

## 8. Resource cost, threads against processes

Against the process-based numbers in `benchmarks/cu3s_workers_sdk353/index.html`, taken on the same machine:

- **RAM is where threads win.** That benchmark measured roughly 3 to 3.8 GB per cu3s worker process, so 4 workers is about 14 GB. Four threads with a shared context is 2.66 GB total.
- **VRAM is where the shared context wins.** Per worker process it measured about 1.2 GB, strictly linear. A shared context grows from 1951 to 4005 MiB across 1 to 20 threads.
- Threads also skip the roughly 1.8 s context init that every respawned worker pays.

Do not read throughput figures across the two benchmarks; they differ in cube shape, processing mode and whether a torch DataLoader is in the loop.
The resource figures are comparable, the fps figures are not.

---

## 9. What the dataloader would have to change

None of this is reachable from configuration today.
`cuvis_ai_core/data/datamodule.py:355` builds a plain `DataLoader(dataset, batch_size, shuffle, num_workers)`, and torch's `num_workers` is multiprocessing only.
There is no thread backend to switch to.

Using this requires a thread pool prefetcher feeding batches from `Cu3sCubeReader` with `num_workers=0` on the torch side, holding one `SessionFile` per thread and one shared `ProcessingContext`.

## Recommendations

1. **`cuvis.swig` `8997137` must ship with the GIL release**, not after it. Without the string fix the release is a correctness regression.
2. **Size the prefetcher at 6-8 threads on GPU**, not at the ceiling. Six threads give 78% of maximum Raw throughput and 92% of maximum SpectralRadiance; the remainder costs 2.7x the memory. SpectralRadiance, the mode the dataloader defaults to, tops out at 8 anyway.
3. **One `ProcessingContext`, N `SessionFile` objects.** Verified correct to 20 threads, materially cheaper in VRAM and setup, no throughput given up.
4. **Do not build a prefetcher for CPU processing.** Two threads, and set `processing_thread_count` to the machine's core count. Sixteen threads costs 8.54 GB RSS for the same 5.9 fps that two threads deliver at 2.99 GB.
5. **Raise the two defaults, or ask cuvis.c to.** `processing_thread_count = 8` and `cuda_host_memory_maximum_gb = 12.0` both bind well below this machine's capability. `processing_thread_count` in particular looks like it should scale with the host rather than sit at a fixed 8.
6. **Check the status of `cuvis_measurement_get_data_image` and its siblings** in `Measurement._refresh`, independent of threading.
7. **Add a ThreadSanitizer build on Linux.** It would have found the string race mechanically. Every defect in section 1 was found by looking; that is the weakest part of this investigation.

## Related findings from the same investigation

- **Thread safety beyond the string race.** The SDK error channel is process-wide, so `SDKException` can report another thread's message: 0.9% of reads at 3 threads with the GIL released, and 0.2% already on stock. Only the message text is affected, never the status code, which is returned by value. It surfaced concretely here as `SDKException: Last function returned 'ok'` masking the real cause of a thread-count failure. Sharing a single `Measurement` across threads is a hard crash with the GIL released and an `AttributeError` on stock; sessions and contexts survive sharing. `cuvis_proc_cont_apply` also declines work intermittently near the memory caps.
- **Non-ASCII paths are broken on Windows**, tracked as ALL-6111. The SDK decodes `CUVIS_CHAR*` paths as ANSI while every binding sends UTF-8, so such paths fail, and a decoy test showed the SDK opening a *different* file than the one requested. A settings directory with a non-ASCII name is accepted and then silently ignored. Not reproducible on Linux. String *content* is unaffected and round-trips correctly.
- **Version-keyed signature checking**, in `SIGNATURE_MISMATCH_REPORT.md`. Unrelated to threading.

## Reproducing

Scripts and raw results in `benchmarks/thread_scaling/`.

```powershell
$S = "C:\dev\cuvis_sdk\cuvis.pyil\benchmarks\thread_scaling"
$env:DL_CU3S    = "D:\Measurements\hbf\Auto_013+01.cu3s"
$env:DL_NPZ_DIR = "D:\Measurements\hbf\Auto_013+01_npz_bench"
$env:PYLAYER    = "C:\dev\cuvis_sdk\cuvis.python-await"
$env:IL_DIR     = "C:\dev\cuvis_sdk\cuvis.pyil"
$env:PATH       = "C:\Program Files\Cuvis\bin;$env:PATH"

# topology and ceiling sweeps; DL_VERIFY=1 adds the per-frame cube hash check
$env:DL_TOPOLOGY = "shared_pc"; $env:DL_MODE = "Raw"; $env:DL_VERIFY = "0"
& C:\dev\cuvis_sdk\.venv-pyil312\Scripts\python.exe $S\topology_scale.py 8 24

# stock-vs-branch matrix
& C:\dev\cuvis_sdk\.venv-pyil312\Scripts\python.exe $S\drive.py 16 3
```

`topology_scale.py` runs one cell of the topology sweep, `thread_scale.py` the older per-thread-context one, `drive.py` the interleaved stock-vs-branch matrix, `agg.py` prints medians, `cpu_util.py` measures the cores one call already uses, `gil_probe.py` shows per-phase GIL release.
The stock baseline is the PyPI `cuvis_il` 3.5.3.2 wheel unpacked to a directory and put first on `sys.path`.
`DL_SETTINGS` points at a copied settings directory; the variants used here change `force_gpu_mode`, `cuda_host_memory_maximum_gb` and `processing_thread_count`.
