"""Portable Version 4 validation serialization."""
from __future__ import annotations
import csv,json
from datetime import datetime,timezone
from pathlib import Path

def validation_id(prefix,seed):
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+f"-{prefix}-s{seed}"

def _csv_bytes(rows):
    if not rows:return b""
    from io import StringIO
    stream=StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:writer.writerow({key:json.dumps(value,sort_keys=True) if isinstance(value,(dict,list)) else value for key,value in row.items()})
    return stream.getvalue().encode("utf-8")

def serialize_outputs(files):
    result={}
    for name,value in files.items():
        if isinstance(value,bytes):result[name]=value
        elif name.endswith(".csv"):result[name]=_csv_bytes(value)
        elif name.endswith(".md"):result[name]=str(value).encode("utf-8")
        else:result[name]=json.dumps(value,indent=2,sort_keys=True,default=str).encode("utf-8")
    return result

def save_validation_outputs(files,output_dir,identifier):
    destination=Path(output_dir)/identifier;destination.mkdir(parents=True,exist_ok=False)
    binary=serialize_outputs(files)
    for name,value in binary.items():(destination/name).write_bytes(value)
    return destination,binary
