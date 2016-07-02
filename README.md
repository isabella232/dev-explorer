Explore developer clusters
==========================

Setup
-----
```
pip3 install -r requirements.txt
cp config.json{.example,}
```
Change `config.json` as needed.
You must have the pickled clusters. Use the sample k-means file from this repo.

Run
---
```
python3 explorer.py --config config.json
```
Open `http://<host>:<port>/view?dev=mcuadros@gmail.com`.
API is at `json?dev=mcuadros@gmail.com`.
