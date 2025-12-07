import streamlit as st
import pandas as pd
import numpy as np
import json

st.set_page_config(page_title="PAPL Comparison Dashboard", layout="wide")
st.title("📘 PAPL Comparison Dashboard")


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def find_all_lists(obj):
    found = []
    if isinstance(obj, list):
        found.append(obj)
        for item in obj:
            found.extend(find_all_lists(item))
    elif isinstance(obj, dict):
        for v in obj.values():
            found.extend(find_all_lists(v))
    return found


def is_price_row(entry):
    return (
        isinstance(entry, dict)
        and "old_price" in entry
        and "new_price" in entry
        and "item_number" in entry
    )


def extract_price_rows(root):
    all_lists = find_all_lists(root)
    price_lists = []

    for lst in all_lists:
        if isinstance(lst, list) and any(is_price_row(x) for x in lst):
            price_lists.append(lst)

    flattened = []
    for lst in price_lists:
        flattened.extend([x for x in lst if is_price_row(x)])

    return flattened


# ---------------------------------------------------------
# UPLOAD
# ---------------------------------------------------------
uploaded_file = st.file_uploader("Upload PAPL comparison JSON", type=["json"])
if not uploaded_file:
    st.stop()

raw = json.load(uploaded_file)
price_rows = extract_price_rows(raw)

if len(price_rows) == 0:
    st.error("❌ No price rows found anywhere in the JSON.")
    st.json(raw)
    st.stop()

df = pd.DataFrame(price_rows)

# Ensure required fields exist
for col in ["difference", "percent_change", "item_description"]:
    if col not in df.columns:
        df[col] = np.nan


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------
st.subheader("Summary of Price Changes")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Items", len(df))
col2.metric("Increases", int((df["difference"] > 0).sum()))
col3.metric("Decreases", int((df["difference"] < 0).sum()))
col4.metric("No Change", int((df["difference"] == 0).sum()))


# ---------------------------------------------------------
# THRESHOLD FILTER
# ---------------------------------------------------------
st.subheader("Filter Price Changes by Threshold")

threshold = st.slider(
    "Show items where ABS(percent change) ≥ threshold (%)",
    min_value=0,
    max_value=100,
    value=5,
    step=1,
)

significant = df[df["percent_change"].abs() >= threshold]

st.write(f"### Items with ≥ {threshold}% Change ({len(significant)} items found)")

st.dataframe(
    significant[
        [
            "item_number",
            "item_description",
            "old_price",
            "new_price",
            "difference",
            "percent_change",
        ]
    ],
    use_container_width=True
)


# ---------------------------------------------------------
# DRILL-DOWN
# ---------------------------------------------------------
st.subheader("Item Drill-Down")

if len(significant) > 0:
    selected = st.selectbox(
        "Select an item to inspect",
        significant["item_number"].unique()
    )

    row = significant[significant["item_number"] == selected].iloc[0]

    st.markdown(f"### {row['item_number']}: {row['item_description']}")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Old Price", f"${row['old_price']}")
        st.metric("New Price", f"${row['new_price']}")
        st.metric("Difference", round(row["difference"], 2))
        st.metric("Percent Change", f"{round(row['percent_change'], 2)}%")

    with c2:
        st.write("**Old Location**")
        st.json(row.get("old_location", {}))
        st.write("**New Location**")
        st.json(row.get("new_location", {}))

    with st.expander("Raw JSON"):
        st.json(row.to_dict())

else:
    st.info("No items meet the threshold.")
