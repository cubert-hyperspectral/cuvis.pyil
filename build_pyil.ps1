# build_pyil.ps1 - fast rebuild of the cuvis.pyil SWIG binding for iteration.
#
# Links against the cuvis.lib shipped with the SDK: the CUDA/IPC symbols it lacks are
# resolved at call time by the shims in cuvis_il.i, so no import-lib regeneration is
# needed. First run creates a venv with matching numpy and configures; later runs are
# an incremental build + copy (only a changed .i re-runs SWIG). -Fresh wipes venv+build.
#
#   powershell -ExecutionPolicy Bypass -File build_pyil.ps1
#   powershell -ExecutionPolicy Bypass -File build_pyil.ps1 -Fresh
[CmdletBinding()]
param(
  [string]$Python = "C:\Program Files\Python312\python.exe",
  [string]$Swig   = "C:\swigwin-4.2.1",
  [string]$Venv   = "C:\dev\cuvis_sdk\.venv-pyil312",
  [string]$Numpy  = "2.0.0",
  [string]$CuvisRoot = "C:\Program Files\Cuvis",
  [string]$CuvisLib  = "",
  [string]$CuvisInclude = "",
  [switch]$Fresh
)
$ErrorActionPreference = "Stop"
$pyil = "C:\dev\cuvis_sdk\cuvis.pyil"
$build = Join-Path $pyil "build"
$env:PATH = "$CuvisRoot\bin;$Swig;$env:PATH"
if (-not $CuvisLib) { $CuvisLib = Join-Path $CuvisRoot "sdk\cuvis_c\cuvis.lib" }
if (-not (Test-Path $CuvisLib)) { throw "cuvis.lib not found at $CuvisLib" }
if (-not $CuvisInclude) { $CuvisInclude = Join-Path $CuvisRoot "sdk\cuvis_c" }
if (-not (Test-Path (Join-Path $CuvisInclude "cuvis.h"))) { throw "cuvis.h not found in $CuvisInclude" }
Write-Host "[1] import lib -> $CuvisLib, header -> $CuvisInclude"

# --- 2. venv with matching numpy (create once) ---
if ($Fresh -and (Test-Path $Venv)) { Remove-Item -Recurse -Force $Venv }
if (-not (Test-Path $Venv)) {
  & $Python -m venv $Venv
  & "$Venv\Scripts\python.exe" -m pip install -q -U pip setuptools wheel "numpy==$Numpy"
  Write-Host "[2] created venv $Venv (numpy $Numpy)"
} else {
  Write-Host "[2] reusing venv $Venv"
}

# --- 3. configure once (seed Cuvis_LIBRARY so the stale shipped lib is bypassed) ---
if ($Fresh -and (Test-Path $build)) { Remove-Item -Recurse -Force $build }
if (-not (Test-Path (Join-Path $build "CMakeCache.txt"))) {
  cmake -DCMAKE_BUILD_TYPE=Release -DDOXYGEN_BUILD_DOCUMENTATION=FALSE `
        -DSWIG_EXECUTABLE="$Swig\swig.exe" -DSWIG_DIR="$Swig\Lib" `
        -DPython_ROOT_DIR="$Venv" `
        -DCMAKE_PREFIX_PATH="$CuvisRoot" `
        -DCuvis_INCLUDE_DIR="$CuvisInclude" `
        -DCuvis_LIBRARY="$CuvisLib" `
        -B $build $pyil
  if ($LASTEXITCODE -ne 0) { throw "cmake configure failed ($LASTEXITCODE)" }
  Write-Host "[3] configured -> $build"
} else {
  Write-Host "[3] reusing CMake cache in $build"
}

# --- 4. build (incremental) ---
cmake --build $build --target cuvis_pyil --config Release
if ($LASTEXITCODE -ne 0) { throw "cmake build failed ($LASTEXITCODE)" }
Write-Host "[4] built cuvis_pyil"

# --- 5. copy artifacts into the importable package dir ---
$pyd = Get-ChildItem -Recurse -Path $build -Filter "_cuvis_pyil.pyd" | Select-Object -First 1
$wrp = Get-ChildItem -Recurse -Path $build -Filter "cuvis_il.py"     | Select-Object -First 1
if (-not $pyd) { throw "_cuvis_pyil.pyd not found under $build" }
if (-not $wrp) { throw "cuvis_il.py not found under $build" }
Copy-Item $pyd.FullName "$pyil\cuvis_il\" -Force
Copy-Item $wrp.FullName "$pyil\cuvis_il\" -Force
Write-Host "[5] pyil rebuilt -> $pyil\cuvis_il"
Write-Host ""
Write-Host "To use: keep CUVIS=$CuvisRoot\bin, then"
Write-Host "  `$env:PYTHONPATH='$pyil;C:\dev\cuvis_sdk\cuvis.python'"
Write-Host "  & '$Venv\Scripts\python.exe' <script>"
