"""Reads configuration from Streamlit secrets, falling back to environment variables."""

import os

import streamlit as st


def secret(name: str) -> str:
    try:
        return st.secrets.get(name, "") or os.environ.get(name, "")
    except Exception:  # no secrets.toml
        return os.environ.get(name, "")
