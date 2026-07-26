from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from ovc.research_operations.read_model import ResearchReadModel, ReadModelNode


st.set_page_config(page_title="OVC Research Console", layout="wide")
st.title("OVC Research Console")
st.caption("RO-WP3 · read-only typed read model · no market, selector, threshold or execution authority")

model_path = Path(os.environ.get("OVC_RESEARCH_READ_MODEL", "var/research_operations/read_model/current.json"))
if not model_path.is_file():
    st.warning(f"Read model unavailable: {model_path}")
    st.stop()

raw = json.loads(model_path.read_text(encoding="utf-8"))
model = ResearchReadModel(
    schema=raw["schema"],
    source_commit=raw["source_commit"],
    catalogue_sha256=raw.get("catalogue_sha256"),
    nodes=tuple(ReadModelNode(**{**node, "source_refs": tuple(node.get("source_refs", []))}) for node in raw.get("nodes", [])),
    health=tuple(raw.get("health", [])),
    logical_sha256=raw["logical_sha256"],
)

st.code(f"source_commit={model.source_commit}\nread_model_sha256={model.logical_sha256}")
left, right = st.columns(2)
left.metric("Indexed objects", len(model.nodes))
right.metric("Health signals", len(model.health))

st.subheader("Authority boundary")
st.json({
    "mode": "READ_ONLY",
    "repository_mutation": "NONE",
    "selector_mutation": "NONE",
    "threshold_mutation": "NONE",
    "market_classification": "NONE",
    "probability": "NONE",
    "exposure": "NONE",
    "execution": "NONE",
    "agent": "NONE",
})

st.subheader("Health")
st.dataframe(list(model.health), use_container_width=True)

st.subheader("Research objects and lineage")
object_type = st.selectbox("Object type", ["ALL"] + sorted({node.object_type for node in model.nodes}))
rows = [node.to_dict() for node in model.nodes if object_type == "ALL" or node.object_type == object_type]
st.dataframe(rows, use_container_width=True)
