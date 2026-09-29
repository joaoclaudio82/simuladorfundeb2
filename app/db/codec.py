"""Snapshots portáveis: JSON + Arrow IPC, sem executar pickle ao ler o banco."""

from dataclasses import fields
from io import BytesIO
import hashlib
import json
import math
import zipfile
import numpy as np
import pandas as pd
import pyarrow as pa


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_dumps(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def pack(value):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        counter = [0]

        def write(name, data):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)

        def encode(obj):
            if isinstance(obj, pd.DataFrame):
                name = f"tables/{counter[0]}.arrow"
                counter[0] += 1
                table = pa.Table.from_pandas(obj)
                sink = pa.BufferOutputStream()
                with pa.ipc.new_file(sink, table.schema) as writer:
                    writer.write_table(table)
                write(name, sink.getvalue().to_pybytes())

                def dtype_info(dtype):
                    if isinstance(dtype, pd.CategoricalDtype):
                        return {
                            "kind": "category",
                            "values": encode(dtype.categories.tolist()),
                            "dtype": dtype_info(dtype.categories.dtype),
                            "ordered": dtype.ordered,
                        }
                    if isinstance(dtype, pd.StringDtype):
                        return {
                            "kind": "string",
                            "storage": dtype.storage,
                            "na": "NA" if dtype.na_value is pd.NA else "nan",
                        }
                    return {"kind": "dtype", "value": str(dtype)}

                nulls = []
                for col_pos, dtype in enumerate(obj.dtypes):
                    if dtype == object:
                        for row_pos, value in enumerate(obj.iloc[:, col_pos]):
                            if value is None:
                                nulls.append([row_pos, col_pos, "None"])
                            elif value is pd.NA:
                                nulls.append([row_pos, col_pos, "NA"])
                            elif value is pd.NaT:
                                nulls.append([row_pos, col_pos, "NaT"])
                            elif isinstance(value, float) and math.isnan(value):
                                nulls.append([row_pos, col_pos, "nan"])
                return {
                    "type": "frame",
                    "file": name,
                    "dtypes": [dtype_info(dtype) for dtype in obj.dtypes],
                    "index_dtypes": [
                        dtype_info(obj.index.get_level_values(i).dtype)
                        for i in range(obj.index.nlevels)
                    ],
                    "column_dtypes": [
                        dtype_info(obj.columns.get_level_values(i).dtype)
                        for i in range(obj.columns.nlevels)
                    ],
                    "nulls": nulls,
                    "attrs": encode(obj.attrs),
                }
            if isinstance(obj, dict):
                return {"type": "dict", "items": [[encode(k), encode(v)] for k, v in obj.items()]}
            if isinstance(obj, (list, tuple)):
                return {
                    "type": "tuple" if isinstance(obj, tuple) else "list",
                    "items": [encode(v) for v in obj],
                }
            if isinstance(obj, np.generic):
                obj = obj.item()
            if isinstance(obj, float) and not math.isfinite(obj):
                return {"type": "float", "value": repr(obj)}
            if obj is None or isinstance(obj, (str, bool, int, float)):
                return {"type": "scalar", "value": obj}
            raise TypeError(f"Tipo não suportado no snapshot: {type(obj).__name__}")

        manifest = {"format": "fundeb-snapshot-v1", "value": encode(value)}
        write("manifest.json", json_dumps(manifest).encode())
    return stream.getvalue()


def unpack(data, expected_hash=None):
    if expected_hash and sha256(data) != expected_hash:
        raise ValueError("Snapshot corrompido: SHA-256 divergente.")
    with zipfile.ZipFile(BytesIO(data)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest["format"] != "fundeb-snapshot-v1":
            raise ValueError("Formato de snapshot desconhecido.")

        def decode(obj):
            kind = obj["type"]
            if kind == "frame":
                table = pa.ipc.open_file(pa.BufferReader(archive.read(obj["file"]))).read_all()
                if "dtypes" not in obj:
                    return table.to_pandas()
                # pandas 3 infers StringDtype for object strings: preserve the original explicit dtype.
                with pd.option_context("future.infer_string", False):
                    frame = table.to_pandas()

                def dtype_from(info):
                    if info["kind"] == "category":
                        return pd.CategoricalDtype(
                            pd.Index(decode(info["values"]), dtype=dtype_from(info["dtype"])),
                            ordered=info["ordered"],
                        )
                    if info["kind"] == "string":
                        return pd.StringDtype(
                            storage=info["storage"],
                            na_value=pd.NA if info["na"] == "NA" else np.nan,
                        )
                    return info["value"]

                for pos, info in enumerate(obj["dtypes"]):
                    dtype = dtype_from(info)
                    if isinstance(dtype, pd.CategoricalDtype):
                        values = pd.Categorical.from_codes(
                            frame.iloc[:, pos].cat.codes.to_numpy(), dtype=dtype
                        )
                    else:
                        values = frame.iloc[:, pos].astype(dtype)
                    frame.isetitem(pos, values)
                markers = {"None": None, "NA": pd.NA, "NaT": pd.NaT, "nan": float("nan")}
                for row, col, marker in obj["nulls"]:
                    frame.iat[row, col] = markers[marker]
                if not isinstance(frame.index, pd.RangeIndex):
                    if frame.index.nlevels == 1:
                        frame.index = frame.index.astype(dtype_from(obj["index_dtypes"][0]))
                    else:
                        frame.index = pd.MultiIndex.from_arrays(
                            [
                                frame.index.get_level_values(i).astype(dtype_from(info))
                                for i, info in enumerate(obj["index_dtypes"])
                            ],
                            names=frame.index.names,
                        )
                if frame.columns.nlevels == 1:
                    frame.columns = frame.columns.astype(dtype_from(obj["column_dtypes"][0]))
                else:
                    frame.columns = pd.MultiIndex.from_arrays(
                        [
                            frame.columns.get_level_values(i).astype(dtype_from(info))
                            for i, info in enumerate(obj["column_dtypes"])
                        ],
                        names=frame.columns.names,
                    )
                frame.attrs = decode(obj["attrs"])
                return frame
            if kind == "dict":
                return {decode(k): decode(v) for k, v in obj["items"]}
            if kind in ("list", "tuple"):
                values = [decode(v) for v in obj["items"]]
                return tuple(values) if kind == "tuple" else values
            if kind == "float":
                return float(obj["value"])
            if kind == "scalar":
                return obj["value"]
            raise ValueError("Tipo inválido no snapshot.")

        return decode(manifest["value"])


def dataclass_values(obj):
    return {f.name: getattr(obj, f.name) for f in fields(obj)}
