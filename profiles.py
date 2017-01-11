import argparse
from io import BytesIO
import logging
import pickle

from flask import Blueprint, Flask, request, make_response, render_template
import numpy
import matplotlib
matplotlib.use("Cairo")
import matplotlib.pyplot as pyplot


bp = Blueprint("suburi", "suburi", template_folder="templates")


class Data(object):
    pass


def render_image(image):
    figure = pyplot.figure()
    axes = figure.add_axes((0, 0, 1, 1))
    axes.imshow(image, interpolation="nearest", cmap=bp.data.cmap,
                origin="lower")
    axes.set_axis_off()
    file = BytesIO()
    figure.savefig(file, format="png", bbox_inches=0)
    file.seek(0)
    response = make_response(file.getvalue())
    response.headers["Content-Type"] = "image/png"
    response.headers["Content-Disposition"] = "attachment; filename=image.png"
    return response


@bp.route("/image/topics/<int:dev>.png", methods=["GET"])
def image_topics(dev):
    image_topics = numpy.zeros((64, 64), dtype=numpy.float32)
    dev = bp.data.labels[dev]
    for ri in dev.indices:
        topic_cluster = bp.data.topics_clusters[bp.data.topic_index_map[ri]]
        topic_pos = (bp.data.grid_topics[topic_cluster] * 63).astype(int)
        image_topics[tuple(topic_pos)] += dev[0, ri]
    return render_image(image_topics)


@bp.route("/image/langs/<int:dev>.png", methods=["GET"])
def image_langs(dev):
    image_langs = numpy.zeros((64, 64), dtype=numpy.float32)
    dev = bp.data.labels[dev]
    for ri in dev.indices:
        lang_cluster = bp.data.langs_clusters[ri]
        lang_pos = (bp.data.grid_langs[lang_cluster] * 63).astype(int)
        image_langs[tuple(lang_pos)] += dev[0, ri]
    return render_image(image_langs)


@bp.route("/view", methods=["GET"])
def view_cluster():
    email = request.args["dev"]
    index = bp.data.emails[email]
    repos = bp.data.labels[index]
    return render_template("view_profile.html", dev_email=email,
                           dev_index=index, dev_repos=len(repos.indices))


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic-clusters", required=True)
    parser.add_argument("--lang-clusters", required=True)
    parser.add_argument("--topic-lap", required=True)
    parser.add_argument("--lang-lap", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--emails", required=True)
    parser.add_argument("--topic-index-map", required=True)
    parser.add_argument("--cmap", default="Blues")
    parser.add_argument("--host", "-o", default="0.0.0.0")
    parser.add_argument("--port", "-p", type=int, default=8080)
    parser.add_argument("--prefix")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", "-l", choices=logging._nameToLevel.keys(),
                        default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.level))
    return args, logging.getLogger("app")


def load_pickle(fn, logger):
    logger.info("loading %s...", fn)
    with open(fn, "rb") as fin:
        return pickle.load(fin)


def load_data(args, logger):
    data = Data()
    _, data.topics_clusters = load_pickle(args.topic_clusters, logger)
    _, data.langs_clusters = load_pickle(args.lang_clusters, logger)
    grid = numpy.dstack(numpy.meshgrid(
        numpy.linspace(0, 1, 64), numpy.linspace(0, 1, 64))).reshape(-1, 2)
    _, col_ind_topics = load_pickle(args.topic_lap, logger)
    data.grid_topics = grid[col_ind_topics]
    _, col_ind_langs = load_pickle(args.lang_lap, logger)
    data.grid_langs = grid[col_ind_langs]
    data.labels = load_pickle(args.labels, logger).T.tocsr()
    data.emails = load_pickle(args.emails, logger)
    data.topic_index_map = load_pickle(args.topic_index_map, logger)
    data.cmap = args.cmap
    return data


def main():
    args, logger = setup()
    bp.data = load_data(args, logger)
    logger.info("starting the application...")
    app = Flask("DevProfiler")
    app.register_blueprint(bp, uri_prefix=args.prefix)
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
