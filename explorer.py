import argparse
from collections import defaultdict
from itertools import chain
import json
import logging
import pickle

from flask import Blueprint, Flask, request, Response, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import json_util, codec_options
import numpy
from sklearn.manifold import TSNE

bp = Blueprint("suburi", "suburi", template_folder="templates")

FIELDS = ["email", "location", "personal", "profiles", "skills", "pagerank"]
CUT = 20


def cook(dev, scheme):
    p = {k: dev.get(k) for k in FIELDS}
    p["id"] = str(dev["_id"])
    p["scheme"] = scheme
    return p


def dev_id(dev):
    return dev["_id"].binary


def refine(devs, scheme, me):
    features = bp.features[scheme]
    id2index = bp.id2index[scheme]
    samples = numpy.zeros((len(devs), features.shape[-1]))
    for i, dev in enumerate(devs):
        samples[i] = features[id2index[dev_id(dev)]]
    my_features = features[id2index[dev_id(me)]]
    dists = [(d, i) for i, d in enumerate(numpy.arccos(numpy.minimum(
        samples.dot(my_features), 1)))]
    dists.sort()
    for j, (_, i) in enumerate(dists[:CUT]):
        samples[j] = features[id2index[dev_id(devs[i])]]
    model = TSNE(random_state=777)
    positions = model.fit_transform(samples[:CUT])
    positions /= numpy.max(numpy.abs(positions))
    return [(p[0], p[1]) for p in positions], [devs[i] for _, i in dists[:CUT]]


@bp.route("/json", methods=["POST", "GET"])
def lookup_developer():
    if request.method == "POST":
        dev = json.loads(request.data)["dev"]
    else:
        dev = request.args["dev"]
    devobj = bp.db.find_one(
        {"email": {"$elemMatch": {"address": {"$eq": dev}}}},
        projection=[])
    if devobj is None:
        return "", 404
    data = []
    for scheme, clusters in sorted(bp.clusters.items()):
        cluster = clusters[bp.id2index[scheme][dev_id(devobj)]]
        dev_ids = [ObjectId(bp.index2id[scheme][i])
                   for i in bp.reversed_clusters[scheme][cluster]]
        neighbors = list(bp.db.find({"_id": {"$in": dev_ids}}, FIELDS))
        neighbors.sort(key=lambda d: d["_id"])
        positioned, reduced_neighbors = refine(neighbors, scheme, devobj)
        cooked = [cook(n, scheme) for n in reduced_neighbors]
        data.append((cooked, positioned))
    result = {"nodes": list(chain.from_iterable(d[0] for d in data)),
              "tsne": list(chain.from_iterable(d[1] for d in data))}
    response = Response(response=json.dumps(result, default=json_util.default),
                        mimetype="application/json")
    return response


@bp.route("/view", methods=["GET"])
def view_cluster():
    dev = request.args["dev"]
    scheme = request.args["map"]
    return render_template("view_cluster.html", dev=dev, map=scheme)


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "-o", default="0.0.0.0")
    parser.add_argument("--port", "-p", type=int, default=8080)
    parser.add_argument("--config", "-c", required=True)
    parser.add_argument("--level", "-l", choices=logging._nameToLevel.keys(),
                        default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.level))
    with open(args.config) as fin:
        config = json.load(fin)
    return args, config, logging.getLogger("app")


def connect_to_mongo(config):
    client = MongoClient(**config["@"])
    db = getattr(client, config["db"])
    people = getattr(db, config["collections"]["people"])
    people = people.with_options(
        codec_options=codec_options.CodecOptions(
        unicode_decode_error_handler="ignore"))
    return people


class MacOSFile(object):
    def __init__(self, f):
        self.f = f

    def __getattr__(self, item):
        return getattr(self.f, item)

    def read(self, n):
        if n >= (1 << 31):
            buffer = bytearray(n)
            pos = 0
            while pos < n:
                size = min(n - pos, 1 << 31 - 1)
                chunk = self.f.read(size)
                buffer[pos:pos + size] = chunk
                pos += size
            return buffer
        return self.f.read(n)


def load_pickle(fn, log):
    log.info("loading %s...", fn)
    with open(fn, "rb") as fin:
        return pickle.load(MacOSFile(fin))


def setup_clusters(clusters, log):
    bp.index2id = {}
    bp.id2index = {}
    bp.features = {}
    bp.clusters = {}
    bp.reversed_clusters = {}
    for scheme, fn in clusters.items():
        index2id, bp.features[scheme], clusters = load_pickle(fn, log)
        bp.index2id[scheme] = index2id
        bp.id2index[scheme] = {k: i for i, k in enumerate(index2id)}
        bp.clusters[scheme] = clusters
        bp.reversed_clusters[scheme] = rc = defaultdict(list)
        for dev, cli in enumerate(clusters):
            rc[cli].append(dev)


def main():
    args, config, log = setup()
    log.info("connecting to MongoDB...")
    bp.db = connect_to_mongo(config["mongo"])
    setup_clusters(config["clusters"], log)
    log.info("starting the web server...")
    app = Flask("DevExplorer")
    app.register_blueprint(bp, uri_prefix=config.get("prefix"))
    app.run(host=args.host, port=args.port, debug=config.get("debug", False),
            **config.get("extra", {}))

if __name__ == "__main__":
    main()
