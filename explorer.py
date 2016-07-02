import argparse
import json
import logging
import pickle

from flask import Blueprint, Flask, request, Response, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import json_util
import numpy
from sklearn.manifold import TSNE

bp = Blueprint("suburi", "suburi", template_folder="templates")

FIELDS = ["email", "location", "personal", "profiles", "skills", "pagerank"]
LANGUAGES = {"Linker Script": 194, "Opa": 253, "Slim": 337, "Stan": 343, "Eiffel": 94, "JSON5": 167, "Ox": 260, "PureScript": 293, "AutoHotkey": 23, "POV-Ray SDL": 267, "PAWN": 263, "CartoCSS": 49, "Factor": 103, "eC": 399, "Prolog": 286, "Sage": 325, "Moocode": 229, "ActionScript": 8, "desktop": 398, "Unity3D Asset": 366, "JavaScript": 175, "Oxygene": 261, "Haskell": 149, "Less": 190, "Csound Document": 70, "Thrift": 360, "Pan": 268, "BitBake": 29, "LabVIEW": 186, "LookML": 203, "Limbo": 193, "FreeMarker": 109, "Python": 294, "Max": 219, "AMPL": 2, "edn": 400, "Emacs Lisp": 97, "C": 37, "SystemVerilog": 349, "World of Warcraft Addon Data": 382, "Gradle": 128, "Ruby": 314, "Forth": 108, "Omgrofl": 252, "HTML+EEX": 141, "Elixir": 95, "J": 164, "Vala": 372, "Lex": 191, "xBase": 407, "Stata": 345, "GLSL": 116, "Arduino": 18, "DTrace": 81, "Raw token data": 306, "Puppet": 290, "Java Server Pages": 174, "Protocol Buffer": 288, "Frege": 110, "HTML+PHP": 143, "Diff": 84, "MediaWiki": 220, "ATS": 7, "Twig": 363, "CoffeeScript": 59, "C2hs Haskell": 41, "LiveScript": 200, "Crystal": 68, "KRL": 178, "Clarion": 55, "Jade": 171, "Common Lisp": 62, "IDL": 153, "Python traceback": 295, "Io": 160, "Ninja": 242, "Ioke": 161, "HTTP": 144, "Elm": 96, "RMarkdown": 303, "Isabelle ROOT": 163, "Isabelle": 162, "AppleScript": 16, "Mathematica": 216, "Formatted": 107, "NL": 233, "PogoScript": 281, "Uno": 367, "Stylus": 346, "Fancy": 104, "Lean": 189, "Inform 7": 158, "Smarty": 340, "Zimpl": 397, "Nginx": 240, "DNS Zone": 80, "Logtalk": 202, "X10": 383, "Haml": 146, "MiniD": 223, "AspectJ": 20, "YANG": 394, "VCL": 370, "Logos": 201, "ObjDump": 248, "Perl": 274, "NetLogo": 238, "HLSL": 137, "TypeScript": 364, "Gosu": 126, "VHDL": 371, "Grammatical Framework": 129, "Turing": 361, "Brainfuck": 34, "mupad": 402, "Csound": 69, "DIGITAL Command Language": 78, "INI": 155, "PicoLisp": 277, "Latte": 188, "Zephir": 396, "Swift": 348, "C++": 39, "LSL": 185, "Bro": 36, "ECL": 89, "Matlab": 217, "CSV": 47, "Cython": 75, "Sass": 327, "Nu": 245, "SPARQL": 319, "Game Maker Language": 117, "ooc": 404, "Turtle": 362, "Opal": 254, "Smalltalk": 339, "Textile": 359, "Text": 358, "LilyPond": 192, "Kotlin": 181, "SMT": 318, "Jasmin": 172, "RHTML": 302, "fish": 401, "JSX": 170, "Rust": 315, "JSONLD": 168, "Nimrod": 241, "GraphQL": 131, "Slash": 336, "R": 298, "Gentoo Eclass": 120, "Metal": 222, "Clean": 56, "Graphviz (DOT)": 132, "HTML+Django": 139, "XC": 384, "ABAP": 0, "Ant Build System": 13, "HCL": 136, "Objective-J": 251, "Literate Haskell": 199, "Xtend": 392, "Markdown": 214, "XML": 385, "Cool": 64, "Cpp-ObjDump": 66, "Creole": 67, "Pickle": 276, "Dogescript": 86, "HTML+ECR": 140, "MUF": 211, "Wavefront Material": 378, "Chapel": 51, "Objective-C++": 250, "PigLatin": 278, "Myghty": 231, "Bluespec": 32, "WebIDL": 381, "OpenEdge ABL": 256, "REALbasic": 301, "FORTRAN": 102, "Literate CoffeeScript": 198, "CLIPS": 42, "Makefile": 212, "Propeller Spin": 287, "Component Pascal": 63, "TLA": 350, "Pure Data": 291, "API Blueprint": 4, "Tcsh": 354, "Haxe": 150, "SaltStack": 326, "OpenSCAD": 258, "Xojo": 391, "Darcs Patch": 82, "Pascal": 273, "Click": 57, "Yacc": 395, "SCSS": 317, "Cycript": 74, "Monkey": 228, "Cuda": 73, "Ada": 9, "Grace": 127, "Graph Modeling Language": 130, "Pike": 279, "Red": 308, "Rebol": 307, "Gnuplot": 123, "APL": 5, "Processing": 285, "AGS Script": 1, "Liquid": 196, "Alloy": 11, "XPages": 386, "Terra": 357, "Pod": 280, "Groovy Server Pages": 135, "Parrot": 270, "Augeas": 22, "TXL": 352, "RenderScript": 311, "Visual Basic": 375, "Nix": 244, "BlitzBasic": 30, "Cucumber": 72, "Cirru": 54, "Scala": 328, "Scaml": 329, "Vue": 377, "OpenRC runscript": 257, "JFlex": 165, "YAML": 393, "Verilog": 373, "Ceylon": 50, "SQF": 320, "XProc": 387, "Papyrus": 269, "ApacheConf": 14, "Objective-C": 249, "NCL": 232, "E": 88, "Filterscript": 106, "Coq": 65, "Gettext Catalog": 121, "Idris": 157, "MTML": 210, "Apex": 15, "Golo": 125, "NetLinx": 236, "PostScript": 283, "BlitzMax": 31, "GDScript": 115, "ANTLR": 3, "Module Management System": 227, "Modula-2": 226, "HTML": 138, "Mirah": 224, "Dockerfile": 85, "M": 206, "Dylan": 87, "QML": 296, "Glyph": 122, "D-ObjDump": 77, "Ecere Projects": 93, "SourcePawn": 341, "D": 76, "RDoc": 300, "Java": 173, "Tcl": 353, "PLSQL": 265, "Web Ontology Language": 380, "LLVM": 183, "Assembly": 21, "IGOR Pro": 154, "PureBasic": 292, "COBOL": 44, "MAXScript": 209, "IRC log": 156, "UnrealScript": 368, "Dart": 83, "SVG": 324, "COLLADA": 45, "CMake": 43, "G-code": 111, "Modelica": 225, "Genshi": 118, "Batchfile": 26, "RobotFramework": 312, "Handlebars": 147, "Csound Score": 71, "GAP": 113, "Wavefront Object": 379, "Perl6": 275, "DM": 79, "Brightscript": 35, "Mask": 215, "UrWeb": 369, "NSIS": 234, "Lasso": 187, "Oz": 262, "Squirrel": 342, "Standard ML": 344, "Go": 124, "PHP": 264, "EJS": 91, "wisp": 406, "PLpgSQL": 266, "ECLiPSe": 90, "Pony": 282, "KiCad": 179, "ShellSession": 334, "F#": 100, "SQLPL": 322, "Inno Setup": 159, "CSS": 46, "HTML+ERB": 142, "SuperCollider": 347, "LoomScript": 204, "Awk": 25, "Lua": 205, "QMake": 297, "ChucK": 53, "reStructuredText": 405, "AsciiDoc": 19, "SAS": 316, "Parrot Assembly": 271, "OCaml": 247, "Nemerle": 235, "Public Key": 289, "Mercury": 221, "C#": 38, "nesC": 403, "Cap\"n Proto": 48, "Hack": 145, "Eagle": 92, "Redcode": 309, "RAML": 299, "Ren\"Py": 310, "XS": 389, "Hy": 151, "TeX": 355, "Scilab": 331, "M4": 207, "Smali": 338, "PowerShell": 284, "Shen": 335, "NewLisp": 239, "ColdFusion": 60, "Befunge": 27, "C-ObjDump": 40, "Julia": 176, "Harbour": 148, "Boo": 33, "Rouge": 313, "MoonScript": 230, "Jupyter Notebook": 177, "NumPy": 246, "Scheme": 330, "Bison": 28, "Agda": 10, "Arc": 17, "Clojure": 58, "SQL": 321, "Parrot Internal Representation": 272, "HyPhy": 152, "LOLCODE": 184, "Charity": 52, "Fantom": 105, "OpenCL": 255, "Org": 259, "EmberScript": 98, "ASP": 6, "VimL": 374, "GAS": 114, "Alpine Abuild": 12, "Mako": 213, "XQuery": 388, "Groovy": 134, "M4Sugar": 208, "Groff": 133, "Ragel in Ruby Host": 305, "ColdFusion CFC": 61, "Volt": 376, "Linux Kernel Module": 195, "Unified Parallel C": 365, "STON": 323, "LFE": 182, "Tea": 356, "GAMS": 112, "Racket": 304, "JSONiq": 169, "TOML": 351, "JSON": 166, "Gentoo Ebuild": 119, "XSLT": 390, "Erlang": 99, "Nit": 243, "Kit": 180, "Self": 332, "Literate Agda": 197, "FLUX": 101, "AutoIt": 24, "Shell": 333, "NetLinx+ERB": 237, "Maven POM": 218}


def cook(dev):
    p = {k: dev.get(k) for k in FIELDS}
    p["id"] = str(dev["_id"])
    return p


def tsne(raw_data):
    logger = logging.getLogger("tsne")
    features = numpy.zeros((len(raw_data), len(LANGUAGES)))
    for i, dev in enumerate(raw_data):
        for lang, stats in dev["skills"]["languages"].items():
            if lang == "Other":
                continue
            try:
                li = LANGUAGES[lang]
            except KeyError:
                logger.warning("\"%s\" not found for %s", lang, dev["id"])
                continue
            features[i, li] = numpy.log(max(stats["agedbytes"], 1)) - 1
    model = TSNE(random_state=777)
    positions = model.fit_transform(features)
    positions /= numpy.max(numpy.abs(positions))
    return [(p[0], p[1]) for p in positions]


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
    try:
        cluster = bp.reversed_clusters[int(str(devobj["_id"]), 16)]
    except KeyError:
        return "", 404
    others = bp.clusters[cluster]
    neighbors = bp.db.find({"_id": {"$in": [ObjectId(hex(i)[2:]) for i in others]}},
                           projection=FIELDS)
    data = [cook(n) for n in neighbors]
    data.sort(key=lambda d: d["id"])
    result = {"nodes": data, "tsne": tsne(data)}
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
    collection = getattr(db, config["collection"])
    return collection


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
