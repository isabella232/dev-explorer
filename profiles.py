import argparse
from itertools import chain
import json
import logging
import pickle

from flask import Blueprint, Flask, request, Response, render_template

bp = Blueprint("suburi", "suburi", template_folder="templates")


def get_data(dev):
    devobj = bp.db.people.find_one(
        {"email": {"$elemMatch": {"address": {"$eq": dev}}}},
        projection=[])
    if devobj is None:
        return "", 404
    try:
        cluster = bp.reversed_clusters[int(str(devobj["_id"]), 16)]
    except KeyError:
        return "", 404
    dev_ids = [ObjectId(hex(i)[2:]) for i in bp.clusters[cluster]]
    neighbors = list(bp.db.people.find({"_id": {"$in": dev_ids}}, FIELDS))
    emails = list(chain.from_iterable((
                                          e["address"] for e in n["email"]) for
                                      n in neighbors))
    proposals = bp.db.proposals.find(
        {"email": {"$in": emails}},
        {"email": True, "conversation": True})
    proposals = {p["email"]: bool(p["conversation"].get("messages", False))
                 for p in proposals}
    data = [cook(n, proposals) for n in neighbors]
    data.sort(key=lambda d: d["id"])
    result = {"nodes": data, "tsne": tsne(data)}


@bp.route("/json", methods=["POST", "GET"])
def lookup_developer():
    if request.method == "POST":
        dev = json.loads(request.data)["dev"]
    else:
        dev = request.args["dev"]
    data = get_data(dev)
    response = Response(response=json.dumps(result, default=json_util.default),
                        mimetype="application/json")
    return response


@bp.route("/view", methods=["GET"])
def view_cluster():
    dev = request.args["dev"]
    return render_template("view_cluster.html", dev=dev)


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
    return args, config


def connect_to_mongo(config):
    client = MongoClient(**config["@"])
    db = getattr(client, config["db"])
    people = getattr(db, config["collections"]["people"])
    proposals = getattr(db, config["collections"]["proposals"])
    return Collections(people, proposals)


def load_pickle(fn):
    with open(fn, "rb") as fin:
        return pickle.load(fin)


def setup_clusters(fn):
    bp.clusters = load_pickle(fn)
    bp.reversed_clusters = rc = {}
    for i, devs in bp.clusters.items():
        for d in devs:
            bp.reversed_clusters[d] = i


def main():
    args, config = setup()
    bp.db = connect_to_mongo(config["mongo"])
    setup_clusters(config["clusters"])
    app = Flask("DevExplorer")
    app.register_blueprint(bp, uri_prefix=config.get("prefix"))
    app.run(host=args.host, port=args.port, debug=config.get("debug", False),
            **config.get("extra", {}))

if __name__ == "__main__":
    main()