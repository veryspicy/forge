@echo off
cd /d D:\codeRepo\forge\frontend
call fnm env --use-on-cd | powershell -Command " | Invoke-Expression"
set NUXT_PUBLIC_API_BASE=http://127.0.0.1:8002
set NUXT_PUBLIC_AI_CHAT_BASE=http://127.0.0.1:8001
call pnpm dev --host 0.0.0.0 --port 3000
