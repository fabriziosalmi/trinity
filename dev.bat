@echo off
REM dev.bat - Trinity Core Development Helper Script (Windows)
REM Rule #96: Explicit commands with error handling

setlocal enabledelayedexpansion

REM Command router
if "%1"=="" goto :help
if "%1"=="start" goto :start
if "%1"=="stop" goto :stop
if "%1"=="restart" goto :restart
if "%1"=="status" goto :status
if "%1"=="build" goto :build
if "%1"=="build-llm" goto :build_llm
if "%1"=="guardian" goto :guardian
if "%1"=="chaos" goto :chaos
if "%1"=="logs" goto :logs
if "%1"=="shell" goto :shell
if "%1"=="clean" goto :clean
if "%1"=="rebuild" goto :rebuild
if "%1"=="help" goto :help

echo [ERROR] Unknown command: %1
echo.
goto :help

:start
echo [Trinity] Starting Trinity Core services...
docker-compose up -d
timeout /t 3 /nobreak >nul
goto :status

:stop
echo [Trinity] Stopping Trinity Core services...
docker-compose down
echo [SUCCESS] Services stopped
goto :eof

:restart
echo [Trinity] Restarting Trinity Core services...
docker-compose restart
timeout /t 2 /nobreak >nul
goto :status

:status
echo [Trinity] Checking service health...
echo.
docker-compose ps
echo.
echo Testing LM Studio connection...
docker-compose exec -T trinity-builder curl -s http://host.docker.internal:1234/v1/models >nul 2>&1
if %errorlevel%==0 (
    echo [SUCCESS] LM Studio: Connected
) else (
    echo [WARNING] LM Studio: Not reachable
)
echo.
echo Web Server: http://localhost:8080
goto :eof

:build
set theme=%2
if "%theme%"=="" set theme=brutalist
echo [Trinity] Building site with theme: %theme%
docker-compose exec trinity-builder python main.py --demo --theme %theme%
echo [SUCCESS] Build complete! View at: http://localhost:8080
goto :eof

:build_llm
set theme=%2
if "%theme%"=="" set theme=brutalist
echo [Trinity] Building with LLM content generation...
docker-compose exec trinity-builder python main.py --use-llm --theme %theme%
echo [SUCCESS] LLM build complete! View at: http://localhost:8080
goto :eof

:guardian
set theme=%2
if "%theme%"=="" set theme=brutalist
echo [Trinity] Running Guardian QA inspection...
docker-compose exec trinity-builder python main.py --demo --theme %theme% --guardian
echo [SUCCESS] Guardian inspection complete!
goto :eof

:chaos
echo [Trinity] Running CHAOS TEST with Guardian...
docker-compose exec trinity-builder python main.py --static-json --input data/chaos_content.json --theme brutalist --guardian --guardian-only-dom
echo [SUCCESS] Chaos test complete!
goto :eof

:logs
set service=%2
if "%service%"=="" set service=trinity-builder
echo [Trinity] Tailing logs for: %service%
docker-compose logs -f %service%
goto :eof

:shell
echo [Trinity] Opening shell in builder container...
docker-compose exec trinity-builder /bin/bash
goto :eof

:clean
echo [Trinity] Cleaning generated files...
del /q output\*.html 2>nul
del /q logs\*.log 2>nul
echo [SUCCESS] Clean complete
goto :eof

:rebuild
echo [Trinity] Rebuilding Docker images...
docker-compose build --no-cache
echo [SUCCESS] Rebuild complete
goto :eof

:help
echo Trinity Core - Development Script (Windows)
echo.
echo USAGE:
echo     dev.bat ^<command^> [arguments]
echo.
echo COMMANDS:
echo     start               Start all services (builder + web)
echo     stop                Stop all services
echo     restart             Restart all services
echo     status              Check service health
echo.
echo     build [theme]       Build with demo data (default: brutalist)
echo     build-llm [theme]   Build with LLM content generation
echo     guardian [theme]    Run Guardian QA inspection
echo     chaos               Run chaos test with broken layout
echo.
echo     logs [service]      Tail logs (default: trinity-builder)
echo     shell               Open bash shell in builder container
echo     clean               Remove generated files
echo     rebuild             Rebuild Docker images
echo.
echo     help                Show this help message
echo.
echo EXAMPLES:
echo     dev.bat start
echo     dev.bat build brutalist
echo     dev.bat build-llm editorial
echo     dev.bat guardian
echo     dev.bat chaos
echo.
echo URLS:
echo     Web Server:  http://localhost:8080
echo     LM Studio:   http://192.168.100.12:1234
echo.
goto :eof
