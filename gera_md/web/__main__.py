# -*- coding: utf-8 -*-
"""Frontend web local do Gera Documents.

Uso:
    python -m gera_md.web            → sobe o servidor e abre o navegador
    python -m gera_md.web --sem-navegador --porta 8800
    (ou dois cliques em "Gera Documents.cmd")

Roda só nesta máquina (127.0.0.1); o link aberto no navegador traz o acesso da
sessão. A revisão com IA usa por padrão o Claude da assinatura Pro/Max, pelo login
do Claude Code (confira com `claude auth status --text`) — sem chave de API e sem
cobrança extra. O acesso por API é opcional, separado e cobrado por uso.
"""

import argparse
import os
import socket
import sys
import threading
import webbrowser

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HOST = "127.0.0.1"
PORTA_PREFERIDA = 8765


def porta_livre(preferida=PORTA_PREFERIDA, tentativas=50):
    for porta in range(preferida, preferida + tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, porta))
            except OSError:
                continue
            return porta
    raise SystemExit(f"Nenhuma porta livre entre {preferida} e {preferida + tentativas - 1}.")


def main():
    ap = argparse.ArgumentParser(description="Frontend web local do Gera Documents")
    ap.add_argument("--porta", type=int, default=PORTA_PREFERIDA)
    ap.add_argument("--sem-navegador", action="store_true")
    args = ap.parse_args()

    try:
        import uvicorn
    except ImportError:
        raise SystemExit("Faltam dependências. Execute: pip install -r requirements.txt")
    from gera_md.web.app import criar_app
    from gera_md.web.seguranca import gerar_token

    porta = porta_livre(args.porta)
    token = gerar_token()
    url = f"http://{HOST}:{porta}/?t={token}"
    app = criar_app(token, porta)

    print("Gera Documents — frontend local", flush=True)
    print(f"  Abra: {url}", flush=True)
    print("  (o link só funciona nesta máquina; Ctrl+C para sair)", flush=True)
    if not args.sem_navegador:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=HOST, port=porta, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
