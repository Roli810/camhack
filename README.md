Vibecoded trash - but at least it works.

RTSP Camera Discovery & Audit Tool
A two-stage pipeline for RTSP stream security auditing. Built in a weekend as a learning project.

zoomeye.py — queries ZoomEye's API (cookie-based auth, base64-encoded queries, pagination) to enumerate exposed RTSP endpoints matching a given filter
radar.py — wraps the cameradar Docker image, parallelizes scans with ThreadPoolExecutor, handles output parsing and ANSI stripping
Intended for use on infrastructure you own or have written authorization to test.

How to use:

Log into zoomeye's website

copy cookies into a cookies.json in the same folder as this

adjust query parameter in zoomeye.py

run zoomeye.py 

run radar.py
