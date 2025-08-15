# Enhanced Spotify Voice Assistant - PowerShell Setup Script
# Automated setup for Windows with enhanced error handling

param(
    [switch]$SkipDependencies,
    [switch]$SkipSpotifyCheck,
    [switch]$NoVenv
)

Write-Host "🎤 Enhanced Spotify Voice Assistant - Windows Setup" -ForegroundColor Cyan
Write-Host "✨ Features: Wake word 'jarvis', persistent calibration, Windows notifications" -ForegroundColor Green
Write-Host ""

# Function to check if a command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check Python installation
if (-not (Test-Command python)) {
    Write-Host "❌ Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Python detected: $(python --version)" -ForegroundColor Green

# Check pip
if (-not (Test-Command pip)) {
    Write-Host "❌ pip is not available. Please reinstall Python with pip included." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ pip detected: $(pip --version)" -ForegroundColor Green
Write-Host ""

# Create virtual environment
if (-not $NoVenv -and -not (Test-Path "venv")) {
    $venvcreate = Read-Host "🐍 Create Python virtual environment? [Y/n]"
    if ($venvcreate -eq "n" -or $venvcreate -eq "N") {
        Write-Host "⚠️  Skipping venv creation. Using system Python." -ForegroundColor Yellow
    } else {
        Write-Host "Creating virtual environment..." -ForegroundColor Blue
        python -m venv venv
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Virtual environment created." -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to create virtual environment." -ForegroundColor Red
        }
    }
} elseif (Test-Path "venv") {
    Write-Host "✅ Virtual environment already exists." -ForegroundColor Green
}

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Blue
    & "venv\Scripts\Activate.ps1"
}

# Install dependencies
if (-not $SkipDependencies) {
    $pydeps = Read-Host "📦 Install Python dependencies? [Y/n]"
    if ($pydeps -ne "n" -and $pydeps -ne "N") {
        Write-Host "Installing Python dependencies..." -ForegroundColor Blue
        
        # Upgrade pip
        python -m pip install --upgrade pip
        
        # Try requirements.txt first
        if (Test-Path "requirements.txt") {
            Write-Host "Installing from requirements.txt..." -ForegroundColor Blue
            pip install -r requirements.txt
            if ($LASTEXITCODE -ne 0) {
                Write-Host "⚠️  requirements.txt failed, trying individual packages..." -ForegroundColor Yellow
            }
        }
        
        # Install core packages individually
        $packages = @("spotipy", "SpeechRecognition", "pyttsx3", "python-dotenv", "colorama", "psutil")
        foreach ($package in $packages) {
            Write-Host "Installing $package..." -ForegroundColor Blue
            pip install $package
        }
        
        # Special handling for PyAudio on Windows
        Write-Host "Installing PyAudio (may require Visual C++ Build Tools)..." -ForegroundColor Blue
        pip install pyaudio
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  PyAudio installation failed. Trying alternative method..." -ForegroundColor Yellow
            pip install pipwin
            if ($LASTEXITCODE -eq 0) {
                pipwin install pyaudio
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "❌ PyAudio installation failed with pipwin too." -ForegroundColor Red
                }
            }
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ PyAudio installation failed. Manual steps required:" -ForegroundColor Red
                Write-Host "1. Install Microsoft Visual C++ Build Tools" -ForegroundColor Yellow
                Write-Host "2. Or download PyAudio wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor Yellow
                Write-Host "3. Install manually: pip install downloaded_wheel.whl" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✅ PyAudio installed successfully." -ForegroundColor Green
        }
        
        # Install Windows notification libraries
        Write-Host "Installing Windows notification support..." -ForegroundColor Blue
        pip install plyer win10toast
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Windows notification libraries installed." -ForegroundColor Green
        } else {
            Write-Host "⚠️  Notification libraries installation failed (optional)." -ForegroundColor Yellow
        }
    }
}

# Check for Spotify installation
if (-not $SkipSpotifyCheck) {
    Write-Host ""
    Write-Host "🎵 Checking for Spotify installation..." -ForegroundColor Blue
    
    $spotifyPaths = @(
        "$env:APPDATA\Spotify\Spotify.exe",
        "$env:LOCALAPPDATA\Microsoft\WindowsApps\Spotify.exe",
        "C:\Program Files\Spotify\Spotify.exe",
        "C:\Program Files (x86)\Spotify\Spotify.exe"
    )
    
    $spotifyFound = $false
    foreach ($path in $spotifyPaths) {
        if (Test-Path $path) {
            Write-Host "✅ Spotify found: $path" -ForegroundColor Green
            $spotifyFound = $true
            break
        }
    }
    
    if (-not $spotifyFound) {
        Write-Host "❌ Spotify not found." -ForegroundColor Red
        $installSpotify = Read-Host "Open Spotify download page? [Y/n]"
        if ($installSpotify -ne "n" -and $installSpotify -ne "N") {
            Write-Host "Opening Spotify download page..." -ForegroundColor Blue
            Start-Process "https://www.spotify.com/download/windows/"
        } else {
            Write-Host "⚠️  Please install Spotify manually:" -ForegroundColor Yellow
            Write-Host "  - https://www.spotify.com/download/windows/" -ForegroundColor Yellow
            Write-Host "  - Microsoft Store" -ForegroundColor Yellow
            Write-Host "  - winget install Spotify.Spotify" -ForegroundColor Yellow
        }
    }
}

# Create env directory and .env file
if (-not (Test-Path "env")) {
    New-Item -ItemType Directory -Path "env" | Out-Null
}

if (-not (Test-Path "env\.env")) {
    if (Test-Path "env\.env.template") {
        $envfile = Read-Host "📝 Create env\.env file from template? [Y/n]"
        if ($envfile -ne "n" -and $envfile -ne "N") {
            Copy-Item "env\.env.template" "env\.env"
            Write-Host "✅ Created env\.env file. Please edit it with your credentials." -ForegroundColor Green
        }
    } else {
        Write-Host "Creating basic .env file..." -ForegroundColor Blue
        @"
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback
"@ | Set-Content "env\.env"
        Write-Host "✅ Created basic env\.env file. Please edit it with your credentials." -ForegroundColor Green
    }
} else {
    Write-Host "✅ env\.env file already exists." -ForegroundColor Green
}

# Display completion message
Write-Host ""
Write-Host "🎉 Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit the env\.env file with your Spotify credentials:" -ForegroundColor White
Write-Host "   notepad env\.env" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Get Spotify API credentials:" -ForegroundColor White
Write-Host "   - Go to https://developer.spotify.com/dashboard/" -ForegroundColor Yellow
Write-Host "   - Create a new app named 'Enhanced Voice Assistant'" -ForegroundColor Yellow
Write-Host "   - Copy Client ID and Client Secret to .env" -ForegroundColor Yellow
Write-Host "   - Add redirect URI: http://127.0.0.1:8080/callback" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Start the enhanced voice assistant:" -ForegroundColor White
Write-Host "   python -m app.main" -ForegroundColor Yellow
Write-Host ""
Write-Host "🎤 Voice commands (wake word: 'jarvis'):" -ForegroundColor Cyan
Write-Host "   - 'jarvis' → 'play Hotel California by Eagles'" -ForegroundColor White
Write-Host "   - 'jarvis' → 'pause' / 'next track' / 'previous'" -ForegroundColor White
Write-Host "   - 'jarvis' → 'what's playing' / 'volume up'" -ForegroundColor White
Write-Host ""
Write-Host "🔧 System commands:" -ForegroundColor Cyan
Write-Host "   - Ctrl+C → Switch to text mode" -ForegroundColor White
Write-Host "   - Type 'voice' → Return to voice mode" -ForegroundColor White
Write-Host "   - Type 'wake' → Change wake word" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
