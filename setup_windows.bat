@echo off
REM Enhanced Spotify Voice Assistant - Windows Setup Script
REM Automated setup for Windows with wake word "jarvis"

echo 🎤 Setting up Enhanced Spotify Voice Assistant for Windows...
echo ✨ Features: Wake word 'jarvis', persistent calibration, background mode
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH.
    echo Please install Python from https://python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo ✅ Python detected: 
python --version

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is not available. Please reinstall Python with pip included.
    pause
    exit /b 1
)

echo ✅ pip detected: 
pip --version
echo.

REM Create virtual environment
if not exist "venv" (
    set /p venvcreate="🐍 Create Python virtual environment? [Y/n] "
    if /i "%venvcreate%"=="n" (
        echo ⚠️  Skipping venv creation. Using system Python.
    ) else (
        echo Creating virtual environment...
        python -m venv venv
        echo ✅ Virtual environment created.
    )
) else (
    echo ✅ Virtual environment already exists.
)

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install Python dependencies
set /p pydeps="📦 Install Python dependencies? [Y/n] "
if /i "%pydeps%"=="n" (
    echo ⚠️  Skipping Python dependency installation.
) else (
    echo Installing Python dependencies...
    python -m pip install --upgrade pip
    
    REM Try to install from requirements.txt, fallback to individual packages
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ⚠️  requirements.txt failed, trying individual packages...
        pip install spotipy SpeechRecognition pyttsx3 python-dotenv colorama psutil
        
        REM Try to install PyAudio (might need special handling on Windows)
        echo Attempting to install PyAudio...
        pip install pyaudio
        if errorlevel 1 (
            echo ⚠️  PyAudio installation failed. Trying alternative method...
            pip install pipwin
            pipwin install pyaudio
            if errorlevel 1 (
                echo ❌ PyAudio installation failed. You may need to:
                echo 1. Install Microsoft Visual C++ Build Tools
                echo 2. Download PyAudio wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
                echo 3. Install manually: pip install downloaded_wheel.whl
            )
        )
        
        REM Install Windows-specific notification libraries
        echo Installing Windows notification support...
        pip install plyer win10toast
    )
)

REM Check for Spotify installation
echo.
echo 🎵 Checking for Spotify installation...

REM Check common Spotify locations
set spotify_found=0

if exist "%APPDATA%\Spotify\Spotify.exe" (
    echo ✅ Spotify found: %APPDATA%\Spotify\Spotify.exe
    set spotify_found=1
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe" (
    echo ✅ Spotify found: Windows Store version
    set spotify_found=1
)

if exist "C:\Program Files\Spotify\Spotify.exe" (
    echo ✅ Spotify found: C:\Program Files\Spotify\Spotify.exe
    set spotify_found=1
)

if %spotify_found%==0 (
    echo ❌ Spotify not found.
    set /p installspotify="Install Spotify? [Y/n] "
    if /i "%installspotify%"=="n" (
        echo ⚠️  Please install Spotify manually from:
        echo   - https://www.spotify.com/download/windows/
        echo   - Microsoft Store
        echo   - winget install Spotify.Spotify
    ) else (
        echo Opening Spotify download page...
        start https://www.spotify.com/download/windows/
    )
)

REM Create env/.env file if it doesn't exist
if not exist "env" mkdir env
if not exist "env\.env" (
    if exist "env\.env.template" (
        set /p envfile="📝 Create env\.env file from template? [Y/n] "
        if /i "%envfile%"=="n" (
            echo ⚠️  Skipping .env file creation.
        ) else (
            copy "env\.env.template" "env\.env"
            echo ✅ Created env\.env file. Please edit it with your credentials.
        )
    ) else (
        echo Creating basic .env file...
        echo SPOTIFY_CLIENT_ID=your_client_id_here > env\.env
        echo SPOTIFY_CLIENT_SECRET=your_client_secret_here >> env\.env
        echo SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback >> env\.env
        echo ✅ Created basic env\.env file. Please edit it with your credentials.
    )
) else (
    echo ✅ env\.env file already exists.
)

echo.
echo 🎉 Setup complete!
echo.
echo 📋 Next steps:
echo 1. Edit the env\.env file with your Spotify credentials:
echo    notepad env\.env
echo.
echo 2. Get Spotify API credentials:
echo    - Go to https://developer.spotify.com/dashboard/
echo    - Create a new app named 'Enhanced Voice Assistant'
echo    - Copy Client ID and Client Secret to .env
echo    - Add redirect URI: http://127.0.0.1:8080/callback
echo.
echo 3. Start the enhanced voice assistant:
echo    python -m app.main
echo.
echo 🎤 Enhanced voice commands (wake word: 'jarvis'^):
echo    Wake word: Say 'jarvis' to activate, then:
echo    - 'play Hotel California by Eagles' - Play specific song
echo    - 'play Bohemian Rhapsody' - Play song (artist optional^)
echo    - 'pause' - Pause playback
echo    - 'next track' - Skip to next
echo    - 'previous' - Go to previous track
echo    - 'volume up/down' - Adjust volume
echo    - 'what's playing' - Get current track info
echo    - 'quit' - Stop the assistant
echo.
echo 🔧 System commands:
echo    - Ctrl+C → Switch to text mode
echo    - Type 'voice' → Return to voice mode
echo    - Type 'wake' → Change wake word
echo    - Type 'recalibrate' → Redo voice setup
echo.
echo 🎛️ Smart features:
echo    - ✅ One-time voice calibration (remembers your settings^)
echo    - ✅ Auto-fallback to text mode when voice fails
echo    - ✅ Windows notifications for background operation
echo    - ✅ Wake word detection with no external dependencies
echo    - ✅ Cross-platform support (Windows, Linux, macOS^)
echo.

pause
