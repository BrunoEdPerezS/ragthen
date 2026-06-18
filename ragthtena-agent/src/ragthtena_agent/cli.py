"""Raghtena CLI — RAG agent with local/remote backends."""

import os
import sys
import json
import argparse
from pathlib import Path

from ragthtena_core.config import load_config, CONFIG_FILE, LIBRARIES_DIR
from ragthtena_agent.backends import LocalBackend, RemoteBackend
from ragthtena_agent import vault as vlt

_log_tag = "[ragthtena]"


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def _get_backend():
    cfg = load_config()
    mode = cfg.get("backend_mode", "local")
    if mode == "remote":
        return RemoteBackend()
    return LocalBackend()


def _auto_lib(backend) -> str | None:
    lib_dir = LIBRARIES_DIR
    if lib_dir.exists():
        names = sorted(
            d.name for d in lib_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")
        )
        if len(names) == 1:
            return names[0]
    return None


def _handle_vault_ingest(args):
    vault_path = vlt.resolve(args.vault)
    if not vault_path:
        print(f"{_log_tag} No vault path set. Use --vault PATH or add 'vault_path' to {CONFIG_FILE}")
        return

    lib_name = args.library or _auto_lib(_get_backend())
    if not lib_name:
        print(f"{_log_tag} No library specified. Use -l NAME.")
        return

    notes = vlt.scan_notes(vault_path)
    if not notes:
        print(f"{_log_tag} No notes found in vault: {vault_path}")
        return

    flat = sorted(p for paths in notes.values() for p in paths)
    vault_p = Path(vault_path)
    lib_dir = LIBRARIES_DIR / lib_name
    lib_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for fp in flat:
        rel = fp.relative_to(vault_p).with_suffix("")
        dest = lib_dir / f"_vault_{str(rel).replace(chr(92), '_').replace('/', '_')}.md"
        content = vlt.read_note(str(vault_p), str(rel))
        if content is None:
            continue
        dest.write_text(content, encoding="utf-8")
        copied += 1

    print(f"{_log_tag} Copied {copied} notes from vault to library '{lib_name}'")

    backend = _get_backend()
    backend.ingest(lib_name)
    print(f"{_log_tag} Vault ingest complete — all {copied} notes indexed into '{lib_name}'.")


def main():
    parser = argparse.ArgumentParser(description="Raghtena — Multi-library RAG agent")
    parent_lib = argparse.ArgumentParser(add_help=False)
    parent_lib.add_argument("-l", "--library", metavar="NAME",
                            help="Library name under ~/.ragthtena/libraries/")
    parent_vault = argparse.ArgumentParser(add_help=False)
    parent_vault.add_argument("--vault", metavar="PATH", default="",
                              help="Obsidian vault path (or set in config.json)")

    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("ingest", parents=[parent_lib],
                   help="Index all PDFs/TXTs/MDs in a library")
    p_search = sub.add_parser("search", parents=[parent_lib],
                              help="Semantic search (returns JSON context)")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--top", type=int, default=5)
    p_search.add_argument("--relevance-threshold", type=float, default=0.0)
    p_search.add_argument("--rerank", action="store_true",
                          help="Enable cross-encoder reranking")
    p_ask = sub.add_parser("ask", parents=[parent_lib],
                           help="Full RAG answer via LLM")
    p_ask.add_argument("query", help="Your question")
    p_ask.add_argument("--api-key", help="OpenAI key (or set env OPENAI_API_KEY)")
    p_ask.add_argument("--model", default="gpt-4o")
    sub.add_parser("status", parents=[parent_lib], help="Show library index status")
    sub.add_parser("clear", parents=[parent_lib], help="Delete the library index")
    sub.add_parser("libraries", help="List all available libraries")
    sub.add_parser("config", help="Show config path and current settings")

    p_vault = sub.add_parser("vault", help="Obsidian vault operations")
    vault_sub = p_vault.add_subparsers(dest="vault_cmd")
    vault_sub.add_parser("ingest", parents=[parent_lib, parent_vault],
                         help="Ingest all vault notes into a library")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return

    if args.cmd == "libraries":
        backend = _get_backend()
        backend.list_libraries()
        return

    if args.cmd == "config":
        cfg = load_config()
        print(f"{_log_tag} Config file: {CONFIG_FILE}")
        print(f"{_log_tag} Libraries path: {LIBRARIES_DIR}")
        print(json.dumps(cfg, indent=2, ensure_ascii=False))
        return

    if args.cmd == "vault":
        if args.vault_cmd == "ingest":
            _handle_vault_ingest(args)
            return
        p_vault.print_help()
        return

    backend = _get_backend()

    if args.cmd == "ingest":
        backend.ingest(args.library)
    elif args.cmd == "search":
        results = backend.search(args.query, args.library, top_k=args.top,
                                 relevance_threshold=args.relevance_threshold,
                                 rerank=args.rerank)
        _safe_print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.cmd == "ask":
        key = args.api_key or os.environ.get("OPENAI_API_KEY")
        _safe_print(backend.ask(args.query, args.library, api_key=key, model=args.model))
    elif args.cmd == "status":
        backend.status(args.library)
    elif args.cmd == "clear":
        backend.clear(args.library)


if __name__ == "__main__":
    main()
