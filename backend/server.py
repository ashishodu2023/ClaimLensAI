"""
Production server entry point.
uvloop replaces asyncio's default event loop with a faster C implementation
(2-4× higher throughput for I/O-bound workloads like ours).

Usage:
  python backend/server.py              # single process
  python backend/server.py --workers 4  # multi-process (one per CPU core)
"""

import argparse
import multiprocessing
import os
import uvicorn

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',    default='0.0.0.0')
    parser.add_argument('--port',    type=int, default=8000)
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of worker processes (default: 1, set to CPU count for prod)')
    parser.add_argument('--reload',  action='store_true',
                        help='Auto-reload on code changes (dev only)')
    args = parser.parse_args()

    config = dict(
        app='backend.app:app',
        host=args.host,
        port=args.port,
        loop='uvloop',          # 2-4× faster than asyncio default loop
        http='httptools',       # faster HTTP parsing
        workers=args.workers,
        reload=args.reload,
        access_log=True,
        log_level='info',
        # Tuned for high-concurrency
        limit_concurrency=1000,
        backlog=2048,
        timeout_keep_alive=30,
    )

    print(f"Starting server: http://{args.host}:{args.port}")
    print(f"Workers: {args.workers}  |  Loop: uvloop  |  HTTP: httptools")
    print(f"Concurrency limit: {config['limit_concurrency']}")
    print(f"MAX_CONCURRENT_API_CALLS: {os.getenv('MAX_CONCURRENT_API_CALLS', 50)}")
    uvicorn.run(**config)

if __name__ == '__main__':
    main()
