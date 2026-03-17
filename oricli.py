#!/usr/bin/env python3
import argparse
import sys
import json
from oricli_client import OricliClient

def main():
    parser = argparse.ArgumentParser(description="Oricli-Alpha Sovereign CLI")
    parser.add_argument("--url", default="http://localhost:8089", help="Backbone URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # oricli chat
    chat_parser = subparsers.add_parser("chat", help="Interactive chat")
    chat_parser.add_argument("prompt", nargs="?", help="Chat prompt")

    # oricli ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest file or text")
    ingest_parser.add_argument("path", help="File path or raw text")
    ingest_parser.add_argument("--type", choices=["file", "text"], default="file")

    # oricli crawl
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a website")
    crawl_parser.add_argument("url", help="Target URL")
    crawl_parser.add_argument("--pages", type=int, default=5)

    # oricli arc
    arc_parser = subparsers.add_parser("arc", help="Solve ARC-AGI task")
    arc_parser.add_argument("file", help="Path to ARC task JSON")

    # oricli memory
    mem_parser = subparsers.add_parser("memory", help="Search knowledge base")
    mem_parser.add_argument("query", help="Search query")

    args = parser.parse_args()
    client = OricliClient(base_url=args.url)

    if args.command == "chat":
        if args.prompt:
            print(client.chat(args.prompt))
        else:
            print("[*] Entering interactive mode (Ctrl+C to exit)")
            while True:
                try:
                    p = input("oricli> ")
                    if p.strip():
                        print(client.chat(p))
                except KeyboardInterrupt:
                    break

    elif args.command == "ingest":
        if args.type == "file":
            print(json.dumps(client.ingest_file(args.path), indent=2))
        else:
            print(json.dumps(client.ingest_text(args.path), indent=2))

    elif args.command == "crawl":
        print(json.dumps(client.crawl(args.url, args.pages), indent=2))

    elif args.command == "arc":
        with open(args.file, "r") as f:
            task = json.load(f)
        print(json.dumps(client.solve_arc(task), indent=2))

    elif args.command == "memory":
        print(json.dumps(client.memory_search(args.query), indent=2))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
